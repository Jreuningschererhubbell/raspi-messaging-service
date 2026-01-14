import json
from loguru import logger
import requests

import ServiceMessenger

class DiscordMessenger(ServiceMessenger.ServiceMessenger):
    def __init__(self, device_name: str, secrets_file: str = "secrets.json"):
        super().__init__(device_name)
        self.service_name = "discord"
        try:
            with open(secrets_file, "r") as f:
                secrets = json.load(f)
                self.discord_webhook_url = secrets.get("discord_webhook_url", "")
        except FileNotFoundError:
            raise Exception("The secrets.json file was not found. Please ensure it exists.")

    def post_message(self, message):
        if not self.discord_webhook_url:
            logger.error("Discord webhook URL is not configured.")
            return False

        payload = {
            "content": f"# Message from {self.device_name}\n{message}",
        }

        try:
            response = requests.post(self.discord_webhook_url, json=payload)
            if response.status_code == 200:
                logger.info("Message posted to Discord successfully.")
                return True
            else:
                logger.error(f"Failed to post message to Discord. Status code: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception occurred while posting to Discord: {e}")
            return False