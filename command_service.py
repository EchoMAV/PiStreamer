#!/usr/bin/env python3

from typing import Tuple, List, Any

"""
Commands are communicated to the pistreamer app through either through a dedicated socket host:port
or a similar process called ZeroMQ. Status and other data is returned back to the mavlink service
through the same protocol but a different connection.
"""


class CommandService:
    def _get_commands_from_data(self, data: str) -> List[Any]:
        commands: List[Any] = []

        if not data:
            return commands

        decoded_data = str(data).split("\n")
        decoded_data = [str(item).strip() for item in decoded_data if item]
        print(f"Received {len(decoded_data)} total command(s): {decoded_data}")
        for command in decoded_data:
            command_details = command.strip().split(" ")
            commands.append(
                (
                    command_details[0].strip(),
                    command_details[1].strip() if len(command_details) > 1 else "",
                )
            )
        return commands

    def send_data_out(self, data: str) -> None:
        raise NotImplementedError()

    def get_pending_commands(self) -> List[Tuple[str, str]]:
        raise NotImplementedError()
