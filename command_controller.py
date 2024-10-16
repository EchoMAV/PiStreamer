#!/usr/bin/env python3

from time import time
from typing import Any, Literal, Union
from constants import MAX_ZOOM, MIN_ZOOM, ZOOM_RATE, CommandType, ZoomStatus
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
        if command_type == CommandType.RECORD.value:
            self.pi_streamer.start_recording()
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
        elif command_type == CommandType.STABILIZE.value:
            try:
                stab_value = (
                    True if str(command_value).lower().strip() == "start" else False
                )
                self.pi_streamer.stabilize = stab_value
            except Exception:
                raise Exception("Invalid stabilization command.")
        elif command_type == CommandType.TAKE_PHOTO.value:
            self.pi_streamer.take_photo()
        elif command_type == CommandType.STOP_RECORDING.value:
            self.pi_streamer.stop_recording()
        elif command_type == CommandType.GCS_HOST.value:
            self._reset_host(command_value, "gcs")
        elif command_type == CommandType.START_GCS_STREAM.value:
            self.pi_streamer.start_gcs_stream(
                ip=self.pi_streamer.gcs_ip, port=self.pi_streamer.gcs_port  # type: ignore
            )
        elif command_type == CommandType.STOP_GCS_STREAM.value:
            self.pi_streamer.stop_gcs_stream()
        elif command_type == CommandType.ATAK_HOST.value:
            self._reset_host(command_value, "atak")
        elif command_type == CommandType.STOP_ATAK.value:
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
                self._reset_stream("streaming_bitrate", bitrate)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid bitrate command. Use 'bitrate <value>' where value is an int 500-10000 kbps."
                )
        elif command_type == CommandType.GCS_PORT.value:
            try:
                new_port = str(command_value)
                if not self.validator.validate_port(new_port):
                    raise Exception(
                        f"Error: {new_port} is not a valid port. It must be between 1 and 65535."
                    )
                print(f"Setting new GCS port: {new_port}")
                self._reset_stream("gcs_port", new_port)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid port command. Use 'port <value>' where value is an int between 1 and 65535."
                )
        elif command_type == CommandType.GCS_IP.value:
            try:
                new_ip = str(command_value)
                if not self.validator.validate_ip(new_ip):
                    raise Exception(f"Error: {new_ip} is not a valid IP Address.")
                print(f"Setting new GCS IP: {new_ip}")
                self._reset_stream("gcs_ip", new_ip)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid ip command. Use 'ip <value>' where value is a valid ip address."
                )
        elif command_type == CommandType.STOP.value:
            self.pi_streamer.stop_and_clean_all()
        elif command_type == CommandType.KILL.value:
            self.pi_streamer.stop_and_clean_all()
        else:
            raise Exception(f"Unknown command_type: `{command_type}`")

    def _reset_host(self, command_value: str, stream_name: Literal["atak", "gcs"]):
        """
        If the ATAK or GCS host changes, we change the ip and port and reset the ffmpeg stream.
        """
        try:
            ip, port = str(command_value).split(" ")[0].split(":")
            if not self.validator.validate_ip(ip):
                raise Exception(f"Error: {ip} is not a valid ip.")
            if not self.validator.validate_port(port):
                raise Exception(f"Error: {port} is not a valid port.")
            print(f"Setting new {stream_name} IP: {ip} and port: {port}")

            # first we stop the stream then restart it
            _stop_method = getattr(self.pi_streamer, f"stop_{stream_name}_stream")
            _start_method = getattr(self.pi_streamer, f"start_{stream_name}_stream")
            _stop_method()
            _start_method(ip=ip, port=port)

        except (IndexError, ValueError):
            raise Exception("Invalid ip:port host command.")

    def _reset_stream(
        self,
        field_name: Literal["streaming_bitrate", "gcs_ip", "gcs_port"],
        field_value: Any,
    ):
        """
        The pi_streamer controls the major properties of the stream. This function pauses
        the current stream, sets the new value, and resumes the stream.

        This is a hard reset since it also can effect the underlying ffmpeg processes as well.
        """
        self.pi_streamer.stop_and_clean_all()
        setattr(self.pi_streamer, field_name, field_value)
        self.pi_streamer.stream()

    def set_zoom(self, zoom_factor: Union[int, float]) -> None:
        # Adjust the zoom by setting the crop rectangle
        if zoom_factor <= MIN_ZOOM:
            zoom_factor = MIN_ZOOM
        elif zoom_factor >= MAX_ZOOM:
            zoom_factor = MAX_ZOOM

        self.current_zoom = round(zoom_factor, 2)

        full_res = self.pi_streamer.picam2.camera_properties["PixelArraySize"]
        size = [int(s / self.current_zoom) for s in self.pi_streamer.original_size]
        offset = [(r - s) // 2 for r, s in zip(full_res, size)]
        self.pi_streamer.picam2.set_controls({"ScalerCrop": offset + size})

        if self.pi_streamer.verbose:
            print(f"Zoom set to {self.current_zoom}x {offset + size}")

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
        elif self.current_zoom >= MAX_ZOOM:
            self.current_zoom = MAX_ZOOM
            stop_zoom = True

        if stop_zoom:
            # reset the status and zoom time reference
            self.zoom_status = ZoomStatus.STOP.value
            self.last_zoom_time = 0

        self.set_zoom(self.current_zoom)
