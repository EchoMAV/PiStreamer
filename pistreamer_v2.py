#!/usr/bin/env python3

from typing import Any, Optional, Union
from command_service import CommandService
from ffmpeg_configs import (
    get_ffmpeg_command_atak,
    get_ffmpeg_command_record,
    get_ffmpeg_command_qgc,
)
import os
from pathlib import Path
from picamera2 import Picamera2
import cv2
import numpy as np
import time
import subprocess
import argparse
from pathlib import Path
import sys
from constants import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_MAX_ZOOM,
    FRAMERATE,
    INIT_BBOX_COLOR,
    MEDIA_FILES_DIRECTORY,
    MIN_ZOOM,
    STREAMING_FRAMESIZE,
    STILL_FRAMESIZE,
    GCSType,
    TrackStatus,
    ZoomStatus,
)
from object_tracker import ObjectTracker
from cam_utils import get_timestamp
from validator import Validator


class PiStreamer2:
    def __init__(
        self,
        stabilize: bool,
        resolution: str,
        streaming_bitrate: int,
        qgc_ip: Optional[str] = None,
        qgc_port: Optional[str] = None,
        atak_ip: Optional[str] = None,
        atak_port: Optional[Union[str, int]] = None,
        config_file: str = "./477-Pi4.json",
        verbose: bool = False,
        max_zoom: float = DEFAULT_MAX_ZOOM,
        active_gcs: str = GCSType.QGC.value,
    ) -> None:
        # utilities
        from command_controller import CommandController

        self.command_controller: CommandController = None  # type: ignore # this is set later in _set_command_controller
        self.command_service: CommandService = CommandService()
        self.pid = 0
        self.verbose = verbose
        self.active_gcs = active_gcs
        # video settings
        self.qgc_ip = qgc_ip
        self.qgc_port = qgc_port
        self.atak_ip = atak_ip
        self.atak_port = atak_port
        self.streaming_bitrate = streaming_bitrate
        self.original_size = (0, 0)
        self.recording_start_time = 0
        self.max_zoom = max_zoom
        # stabilize settings
        self.stabilize = stabilize
        self.prev_gray = None
        # picamera config
        self.resolution = tuple(map(int, resolution.split("x")))
        tuning = Picamera2.load_tuning_file(Path(config_file).resolve())
        self.picam2 = Picamera2(tuning=tuning)
        self.streaming_config = self.picam2.create_video_configuration(
            main={"size": self.resolution}
        )
        self.photo_config = self.picam2.create_still_configuration(
            main={"size": tuple(map(int, STILL_FRAMESIZE.split("x")))}
        )
        # ffmpeg processes
        self.is_recording = False
        self.is_qgc_streaming = False
        self.is_atak_streaming = False
        self.ffmpeg_process_record = None
        self.ffmpeg_process_qgc = None
        self.ffmpeg_process_atak = None
        # tracking
        self.tracker = ObjectTracker()
        self.track_status = TrackStatus.NONE.value

        # Ensure the media files directory exists
        media_directory = Path(f"./{MEDIA_FILES_DIRECTORY}")
        os.makedirs(media_directory, exist_ok=True)

    def _init_ffmpeg_processes(self) -> None:
        """
        Only needs to be done once at the start of the stream.
        Later modifications to GCS streams will be handled by the command controller.
        """
        self._close_ffmpeg_processes()

        self.ffmpeg_command_record = get_ffmpeg_command_record(
            self.resolution,
            str(FRAMERATE),
            f"./{MEDIA_FILES_DIRECTORY}/{get_timestamp()}.ts",
        )
        print(f"streaming_bitrate {str(self.streaming_bitrate)}")
        if self.qgc_ip and self.qgc_port:
            self.ffmpeg_command_qgc = get_ffmpeg_command_qgc(
                self.resolution,
                str(FRAMERATE),
                self.qgc_ip,
                str(self.qgc_port),
                str(self.streaming_bitrate),
            )
        else:
            self.ffmpeg_command_qgc = None  # type: ignore
        if self.atak_ip and self.atak_port:
            self.ffmpeg_command_atak = get_ffmpeg_command_atak(
                self.resolution,
                str(FRAMERATE),
                self.atak_ip,
                str(self.atak_port),
                str(self.streaming_bitrate),
            )
        else:
            self.ffmpeg_command_atak = None  # type: ignore

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
            self.prev_gray = gray  # type: ignore
            return frame

        # Select good points
        good_new = p1[st == 1]  # type: ignore
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
            stabilized_frame = frame  # type: ignore

        # Update the previous frame and gray image
        self.prev_gray = gray  # type: ignore

        return stabilized_frame

    def start_recording(self, file_name: str = "") -> None:
        if self.is_recording:
            print("Already recording...")
            return

        self.recording_start_time = int(time.time())

        if file_name:
            self.ffmpeg_command_record = get_ffmpeg_command_record(
                self.resolution, str(FRAMERATE), file_name
            )

        self.ffmpeg_process_record = subprocess.Popen(  # type: ignore
            self.ffmpeg_command_record, stdin=subprocess.PIPE
        )
        self.is_recording = True

    def stop_recording(self) -> None:
        self.is_recording = False
        if self.ffmpeg_process_record:
            print("Stopping recording...")
            if self.ffmpeg_process_record.stdin:
                self.ffmpeg_process_record.stdin.close()
            self.ffmpeg_process_record.wait()

    def start_qgc_stream(self, ip: str, port: str) -> None:
        if self.is_qgc_streaming:
            print("Already QGC streaming...")
            return
        self.qgc_ip = ip
        self.qgc_port = port
        self.ffmpeg_command_qgc = get_ffmpeg_command_qgc(
            self.resolution,
            str(FRAMERATE),
            self.qgc_ip,
            str(self.qgc_port),
            str(self.streaming_bitrate),
        )
        print(f"Starting QGC stream {self.ffmpeg_command_qgc}")
        self.ffmpeg_process_qgc = subprocess.Popen(  # type: ignore
            self.ffmpeg_command_qgc, stdin=subprocess.PIPE
        )
        if not self.picam2.started:
            self.picam2.start()
        self.is_qgc_streaming = True

    def stop_qgc_stream(self) -> None:
        self.is_qgc_streaming = False
        if self.ffmpeg_process_qgc:
            print("Stopping QGC stream...")
            if self.ffmpeg_process_qgc.stdin:
                self.ffmpeg_process_qgc.stdin.close()
            self.ffmpeg_process_qgc.wait()

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
        print(f"Starting ATAK stream {self.ffmpeg_command_atak}")
        self.ffmpeg_process_atak = subprocess.Popen(  # type: ignore
            self.ffmpeg_command_atak, stdin=subprocess.PIPE
        )
        if not self.picam2.started:
            self.picam2.start()
        self.is_atak_streaming = True

    def stop_atak_stream(self) -> None:
        self.is_atak_streaming = False
        if self.ffmpeg_process_atak:
            print("Stopping ATAK streaming...")
            if self.ffmpeg_process_atak.stdin:
                self.ffmpeg_process_atak.stdin.close()
            self.ffmpeg_process_atak.wait()

    def take_photo(self, file_name: str = "") -> None:
        """
        Since photos are taken at higher resolution than streaming, the picam2 must stop and
        be reconfigured before the photo can be taken. Once taken, the streaming config is reapplied.
        If the photo resolution is the same as the streaming resolution, the picam2 does not need to
        change resolution. The photo will also be capture at the same zoom level as set on the GCS.

        Also note that the command sender may optionally send the desired file name for the photo.
        """
        if not self.is_qgc_streaming:
            return

        is_same_resolution = (
            tuple(map(int, STILL_FRAMESIZE.split("x"))) == self.resolution
        )

        _original_zoom = self.command_controller.current_zoom

        if not is_same_resolution:
            self.picam2.stop()
            self.picam2.configure(self.photo_config)
            self.command_controller.set_zoom(_original_zoom)
            self.picam2.start()

        if not file_name:
            file_name = f"./{MEDIA_FILES_DIRECTORY}/{get_timestamp()}.jpg"
        self.picam2.capture_file(file_name)

        if not is_same_resolution:
            self.picam2.stop()
            self.picam2.configure(self.streaming_config)
            self.command_controller.set_zoom(_original_zoom)
            self.picam2.start()

    def _format_duration(self, seconds: int) -> str:
        """Convert a duration in seconds to a minutes:seconds format."""
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:02d}"

    def _draw_rec(self, frame: np.ndarray) -> np.ndarray:
        """
        Paints "REC" on the top of streams (but not the saved video).
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
        self.stop_qgc_stream()
        self.stop_atak_stream()

    def stop_and_clean_all(self) -> None:
        print("Stopping and cleaning camera resources...")
        if self.picam2:
            self.picam2.stop()
        cv2.destroyAllWindows()
        self._close_ffmpeg_processes()

    def _read_and_process_commands(self) -> None:
        commands = self.command_service.get_pending_commands()
        for command in commands:
            print(f"Processing command `{command}`")
            try:
                self.command_controller.handle_command(
                    command_type=command[0], command_value=command[1]
                )
            except Exception as e:
                print(f"Error processing command: {e}")

    def stream(self) -> None:
        # Start the ffmpeg processes
        self._init_ffmpeg_processes()

        # Start the camera
        self.picam2.configure(self.streaming_config)
        self.picam2.start()
        self.original_size = self.picam2.capture_metadata()["ScalerCrop"][2:]

        # Init frame and stream
        fps = []

        # Start the active GCS stream
        if self.active_gcs == GCSType.ATAK.value:
            if not str(self.atak_ip) or not str(self.atak_port):
                print(
                    "ATAK IP and port must be set to stream to ATAK. Defaulting to QGC."
                )
                self.active_gcs = GCSType.QGC.value
            else:
                self.start_atak_stream(ip=str(self.atak_ip), port=str(self.atak_port))

        if self.active_gcs == GCSType.QGC.value:
            self.start_qgc_stream(ip=str(self.qgc_ip), port=str(self.qgc_port))

        self.command_controller.set_zoom(MIN_ZOOM)

        # Main loop
        fps_counter = 20
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
                if self.verbose and i == fps_counter:
                    elapsed_time = time.perf_counter() - startt
                    startt = time.perf_counter()
                    fps.append(fps_counter / elapsed_time)
                    print(f"fps={fps_counter/elapsed_time} | ")
                    i = 0

                if self.track_status == TrackStatus.INIT.value:
                    ret = self.tracker._init_bounding_box(frame)
                    if ret:
                        frame = self.tracker.draw_bounding_box(frame, INIT_BBOX_COLOR)
                        self.track_status = TrackStatus.ACTIVE.value

                if self.track_status == TrackStatus.ACTIVE.value:
                    frame = self.tracker.draw_bounding_box(frame, INIT_BBOX_COLOR)
                    ret, frame = self.tracker.track_object(frame)
                    if not ret:
                        print("Tracking has been lost")
                        self.track_status = TrackStatus.STOP.value

                if self.stabilize:
                    if self.prev_gray is None:
                        self.prev_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                    frame = self._stabilize(frame)

                if (
                    self.command_controller
                    and self.command_controller.zoom_status != ZoomStatus.STOP.value
                ):
                    self.command_controller.do_continuous_zoom()

                # Convert the frame back to YUV format before sending to FFmpeg
                frame_8bit = cv2.convertScaleAbs(frame)
                frame_yuv = cv2.cvtColor(frame_8bit, cv2.COLOR_RGB2YUV_I420)
                pure_frame_yuv_bytes = frame_yuv.tobytes()
                modified_frame_yuv_bytes = None

                # Forward the stabilized frame to rtp
                if self.is_recording:
                    # video should not have 'REC' appearing in the frame
                    self.ffmpeg_process_record.stdin.write(pure_frame_yuv_bytes)  # type: ignore
                    frame_8bit_rec = self._draw_rec(frame_8bit)
                    frame_yuv = cv2.cvtColor(frame_8bit_rec, cv2.COLOR_RGB2YUV_I420)
                    modified_frame_yuv_bytes = frame_yuv.tobytes()

                if not modified_frame_yuv_bytes:
                    modified_frame_yuv_bytes = pure_frame_yuv_bytes

                if self.is_atak_streaming:
                    self.ffmpeg_process_atak.stdin.write(modified_frame_yuv_bytes)  # type: ignore

                if self.is_qgc_streaming:
                    self.ffmpeg_process_qgc.stdin.write(modified_frame_yuv_bytes)  # type: ignore

        finally:
            self.stop_and_clean_all()
            if self.verbose:
                print(f"\n\nAverage FPS = {sum(fps)/len(fps)}\n\n")


if __name__ == "__main__":
    # Argument parsing
    parser = argparse.ArgumentParser(description="PiStreamer for IMX477 Camera.")
    parser.add_argument("--stabilize", action="store_true", help="Whether to stabilize")
    parser.add_argument(
        "--resolution",
        type=str,
        default=STREAMING_FRAMESIZE,
        help="Resolution of the video frames (e.g., 1280x720)",
    )
    parser.add_argument(
        "--qgc_ip",
        type=str,
        default="192.168.1.124",
        help="Destination IP address for QGroundControl stream",
    )
    parser.add_argument(
        "--qgc_port",
        type=int,
        default=5600,
        help="Destination port for QGroundControl stream",
    )
    parser.add_argument(
        "--atak_ip",
        type=str,
        default="",
        help="Destination ATAK IP address for RTP stream",
    )
    parser.add_argument(
        "--atak_port",
        type=int,
        default=0,
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
    parser.add_argument(
        "--verbose", action="store_true", help="Whether to print verbose FPS data"
    )
    parser.add_argument(
        "--max_zoom",
        type=float,
        default=DEFAULT_MAX_ZOOM,
        help="Max Zoom rate of the EO",
    )
    parser.add_argument(
        "--active_gcs",
        type=str,
        default=GCSType.QGC.value,
        help="Active GCS type to stream too",
    )
    args = parser.parse_args()
    try:
        Validator(args)
    except Exception as e:
        print(f"Validation Error: {e}")
        sys.exit(1)
    pi_streamer = PiStreamer2(
        stabilize=args.stabilize,
        resolution=args.resolution,
        streaming_bitrate=args.bitrate,
        qgc_ip=args.qgc_ip,
        qgc_port=args.qgc_port,
        atak_ip=args.atak_ip,
        atak_port=args.atak_port,
        config_file=args.config_file,
        verbose=args.verbose,
        max_zoom=args.max_zoom,
        active_gcs=args.active_gcs,
    )
    from command_controller import CommandController

    controller = CommandController(pi_streamer)
    pi_streamer.stream()
