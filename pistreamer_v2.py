#!/usr/bin/env python3

from typing import Any, Optional, Union
from ffmpeg_configs import (
    get_ffmpeg_command_atak,
    get_ffmpeg_command_mp4,
    get_ffmpeg_command_rtp,
)
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
from utils import get_timestamp
from validator import Validator


class PiStreamer2:
    def __init__(
        self,
        stabilize: bool,
        resolution: str,
        destination_ip: str,
        destination_port: int,
        streaming_bitrate: int,
        atak_ip: Optional[str] = None,
        atak_port: Optional[Union[str, int]] = None,
    ) -> None:
        from command_controller import CommandController

        self.stabilize = stabilize
        self.prev_gray = None
        if self.stabilize:
            resolution = STABILIZATION_FRAMESIZE
            print(
                f"Forcing resolution to {STABILIZATION_FRAMESIZE} for stabilization performance."
            )
        self.resolution = tuple(map(int, resolution.split("x")))
        self.command_controller: CommandController = None  # type: ignore # this is set later in _set_command_controller
        self.destination_ip = destination_ip
        self.destination_port = destination_port
        self.atak_ip = atak_ip
        self.atak_port = atak_port
        self.ffmpeg_process_mp4 = None
        self.ffmpeg_process_rtp = None
        self.ffmpeg_process_atak = None
        self.streaming_bitrate = streaming_bitrate
        self.original_size = (0, 0)
        self.is_recording = False
        self.is_atak_streaming = False
        self.recording_start_time = 0
        tuning = Picamera2.load_tuning_file(Path("./477-Pi4.json").resolve())
        self.picam2 = Picamera2(tuning=tuning)
        self.streaming_config = self.picam2.create_preview_configuration(
            main={"size": self.resolution}
        )
        self.photo_config = self.picam2.create_preview_configuration(
            main={"size": tuple(map(int, STILL_FRAMESIZE.split("x")))}
        )

    def _init_ffmpeg_processes(self) -> None:
        """
        Used to configure both the rtp and mp4 FFmpeg commands.
        """
        self._close_ffmpeg_processes()

        self.ffmpeg_command_mp4 = get_ffmpeg_command_mp4(
            self.resolution, str(FRAMERATE)
        )
        self.ffmpeg_command_rtp = get_ffmpeg_command_rtp(
            self.resolution,
            str(FRAMERATE),
            self.destination_ip,
            str(self.destination_port),
            str(self.streaming_bitrate),
        )
        if self.atak_ip and self.atak_port:
            self.ffmpeg_command_atak = get_ffmpeg_command_atak(
                self.resolution,
                str(FRAMERATE),
                self.atak_ip,
                str(self.atak_port),
                str(self.streaming_bitrate),
            )
        else:
            self.ffmpeg_command_atak = None

        # Start the RTP FFmpeg process only (mp4 and/or ATAK only if activated)
        self.ffmpeg_process_rtp = subprocess.Popen(  # type: ignore
            self.ffmpeg_command_rtp, stdin=subprocess.PIPE
        )

    def __del__(self):
        self.stop_and_clean_all()

    def _set_command_controller(self, command_controller: Any) -> None:
        """
        Circular reference setter.
        """
        self.command_controller = command_controller

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
        self.recording_start_time = int(time.time())
        self.ffmpeg_process_mp4 = subprocess.Popen(  # type: ignore
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

    def start_atak_stream(self, ip: str, port: str) -> None:
        if self.is_atak_streaming:
            print("Already ATAK streaming...")
            return
        self.atak_ip = ip
        self.atak_port = port
        self.ffmpeg_command_atak = get_ffmpeg_command_atak(
            self.resolution,
            str(FRAMERATE),
            self.atak_ip,
            str(self.atak_port),
            str(self.streaming_bitrate),
        )
        self.ffmpeg_process_atak = subprocess.Popen(  # type: ignore
            self.ffmpeg_command_atak, stdin=subprocess.PIPE
        )
        self.is_atak_streaming = True

    def stop_atak_stream(self) -> None:
        self.is_atak_streaming = False
        if self.ffmpeg_process_atak:
            print("Stopping ATAK streaming...")
            if self.ffmpeg_process_atak.stdin:
                self.ffmpeg_process_atak.stdin.close()
            self.ffmpeg_process_atak.wait()

    def take_photo(self) -> None:
        """
        Since photos are taken at higher resolution than streaming, the picam2 must stop and
        be reconfigured before the photo can be taken. Once taken, the streaming config is reapplied.
        """
        self.picam2.stop()
        self.picam2.configure(self.photo_config)
        self.picam2.start()
        self.picam2.capture_file(f"{get_timestamp()}.jpg")
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
        if command and self.command_controller:
            try:
                self.command_controller.handle_command(command)
                update_command_status(
                    command_id=str(command.id), new_status=CommandStatus.COMPLETED
                )
            except Exception as e:
                msg = f"Error processing command: {e}"
                print(msg)
                update_command_status_failure(command_id=str(command.id), meta_data=msg)

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
                    self.ffmpeg_process_mp4.stdin.write(frame_yuv.tobytes())  # type: ignore
                    frame_8bit_rec = self._draw_rec(frame_8bit)
                    frame_yuv = cv2.cvtColor(frame_8bit_rec, cv2.COLOR_RGB2YUV_I420)

                self.ffmpeg_process_rtp.stdin.write(frame_yuv.tobytes())  # type: ignore

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
        "--atak_ip",
        type=str,
        null=True,
        help="Destination ATAK IP address for RTP stream",
    )
    parser.add_argument(
        "--atak_port",
        type=int,
        null=True,
        help="Destination ATAK port for RTP stream",
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
