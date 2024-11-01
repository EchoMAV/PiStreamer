#!/usr/bin/env python3

from time import time
from typing import Literal, Union
from command_service import CommandService
from constants import (
    MIN_ZOOM,
    ZOOM_RATE,
    CommandType,
    OutputCommandType,
    ZoomStatus,
    OUTPUT_SOCKET_PORT,
    OUTPUT_SOCKET_HOST,
    TrackStatus,
)
from validator import Validator


class CommandController:
    from pistreamer_v2 import PiStreamer2

    def __init__(self, pi_streamer: PiStreamer2) -> None:
        self.pi_streamer = pi_streamer
        self.validator = Validator()
        self.pi_streamer._set_command_controller(self)
        self.zoom_status = ZoomStatus.STOP.value
        self.current_zoom = MIN_ZOOM
        self.last_zoom_time = 0

    def handle_command(self, command_type: str, command_value: str = "") -> None:
        """
        Attempts to handle the GCS commands for PiStreamer. If an exception occurs it is
        raised so PiStreamer can update the db row with the error.
        """
        # Higher priority commands should come first in if/elif/else for minor performance improvements
        if command_type == CommandType.TAKE_PHOTO.value:
            self.pi_streamer.take_photo(file_name=command_value)
        elif command_type == CommandType.RECORD.value:
            self.pi_streamer.start_recording(file_name=command_value)
        elif command_type == CommandType.ZOOM.value:
            try:
                zoom_status = str(command_value).lower().strip()
                if zoom_status in [
                    ZoomStatus.IN.value,
                    ZoomStatus.OUT.value,
                    ZoomStatus.STOP.value,
                ]:
                    self.zoom_status = zoom_status
                    if zoom_status == ZoomStatus.STOP.value:
                        self.last_zoom_time = 0
                else:
                    zoom_factor = float(zoom_status)
                    self.set_zoom(zoom_factor)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid zoom command. Use 'zoom <factor>' where factor is a float otherwise 'in' or 'out'."
                )
        elif command_type == CommandType.MAX_ZOOM.value:
            max_zoom = float(command_value)
            if not self.validator.validate_max_zoom(max_zoom):
                raise Exception(
                    f"Error: {max_zoom} is not a valid max_zoom. It must be between 8.0 and 16.0 inclusive."
                )
            self.pi_streamer.max_zoom = max_zoom
            self.set_zoom(MIN_ZOOM)  # reset the zoom back to the original
        elif command_type == CommandType.INIT_TRACKING_POI.value:
            x_center, y_center = command_value.split(",")
            self.pi_streamer.tracker._init_tracking_poi(
                x_center=int(x_center), y_center=int(y_center)
            )
            self.pi_streamer.track_status = TrackStatus.INIT.value
        elif command_type == CommandType.STABILIZE.value:
            try:
                stab_value = (
                    True if str(command_value).lower().strip() == "start" else False
                )
                self.pi_streamer.stabilize = stab_value
            except Exception:
                raise Exception("Invalid stabilization command.")
        elif command_type == CommandType.STOP_RECORDING.value:
            self.pi_streamer.stop_recording()
        elif command_type == CommandType.QGC_HOST.value:
            self._reset_gcs_host(command_value, "qgc")
        elif command_type == CommandType.START_QGC_STREAM.value:
            self.pi_streamer.start_qgc_stream(
                ip=str(self.pi_streamer.qgc_ip),
                port=str(self.pi_streamer.qgc_port),
            )
        elif command_type == CommandType.STOP_QGC_STREAM.value:
            self.pi_streamer.stop_qgc_stream()
        elif command_type == CommandType.ATAK_HOST.value:
            self._reset_gcs_host(command_value, "atak")
        elif command_type == CommandType.STOP_ATAK_STREAM.value:
            self.pi_streamer.stop_atak_stream()
        elif command_type == CommandType.BITRATE.value:
            try:
                bitrate = int(command_value)
                if not self.validator.validate_bitrate(bitrate):
                    raise Exception(
                        f"Error: {bitrate} is not a valid bitrate. It must be between 500 and 10000 kbps."
                    )
                print(f"Setting new bitrate: {bitrate} kbps")
                bitrate = bitrate * 1000
                self._reset_bitrate(bitrate)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid bitrate command. Use 'bitrate <value>' where value is an int 500-10000 kbps."
                )
        elif command_type == CommandType.QGC_PORT.value:
            try:
                new_port = str(command_value)
                if not self.validator.validate_port(new_port):
                    raise Exception(
                        f"Error: {new_port} is not a valid port. It must be between 1 and 65535."
                    )
                print(f"Setting new QGC port: {new_port}")
                self._reset_gcs_host("qgc_port", new_port)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid port command. Use 'port <value>' where value is an int between 1 and 65535."
                )
        elif command_type == CommandType.QGC_IP.value:
            try:
                new_ip = str(command_value)
                if not self.validator.validate_ip(new_ip):
                    raise Exception(f"Error: {new_ip} is not a valid IP Address.")
                print(f"Setting new QGC IP: {new_ip}")
                self._reset_gcs_host("qgc_ip", new_ip)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid ip command. Use 'ip <value>' where value is a valid ip address."
                )
        else:
            raise Exception(f"Unknown command_type: `{command_type}`")

    def _reset_gcs_host(
        self, ip: str, port: str, new_preferred_gcs: PreferredGCSType
    ) -> None:
        """
        If the ATAK or QGC (the supported GCS options) hosts change, we first stop all GCS streams,
        change their ip and port, and start the new target stream.
        """
        try:
            if not self.validator.validate_ip(ip):
                raise Exception(f"Error: {ip} is not a valid ip.")
            if not self.validator.validate_port(port):
                raise Exception(f"Error: {port} is not a valid port.")
            print(f"Setting new {stream_name} IP: {ip} and port: {port}")

            # first we stop both streams then restart the target one
            self.pi_streamer.stop_and_clean_all()
            _start_method = getattr(self.pi_streamer, f"start_{stream_name}_stream")
            _start_method(ip=ip, port=port)

        except (IndexError, ValueError):
            raise Exception("Invalid ip:port host command.")

    def _reset_bitrate(
        self,
        bitrate: int,
    ):
        """
        Similar to _reset_gcs_host but allows for more granular control over the field being set.
        """
        self.pi_streamer.stop_and_clean_all()
        self.pi_streamer.streaming_bitrate = bitrate
        # TODO based on preferred_gcs_type start that stream

    def set_zoom(self, zoom_factor: Union[int, float]) -> None:
        # Adjust the zoom by setting the crop rectangle
        if zoom_factor <= MIN_ZOOM:
            zoom_factor = MIN_ZOOM
        elif zoom_factor >= self.pi_streamer.max_zoom:
            zoom_factor = self.pi_streamer.max_zoom

        self.current_zoom = round(zoom_factor, 2)
        x, y, width, height = self.pi_streamer.picam2.camera_controls["ScalerCrop"][1]

        # Calculate new width and height based on zoom factor
        new_width = int(width / self.current_zoom)
        new_height = int(new_width * 9 / 16)  # Maintain 16:9 aspect ratio

        # Calculate new offsets to keep the zoom centered
        x_offset = x + (width - new_width) // 2
        y_offset = y + (height - new_height) // 2

        # Apply the new crop to the second region
        new_crop = (x_offset, y_offset, new_width, new_height)

        # Set the updated ScalerCrop for the second stream
        self.pi_streamer.picam2.set_controls({"ScalerCrop": new_crop})

        CommandService.send_data_out(
            data=f"{OutputCommandType.ZOOM_LEVEL.value} {self.current_zoom}",
            host=OUTPUT_SOCKET_HOST,
            port=OUTPUT_SOCKET_PORT,
        )

        if self.pi_streamer.verbose:
            print(f"Zoom set to {self.current_zoom}x {new_crop}")

    def do_continuous_zoom(self) -> None:
        """
        Controls a continuos "smooth" zoom in or out until min or max is reached or stop is reached
        (whichever comes first).
        """
        if self.zoom_status == ZoomStatus.STOP.value:
            return

        current_time = int(time() * 1000)

        # set our initial zoom reference point once
        if not self.last_zoom_time:
            self.last_zoom_time = current_time
            return

        elapsed_time = current_time - self.last_zoom_time
        self.last_zoom_time = current_time
        delta_zoom = float((ZOOM_RATE * elapsed_time) / 1000.0)

        if self.zoom_status == ZoomStatus.IN.value:
            self.current_zoom += delta_zoom
        elif self.zoom_status == ZoomStatus.OUT.value:
            self.current_zoom -= delta_zoom

        # if we have reached zoom limits then stop zooming
        stop_zoom = False
        if self.current_zoom <= MIN_ZOOM:
            self.current_zoom = MIN_ZOOM
            stop_zoom = True
        elif self.current_zoom >= self.pi_streamer.max_zoom:
            self.current_zoom = self.pi_streamer.max_zoom
            stop_zoom = True

        if stop_zoom:
            # reset the status and zoom time reference
            self.zoom_status = ZoomStatus.STOP.value
            self.last_zoom_time = 0

        self.set_zoom(self.current_zoom)
