#! /bin/bash

# get the current working directory
CWD=$(pwd)

# remove existing service file
if [ -f /etc/systemd/system/messagePoster.service ]; then
    echo "Removing existing messagePoster service file..."
    sudo rm /etc/systemd/system/messagePoster.service
fi  

# Copy the new service file to systemd directory
echo "Copying new messagePoster service file..."
sudo cp "$CWD/messagePoster.service" /etc/systemd/system/messagePoster.service

# Reload systemd to recognize the new service file
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload