#!/usr/bin/env python3

from typing import Tuple, List

"""
Commands are communicated to the pistreamer app through either through a dedicated socket host:port
or a similar process called ZeroMQ. Status and other data is returned back to the mavlink service
through the same protocol but a different connection.
"""


class CommandService:
    def send_data_out(self, data: str, destination_kwargs: dict) -> None:
        raise NotImplementedError()

    def get_pending_commands(self) -> List[Tuple[str, str]]:
        raise NotImplementedError()
