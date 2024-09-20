#!/usr/bin/env python3

from command_model import add_command, initialize_db
from constants import CommandStatus, CommandType
import time
initialize_db()

# Modify the command_type and command_value as needed
add_command(command_type=CommandType.ZOOM, command_value="1.0")
add_command(command_type=CommandType.TAKE_PHOTO)
add_command(command_type=CommandType.RECORD)
time.sleep(15)
add_command(command_type=CommandType.STOP_RECORDING)
