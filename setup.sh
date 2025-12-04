#! /bin/bash

# Get the current working directory
CWD=$(pwd)

# Create python virtual environment
echo "Setting up Python virtual environment in $CWD/venv"
python3 -m venv venv
. ./venv/bin/activate
pip install -r requirements.txt

# Create a systemd service file to run the script on boot
cat <<EOL > messagePoster.service
[Unit]
Description=Post IP addresses to Slack

[Service]
Type=simple
WorkingDirectory=$CWD
User=$USER
Restart=on-failure
StartLimitIntervalSec=30
ExecStart=$CWD/venv/bin/python3 $CWD/postIpToSlack.py
Environment="PATH=$CWD/venv/bin:$PATH"
Environment="VIRTUAL_ENV=$CWD/venv"

[Install]
WantedBy=multi-user.target
EOL

# Move the service file to systemd directory and enable it
echo "Setting up systemd service"
sudo cp messagePoster.service /etc/systemd/system/messagePoster.service
sudo systemctl daemon-reload
sudo systemctl enable messagePoster.service
sudo systemctl start messagePoster.service

echo "Setup complete. The messagePoster service is now running."