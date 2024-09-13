import argparse
import os
import ipaddress
from typing import Optional

class Validator():
    def __init__(self, args: Optional[argparse.ArgumentParser] = None) -> None:
        self.args = args
        if self.args:
            self._validate_args()

    def _validate_args(self) -> None:
        self.validate_ip(self.args.destination_ip)
        self.validate_port(self.args.destination_port)
        self.validate_bitrate(self.args.bitrate)
        self.is_json_file(self.args.config_file)

    def validate_ip(self, ip: str) -> None:
            try:
                ipaddress.ip_address(ip)
                return True
            except ValueError:
                return False

    def validate_port(self, port: str) -> None:
        try:
            port = int(port)
            if 1 <= port <= 65535:
                return True
            return False
        except ValueError:
            return False

    def validate_bitrate(self, bitrate: str) -> None:
        try:
            bitrate = int(bitrate)
            if 500 <= bitrate <= 10000:
                return True
            return False
        except ValueError:
            return False
        
    def is_json_file(str, file_name:str) -> None:   
        return os.path.isfile(file_name) and file_name.lower().endswith('.json')
