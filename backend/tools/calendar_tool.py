import time
import logging

logger = logging.getLogger(__name__)

def schedule_meeting(title: str, date: str, time_str: str, attendees: list = None, duration_minutes: int = 30) -> dict:
    """Mocks scheduling a meeting on Google Calendar / Outlook."""
    logger.info(f"Scheduling meeting: '{title}' on {date} at {time_str}")
    time.sleep(0.9)  # Simulate API call
    
    attendees = attendees or []
    
    return {
        "status": "success",
        "tool": "Calendar Tool",
        "action": "schedule_meeting",
        "details": {
            "title": title,
            "date": date,
            "time": time_str,
            "duration": duration_minutes,
            "attendees": attendees,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "log": f"Meeting '{title}' scheduled successfully on {date} at {time_str} ({duration_minutes} mins) with attendees: {', '.join(attendees) if attendees else 'None'}."
    }
