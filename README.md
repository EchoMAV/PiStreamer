# PiStreamer

This is a Python appication using the picamera2 library to open a camera on an Rpi and stream it to an RTP UDP endpoint.  

The application runs as a daemon, which allows you to start it and run it in the background, and then interact with the daemon using a shared FIFO.  

## To start

python3 camerad.py {ip address} {port} {bitrate in kpbs}

## To modify

zoom full out: `echo "zoom 1.0" > /tmp/pistreamer`  
zoom full IN: `echo "zoom 8.0" > /tmp/pistreamer`  

To stop the daemon `echo "kill" > /tmp/pistreamer`  

To do  
[ ] Ability to control bitrate
[ ] Ability to control destination ip and port at runtime
