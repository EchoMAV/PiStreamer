#!/usr/bin/env python3

from typing import Any, Literal, Union
from command_model import CommandModel
from constants import MAX_ZOOM, MIN_ZOOM, CommandType
from validator import Validator


class CommandController:
    from pistreamer_v2 import PiStreamer2

    def __init__(self, pi_streamer: PiStreamer2) -> None:
        self.pi_streamer = pi_streamer
        self.validator = Validator()
        self.pi_streamer._set_command_controller(self)

    def handle_command(self, command: CommandModel) -> None:
        """
        Attempts to handle the GCS commands for PiStreamer. If an exception occurs it is
        raised so PiStreamer can update the db row with the error.
        """
        if command.command_type == CommandType.RECORD.value:
            self.pi_streamer.start_recording()
        if command.command_type == CommandType.TAKE_PHOTO.value:
            self.pi_streamer.take_photo()
        elif command.command_type == CommandType.ZOOM.value:
            try:
                zoom_factor = float(str(command.command_value))
                self.set_zoom(zoom_factor)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid zoom command. Use 'zoom <factor>' where factor is a float."
                )
        elif command.command_type == CommandType.STOP_RECORDING.value:
            self.pi_streamer.stop_recording()
        elif command.command_type == CommandType.ATAK_HOST.value:
            try:
                ip, port = str(command.command_value).split(" ")[0].split(":")
                if not self.validator.validate_ip(ip):
                    raise Exception(f"Error: {ip} is not a valid ip.")
                if not self.validator.validate_port(port):
                    raise Exception(f"Error: {port} is not a valid port.")
                print(f"Setting new ATAK IP: {ip} and port: {port}")
                self.pi_streamer.start_atak_stream(ip=ip, port=port)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid bitrate command. Use 'bitrate <value>' where value is an int 500-10000 kbps."
                )
        elif command.command_type == CommandType.STOP_ATAK.value:
            self.pi_streamer.stop_atak_stream()
        elif command.command_type == CommandType.BITRATE.value:
            try:
                bitrate = str(command.command_value)
                if not self.validator.validate_bitrate(bitrate):
                    raise Exception(
                        f"Error: {bitrate} is not a valid bitrate. It must be between 500 and 10000 kbps."
                    )
                print(f"Setting new bitrate: {bitrate} kbps")
                bitrate = bitrate * 1000
                self.reset_stream("streaming_bitrate", bitrate)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid bitrate command. Use 'bitrate <value>' where value is an int 500-10000 kbps."
                )
        elif command.command_type == CommandType.PORT.value:
            try:
                new_port = str(command.command_value)
                if not self.validator.validate_port(new_port):
                    raise Exception(
                        f"Error: {new_port} is not a valid port. It must be between 1 and 65535."
                    )
                print(f"Setting new port: {new_port}")
                self.reset_stream("destination_port", new_port)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid port command. Use 'port <value>' where value is an int between 1 and 65535."
                )
        elif command.command_type == CommandType.IP_ADDRESS.value:
            try:
                new_iP = str(command.command_value)
                if not self.validator.validate_ip(new_iP):
                    raise Exception(f"Error: {new_iP} is not a valid IP Address.")
                print(f"Setting new IP: {new_iP}")
                self.reset_stream("destination_ip", new_iP)
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid ip command. Use 'ip <value>' where value is a valid ip address."
                )
        elif command.command_type == CommandType.STOP.value:
            self.pi_streamer.stop_and_clean_all()
        elif command.command_type == CommandType.KILL.value:
            # TODO kill daemon
            self.pi_streamer.stop_and_clean_all()
        else:
            raise Exception(f"Unknown command: {command}")

    def reset_stream(
        self,
        field_name: Literal["streaming_bitrate", "destination_ip", "destination_port"],
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
        if zoom_factor < MIN_ZOOM:
            zoom_factor = MIN_ZOOM
        elif zoom_factor > MAX_ZOOM:
            zoom_factor = MAX_ZOOM

        full_res = self.pi_streamer.picam2.camera_properties["PixelArraySize"]
        print(
            f"original size {self.pi_streamer.original_size[0]} x {self.pi_streamer.original_size[1]}"
        )
        size = [int(s / zoom_factor) for s in self.pi_streamer.original_size]
        offset = [(r - s) // 2 for r, s in zip(full_res, size)]
        self.pi_streamer.picam2.set_controls({"ScalerCrop": offset + size})
        print(f"Zoom set to {zoom_factor}x")
