import cv2
from picamera2 import Picamera2, MappedArray
import numpy as np
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
from pathlib import Path

# Initialize Picamera2
tuning = Picamera2.load_tuning_file(Path("./477-Pi4.json").resolve())
picam2 = Picamera2(tuning=tuning)
encoder = H264Encoder(bitrate=int(2000000), repeat=True, framerate=int(30))
config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(config)

# Start recording with the custom callback
ffmpeg_command = f"-f rtp udp://192.168.1.38:5600"
picam2.start_recording(encoder, output=FfmpegOutput(ffmpeg_command))

try:
    while True:
        pass  # Keep the script running
except KeyboardInterrupt:
    pass
finally:
    picam2.stop_recording()