from picamera2 import Picamera2
import cv2
import numpy as np
import time
import subprocess
import argparse
from pathlib import Path

# Argument parsing
parser = argparse.ArgumentParser(description='Video stabilization script.')
parser.add_argument('--stabilize', action='store_true', help='Whether to stabilize')
parser.add_argument('--resolution', type=str, default='640x360', help='Resolution of the video frames (e.g., 640x360)')
parser.add_argument('--destination_ip', type=str, default='192.168.1.38', help='Destination IP address for RTP stream')
parser.add_argument('--destination_port', type=int, default=5600, help='Destination port for RTP stream')
args = parser.parse_args()

# Initialize the Picamera2 instance
tuning = Picamera2.load_tuning_file(Path("./477-Pi4.json").resolve())
picam2 = Picamera2(tuning=tuning)

# Configure the camera to capture video frames
resolution = tuple(map(int, args.resolution.split('x')))
config = picam2.create_preview_configuration(main={"size": resolution})
picam2.configure(config)

# Start the camera
picam2.start()

# Construct the FFmpeg command
ffmpeg_command = [
    'ffmpeg',
    '-y',  # Overwrite output files without asking
    '-f', 'rawvideo',  # Input format
    '-pix_fmt', 'yuv420p',  # Pixel format
    '-s', f'{resolution[0]}x{resolution[1]}',  # Frame size
    '-i', '-',  # Input from stdin
    '-c:v', 'libx264',  # Video codec
    '-preset', 'ultrafast',  # Faster encoding
    '-tune', 'zerolatency',  # Tune for low latency
    '-bufsize', '64k',  # Reduce buffer size
    '-f', 'rtp',  # Output format
    f'udp://{args.destination_ip}:{args.destination_port}'  # Destination
]

# Start the FFmpeg process
ffmpeg_process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)

# Init frame
fps = []
init_frame = picam2.capture_array()
if args.stabilize:
    prev_gray = cv2.cvtColor(init_frame, cv2.COLOR_RGB2GRAY)

# Main loop
try:
    i = 0
    startt = time.perf_counter()
    while True:
        i += 1
        frame = picam2.capture_array()

        if frame is None or frame.size == 0:
            print("Empty frame captured, skipping...")
            continue

        if args.stabilize:
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
           
            # Apply opencv stabilization algorithms 
            p0 = cv2.goodFeaturesToTrack(prev_gray, maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)
            if p0 is None:
                print("No good features to track, skipping...")
                prev_gray = gray
                continue

            p1, st, err = cv2.calcOpticalFlowPyrLK(prev_gray, gray, p0, None)
            if p1 is None or st is None:
                print("Optical flow calculation failed, skipping...")
                prev_gray = gray
                continue

            # Select good points
            good_new = p1[st == 1]
            good_old = p0[st == 1]

            # Calculate the transformation matrix
            dx = np.mean(good_new[:, 0] - good_old[:, 0])
            dy = np.mean(good_new[:, 1] - good_old[:, 1])
            transform = np.array([[1, 0, -dx], [0, 1, -dy]], dtype=np.float32)

            # Apply the transformation
            try:
                # BORDER_REPLICATE prevents the distracting black edges from forming
                stabilized_frame = cv2.warpAffine(frame, transform, resolution, borderMode=cv2.BORDER_REPLICATE)
            except cv2.error as e:
                print(f"Error applying warpAffine: {e}")
                stabilized_frame = frame

            # Update the previous frame and gray image
            prev_gray = gray
        else:
            stabilized_frame = frame


        # Convert the frame back to YUV format before sending to FFmpeg
        stabilized_frame_8bit = cv2.convertScaleAbs(stabilized_frame)
        stabilized_frame_yuv= cv2.cvtColor(stabilized_frame_8bit, cv2.COLOR_RGB2YUV_I420)
        
        # Forward the stabilized frame to rtp
        ffmpeg_process.stdin.write(stabilized_frame_yuv.tobytes())
        
        # Calculate fps
        if i == 10:
            i = 0
            elapsed_time = time.perf_counter() - startt
            startt = time.perf_counter()
            fps.append(10/elapsed_time)
            print(f"fps={10/elapsed_time} | ")

        # Break the loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    # Stop and cleanup
    picam2.stop()
    cv2.destroyAllWindows()
    print(f"\n\nAverage FPS = {sum(fps)/len(fps)}\n\n")