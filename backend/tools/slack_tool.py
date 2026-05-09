import time
import logging

logger = logging.getLogger(__name__)

def send_slack_notification(channel: str, message: str) -> dict:
    """Mocks sending a notification to a specific Slack channel."""
    logger.info(f"Sending Slack message to channel {channel}: '{message}'")
    time.sleep(0.8)  # Simulate API call
    
    formatted_channel = channel if channel.startswith("#") else f"#{channel}"
    
    return {
        "status": "success",
        "tool": "Slack Tool",
        "action": "send_slack_notification",
        "details": {
            "channel": formatted_channel,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "log": f"Slack notification posted to {formatted_channel}: '{message}'"
    }
