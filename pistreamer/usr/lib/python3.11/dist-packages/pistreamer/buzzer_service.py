#!/usr/bin/env python3
from typing import Final
import RPi.GPIO as GPIO
import time

BUZZER_PIN = 6
ON_DURATION = 0.08
SLOW_HEART_BEEP_DURATION = 2.75
FAST_HEART_BEEP_DURATION = 2.0
GPIO_HIGH: Final = 0  # the SBX board inverts this logic
GPIO_LOW: Final = 1  # the SBX board inverts this logic
"""
# Buzzer Specs
## Pairing Drone
Single double beep slow heartbeat (Drone is in pairing mode scanning for QR codes)
Three quick beeps (Drone has successfully scanned the QR code)
Double beep slow heartbeat (Pairing is in progress)
"""


class BuzzerService:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUZZER_PIN, GPIO.OUT)

    def quick_beep(self):
        try:
            GPIO.output(BUZZER_PIN, GPIO_HIGH)
            time.sleep(ON_DURATION)
            GPIO.output(BUZZER_PIN, GPIO_LOW)
            time.sleep(0.065)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def double_beep_slow_heartbeat(self):
        try:
            while True:
                self.quick_beep()
                self.quick_beep()
                time.sleep(SLOW_HEART_BEEP_DURATION)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def single_beep_slow_heartbeat(self):
        try:
            while True:
                self.quick_beep()
                time.sleep(SLOW_HEART_BEEP_DURATION)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def three_quick_beeps(self):
        try:
            for _ in range(0, 3):
                self.quick_beep()
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def long_beep(self):
        try:
            GPIO.output(BUZZER_PIN, GPIO_HIGH)
            time.sleep(3)
            GPIO.output(BUZZER_PIN, GPIO_LOW)
            time.sleep(0.065)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)
