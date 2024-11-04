# PiStreamer
This is a Python application using the picamera2 library to open a camera on an RPi and perform a series of commands. A full list of support commands can be found at `CommandType`. Here are some common examples:
* Streaming to UDP GCS destination
* Streaming to ATAK
* Capturing still photos
* Recording video
* Changing the digital zoom of the frame
* Stabilizing the stream

## Dependencies
Tested on RPi4 CM running Raspian:
Release date: July 4th 2024
System: 64-bit
Kernel version: 6.6
Debian version: 12 (bookworm)

Software dependencies:
```
sudo apt install -y python3-libcamera libcamera-apps
sudo apt install -y python3-picamera2
sudo apt install -y ffmpeg
sudo apt install -y python3-opencv
sudo apt install -y python3-numpy
```
## GCS Selection
pistreamer_v2 has the option to stream to QGroundControl as the GCS or ATAK. Generally speaking ATAK requires a MPEG-TS video format whereas GCS is a RDP stream. Since a pilot will only need one active GCS at a time, either `ffmpeg_command_atak` or `ffmpeg_command_qgc` will be actively streaming at a time.

## Non-Daemon operation
For normal (non-daemon) functionality run the script as below:

```
python pistreamer_v2.py --gcs_ip={IP Address} --gcs_port={Port} --config_file="./477-Pi4.json"
```
Once the app is running you can send a variety of commands (from a different session) by sending data over a socket defined by `SOCKET_HOST:CMD_SOCKET_PORT`. `_command_tester.py` has several examples you can uncomment and/or modify.

## Commands
You can run `python _command_tester.py` to send data over the cmd socket which the pistreamer will ingest. Below are some examples:
```
_send_data(command_type=CommandType.ZOOM.value, command_value="1.0") #zoom out fully
_send_data(command_type=CommandType.ZOOM.value, command_value="8.0") #zoom in fully
_send_data(command_type=CommandType.BITRATE.value, command_value="2000") #set bitrate to 2000 kpbs
_send_data(command_type=CommandType.IP_ADDRESS.value, command_value="192.168.1.85") #change endpoint ip to 192.168.1.85
_send_data(command_type=CommandType.PORT.value, command_value="5601") #change endpoint port to 5601
_send_data(command_type=CommandType.RECORD.value) #start recording to mp4
_send_data(command_type=CommandType.STOP_RECORDING) #stop recording to mp4
_send_data(command_type=CommandType.TAKE_PHOTO) #take single frame photo at 4K resolution.
_send_data(command_type=CommandType.START_GCS_STREAM) #start the GCS feed
_send_data(command_type=CommandType.STABILIZE, command_value="start") #start stabilization at current framerate
_send_data(command_type=CommandType.STABILIZE, command_value="stop") #stop stabilization at current framerate
```

## Service operation
To run the streamer and all ffmpeg processes in the background configure the script to be a service on the rpi.

## Stabilization
Pass the flag `--stabilization` to the command line to achieve software image stabilization through opencv. Due to the computational overhead of stabilization, a significant FPS penalty is incurred at all resolutions. See the spec table below to evaluate the best options.

## Recording and Still Photos
The command_type `record` will simultaneously record the RTP upsink video frames to a ts video file. The resolution is the same as the GCS receives. `take_photo` will capture a 4K still frame and save to the filesystem. One thing to note about the behavior of picamer2 is that only a single configuration (i.e. resolution) can be active on the camera at a time. In order to switch configuration, the camera but me stopped and restarted with the new configuration.

## Camera configuration file
A camera tuning json file is expected. Starting points for these files for the IMX477 sensor: https://github.com/raspberrypi/libcamera/blob/main/src/ipa/rpi/vc4/data/imx477.json and https://www.arducam.com/wp-content/uploads/2023/12/Arducam-477M-Pi4.json

## IMX477 EchoLITE SBX Performance Specs
Below are bench tested results of the IMX477 functioning at various resolutions and capture modes. Captured video and photo files are saved to the RPi filesystem whilst the streaming destination a RTP feed to a configuration IP and port.

### Resolutions & Aspect Ratios
| Resolution | Aspect Ratio | Notes         |
|------------|--------------|---------------|
| 640x360    | 16:9         | 360p LD       |
| 854x480    | 16:9         | 480p SD       |
| 1280x720   | 16:9         | 720p HD       |
| 1920x1080  | 16:9         | 1080p Full HD |
| 3840x2160  | 16:9         | 4K            |
| 4056x3040  | 4:3          | 12 MP         |

### Streaming Only (2M bitrate)
| Resolution | Avg. Frame Rate | Aspect Ratio | Notes         |
|------------|-----------------|--------------|---------------|
| 640x360    | 50              | 16:9         | 360p LD       |
| 854x480    | 50              | 16:9         | 480p SD       |
| 1280x720   | 45              | 16:9         | 720p HD       |
| 1920x1080  | 20              | 16:9         | 1080p Full HD |

### Streaming + Saved Video (2M bitrate)
| Streaming Resolution | Video Resolution | Avg. Frame Rate |
|----------------------|------------------|-----------------|
| 640x360              | 640x360          | 48              |
| 854x480              | 854x480          | 47              |
| 1280x720             | 1280x720         | 34              |
| 1920x1080            | 1920x1080        | 13              |
| 1280x720             | 3840x2160        | N/A             |

### Streaming + Saved Photo (2M bitrate)
In order to take a photo at higher resolution than streaming resolution, there is a momentary delay in the camera software to switch between resolutions. Capturing photos at the same resolution as streaming incurs no significant delay.
| Streaming Resolution | Photo Resolution | Avg. Photo Delay |
|----------------------|------------------|------------------|
| Not 1920x1080        | 1920x1080        | .75 sec          |
| Not 3840x2160        | 3840x2160        | 1.15 sec         |
| Not 4056x3040        | 4056x3040        | 1.42 sec         |

### Streaming + Saved Video + Saved Photo (2M bitrate)
To save a photo at the same resolution as streaming and recording video, there is no
significant impact to fps or streaming delay. However, if capturing a photo at a
higher resolution than streaming+video, the photo delay time above will apply and the
mp4 file up to that point will be saved and a new mp4 file will resume after the photo
has been captured.

### Stabilized Streaming Only (2M bitrate)
Software stabilization algorithms require significant overhead which lowers the max FPS available.
If this mode is desired 480p is recommended as a fair balance between image quality, FPS, and lag.
| Resolution | Avg. Frame Rate | Aspect Ratio | Notes                                                                  |
|------------|-----------------|--------------|------------------------------------------------------------------------|
| 640x360    | 28              | 16:9         | 360p LD - Higher FPS but may result in more frequency image cropping   |
| 854x480    | 16              | 16:9         | 480p SD - Lower FPS but may contribute to a perceived smoother display |
| 1280x720   | 7               | 16:9         | 720p HD - Lowest FPS which introduces perceived lag. Not recommended.  |
