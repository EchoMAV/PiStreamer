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

        for command in decoded_data:
            command = command.strip()
            first_space_index = command.find(" ")

            if first_space_index != -1:
                command_type = command[
                    :first_space_index
                ].strip()  # Part before the first space
                command_value = command[
                    first_space_index + 1 :
                ].strip()  # Rest of the string after the first space
            else:
                command_type = (
                    command.strip()
                )  # No space found, entire string is command_type
                command_value = ""

            commands.append(
                (
                    command_type,
                    command_value,
                )
            )
        return commands

    def send_data_out(self, data: str) -> None:
        raise NotImplementedError()

    def get_pending_commands(self) -> List[Tuple[str, str]]:
        raise NotImplementedError()
