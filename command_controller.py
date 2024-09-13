#!/usr/bin/env python3

import subprocess
from typing import Any, Union
from constants import PiCameraCommand
from validator import Validator


class CommandController:
    from pistreamer_v2 import PiStreamer2
    def __init__(self, pi_streamer: PiStreamer2) -> None:
        self.pi_streamer = pi_streamer
        self.validator = Validator()
        self.pi_streamer._set_command_controller(self)

    def handle_command(self,command:str):    
        if command == PiCameraCommand.STOP.value:
            self.pi_streamer.stop_and_clean()
        elif command == PiCameraCommand.KILL.value:
            # TODO kill daemon
            self.pi_streamer.stop_and_clean()
        elif command.startswith(PiCameraCommand.BITRATE.value):
            try:
                bitrate = int(command.split(" ")[1])
                if not self.validator.validate_bitrate(bitrate):
                    print(f"Error: {bitrate} is not a valid bitrate. It must be between 500 and 10000 kbps.")                
                else:
                    print(f"Setting new bitrate: {bitrate} kbps")
                    self.reset_stream(("streaming_bitrate", bitrate))
            except (IndexError, ValueError):
                print("Invalid bitrate command. Use 'bitrate <value>' where value is an int 500-10000 kbps.")
        elif command.startswith(PiCameraCommand.PORT.value):
            try:
                new_port = int(command.split(" ")[1])
                if not self.validator.validate_port(new_port):
                    print(f"Error: {new_port} is not a valid port. It must be between 1 and 65535.")                
                else:
                    print(f"Setting new port: {new_port}")
                    self.reset_stream(("destination_port", new_port))
            except (IndexError, ValueError):
                print("Invalid port command. Use 'port <value>' where value is an int between 1 and 65535.")          
        elif command.startswith(PiCameraCommand.IP_ADDRESS.value):
            try:
                new_iP = command.split(" ")[1]
                if not self.validator.validate_ip(new_iP):
                    print(f"Error: {new_iP} is not a valid IP Address.")                
                else:
                    print(f"Setting new IP: {new_iP}")
                    self.reset_stream(("destination_ip", new_iP))
            except (IndexError, ValueError):
                print("Invalid ip command. Use 'ip <value>' where value is a valid ip address.")           
        elif command.startswith("zoom"):
            try:
                zoom_factor = float(command.split(" ")[1])
                self.set_zoom(zoom_factor)
            except (IndexError, ValueError):
                print("Invalid zoom command. Use 'zoom <factor>' where factor is a float.")
        else:
            print(f"Unknown command: {command}")

    def reset_stream(self, field_values: list[tuple[str, Any]]):  
        """ 
        The pi_streamer controls the major properties of the stream. This function pauses
        the current stream, sets the new value, and resumes the stream.
        """
        self.pi_streamer.stop_and_clean()
        for field, value in field_values:
            setattr(self.pi_streamer, field, value)
        self.pi_streamer.stream()

    def set_zoom(self,zoom_factor:Union[int,float]) -> None:
        # Adjust the zoom by setting the crop rectangle
        if zoom_factor < 1.0:
            zoom_factor = 1.0
        elif zoom_factor > 8.0:
            zoom_factor = 8.0  # Max zoom level, adjust based on your requirements

        full_res = self.pi_streamer.picam2.camera_properties['PixelArraySize']    
        print(f"original size {self.pi_streamer.original_size[0]} x {self.pi_streamer.original_size[1]}")
        size = [int(s / zoom_factor) for s in self.pi_streamer.original_size]
        offset = [(r - s) // 2 for r, s in zip(full_res, size)]
        self.pi_streamer.picam2.set_controls({"ScalerCrop": offset + size})
        print(f"Zoom set to {zoom_factor}x")

    # Function to run a shell command
    def run_command(self,command):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Command succeeded: {command}")
            print(result.stdout)
        else:
            print(f"Command failed: {command}")
            print(result.stderr)
        
