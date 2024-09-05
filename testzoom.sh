#!/bin/bash

# Loop from 1.0 to 4.0 with a step of 0.1
for x in $(seq 1.0 0.05 8.0)
do
    # Send the zoom command to /tmp/camerad
    echo "zoom $x" > /tmp/camera
    
    # Wait for 0.1 seconds before the next iteration
    sleep 0.05
done

for x in $(seq 8.0 -0.05 1.0)
do
    # Send the zoom command to /tmp/camerad
    echo "zoom $x" > /tmp/camera
    
    # Wait for 0.1 seconds before the next iteration
    sleep 0.05
done