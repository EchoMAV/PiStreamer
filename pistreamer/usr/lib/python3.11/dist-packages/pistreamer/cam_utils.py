#!/usr/bin/env python3
from datetime import datetime


def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
