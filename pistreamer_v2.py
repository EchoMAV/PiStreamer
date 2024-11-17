#!/usr/bin/env python3

from typing import Any, Optional
from exif_service import EXIFService
from ffmpeg_configs import (
    get_ffmpeg_command_mpeg_ts,
    get_ffmpeg_command_record,
    get_ffmpeg_command_rtp,
)
import os
from pathlib import Path
from picamera2 import Picamera2
import pyexiv2
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
    NAMESPACE_PREFIX,
    NAMESPACE_URI,
    STREAMING_FRAMESIZE,
    STILL_FRAMESIZE,
    CommandProtocolType,
    MavlinkGPSData,
    MavlinkMiscData,
    StreamingProtocolType,
    TrackStatus,
    ZoomStatus,
)
from object_tracker import ObjectTracker
from cam_utils import get_timestamp
from socket_service import SocketService
from validator import Validator
from zeromq_service import ZeroMQService


class PiStreamer2:
    def __init__(
        self,
        stabilize: bool,
        resolution: str,
        streaming_bitrate: int,
        gcs_ip: Optional[str] = None,
        gcs_port: Optional[str] = None,
        config_file: str = "./477-Pi4.json",
        verbose: bool = False,
        max_zoom: float = DEFAULT_MAX_ZOOM,
        streaming_protocol: str = StreamingProtocolType.RTP.value,
        command_protocol: str = CommandProtocolType.ZEROMQ.value,
    ) -> None:
        # utilities
        from command_controller import CommandController

        self.command_controller: CommandController = None  # type: ignore # this is set later in _set_command_controller

        if command_protocol == CommandProtocolType.ZEROMQ.value:
            self.command_service: ZeroMQService = ZeroMQService()
        elif command_protocol == CommandProtocolType.SOCKET.value:
            self.command_service: SocketService = SocketService()  # type: ignore
        else:
            raise NotImplementedError(
                "Only ZEROMQ and SOCKET message protocols are supported"
            )

        self.pid = 0
        self.verbose = verbose
        self.streaming_protocol = streaming_protocol
        # video settings
        self.gcs_ip = gcs_ip
        self.gcs_port = gcs_port
        self.streaming_bitrate = streaming_bitrate
        self.original_size = (0, 0)
        self.recording_start_time = 0
        self.max_zoom = max_zoom
        # video metadata
        self.gps_data = MavlinkGPSData()
        self.misc_data = MavlinkMiscData()
        pyexiv2.xmp.register_namespace(
            NAMESPACE_URI, NAMESPACE_PREFIX
        )  # Register the custom namespace for XMP
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
        self.is_rtp_streaming = False
        self.is_mpeg_ts_streaming = False
        self.ffmpeg_process_record = None
        self.ffmpeg_process_rtp = None
        self.ffmpeg_process_mpeg_ts = None
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

        if not self.gcs_ip and not self.gcs_port:
            raise Exception("GCS IP and port must be set to stream to a GCS.")

        self.ffmpeg_command_record = get_ffmpeg_command_record(
            self.resolution,
            str(FRAMERATE),
            f"./{MEDIA_FILES_DIRECTORY}/{get_timestamp()}.ts",
        )
        self.ffmpeg_command_rtp = get_ffmpeg_command_rtp(
            self.resolution,
            str(FRAMERATE),
            str(self.gcs_ip),
            str(self.gcs_port),
            str(self.streaming_bitrate),
        )
        self.ffmpeg_command_mpeg_ts = get_ffmpeg_command_mpeg_ts(
            self.resolution,
            str(FRAMERATE),
            str(self.gcs_ip),
            str(self.gcs_port),
            str(self.streaming_bitrate),
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

    def start_rtp_stream(self, ip: str, port: str) -> None:
        if self.is_rtp_streaming:
            print("Already RTP streaming...")
            return
        self.gcs_ip = ip
        self.gcs_port = port
        self.streaming_protocol = StreamingProtocolType.RTP.value
        self.ffmpeg_command_rtp = get_ffmpeg_command_rtp(
            self.resolution,
            str(FRAMERATE),
            self.gcs_ip,
            str(self.gcs_port),
            str(self.streaming_bitrate),
        )
        print(f"Starting RTP stream {self.ffmpeg_command_rtp}")
        self.ffmpeg_process_rtp = subprocess.Popen(  # type: ignore
            self.ffmpeg_command_rtp, stdin=subprocess.PIPE
        )
        if not self.picam2.started:
            self.picam2.start()
        self.is_rtp_streaming = True

    def stop_rtp_stream(self) -> None:
        self.is_rtp_streaming = False
        if self.ffmpeg_process_rtp:
            print("Stopping RTP stream...")
            if self.ffmpeg_process_rtp.stdin:
                self.ffmpeg_process_rtp.stdin.close()
            self.ffmpeg_process_rtp.wait()

    def start_mpeg_ts_stream(self, ip: str, port: str) -> None:
        if self.is_mpeg_ts_streaming:
            print("Already MPEG-TS streaming...")
            return
        self.gcs_ip = ip
        self.gcs_port = port
        self.streaming_protocol = StreamingProtocolType.MPEG_TS.value
        self.ffmpeg_command_mpeg_ts = get_ffmpeg_command_mpeg_ts(
            self.resolution,
            str(FRAMERATE),
            self.gcs_ip,
            str(self.gcs_port),
            str(self.streaming_bitrate),
        )
        print(f"Starting MPEG-TS stream {self.ffmpeg_command_mpeg_ts}")
        self.ffmpeg_process_mpeg_ts = subprocess.Popen(  # type: ignore
            self.ffmpeg_command_mpeg_ts, stdin=subprocess.PIPE
        )
        if not self.picam2.started:
            self.picam2.start()
        self.is_mpeg_ts_streaming = True

    def stop_mpeg_ts_stream(self) -> None:
        self.is_mpeg_ts_streaming = False
        if self.ffmpeg_process_mpeg_ts:
            print("Stopping MPEG-TS streaming...")
            if self.ffmpeg_process_mpeg_ts.stdin:
                self.ffmpeg_process_mpeg_ts.stdin.close()
            self.ffmpeg_process_mpeg_ts.wait()

    def take_photo(self, file_name: str = "") -> None:
        """
        Since photos are taken at higher resolution than streaming, the picam2 must stop and
        be reconfigured before the photo can be taken. Once taken, the streaming config is reapplied.
        If the photo resolution is the same as the streaming resolution, the picam2 does not need to
        change resolution. The photo will also be capture at the same zoom level as set on the GCS.

        Also note that the command sender may optionally send the desired file name for the photo.
        """
        if not self.is_rtp_streaming:
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

        # Lastly update the photo with the exif data
        EXIFService(self.gps_data, self.misc_data, file_name).add_metadata()

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
        self.stop_rtp_stream()
        self.stop_mpeg_ts_stream()

    def stop_and_clean_all(self) -> None:
        print("Stopping and cleaning camera resources...")
        if self.picam2:
            self.picam2.stop()
        cv2.destroyAllWindows()
        self._close_ffmpeg_processes()

    def _read_and_process_commands(self) -> None:
        commands = self.command_service.get_pending_commands()
        for command in commands:
            if self.verbose:
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
        if self.streaming_protocol == StreamingProtocolType.RTP.value:
            self.start_rtp_stream(ip=str(self.gcs_ip), port=str(self.gcs_port))
        elif self.streaming_protocol == StreamingProtocolType.MPEG_TS.value:
            self.start_mpeg_ts_stream(ip=str(self.gcs_ip), port=str(self.gcs_port))
        else:
            raise Exception("Invalid active GCS type")

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

                if self.is_rtp_streaming:
                    self.ffmpeg_process_rtp.stdin.write(modified_frame_yuv_bytes)  # type: ignore
                elif self.is_mpeg_ts_streaming:
                    self.ffmpeg_process_mpeg_ts.stdin.write(modified_frame_yuv_bytes)  # type: ignore

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
        "--gcs_ip",
        type=str,
        default="192.168.1.124",
        help="Destination IP address for the GCS stream (i.e. QGroundControl or ATAK)",
    )
    parser.add_argument(
        "--gcs_port",
        type=int,
        default=5600,
        help="Destination port for the GCS stream (i.e. QGroundControl or ATAK)",
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
        "--streaming_protocol",
        type=str,
        default=StreamingProtocolType.RTP.value,
        help="Streaming protocol to use (RTP or MPEGTS)",
    )
    parser.add_argument(
        "--command_protocol",
        type=str,
        default=CommandProtocolType.ZEROMQ.value,
        help="Command protocol to use for messages (socket or zeromq)",
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
        gcs_ip=args.gcs_ip,
        gcs_port=args.gcs_port,
        config_file=args.config_file,
        verbose=args.verbose,
        max_zoom=args.max_zoom,
        streaming_protocol=args.streaming_protocol.lower(),
        command_protocol=args.command_protocol.lower(),
    )
    from command_controller import CommandController

    controller = CommandController(pi_streamer)
    pi_streamer.stream()
