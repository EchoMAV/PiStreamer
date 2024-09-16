# PiStreamer
This is a Python application using the picamera2 library to open a camera on an Rpi and stream it to an RTP UDP endpoint.

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
sudo apt install -y python3-peewee
sudo apt install -y python3-numpy
```

## Non-Daemon operation
For normal (non-daemon) functionality run the script as below:

```
python3 pistreamer_v2.py --destination_ip={IP Address}
```
Once the app is running you can send a variety of commands (from a different session) by writing to the sqlite database through `_command_tester.py`.

## Commands
You can use `_command_tester.py` to issue inserts into the command database. Below are some examples:
```
add_command(command_type=CommandType.ZOOM.value, command_value="1.0") #zoom out fully
add_command(command_type=CommandType.ZOOM.value, command_value="8.0") #zoom in fully
add_command(command_type=CommandType.BITRATE.value, command_value="2000") #set bitrate to 2000 kpbs
add_command(command_type=CommandType.IP_ADDRESS.value, command_value="192.168.1.85") #change endpoint ip to 192.168.1.85
add_command(command_type=CommandType.PORT.value, command_value="5601") #change endpoint port to 5601
add_command(command_type=CommandType.RECORD.value) #start recording to mp4
add_command(command_type=CommandType.STOP_RECORDING) #stop recording to mp4
add_command(command_type=CommandType.TAKE_PHOTO) #take single frame photo at 4K resolution.
```

## Daemon operation
To fork the process and run it in the background, you can use
```
python3 pistreamer_v2.py --destination_ip={IP Address} --stabilize --daemon
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
The command_type `record` will simultaneously record the RTP upsink video frames to mp4. If the file size exceeds 125 MB, a new file is created. The resolution is the same as the GCS receives. `take_photo` will capture a 4K still frame and save to the filesystem. One thing to note about the behavior of picamer2 is that only a single configuration (i.e. resolution) can be active on the camera at a time. In order to switch configuration, the camera but me stopped and restarted with the new configuration.

## Camera configuration file
A camera tuning json file is expected. Starting points for these files for the IMX477 sensor: https://github.com/raspberrypi/libcamera/blob/main/src/ipa/rpi/vc4/data/imx477.json and https://www.arducam.com/wp-content/uploads/2023/12/Arducam-477M-Pi4.json
