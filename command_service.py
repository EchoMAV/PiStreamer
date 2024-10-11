#!/usr/bin/env python3

from typing import List, Optional, Tuple
from constants import INPUT_FIFO_PATH, OUTPUT_FIFO_PATH, CommandType
import os

"""
Commands are communicated to the pistreamer app via a dedicated FIFO queue and status
is returned back to the mavlink service with a different FIFO queue.
"""


class CommandService:
    def __init__(self):
        if not os.path.exists(INPUT_FIFO_PATH):
            os.mkfifo(INPUT_FIFO_PATH)
        if not os.path.exists(OUTPUT_FIFO_PATH):
            os.mkfifo(OUTPUT_FIFO_PATH)

        # Open FIFO for reading
        self.fifo_input_read = os.open(INPUT_FIFO_PATH, os.O_RDONLY | os.O_NONBLOCK)

    def __del__(self):
        if self.fifo_input_read:
            os.close(self.fifo_input_read)

    def add_input_command(
        self, command_type: CommandType, command_value: Optional[str] = ""
    ) -> None:
        """
        This is a way to write to the input FIFO queue.
        """
        try:
            fifo_input_write = os.open(INPUT_FIFO_PATH, os.O_WRONLY)
            os.write(
                fifo_input_write, f"{command_type.value} {command_value}\n".encode()
            )
            os.close(fifo_input_write)
        except Exception as e:
            print(f"Error writing to input FIFO: {e}")
            raise e

    def add_output_data(self, data: str) -> None:
        """
        This is a way to write to the output FIFO queue.
        """
        try:
            fifo_output_write = os.open(OUTPUT_FIFO_PATH, os.O_WRONLY)
            os.write(fifo_output_write, f"{data}\n".encode())
            os.close(fifo_output_write)
        except Exception as e:
            print(f"Error writing to output FIFO: {e}")

    def get_pending_commands(self) -> List[Tuple[str, str]]:
        """
        Returns the a list of command that has not been read yet from the FIFO.
        The first param in the tuple is the command type followed by the command value.
        If no commands are ready, then an empty list is returned.
        """
        commands = []
        try:
            # Try reading from the FIFO
            data = os.read(self.fifo_input_read, 1024)  # Read up to 1024 bytes
            if data:
                decoded_data = str(data.decode()).split("\n")
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
