#!/usr/bin/env python3

from typing import Tuple, List
from command_service import CommandService
from constants import CMD_SOCKET_HOST, CMD_SOCKET_PORT, MAX_SOCKET_CONNECTIONS
import zmq


"""
Commands are communicated to the pistreamer app via a dedicated socket host:port and
status and other data is returned back to the mavlink service at a different port.
"""


class ZeroMQService(CommandService):
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.connect(f"tcp://localhost:{CMD_SOCKET_PORT}")
        self.socket.setsockopt(
            zmq.SNDHWM, 1000
        )  # limit sender high water mark queue size to 1000 messages
        self.socket.setsockopt(
            zmq.RCVHWM, 1000
        )  # limit receiver high water mark queue size to 1000 messages

    def send_data_out(self, data: str, destination_kwargs: dict) -> None:
        pass

    def get_pending_commands(self) -> List[Tuple[str, str]]:
        try:
            data = self.socket.recv_string(zmq.NOBLOCK)
            return self._get_commands_from_data(data)
        except zmq.Again:
            # No message available, continue processing
            pass
        return []
