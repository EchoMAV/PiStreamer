import os
import sys
import time
import subprocess
import argparse
import ipaddress
import signal
from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from libcamera import controls
from picamera2.outputs import FfmpegOutput

FIFO_PATH = "/tmp/pistreamer"
FIFO_CAM_PATH = "/tmp/imx477"
DESTINATION_IP="192.168.1.59"
DESTINATION_PORT="5600"
BITRATE=2000000
pid = None
original_size =[]

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
    
def cleanup_and_exit(picam2):
    """Stop recording and cleanup before exiting."""
    picam2.stop_recording()
    picam2.stop()
    if os.path.exists(FIFO_PATH):
        os.remove(FIFO_PATH)
    print("Daemon killed. Exiting...")
    os.kill(pid, signal.SIGTERM)  # Terminate the process

def main(destination_ip, distination_port, bitrate):
    global original_size 
    # Create the named pipe if it doesn't exist
    if not os.path.exists(FIFO_PATH):
        os.mkfifo(FIFO_PATH)

    # Initialize Picamera2
    tuning = Picamera2.load_tuning_file("477-Pi4.json")

    picam2 = Picamera2(tuning=tuning)

    scaledBitrate = int(bitrate) * 1000

    # Set the camera configuration
    #picam2.configure(picam2.create_video_configuration(main={"size": (1280, 720)}))
    picam2.configure(picam2.create_video_configuration())

    # Set the video encoder with H264 and the specified bitrate
    encoder = H264Encoder(bitrate=int(scaledBitrate), repeat=True, framerate=35)
    #output = FileOutput(FIFO_CAM_PATH)
    print("Starting...")
    picam2.start()
    original_size = picam2.capture_metadata()['ScalerCrop'][2:]
    #picam2.start_encoder(encoder, output)
    ffmpeg_command = f"-f rtp udp://{destination_ip}:{distination_port}"
    picam2.start_recording(encoder, output=FfmpegOutput(ffmpeg_command))
    # Start the command listener loop
    print(f"Listening on {FIFO_PATH} for commands...")
    while True:
        with open(FIFO_PATH, 'r') as fifo:
            command = fifo.read().strip()
            if command:
                print(f"Received command: {command}")
                handle_command(command, picam2)

def handle_command(command, picam2):    
    if command == "stop":
        print("Stopping...")
        picam2.stop_recording()
        picam2.stop()
    elif command == "kill":
        print("Killing daemon...")
        cleanup_and_exit(picam2)
    elif command.startswith("zoom"):
        try:
            zoom_factor = float(command.split(" ")[1])
            set_zoom(picam2, zoom_factor)
        except (IndexError, ValueError):
            print("Invalid zoom command. Use 'zoom <factor>' where factor is a float.")
    else:
        print(f"Unknown command: {command}")

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

    pid = os.fork()
    if pid > 0:
        # Exit the parent process
        print(f"Forked to background with PID {pid}")
        sys.exit()

    # Child process continues to run the main loop
    main(args.ip, args.port, args.bitrate)
    