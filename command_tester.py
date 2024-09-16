#!/usr/bin/env python3

from command_model import add_command, initialize_db
from constants import CommandStatus, CommandType

initialize_db()
add_command(command_type=CommandType.ZOOM.value, command_value="1.0")
add_command(command_type=CommandType.TAKE_PHOTO.value)