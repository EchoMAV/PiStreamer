#!/usr/bin/env python3

from command_service import CommandService
from constants import CommandType
import time

command_service = CommandService()

# Modify the command_type and command_value as needed
# command_service.add_input_command(command_type=CommandType.ZOOM, command_value="1.0")
command_service.add_input_command(command_type=CommandType.TAKE_PHOTO)
# command_service.add_input_command(command_type=CommandType.RECORD)
# time.sleep(15)
# command_service.add_input_command(command_type=CommandType.STOP_RECORDING)

command_service.add_input_command(
    command_type=CommandType.ATAK_HOST, command_value="224.1.1.1:5002"
)


# command_service.add_input_command(command_type=CommandType.RECORD)
# time.sleep(15)
# command_service.add_input_command(command_type=CommandType.STOP_RECORDING)
