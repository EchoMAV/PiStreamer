#!/usr/bin/env python3

"""
Same file between pistreamer, monark-updater, and microhard

# TODO refactor to be its own package and importable.
"""

from typing import Final
import RPi.GPIO as GPIO
import time

BUZZER_PIN = 6
QUICK_BEEP_DURATION = 0.08
BEEP_SPACING = 0.065
NOTE_DURATION = QUICK_BEEP_DURATION + BEEP_SPACING
# Every "sixteenth note" in the measure is 0.145 seconds (NOTE_DURATION = QUICK_BEEP_DURATION + BEEP_SPACING)
# That means means every measure is 16 * 0.145 = 2.32 seconds (HEART_BEEP_MEASURE_DURATION)
HEART_BEEP_MEASURE_DURATION = 16 * NOTE_DURATION
GPIO_HIGH: Final = 0  # the SBX board inverts this logic
GPIO_LOW: Final = 1  # the SBX board inverts this logic


class BuzzerService:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUZZER_PIN, GPIO.OUT)

    def quiet(self) -> None:
        GPIO.output(BUZZER_PIN, GPIO_LOW)

    def quick_beep(self) -> None:
        try:
            GPIO.output(BUZZER_PIN, GPIO_HIGH)
            time.sleep(QUICK_BEEP_DURATION)
            GPIO.output(BUZZER_PIN, GPIO_LOW)
            time.sleep(BEEP_SPACING)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def long_beep(self) -> None:
        try:
            GPIO.output(BUZZER_PIN, GPIO_HIGH)
            time.sleep(8.0 * NOTE_DURATION)
            GPIO.output(BUZZER_PIN, GPIO_LOW)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def single_heartbeat(self) -> None:
        try:
            while True:
                self.quick_beep()
                time.sleep(HEART_BEEP_MEASURE_DURATION - NOTE_DURATION)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def double_heartbeat(self) -> None:
        try:
            while True:
                self.quick_beep()
                self.quick_beep()
                time.sleep(HEART_BEEP_MEASURE_DURATION - (2.0 * NOTE_DURATION))
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def triple_heartbeat(self) -> None:
        try:
            while True:
                self.quick_beep()
                self.quick_beep()
                self.quick_beep()
                time.sleep(HEART_BEEP_MEASURE_DURATION - (3.0 * NOTE_DURATION))
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def success_beeps(self) -> None:
        try:
            self.quick_beep()
            self.quick_beep()
            time.sleep(2.0 * NOTE_DURATION)
            GPIO.output(BUZZER_PIN, GPIO_HIGH)
            time.sleep(4.0 * NOTE_DURATION)
            GPIO.output(BUZZER_PIN, GPIO_LOW)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def two_long_failure_beeps(self) -> None:
        try:
            self.long_beep()
            time.sleep(2.0 * NOTE_DURATION)
            self.long_beep()
            GPIO.output(BUZZER_PIN, GPIO_LOW)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def three_long_failure_beeps(self) -> None:
        try:
            self.long_beep()
            time.sleep(2.0 * NOTE_DURATION)
            self.long_beep()
            time.sleep(2.0 * NOTE_DURATION)
            self.long_beep()
            GPIO.output(BUZZER_PIN, GPIO_LOW)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def four_quick_beeps(self) -> None:
        try:
            for _ in range(0, 4):
                self.quick_beep()
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def five_spaced_out_beeps(self) -> None:
        try:
            for _ in range(0, 5):
                self.quick_beep()
                time.sleep(NOTE_DURATION)
        except Exception:
            GPIO.output(BUZZER_PIN, GPIO_LOW)

    def death_beep(self) -> None:
        """
        Beep and never stop :(
        """
        GPIO.output(BUZZER_PIN, GPIO_HIGH)
