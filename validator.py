import os
import ipaddress
from typing import Any, Optional


class Validator:
    def __init__(self, args: Optional[Any] = None) -> None:
        self.args = args
        if self.args:
            self._validate_args()

    def _validate_args(self) -> bool:
        if not self.args:
            return False
        ret = self.validate_ip(str(self.args.gcs_ip))
        if self.args.atak_ip:
            ret = self.validate_ip(str(self.args.atak_ip))
        if self.args.atak_port:
            ret &= self.validate_port(str(self.args.gcs_port))
        ret &= self.validate_port(str(self.args.atak_port))
        ret &= self.validate_bitrate(int(self.args.bitrate))
        ret &= self.is_json_file(str(self.args.config_file))
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

    def validate_max_zoom(self, bitrate: float) -> bool:
        try:
            if 8.0 <= bitrate <= 16.0:
                return True
            return False
        except ValueError:
            return False

    def is_json_file(str, file_name: str) -> bool:
        return os.path.isfile(file_name) and file_name.lower().endswith(".json")
