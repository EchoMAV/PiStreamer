from typing import List, Tuple


def get_ffmpeg_command_record(
    resolution: Tuple[int, ...], framerate: str, file_name: str
) -> List[str]:
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
        "mpegts",  # Save to mpegts
        file_name,  # Output file pattern
    ]


def get_ffmpeg_command_qgc(
    resolution: Tuple[int, ...],
    framerate: str,
    qgc_ip: str,
    qgc_port: str,
    streaming_bitrate: str,
) -> List[str]:
    """
    Used for streaming video to QGroundControl as the GCS
    """
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
        f"rtp://{qgc_ip}:{qgc_port}",
    ]


def get_ffmpeg_command_atak(
    resolution: Tuple[int, ...],
    framerate: str,
    atak_ip: str,
    atak_port: str,
    streaming_bitrate: str,
) -> List[str]:
    """
    Used for streaming video to ATAK as the GCS
    """
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
        f"udp://{atak_ip}:{atak_port}",
    ]
