#! /bin/bash

# Get the current working directory
CWD=$(pwd)

# Disable service
echo "Disabling messagePoster service..."
sudo systemctl disable messagePoster.service
sudo systemctl stop messagePoster.service
echo "messagePoster service disabled."

# Remove service file
if [ -f /etc/systemd/system/messagePoster.service ]; then
    echo "Removing messagePoster service file..."
    sudo rm /etc/systemd/system/messagePoster.service
    echo "Service file removed."
else
    echo "No service file found to remove."
fi

# Reload systemd to apply changes
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Uninstallation complete."