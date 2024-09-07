# PiStreamer

This is a Python appication using the picamera2 library to open a camera on an Rpi and stream it to an RTP UDP endpoint.  

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
```

## Non-Daemon operation

For normal (non-daemon) functionality run the script as below

```
python3 pistreamer.py {IP Address} {Port} {Bitrate in kbps} {tuning_json_file}
```
Once the app is running you can send a variety of commands (from a different session) using a named fifo `/tmp/pistreamer`  

## Commands
```
echo "zoom 1.0" > /tmp/pistreamer  #zoom out fully
echo "zoom 8.0" > /tmp/pistreamer  #zoom in fully
echo "bitrate 2000" > /tmp/pistreamer #set bitrate to 2000kpbs
echo "ip 192.168.1.85" > /tmp/pistreamer #change endpoint ip to 192.168.1.85
echo "port 5600" > /tmp/pistreamer #change endpoint port to 5600

```

## Daemon operation

To fork the process and run it in the background, you can use
```
python3 pistreamer.py {IP Address} {Port} {Bitrate in kbps} {tuning_json_file} --daemon
```
### To kill the dameon
```
echo "kill" > /tmp/pistreamer
```
Alternatively you can find the daemon and kill it
```
ps -ax | grep pistreamer
sudo kill -9 {PROCESS_ID_FOUND_ABOVE}  
```

## Camera configuration file

A camera tuning json file is expected. Starting points for these files for the IMX477 sensor: https://github.com/raspberrypi/libcamera/blob/main/src/ipa/rpi/vc4/data/imx477.json and https://www.arducam.com/wp-content/uploads/2023/12/Arducam-477M-Pi4.json
