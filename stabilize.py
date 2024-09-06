import os
import numpy as np

import subprocess
from picamera2 import Picamera2
from picamera2.outputs import FfmpegOutput

def main():
    # Initialize Picamera2
    picam2 = Picamera2()
    
    picam2.configure(picam2.create_video_configuration(raw={'format': 'SBGGR12', 'size': (4056, 3040)}))
    
    # Start the camera
    picam2.start()

    # Define the ffmpeg command with deshake filter
    ffmpeg_command = [
        'ffmpeg',
        '-f', 'rawvideo',  # Input format (rawvideo for video stream)
        '-pix_fmt', 'yuv420p',  # Pixel format
        '-s', '1280x720',  # Resolution (adjust based on your configuration)
        '-r', '30',  # Frame rate
        '-i', '-',  # Input from stdin
        '-c:v', 'libx264',  # Use H.264 encoder
        '-preset', 'ultrafast',  # Encoding speed preset (adjust based on your needs)
        '-tune', 'zerolatency',
        '-vf', 'deshake',  # Apply deshake filter
        '-b:v', '2M',  # Bitrate (adjust based on your needs)
        '-f', 'rtp',  # Output format (adjust based on your needs)
        'rtp://192.168.1.85:5600'  # Replace with your destination URL
    ]
    
    # Start ffmpeg process
    ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Capture video frames and send to ffmpeg process
    try:
        while True:
            # Capture frame from Picamera2
            frame = picam2.capture_array()
            data8 = np.array(frame, dtype=np.uint8)
            # Send frame to ffmpeg process
            ffmpeg_process.stdin.write(data8.view(np.uint16))
    except KeyboardInterrupt:
        # Handle termination
        print("Stopping...")
    finally:
        # Cleanup
        picam2.stop()
        ffmpeg_process.stdin.close()
        ffmpeg_process.wait()

if __name__ == "__main__":
    main()
