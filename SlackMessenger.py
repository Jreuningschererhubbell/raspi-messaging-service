import json
from loguru import logger
import requests

class SlackMessenger:
    def __init__(self, device_name: str, secrets_file: str = "secrets.json"):
        try:
            with open(secrets_file, "r") as f:
                secrets = json.load(f)
                self.slack_webhook_url = secrets.get("slack_webhook_url", "")
        except FileNotFoundError:
            raise Exception("The secrets.json file was not found. Please ensure it exists.")
        
        self.name = device_name

    def post_message(self, message):
        if not self.slack_webhook_url:
            logger.error("Slack webhook URL is not configured.")
            return False

        payload = {
            "host": self.name,
            "msg": message
        }

        try:
            response = requests.post(self.slack_webhook_url, json=payload)
            if response.status_code == 200:
                logger.info("Message posted to Slack successfully.")
                return True
            else:
                logger.error(f"Failed to post message to Slack. Status code: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception occurred while posting to Slack: {e}")
            return False