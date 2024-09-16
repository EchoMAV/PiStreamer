#!/usr/bin/env python3

from typing import Any
from picamera2 import Picamera2
import cv2
import numpy as np
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
import sys
from command_model import (
    get_pending_command,
    initialize_db,
    update_command_status_failure,
    update_command_status,
)
from constants import (
    DEFAULT_CONFIG_PATH,
    FRAMERATE,
    STABILIZATION_FRAMESIZE,
    STREAMING_FRAMESIZE,
    CommandStatus,
    STILL_FRAMESIZE,
)
from validator import Validator


class PiStreamer2:
    def __init__(
        self,
        stabilize: bool,
        resolution: str,
        destination_ip: str,
        destination_port: int,
        streaming_bitrate: int,
    ) -> None:
        self.stabilize = stabilize
        self.prev_gray = None
        if self.stabilize:
            resolution = STABILIZATION_FRAMESIZE
            print(
                f"Forcing resolution to {STABILIZATION_FRAMESIZE} for stabilization performance."
            )
        self.resolution = tuple(map(int, resolution.split("x")))
        self.command_controller = None  # set later
        self.destination_ip = destination_ip
        self.destination_port = destination_port
        self.ffmpeg_process_mp4 = None
        self.ffmpeg_process_rtp = None
        self.streaming_bitrate = streaming_bitrate
        self.original_size = (0, 0)
        self.is_recording = False
        self.recording_start_time = 0
        tuning = Picamera2.load_tuning_file(Path("./477-Pi4.json").resolve())
        self.picam2 = Picamera2(tuning=tuning)
        self.streaming_config = self.picam2.create_preview_configuration(
            main={"size": self.resolution}
        )
        self.photo_config = self.picam2.create_preview_configuration(
            main={"size": tuple(map(int, STILL_FRAMESIZE.split("x")))}
        )

    def _get_timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def _init_ffmpeg_processes(self) -> None:
        """
        Used to configure both the rtp and mp4 FFmpeg commands.
        """
        self._close_ffmpeg_processes()

        # Used for saving data to disk
        self.ffmpeg_command_mp4 = [
            "ffmpeg",
            "-y",  # Overwrite output files without asking
            "-f",
            "rawvideo",  # Input format
            "-pix_fmt",
            "yuv420p",  # Pixel format
            "-s",
            f"{self.resolution[0]}x{self.resolution[1]}",  # Frame size
            "-r",
            str(FRAMERATE),  # Frame rate
            "-i",
            "-",  # Input from stdin
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",  # Add silent audio track
            "-shortest",  # Ensure the shortest stream ends the output
            "-c:v",
            "h264_v4l2m2m",  # Hardware acceleration
            "-preset",
            "ultrafast",  # Faster encoding
            "-tune",
            "zerolatency",  # Tune for low latency
            "-b:v",
            "1M",  # Video bitrate
            "-movflags",
            "+faststart",  # Prepare the file for playback
            "-f",
            "mp4",  # Save to mp4
            f"{self._get_timestamp()}.mp4",  # Output file pattern
        ]

        # Used for streaming video to GCS
        self.ffmpeg_command_rtp = [
            "ffmpeg",
            "-y",  # Overwrite output files without asking
            "-f",
            "rawvideo",  # Input format
            "-pix_fmt",
            "yuv420p",  # Pixel format
            "-s",
            f"{self.resolution[0]}x{self.resolution[1]}",  # Frame size
            "-r",
            str(FRAMERATE),  # Frame rate
            "-i",
            "-",  # Input from stdin
            "-c:v",
            "h264_v4l2m2m",  # Hardware acceleration
            "-preset",
            "ultrafast",  # Faster encoding
            "-tune",
            "zerolatency",  # Tune for low latency
            "-bufsize",
            "64k",  # Reduce buffer size
            "-b:v",
            str(self.streaming_bitrate),  # Set video bitrate
            "-flags",
            "low_delay",  # Low delay for RTP
            "-fflags",
            "nobuffer",  # No buffer for RTP
            "-f",
            "rtp",  # Output format for RTP
            f"rtp://{self.destination_ip}:{self.destination_port}",
        ]

        # Start the FFmpeg processes (mp4 only if we are recording)
        self.ffmpeg_process_rtp = subprocess.Popen(
            self.ffmpeg_command_rtp, stdin=subprocess.PIPE
        )

    def __del__(self):
        self.stop_and_clean_all()

    def _set_command_controller(self, command_controller: Any) -> None:
        """
        Circular reference setter.
        """
        from command_controller import CommandController

        self.command_controller: CommandController = command_controller

    def _stabilize(self, frame: np.ndarray) -> np.ndarray:
        """
        This method takes a frame and performs image stabilization algorithms on it.
        The original frame is returned if the stabilization fails. Otherwise, the
        stabilized frame is returned.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        # Apply opencv stabilization algorithms
        p0 = cv2.goodFeaturesToTrack(
            self.prev_gray, maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7
        )
        if p0 is None:
            print("No good features to track, skipping...")
            self.prev_gray = gray
            return frame

        p1, st, err = cv2.calcOpticalFlowPyrLK(self.prev_gray, gray, p0, None)
        if p1 is None or st is None:
            print(f"Optical flow calculation failed, skipping... {err}")
            self.prev_gray = gray
            return frame

        # Select good points
        good_new = p1[st == 1]
        good_old = p0[st == 1]

        # Calculate the transformation matrix
        dx = np.mean(good_new[:, 0] - good_old[:, 0])
        dy = np.mean(good_new[:, 1] - good_old[:, 1])
        transform = np.array([[1, 0, -dx], [0, 1, -dy]], dtype=np.float32)

        # Apply the transformation
        try:
            # BORDER_REPLICATE prevents the distracting black edges from forming
            stabilized_frame = cv2.warpAffine(
                frame, transform, self.resolution, borderMode=cv2.BORDER_REPLICATE
            )
        except cv2.error as e:
            print(f"Error applying warpAffine: {e}")
            stabilized_frame = frame

        # Update the previous frame and gray image
        self.prev_gray = gray

        return stabilized_frame

    def start_recording(self) -> None:
        if self.is_recording:
            print("Already recording...")
            return
        self.recording_start_time = time.time()
        self.ffmpeg_process_mp4 = subprocess.Popen(
            self.ffmpeg_command_mp4, stdin=subprocess.PIPE
        )
        self.is_recording = True

    def stop_recording(self) -> None:
        self.is_recording = False
        if self.ffmpeg_process_mp4:
            print("Stopping recording...")
            if self.ffmpeg_process_mp4.stdin:
                self.ffmpeg_process_mp4.stdin.close()
            self.ffmpeg_process_mp4.wait()

    def take_photo(self) -> None:
        """
        Since photos are taken at higher resolution than streaming, the picam2 must stop and
        be reconfigured before the photo can be taken. Once taken, the streaming config is reapplied.
        """
        self.picam2.stop()
        self.picam2.configure(self.photo_config)
        self.picam2.start()
        self.picam2.capture_file(f"{self._get_timestamp()}.jpg")
        self.picam2.stop()
        self.picam2.configure(self.streaming_config)
        self.picam2.start()

    def _format_duration(self, seconds: int) -> str:
        """Convert a duration in seconds to a minutes:seconds format."""
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:02d}"

    def _draw_rec(self, frame: np.ndarray) -> np.ndarray:
        """
        Paints "REC" on the top of the rtp stream (but not the mp4).
        """
        text = (
            f"REC {self._format_duration(int(time.time() - self.recording_start_time))}"
        )
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.75
        color = (255, 0, 0)
        thickness = 2
        line_type = cv2.LINE_AA
        # Get the text size to calculate the center position
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2  # Centered along width
        text_y = text_size[1] + 10  # Just below the top
        cv2.putText(
            frame, text, (text_x, text_y), font, font_scale, color, thickness, line_type
        )
        return frame

    def _close_ffmpeg_processes(self) -> None:
        self.stop_recording()
        if self.ffmpeg_process_rtp:
            if self.ffmpeg_process_rtp.stdin:
                self.ffmpeg_process_rtp.stdin.close()
            self.ffmpeg_process_rtp.wait()

    def stop_and_clean_all(self) -> None:
        print("Stopping and cleaning camera resources...")
        if self.picam2:
            self.picam2.stop()
        cv2.destroyAllWindows()
        self._close_ffmpeg_processes()

    def _read_and_process_commands(self) -> None:
        command = get_pending_command()
        if command:
            try:
                self.command_controller.handle_command(command)
                update_command_status(
                    command_id=command.id, new_status=CommandStatus.COMPLETED.value
                )
            except Exception as e:
                msg = f"Error processing command: {e}"
                print(msg)
                update_command_status_failure(command_id=command.id, meta_data=msg)

    def stream(self) -> None:
        # Start the ffmpeg processes
        self._init_ffmpeg_processes()
        # Start the camera
        self.picam2.configure(self.streaming_config)
        self.picam2.start()
        self.original_size = self.picam2.capture_metadata()["ScalerCrop"][2:]

        # Init frame
        fps = []
        init_frame = self.picam2.capture_array()
        if self.stabilize:
            self.prev_gray = cv2.cvtColor(init_frame, cv2.COLOR_RGB2GRAY)

        # Main loop
        try:
            i = 0
            startt = time.perf_counter()
            while True:
                frame = self.picam2.capture_array()

                if frame is None or frame.size == 0:
                    print("Empty frame captured, skipping...")
                    continue

                i += 1
                if i % 2 == 0:
                    self._read_and_process_commands()

                # Calculate fps
                if i == 10:
                    elapsed_time = time.perf_counter() - startt
                    startt = time.perf_counter()
                    fps.append(10 / elapsed_time)
                    print(f"fps={10/elapsed_time} | ")
                    i = 0

                if self.stabilize:
                    frame = self._stabilize(frame)

                # Convert the frame back to YUV format before sending to FFmpeg
                frame_8bit = cv2.convertScaleAbs(frame)
                frame_yuv = cv2.cvtColor(frame_8bit, cv2.COLOR_RGB2YUV_I420)

                # Forward the stabilized frame to rtp
                if self.is_recording:
                    # mp4 should not have 'REC' appearing in the frame
                    self.ffmpeg_process_mp4.stdin.write(frame_yuv.tobytes())
                    frame_8bit_rec = self._draw_rec(frame_8bit)
                    frame_yuv = cv2.cvtColor(frame_8bit_rec, cv2.COLOR_RGB2YUV_I420)

                self.ffmpeg_process_rtp.stdin.write(frame_yuv.tobytes())

                # Break the loop on 'q' key press
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            self.stop_and_clean_all()
            print(f"\n\nAverage FPS = {sum(fps)/len(fps)}\n\n")


if __name__ == "__main__":
    # Argument parsing
    initialize_db()
    parser = argparse.ArgumentParser(description="Video stabilization script.")
    parser.add_argument("--stabilize", action="store_true", help="Whether to stabilize")
    parser.add_argument(
        "--resolution",
        type=str,
        default=STREAMING_FRAMESIZE,
        help="Resolution of the video frames (e.g., 1280x720)",
    )
    parser.add_argument(
        "--destination_ip",
        type=str,
        default="192.168.1.124",
        help="Destination IP address for RTP stream",
    )
    parser.add_argument(
        "--destination_port",
        type=int,
        default=5600,
        help="Destination port for RTP stream",
    )
    parser.add_argument(
        "--bitrate", type=int, default=2000000, help="Streaming bitrate in bps"
    )
    parser.add_argument(
        "--config_file",
        type=str,
        default=DEFAULT_CONFIG_PATH,
        help="Relative file path for the IMX477 config json file",
    )
    args = parser.parse_args()
    try:
        Validator(args)
    except Exception as e:
        print(f"Validation Error: {e}")
        sys.exit(1)
    pi_streamer = PiStreamer2(
        args.stabilize,
        args.resolution,
        args.destination_ip,
        args.destination_port,
        args.bitrate,
    )
    from command_controller import CommandController

    controller = CommandController(pi_streamer)
    pi_streamer.stream()
