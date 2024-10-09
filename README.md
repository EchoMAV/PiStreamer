# PiStreamer
This is a Python application using the picamera2 library to open a camera on an RPi and perform a series of commands:
* Streaming to UDP GCS destination
* Streaming to ATAK
* Capturing still photos
* Recording video
* Changing the digital zoom of the frame

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

## Non-Daemon operation
For normal (non-daemon) functionality run the script as below:

```
python pistreamer_v2.py --gcs_ip={IP Address} --gcs_port={Port}
```
Once the app is running you can send a variety of commands (from a different session) via a FIFO by executing `_command_tester.py`.

## Commands
You can run `python _command_tester.py` to writes to the FIFO which the pistreamer will ingest. Below are some examples:
```
command_service = CommandService()
command_service.add_input_command(command_type=CommandType.ZOOM.value, command_value="1.0") #zoom out fully
command_service.add_input_command(command_type=CommandType.ZOOM.value, command_value="8.0") #zoom in fully
command_service.add_input_command(command_type=CommandType.BITRATE.value, command_value="2000") #set bitrate to 2000 kpbs
command_service.add_input_command(command_type=CommandType.IP_ADDRESS.value, command_value="192.168.1.85") #change endpoint ip to 192.168.1.85
command_service.add_input_command(command_type=CommandType.PORT.value, command_value="5601") #change endpoint port to 5601
command_service.add_input_command(command_type=CommandType.RECORD.value) #start recording to mp4
command_service.add_input_command(command_type=CommandType.STOP_RECORDING) #stop recording to mp4
command_service.add_input_command(command_type=CommandType.TAKE_PHOTO) #take single frame photo at 4K resolution.
command_service.add_input_command(command_type=CommandType.START_GCS_STREAM) #start the GCS feed
```

## Daemon operation
To run the streamer and all ffmpeg processes in the background run the following:
```
python pistreamer_v2.py
```

### To kill the dameon
```
echo "kill" > /tmp/pistreamer
```
Alternatively you can find the daemon and kill it
```
ps -ax | grep pistreamer_v2
sudo kill -9 {PROCESS_ID_FOUND_ABOVE}
```

## Stabilization
Pass the flag `--stabilization` to the command line to achieve software image stabilization through opencv. Due to the computation overhead of stabilization,
resolution is limited to `640x360` in order to maintain a natural FPS rate.

## Recording and Still Photos
The command_type `record` will simultaneously record the RTP upsink video frames to a ts video file. The resolution is the same as the GCS receives. `take_photo` will capture a 4K still frame and save to the filesystem. One thing to note about the behavior of picamer2 is that only a single configuration (i.e. resolution) can be active on the camera at a time. In order to switch configuration, the camera but me stopped and restarted with the new configuration.

## Camera configuration file
A camera tuning json file is expected. Starting points for these files for the IMX477 sensor: https://github.com/raspberrypi/libcamera/blob/main/src/ipa/rpi/vc4/data/imx477.json and https://www.arducam.com/wp-content/uploads/2023/12/Arducam-477M-Pi4.json

## IMX477 EchoLITE SBX Performance Specs
Below are bench tested results of the IMX477 functioning at various resolutions and capture modes. Captured video and photo files are saved to the RPi filesystem whilst the streaming destination a RTP feed to a configuration IP and port.

### Resolution & Aspect Ratio
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
