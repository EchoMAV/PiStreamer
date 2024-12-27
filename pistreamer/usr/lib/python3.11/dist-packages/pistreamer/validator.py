#!/usr/bin/env python3
import os
import ipaddress
from typing import Any, Optional

from constants import CommandProtocolType, RadioType, StreamingProtocolType


class Validator:
    def __init__(self, args: Optional[Any] = None) -> None:
        self.args = args
        if self.args:
            self._validate_args()

    def _validate_args(self) -> bool:
        if not self.args:
            return False
        ret = self.validate_ip(str(self.args.gcs_ip))
        ret &= self.validate_port(str(self.args.gcs_port))
        ret &= self.validate_bitrate(int(self.args.bitrate))
        ret &= self.is_json_file(str(self.args.config_file))
        ret &= self.validate_max_zoom(float(self.args.max_zoom))
        ret &= self.validate_streaming_protocol(self.args.streaming_protocol)
        ret &= self.validate_radio_type(self.args.radio_type)
        ret &= self.validate_command_protocol(self.args.command_protocol)
        return ret

    def validate_ip(self, ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def validate_port(self, port: str) -> bool:
        try:
            if 1 <= int(port) <= 65535:
                return True
            return False
        except ValueError:
            return False

    def validate_bitrate(self, bitrate: int) -> bool:
        try:
            if 500 <= bitrate <= 10000:
                return True
            return False
        except ValueError:
            return False

    def validate_max_zoom(self, max_zoom: float) -> bool:
        try:
            if 8.0 <= max_zoom <= 16.0:
                return True
            return False
        except ValueError:
            return False

    def validate_streaming_protocol(self, streaming_protocol: str) -> bool:
        return streaming_protocol.lower() in [
            StreamingProtocolType.RTP.value,
            StreamingProtocolType.MPEG_TS.value,
        ]

    def validate_radio_type(self, radio_type: str) -> bool:
        return radio_type.lower() in [
            RadioType.MICROHARD.value,
            RadioType.HERELINK.value,
        ]

    def validate_command_protocol(self, command_protocol: str) -> bool:
        return command_protocol.lower() in [
            CommandProtocolType.SOCKET.value,
            CommandProtocolType.ZEROMQ.value,
        ]

    def is_json_file(str, file_name: str) -> bool:
        return os.path.isfile(file_name) and file_name.lower().endswith(".json")
