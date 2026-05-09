import time
import logging

logger = logging.getLogger(__name__)

def send_email(recipient: str, subject: str, message: str) -> dict:
    """Mocks sending an email to a recipient with a subject and message."""
    logger.info(f"Sending email to {recipient} with subject: '{subject}'")
    time.sleep(1.0)  # Simulate network request
    
    return {
        "status": "success",
        "tool": "Email Tool",
        "action": "send_email",
        "details": {
            "recipient": recipient,
            "subject": subject,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "log": f"Email successfully dispatched to {recipient}. Subject: '{subject}'."
    }
