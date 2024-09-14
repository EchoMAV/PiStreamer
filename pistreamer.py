#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import argparse
import ipaddress
import signal
from pathlib import Path
from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from libcamera import controls
from picamera2.outputs import FfmpegOutput

FIFO_PATH = "/tmp/pistreamer"
FIFO_CAM_PATH = "/tmp/imx477"
FRAMERATE = 30
pid = None
original_size =[]
ip = None
port = None
bit = None

def validate_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def validate_port(port):
    try:
        port = int(port)
        if 1 <= port <= 65535:
            return True
        return False
    except ValueError:
        return False

def validate_bitrate(bitrate):
    try:
        bitrate = int(bitrate)
        if 500 <= bitrate <= 10000:
            return True
        return False
    except ValueError:
        return False
    
def is_json_file(file_name):   
    return os.path.isfile(file_name) and file_name.lower().endswith('.json')
    
def cleanup_and_exit(picam2):
    """Stop recording and cleanup before exiting."""
    picam2.stop_recording()
    picam2.stop()
    if os.path.exists(FIFO_PATH):
        os.remove(FIFO_PATH)
    print("Daemon killed. Exiting...")
    os.kill(pid, signal.SIGTERM)  # Terminate the process

def main(destination_ip, destination_port, bitrate, config_file):
    global original_size, ip, port, bit

    ip = destination_ip
    port = destination_port
    bit = bitrate
    # Create the named pipe if it doesn't exist
    if not os.path.exists(FIFO_PATH):
        os.mkfifo(FIFO_PATH)
    
    # Load tuning file
    tuning = Picamera2.load_tuning_file(Path(config_file).resolve())

    # Initialize Picamera2    
    picam2 = Picamera2(tuning=tuning)

    scaledBitrate = int(bitrate) * 1000

    # Set the camera configuration
    #picam2.configure(picam2.create_video_configuration(main={"size": (1280, 720)}))
    picam2.configure(picam2.create_video_configuration())

    # Set the video encoder with H264 and the specified bitrate
    encoder = H264Encoder(bitrate=int(scaledBitrate), repeat=True, framerate=int(FRAMERATE))
    #output = FileOutput(FIFO_CAM_PATH)
    print("Starting...")
    picam2.start()
    original_size = picam2.capture_metadata()['ScalerCrop'][2:]
    #picam2.start_encoder(encoder, output)
    ffmpeg_command = f"-f rtp udp://{destination_ip}:{destination_port}"
    picam2.start_recording(encoder, output=FfmpegOutput(ffmpeg_command))
    # Start the command listener loop
    print(f"Listening on {FIFO_PATH} for commands...")
    while True:
        with open(FIFO_PATH, 'r') as fifo:
            command = fifo.read().strip()
            if command:
                print(f"Received command: {command}")
                handle_command(command, picam2, destination_ip, destination_port, bitrate)

