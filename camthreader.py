import threading
from picamera2 import Picamera2
from pathlib import Path
from pistreamer_v2 import PiStreamer2
import cv2
import time
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput


class CamThreader:
    def __init__(self, high_res:str, low_res:str, output_file:str):
        self.high_res = tuple(map(int, high_res.split('x')))
        self.low_res = tuple(map(int, low_res.split('x')))
        self.output_file=output_file
        tuning = Picamera2.load_tuning_file(Path("./477-Pi4.json").resolve())
        self.picam2 = Picamera2(tuning=tuning)
        self.semaphore = threading.Semaphore(1)

        # Setup high res config and ffmpeg
        self.low_res_config = self.picam2.create_preview_configuration(main={"size": self.low_res})
        self.high_res_config = self.picam2.create_video_configuration(raw={"size": self.high_res})

    def __del__(self):
        if self.picam2:
            self.picam2.stop()
            cv2.destroyAllWindows()

    
    def _low_res_processing(self):
        """
        Low-res thread for real-time processing and RTP streaming
        """
        with self.semaphore:
            self.picam2.configure(self.low_res_config)
            self.picam2.start()
            stabilizer = PiStreamer2(self.picam2, self.low_res_config, True, self.low_res, "192.168.1.124", "5600")
            stabilizer.stream()

    def _high_res_saving(self):
        """ 
        High-res thread for saving video to disk
        """
        with self.semaphore:
            self.picam2.configure(self.high_res_config)
            self.picam2.start()
            encoder = H264Encoder(10000000)
            output = FfmpegOutput(self.output_file)
            try:
                self.picam2.start_recording(encoder, output)
                print("Recording started. Press Ctrl+C to stop.")
                while True:
                    time.sleep(1) 
            except KeyboardInterrupt:
                self.picam2.stop_recording()
                print("Recording stopped by user.")
            except Exception as e:
                print(f"Error: {e}")
            finally:
                self.picam2.stop_recording()
                self.picam2.stop()
                cv2.destroyAllWindows()
    def start(self):
        threading.Thread(target=self._low_res_processing).start()
        threading.Thread(target=self._high_res_saving).start()

if __name__=="__main__":
    cam_threader = CamThreader(high_res="2028x1080",low_res="640x360",output_file= "high_res.mp4")
    cam_threader.start()