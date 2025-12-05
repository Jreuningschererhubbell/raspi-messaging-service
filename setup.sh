#! /bin/bash

# See if a full reinstall has been requested
if [ "$1" == "--full-reinstall" ]; then
    echo "Performing full reinstall: removing existing virtual environment and service file."
    rm -rf venv
fi


# Get the current working directory
CWD=$(pwd)

### Configuration Check ###
# Check for service_config.json file
if [ ! -f "$CWD/service_config.json" ]; then
    echo "Configuration file service_config.json not found!"
    echo "Please create service_config.json based on service_config_template.json and fill in the required details."
    exit 1
else
    echo "Configuration file service_config.json found."
fi

# Check for secrets.json file
if [ ! -f "$CWD/secrets.json" ]; then
    echo "Secrets file secrets.json not found!"
    echo "Please create secrets.json based on secrets_template.json and fill in the required secrets."
    exit 1
else
    echo "Secrets file secrets.json found."
fi


### Python Virtual Environment Setup ###

# See if the virtual environment already exists
if [ -d "$CWD/venv" ]; then
    echo "Virtual environment already exists. Skipping environment creation."
else 
    # Create python virtual environment
    echo "Setting up Python virtual environment in $CWD/venv"
    python3 -m venv venv
fi

# Activate the virtual environment and install required packages
echo "Activating virtual environment and installing required packages."
. ./venv/bin/activate
pip install -r requirements.txt



# Create a systemd service file to run the script on boot
cat <<EOL > messagePoster.service
[Unit]
Description=Post IP addresses to Slack
Wants=network.target
StartLimitIntervalSec=30
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory=$CWD
User=$USER
Restart=on-failure
ExecStart=$CWD/venv/bin/python3 $CWD/postIpToSlack.py
Environment="PATH=$CWD/venv/bin:$PATH"
Environment="VIRTUAL_ENV=$CWD/venv"
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL


### Systemd Service Setup ###

# If service file already exists, inform user and remove
if [ -f /etc/systemd/system/messagePoster.service ]; then
    echo "Existing messagePoster service file found. Removing it..."
    sudo rm /etc/systemd/system/messagePoster.service
fi  

# Copy the new service file to systemd directory
echo "Copying new messagePoster service file..."
sudo cp "$CWD/messagePoster.service" /etc/systemd/system/messagePoster.service

# Reload systemd to recognize the new service file
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

sudo systemctl enable --now messagePoster.service

echo "Setup complete. The messagePoster service is now running."