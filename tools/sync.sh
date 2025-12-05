#! /bin/bash

SSH_TARGET="blue@192.168.68.60"
REMOTE_PATH="/home/blue/raspi-messaging-service"

SYNC_EXCLUDES=(
    "--exclude=.git/"
    "--exclude=venv/"
    "--exclude=__pycache__/"
    "--exclude=.env"
    "--exclude=*.pyc"
    "--exclude=*.log"
)

# Use Rsync to sync files to the remote server.
# If the remote's files are newer, ask for confirmation before overwriting.

# First, check for files on the remote that are newer than local
echo "Checking for newer remote files..."
NEWER_FILES=$(rsync -avzn --delete --update --ignore-existing "${SYNC_EXCLUDES[@]}" $SSH_TARGET:$REMOTE_PATH/ ./ | grep '^>f' | awk '{print $2}')

if [ -n "$NEWER_FILES" ]; then
    echo "The following files are newer on the remote server than your local copies:"
    echo "$NEWER_FILES"
    read -p "Do you want to pull these newer files from the remote before pushing your changes? (y/n): " yn
    case $yn in
        [Yy]*)
            echo "Pulling newer files from remote..."
            rsync -avz --update "${SYNC_EXCLUDES[@]}" $SSH_TARGET:$REMOTE_PATH/ ./
            ;;
        *)
            echo "Skipping pull. Proceeding with sync to remote."
            ;;
    esac
else
    echo "No newer remote files detected."
fi

rsync -avz --progress --update "${SYNC_EXCLUDES[@]}" ./ $SSH_TARGET:$REMOTE_PATH
echo "Sync complete."