def handle_command(command, picam2, destination_ip, destination_port, bitrate):        
    if command == "stop":
        print("Stopping...")
        picam2.stop_recording()
        picam2.stop()
    elif command == "kill":
        print("Killing daemon...")
        cleanup_and_exit(picam2)
    elif command.startswith("bitrate"):
        try:
            newBitrate = int(command.split(" ")[1])
             # Validate bitrate
            if not validate_bitrate(newBitrate):
                print(f"Error: {newBitrate} is not a valid bitrate. It must be between 500 and 10000 kbps.")                
            else:
                print(f"Setting new bitrate: {newBitrate} kbps with IP: {destination_ip} and Port: {destination_port}")
                set_stream(picam2, destination_ip, destination_port, newBitrate)
        except (IndexError, ValueError):
            print("Invalid bitrate command. Use 'bitrate <value>' where value is an int 500-10000 kbps.")
    elif command.startswith("port"):
        try:
            newPort = int(command.split(" ")[1])
             # Validate port
            if not validate_port(newPort):
                print(f"Error: {newPort} is not a valid port. It must be between 1 and 65535.")                
            else:
                print(f"Setting new port: {newPort} with ip: {ip} and bitrate: {bitrate}")
                set_stream(picam2, destination_ip, newPort, bitrate)
        except (IndexError, ValueError):
            print("Invalid port command. Use 'port <value>' where value is an int between 1 and 65535.")          
    elif command.startswith("ip"):
        try:
            newIP = command.split(" ")[1]
             # Validate ip
            if not validate_ip(newIP):
                print(f"Error: {newIP} is not a valid IP Address.")                
            else:
                print(f"Setting new IP: {newIP}")
                set_stream(picam2, newIP, destination_port, bitrate)
        except (IndexError, ValueError):
            print("Invalid ip command. Use 'ip <value>' where value is a valid ip address.")           
    elif command.startswith("zoom"):
        try:
            zoom_factor = float(command.split(" ")[1])
            set_zoom(picam2, zoom_factor)
        except (IndexError, ValueError):
            print("Invalid zoom command. Use 'zoom <factor>' where factor is a float.")
    else:
        print(f"Unknown command: {command}")

def set_stream(picam2, ip, port, bitrate):    
    picam2.stop_recording()
    picam2.stop()
    encoder = H264Encoder(bitrate=(int(bitrate) * 1000), repeat=True, framerate=int(FRAMERATE))
    #output = FileOutput(FIFO_CAM_PATH)
    print("Updating pipeline...")
    picam2.start()
    original_size = picam2.capture_metadata()['ScalerCrop'][2:]
    #picam2.start_encoder(encoder, output)
    ffmpeg_command = f"-f rtp udp://{ip}:{port}"
    picam2.start_recording(encoder, output=FfmpegOutput(ffmpeg_command))

def set_zoom(picam2, zoom_factor):
    global original_size 
    # Adjust the zoom by setting the crop rectangle
    if zoom_factor < 1.0:
        zoom_factor = 1.0
    elif zoom_factor > 8.0:
        zoom_factor = 8.0  # Max zoom level, adjust based on your requirements

    full_res = picam2.camera_properties['PixelArraySize']    
    print(f"original size {original_size[0]} x {original_size[1]}")
    size = [int(s / zoom_factor) for s in original_size]
    offset = [(r - s) // 2 for r, s in zip(full_res, size)]
    picam2.set_controls({"ScalerCrop": offset + size})
   
    print(f"Zoom set to {zoom_factor}x")

# Function to run a shell command
def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Command succeeded: {command}")
        print(result.stdout)
    else:
        print(f"Command failed: {command}")
        print(result.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Camera Streaming with Picamera2")
    parser.add_argument("ip", help="Destination IP address")
    parser.add_argument("port", help="Destination port number")
    parser.add_argument("bitrate", help="Bitrate in kbps")
    parser.add_argument("config_file", help="Camera configuration json file")
    parser.add_argument("--daemon", action="store_true", help="Run script as a daemon in the background")
    args = parser.parse_args()

    # Validate IP address
    if not validate_ip(args.ip):
        print(f"Error: {args.ip} is not a valid IP address.")
        sys.exit(1)

    # Validate port number
    if not validate_port(args.port):
        print(f"Error: {args.port} is not a valid port number. It must be between 1 and 65535.")
        sys.exit(1)

    # Validate bitrate
    if not validate_bitrate(args.bitrate):
        print(f"Error: {args.bitrate} is not a valid bitrate. It must be between 500 and 10000 kbps.")
        sys.exit(1)

    # Validate config file
    if not is_json_file(args.config_file):
        print(f"Error: {args.config_file} is not a valid json file. Make sure the file exists.")
        sys.exit(1)

    if args.daemon:
        pid = os.fork()
        if pid > 0:
            # Exit the parent process
            print(f"Forked to background with PID {pid}")
            sys.exit()

    # Child process continues to run the main loop
    main(args.ip, args.port, args.bitrate, args.config_file)
    
