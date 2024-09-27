from typing import List
from utils import get_timestamp


def get_ffmpeg_command_mp4(resolution: tuple[str, str], framerate: str) -> list[str]:
    # Used for saving data to disk
    return [
        "ffmpeg",
        "-y",  # Overwrite output files without asking
        "-f",
        "rawvideo",  # Input format
        "-pix_fmt",
        "yuv420p",  # Pixel format
        "-s",
        f"{resolution[0]}x{resolution[1]}",  # Frame size
        "-r",
        framerate,  # Frame rate
        "-i",
        "-",  # Input from stdin
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=stereo",  # Add silent audio track
        "-shortest",  # Ensure the shortest stream ends the output
        "-c:v",
        "h264_v4l2m2m",  # Hardware acceleration
        "-b:v",
        "1M",  # Video bitrate
        "-movflags",
        "+faststart",  # Prepare the file for playback
        "-f",
        "mp4",  # Save to mp4
        f"{get_timestamp()}.mp4",  # Output file pattern
    ]


def get_ffmpeg_command_rtp(
    resolution: tuple[str, str],
    framerate: str,
    destination_ip: str,
    destination_port: str,
    streaming_bitrate: str,
) -> List[str]:
    # Used for streaming video to GCS
    return [
        "ffmpeg",
        "-y",  # Overwrite output files without asking
        "-f",
        "rawvideo",  # Input format
        "-pix_fmt",
        "yuv420p",  # Pixel format
        "-s",
        f"{resolution[0]}x{resolution[1]}",  # Frame size
        "-r",
        framerate,  # Frame rate
        "-i",
        "-",  # Input from stdin
        "-c:v",
        "h264_v4l2m2m",  # Hardware acceleration
        "-bufsize",
        "64k",  # Reduce buffer size
        "-b:v",
        streaming_bitrate,  # Set video bitrate
        "-flags",
        "low_delay",  # Low delay for RTP
        "-fflags",
        "nobuffer",  # No buffer for RTP
        "-f",
        "rtp",  # Output format for RTP
        f"rtp://{destination_ip}:{destination_port}",
    ]


def get_ffmpeg_command_atak(
    resolution: tuple[str, str],
    framerate: str,
    destination_ip: str,
    destination_port: str,
    streaming_bitrate: str,
) -> list[str]:
    # Used for streaming video to ATAK
    return [
        "ffmpeg",
        "-y",  # Overwrite output files without asking
        "-f",
        "rawvideo",  # Input format
        "-pix_fmt",
        "yuv420p",  # Pixel format
        "-s",
        f"{resolution[0]}x{resolution[1]}",  # Frame size
        "-r",
        framerate,  # Frame rate
        "-i",
        "-",  # Input from stdin
        "-c:v",
        "h264_v4l2m2m",  # Hardware acceleration
        "-bufsize",
        "64k",  # Reduce buffer size
        "-b:v",
        streaming_bitrate,  # Set video bitrate
        "-flags",
        "low_delay",  # Low delay for RTP
        "-fflags",
        "nobuffer",  # No buffer for RTP
        "-f",
        "mpegts",  # Output format for MPEG-TS
        f"udp://{destination_ip}:{destination_port}",
    ]
