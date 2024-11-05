#!/usr/bin/env python3

from typing import Tuple, List
from command_service import CommandService
from constants import (
    CMD_SOCKET_PORT,
    OUTPUT_SOCKET_PORT,
)
import zmq


"""
Commands are communicated to the pistreamer app via a dedicated socket host:port and
status and other data is returned back to the mavlink service at a different port.
"""


class ZeroMQService(CommandService):
    def __init__(self):
        # Used for receiving commands
        self.receive_context = zmq.Context()
        self.receive_socket = self.receive_context.socket(zmq.PAIR)
        self.receive_socket.connect(f"tcp://localhost:{CMD_SOCKET_PORT}")
        self.receive_socket.setsockopt(
            zmq.SNDHWM, 1000
        )  # limit sender high water mark queue size to 1000 messages
        self.receive_socket.setsockopt(
            zmq.RCVHWM, 1000
        )  # limit receiver high water mark queue size to 1000 messages

        # Used for sending commands
        self.send_context = zmq.Context()
        self.send_socket = self.send_context.socket(zmq.PAIR)
        self.send_socket.bind(
            f"tcp://*:{OUTPUT_SOCKET_PORT}"
        )  # notice we are binding here

        self.send_socket = self.receive_context.socket(zmq.PAIR)
        self.send_socket.connect(f"tcp://localhost:{CMD_SOCKET_PORT}")
        self.send_socket.setsockopt(zmq.SNDHWM, 1000)
        self.send_socket.setsockopt(zmq.RCVHWM, 1000)

    def send_data_out(self, data: str) -> None:
        self.send_socket.send_string(data)

    def get_pending_commands(self) -> List[Tuple[str, str]]:
        try:
            data = self.receive_socket.recv_string(zmq.NOBLOCK)
            return self._get_commands_from_data(data)
        except zmq.Again:
            # No message available, continue processing
            pass
        return []
