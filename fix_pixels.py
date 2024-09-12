import subprocess
import cv2
import numpy as np
from picamera2 import Picamera2
import argparse
parser = argparse.ArgumentParser(description='Video stabilization script.')
parser.add_argument('--resolution', type=str, default='640x360', help='Resolution of the video frames (e.g., 640x360)')
parser.add_argument('--destination_ip', type=str, default='192.168.1.38', help='Destination IP address for RTP stream')
parser.add_argument('--destination_port', type=int, default=5600, help='Destination port for RTP stream')

args = parser.parse_args()

resolution = tuple(map(int, args.resolution.split('x')))

# Initialize the camera

# Construct the FFmpeg command
ffmpeg_command = [
    'ffmpeg',
    '-y',  # Overwrite output files without asking
    '-f', 'rawvideo',  # Input format
    '-pix_fmt', 'yuv420p',  # Pixel format
    '-s', f'{args.resolution[0]}x{resolution[1]}',  # Frame size
    '-r', '30',  # Frame rate
    '-i', '-',  # Input from stdin
    # '-vf', f'crop={resolution[0]-40}:{resolution[1]-40},pad={resolution[0]}:{resolution[1]}:20:20:pink',  # Crop and pad
    '-c:v', 'libx264',  # Video codec
    '-preset', 'ultrafast',  # Faster encoding
    '-tune', 'zerolatency',  # Tune for low latency
    '-bufsize', '64k',  # Reduce buffer size
    '-f', 'rtp',  # Output format
    f'udp://{args.destination_ip}:{args.destination_port}'  # Destination
]

# Start the FFmpeg process
ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)
try:
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(raw={"format": "SRGGB12", "size": resolution})
    picam2.configure(config)
    picam2.start()
    while True:
        # Capture raw Bayer image
        raw_image = picam2.capture_array("raw")

        # Debayer the image to RGB
        rgb_image = cv2.cvtColor(raw_image, cv2.COLOR_BAYER_RG2RGB)

        # Convert RGB to YUV420p for RTP streaming
        yuv_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2YUV_I420)

        ffmpeg_process.stdin.write(yuv_image.tobytes())

except:
    # Stop the camera
    # picam2.stop()
    cv2.destroyAllWindows()
    # print(f"\n\nAverage FPS = {sum(fps)/len(fps)}\n\n")

finally:
    # Clean up
    picam2.stop()
    ffmpeg_process.stdin.close()
    ffmpeg_process.wait()