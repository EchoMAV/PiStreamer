#!/usr/bin/env python3

import os
from typing import Any
from picamera2 import Picamera2
import cv2
import numpy as np
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
import sys
from constants import DEFAULT_CONFIG_PATH, FIFO_PATH, FRAMERATE
from validator import Validator


class PiStreamer2:
    def __init__(self, stabilize:bool, resolution:str, destination_ip:str, destination_port:int) -> None:
        self.picam2 = None
        self.stabilize = stabilize
        self.prev_gray = None
        self.resolution = tuple(map(int, resolution.split('x')))
        self.command_controller = None # set later
        self.destination_ip = destination_ip
        self.destination_port = destination_port
        self.ffmpeg_process_mp4 = None
        self.ffmpeg_process_rtp = None
        self.streaming_bitrate = 1000000
        self.original_size = (0,0)

    def _init_ffmpeg_processes(self) -> None:
        """ 
        Used to configure both the rtp and mp4 FFmpeg commands.
        """
        self._close_ffmpeg_processes()
       
        # Used for saving data to disk
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.ffmpeg_command_mp4 = [
            'ffmpeg',
            '-y',  # Overwrite output files without asking
            '-f', 'rawvideo',  # Input format
            '-pix_fmt', 'yuv420p',  # Pixel format
            '-s', f'{self.resolution[0]}x{self.resolution[1]}',  # Frame size
            '-r', str(FRAMERATE),  # Frame rate
            '-i', '-',  # Input from stdin
                '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',  # Add silent audio track
            '-shortest',  # Ensure the shortest stream ends the output
            '-c:v', 'libx264',  # Video codec for MP4
            '-preset', 'ultrafast',  # Faster encoding
            '-tune', 'zerolatency',  # Tune for low latency
            '-b:v', '1M',  # Video bitrate
            '-movflags', '+faststart',  # Prepare the file for playback
            '-f', 'mp4',  # Output format for MP4
            f'{timestamp}.mp4',  # Output file
            ]

        # Used for streaming video to GCS
        self.ffmpeg_command_rtp = [
            'ffmpeg',
            '-y',  # Overwrite output files without asking
            '-f', 'rawvideo',  # Input format
            '-pix_fmt', 'yuv420p',  # Pixel format
            '-s', f'{self.resolution[0]}x{self.resolution[1]}',  # Frame size
            '-r', str(FRAMERATE),  # Frame rate
            '-i', '-',  # Input from stdin
            '-c:v', 'libx264',  # Video codec for MP4
            '-preset', 'ultrafast',  # Faster encoding
            '-tune', 'zerolatency',  # Tune for low latency
            '-bufsize', '64k',  # Reduce buffer size
            '-b:v', str(self.streaming_bitrate),  # Set video bitrate
            '-flags', 'low_delay',  # Low delay for RTP
            '-fflags', 'nobuffer',  # No buffer for RTP
            '-f', 'rtp',  # Output format for RTP
            f'rtp://{self.destination_ip}:{self.destination_port}'
        ]
        
        # Start the FFmpeg processes
        self.ffmpeg_process_mp4 = subprocess.Popen(self.ffmpeg_command_mp4, stdin=subprocess.PIPE)
        self.ffmpeg_process_rtp = subprocess.Popen(self.ffmpeg_command_rtp, stdin=subprocess.PIPE)


    def __del__(self):
        self.stop_and_clean()

    def _set_command_controller(self, command_controller: Any) -> None:
        """ 
        Circular reference setter.
        """
        self.command_controller = command_controller

    def _stabilize(self, frame:np.ndarray) -> np.ndarray:
        """ 
        This method takes a frame and performs image stabilization algorithms on it.
        The original frame is returned if the stabilization fails. Otherwise, the 
        stabilized frame is returned.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                
        # Apply opencv stabilization algorithms 
        p0 = cv2.goodFeaturesToTrack(self.prev_gray, maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)
        if p0 is None:
            print("No good features to track, skipping...")
            self.prev_gray = gray
            return frame

        p1, st, err = cv2.calcOpticalFlowPyrLK(self.prev_gray, gray, p0, None)
        if p1 is None or st is None:
            print(f"Optical flow calculation failed, skipping... {err}")
            self.prev_gray = gray
            return frame

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
            stabilized_frame = cv2.warpAffine(frame, transform, self.resolution, borderMode=cv2.BORDER_REPLICATE)
        except cv2.error as e:
            print(f"Error applying warpAffine: {e}")
            stabilized_frame = frame

        # Update the previous frame and gray image
        self.prev_gray = gray    

        return stabilized_frame

    def _close_ffmpeg_processes(self) -> None:
        if self.ffmpeg_process_mp4:
            if self.ffmpeg_process_mp4.stdin:
                self.ffmpeg_process_mp4.stdin.close()
            self.ffmpeg_process_mp4.wait()

        if self.ffmpeg_process_rtp:
            if self.ffmpeg_process_rtp.stdin:
                self.ffmpeg_process_rtp.stdin.close()
            self.ffmpeg_process_rtp.wait()

    def stop_and_clean(self) -> None:
        print("Stopping and cleaning camera resources...")
        if self.picam2:
            self.picam2.stop()
        cv2.destroyAllWindows()
        self._close_ffmpeg_processes()
        if os.path.exists(FIFO_PATH):
            os.remove(FIFO_PATH)

    def _read_and_process_commands(self) -> None:
        with open(FIFO_PATH, 'r') as fifo:
            command = fifo.read().strip()
            if command:
                print(f"Received command: {command}")
                self.command_controller.handle_command(command)

    def stream(self) -> None:
        if not os.path.exists(FIFO_PATH):
            os.mkfifo(FIFO_PATH)
        # Start the ffmpeg processes
        self._init_ffmpeg_processes()
        # Start the camera
        tuning = Picamera2.load_tuning_file(Path("./477-Pi4.json").resolve())
        self.picam2 = Picamera2(tuning=tuning)
        config = self.picam2.create_preview_configuration(main={"size": self.resolution})
        self.picam2.configure(config)
        self.picam2.start()
        self.original_size = self.picam2.capture_metadata()['ScalerCrop'][2:]

        # Init frame
        fps = []
        init_frame = self.picam2.capture_array()
        if self.stabilize:
            self.prev_gray = cv2.cvtColor(init_frame, cv2.COLOR_RGB2GRAY)

        # Main loop
        try:
            i = 0
            startt = time.perf_counter()
            while True:
                i += 1
                # Calculate fps
                if i == 10:
                    i = 0
                    elapsed_time = time.perf_counter() - startt
                    startt = time.perf_counter()
                    fps.append(10/elapsed_time)
                    print(f"fps={10/elapsed_time} | ")
                    # with open(FIFO_PATH, 'r') as fifo:
                    #     command = fifo.read().strip()
                    #     if command:
                    #         print(f"Received command: {command}")
                    #         self.command_controller.handle_command(command)

                frame = self.picam2.capture_array()

                if frame is None or frame.size == 0:
                    print("Empty frame captured, skipping...")
                    continue

                if self.stabilize:
                    frame = self._stabilize(frame)

                # Convert the frame back to YUV format before sending to FFmpeg
                frame_8bit = cv2.convertScaleAbs(frame)
                frame_yuv= cv2.cvtColor(frame_8bit, cv2.COLOR_RGB2YUV_I420)
                
                # Forward the stabilized frame to rtp
                self.ffmpeg_process_rtp.stdin.write(frame_yuv.tobytes())
                self.ffmpeg_process_mp4.stdin.write(frame_yuv.tobytes())

                # Break the loop on 'q' key press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            self.stop_and_clean()
            print(f"\n\nAverage FPS = {sum(fps)/len(fps)}\n\n")

if __name__ == "__main__":
    # Argument parsing
    parser = argparse.ArgumentParser(description='Video stabilization script.')
    parser.add_argument('--stabilize', action='store_true', help='Whether to stabilize')
    parser.add_argument('--resolution', type=str, default='640x360', help='Resolution of the video frames (e.g., 640x360)')
    parser.add_argument('--destination_ip', type=str, default='192.168.1.124', help='Destination IP address for RTP stream')
    parser.add_argument('--destination_port', type=int, default=5600, help='Destination port for RTP stream')
    parser.add_argument('--bitrate', type=int, default=1000000, help='Streaming bitrate')
    parser.add_argument('--config_file', type=str, default=DEFAULT_CONFIG_PATH, help='Relative file path for the IMX477 config json file')
    args = parser.parse_args()
    try:
        Validator(args)
    except Exception as e:
        print(f"Validation Error: {e}")
        sys.exit(1)
    pi_streamer = PiStreamer2(args.stabilize, args.resolution, args.destination_ip, args.destination_port)
    from command_controller import CommandController
    controller = CommandController(pi_streamer)
    pi_streamer.stream()