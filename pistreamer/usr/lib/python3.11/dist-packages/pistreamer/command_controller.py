#!/usr/bin/env python3

from datetime import datetime
import json
import subprocess
from time import time
from typing import Union
from constants import (
    MIN_ZOOM,
    SD_CARD_LOCATION,
    ZOOM_RATE,
    CommandType,
    MavlinkGPSData,
    MavlinkMiscData,
    StreamingProtocolType,
    OutputCommandType,
    ZoomStatus,
    TrackStatus,
)
from validator import Validator
from functools import cached_property


class CommandController:
    from pistreamer import PiStreamer2

    def __init__(self, pi_streamer: PiStreamer2) -> None:
        self.pi_streamer = pi_streamer
        self.validator = Validator()
        self.pi_streamer._set_command_controller(self)
        self.zoom_status = ZoomStatus.STOP.value
        self.current_zoom = MIN_ZOOM
        self.last_zoom_time = 0

    @cached_property
    def is_sd_card_available(self) -> bool:
        """
        We only want to save files to disk if an SD card is available.
        """
        try:
            result = subprocess.run(
                ["sudo", "fdisk", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2,
            )
            if SD_CARD_LOCATION in result.stdout:
                print("SD card is available so images and videos will save to disk.")
                return True
            print(
                "SD card is not available so images and videos will NOT save to disk."
            )
            return False
        except Exception as e:
            print(f"Error occurred: {e}")
            return False

    def handle_command(self, command_type: str, command_value: str = "") -> None:
        """
        Attempts to handle the GCS commands for PiStreamer. If an exception occurs it is
        raised so PiStreamer can update the db row with the error.
        """
        # Higher priority commands should come first in if/elif/else for minor performance improvements
        print(f"Received command {command_type=} {command_value=}")
        with open("/tmp/command_log.txt", "a") as f:
            f.write(
                f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} - {command_type=} {command_value=}\n'
            )
        if command_type == CommandType.TAKE_PHOTO.value:
            print(
                f"Received photo command {self.is_sd_card_available=} {command_value=}"
            )
            if self.is_sd_card_available:
                self.pi_streamer.take_photo(file_name=command_value)
        elif command_type == CommandType.RECORD.value:
            print(
                f"Received record command {self.is_sd_card_available=} {command_value=}"
            )
            if self.is_sd_card_available:
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
        elif command_type == CommandType.GPS_DATA.value:
            try:
                self.pi_streamer.gps_data = MavlinkGPSData(**json.loads(command_value))
            except Exception as e:
                raise Exception(f"Invalid GPS data command : {e}")
        elif command_type == CommandType.MISC_DATA.value:
            try:
                self.pi_streamer.misc_data = MavlinkMiscData(
                    **json.loads(command_value)
                )
            except Exception as e:
                raise Exception(f"Invalid MISC data command : {e}")
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
        elif command_type == CommandType.GCS_HOST.value:
            ip, port = map(str.strip, command_value.split(" ")[0].split(":"))
            print(f"Setting new GCS host {ip}:{port}")
            self._reset_gcs_host(ip=ip, port=port)
        elif command_type == CommandType.GCS_PORT.value:
            try:
                new_port = str(command_value)
                if not self.validator.validate_port(new_port):
                    raise Exception(
                        f"Error: {new_port} is not a valid port. It must be between 1 and 65535."
                    )
                print(f"Setting new GCS port {new_port}")
                self._reset_gcs_host(
                    ip=str(self.pi_streamer.gcs_ip),
                    port=new_port,
                )
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid port command. Use 'port <value>' where value is an int between 1 and 65535."
                )
        elif command_type == CommandType.GCS_IP.value:
            try:
                new_ip = str(command_value)
                if not self.validator.validate_ip(new_ip):
                    raise Exception(f"Error: {new_ip} is not a valid IP Address.")
                print(f"Setting new GCS IP {new_ip}")
                self._reset_gcs_host(
                    ip=new_ip,
                    port=str(self.pi_streamer.gcs_port),
                )
            except (IndexError, ValueError):
                raise Exception(
                    "Invalid ip command. Use 'ip <value>' where value is a valid ip address."
                )
        elif command_type == CommandType.START_GCS_STREAM.value:
            if self.pi_streamer.streaming_protocol == StreamingProtocolType.RTP.value:
                start_func = self.pi_streamer.start_rtp_stream
            elif (
                self.pi_streamer.streaming_protocol
                == StreamingProtocolType.MPEG_TS.value
            ):
                start_func = self.pi_streamer.start_mpeg_ts_stream
            else:
                raise Exception(
                    f"Unsupported GCS type {self.pi_streamer.streaming_protocol}."
                )
            start_func(
                ip=str(self.pi_streamer.gcs_ip),
                port=str(self.pi_streamer.gcs_port),
            )
        elif command_type == CommandType.STOP_GCS_STREAM.value:
            if self.pi_streamer.streaming_protocol == StreamingProtocolType.RTP.value:
                stop_func = self.pi_streamer.stop_rtp_stream
            elif (
                self.pi_streamer.streaming_protocol
                == StreamingProtocolType.MPEG_TS.value
            ):
                stop_func = self.pi_streamer.stop_mpeg_ts_stream
            else:
                raise Exception(
                    f"Unsupported GCS type {self.pi_streamer.streaming_protocol}."
                )
            stop_func()
        elif command_type == CommandType.STREAMING_PROTOCOL.value:
            command_value = command_value.lower().strip()
            if command_value not in [
                StreamingProtocolType.RTP.value,
                StreamingProtocolType.MPEG_TS.value,
            ]:
                raise Exception(
                    f"Unsupported GCS type {self.pi_streamer.streaming_protocol}."
                )
            self._reset_gcs_host(
                ip=str(self.pi_streamer.gcs_ip),
                port=str(self.pi_streamer.gcs_port),
                streaming_protocol=command_value,
            )
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
        else:
            raise Exception(f"Unknown command_type: `{command_type}`")

    def _reset_gcs_host(self, ip: str, port: str, streaming_protocol: str = "") -> None:
        """
        If the ATAK or QGC (the supported GCS options) hosts change, we first stop all GCS streams,
        change their ip and port, and start the active target stream again.
        """
        try:
            if not self.validator.validate_ip(ip):
                raise Exception(f"Error: {ip} is not a valid ip.")
            if not self.validator.validate_port(port):
                raise Exception(f"Error: {port} is not a valid port.")

            print(
                f"Setting new {self.pi_streamer.streaming_protocol} stream - IP: {ip} and port: {port}"
            )

            # we only want to start a stream upon updated host info if we were streaming before
            should_restart_rtp = self.pi_streamer.is_rtp_streaming
            should_restart_mpeg_ts = self.pi_streamer.is_mpeg_ts_streaming

            self.pi_streamer.stop_and_clean_all()

            if streaming_protocol:
                self.pi_streamer.streaming_protocol = streaming_protocol
            self.pi_streamer.gcs_ip = ip
            self.pi_streamer.gcs_port = port

            if should_restart_rtp:
                self.pi_streamer.start_rtp_stream(ip=ip, port=port)
            elif should_restart_mpeg_ts:
                self.pi_streamer.start_mpeg_ts_stream(ip=ip, port=port)
            else:
                raise Exception("Invalid GCS type.")

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
        start_func = None

        if self.pi_streamer.is_rtp_streaming:
            start_func = self.pi_streamer.start_rtp_stream
        elif self.pi_streamer.is_mpeg_ts_streaming:
            start_func = self.pi_streamer.start_mpeg_ts_stream

        if start_func:
            start_func(
                ip=str(self.pi_streamer.gcs_ip),
                port=str(self.pi_streamer.gcs_port),
            )

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

        self.pi_streamer.command_service.send_data_out(
            data=f"{OutputCommandType.ZOOM_LEVEL.value} {self.current_zoom}"
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
