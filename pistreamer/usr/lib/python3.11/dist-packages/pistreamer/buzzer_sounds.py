import RPi.GPIO as GPIO
import time
from constants import ON_DURATION, SLOW_HEART_BEEP_DURATION, BUZZER_PIN

"""
# Buzzer Specs
## Pairing Drone
Single beep slow heartbeat (Drone is in pairing mode scanning for QR codes)
Three quick beeps (Drone has successfully scanned the QR code)
Double beep slow heartbeat (Pairing is in progress)
## SD Card Operations
Single quick beep (SD card detected)
Double beep fast heartbeat (Software update in progress)
"""


class BuzzerService:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUZZER_PIN, GPIO.OUT)

    def quick_beep(self):
        try:
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            time.sleep(ON_DURATION)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            time.sleep(0.065)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO.LOW)

    def double_beep_slow_heartbeat(self):
        try:
            while True:
                self.quick_beep()
                self.quick_beep()
                time.sleep(SLOW_HEART_BEEP_DURATION)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO.LOW)

    def single_beep_slow_heartbeat(self):
        try:
            while True:
                self.quick_beep()
                time.sleep(SLOW_HEART_BEEP_DURATION)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO.LOW)

    def three_quick_beeps(self):
        try:
            for _ in range(0, 3):
                self.quick_beep()
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO.LOW)
