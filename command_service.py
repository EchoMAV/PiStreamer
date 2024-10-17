#!/usr/bin/env python3

from typing import Any, Tuple, List
from constants import CMD_SOCKET_HOST, CMD_SOCKET_PORT, MAX_SOCKET_CONNECTIONS
import socket
import select

"""
Commands are communicated to the pistreamer app via a dedicated socket host:port and
status and other data is returned back to the mavlink service at a different port.
"""


class CommandService:
    def __init__(self):
        # Create the server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((CMD_SOCKET_HOST, CMD_SOCKET_PORT))
        self.server_socket.listen(MAX_SOCKET_CONNECTIONS)

        print(
            f"{__name__} listening for data on socket {CMD_SOCKET_HOST}:{CMD_SOCKET_PORT}"
        )
        self.server_socket.setblocking(False)

        # Accept a single client connection (blocking until a connection is made)
        self.client_socket, self.client_address = None, None

    def _accept_client(self):
        try:
            ready_to_read, _, _ = select.select(
                [self.server_socket], [], [], 0
            )  # don't wait
            if ready_to_read:
                self.client_socket, self.client_address = self.server_socket.accept()
                self.client_socket.setblocking(
                    False
                )  # Set the client socket to non-blocking mode
                print(f"Accepted connection from {self.client_address}")
        except BlockingIOError:
            # No incoming connections, handle this case as needed
            pass

    def _read_socket(self) -> str:
        self._accept_client()
        if self.client_socket:
            ready_to_read, _, _ = select.select(
                [self.client_socket], [], [], 0
            )  # don't wait
            if ready_to_read:
                try:
                    # Try to receive data from the client
                    data = self.client_socket.recv(1024)
                    if data:
                        return data.decode()
                except Exception as e:
                    if e:
                        print(e)
        return ""

    @staticmethod
    def send_data_out(data: str, host: str, port: int) -> None:
        """
        Used to send data out over another host:port client socket connection.
        """
        try:
            _data = data.strip().encode()
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            client_socket.sendall(_data)
        except Exception as e:
            print(f"{host}:{port} {e}")
        finally:
            client_socket.close()

    def get_pending_commands(self) -> List[Tuple[str, str]]:
        """
        Returns the a list of command that has not been read yet from the socket.
        The first param in the tuple is the command type followed by the command value.
        If no commands are ready, then an empty list is returned.
        """
        commands = []
        try:
            # Try reading from the socket
            data = self._read_socket()
            if data:
                decoded_data = str(data).split("\n")
                decoded_data = [str(item).strip() for item in decoded_data if item]
                print(f"Received {len(decoded_data)} total command(s): {decoded_data}")
                for command in decoded_data:
                    command_details = command.strip().split(" ")
                    commands.append(
                        (
                            command_details[0].strip(),
                            command_details[1].strip()
                            if len(command_details) > 1
                            else "",
                        )
                    )
        except Exception as e:
            print(e)

        return commands
