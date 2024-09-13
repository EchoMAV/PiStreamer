#!/usr/bin/python3
import time
from pathlib import Path

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput

tuning = Picamera2.load_tuning_file(Path("./477-Pi4.json").resolve())
picam2 = Picamera2(tuning=tuning)
# video_config = picam2.create_video_configuration()
video_config = picam2.create_preview_configuration(main={"size": (2028,1080)})
video_config2 = picam2.create_video_configuration()
picam2.configure(video_config2)

encoder = H264Encoder(10000000)

output = FfmpegOutput('testsavelocal.mp4')

picam2.start_recording(encoder, output)
time.sleep(3)
picam2.stop_recording()