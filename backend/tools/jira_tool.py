import time
import random
import logging

logger = logging.getLogger(__name__)

def create_jira_ticket(project_key: str, summary: str, description: str, issue_type: str = "Task", priority: str = "Medium") -> dict:
    """Mocks creating a Jira ticket in a project."""
    logger.info(f"Creating Jira ticket in project {project_key}: '{summary}'")
    time.sleep(1.2)  # Simulate API call
    
    ticket_id = f"{project_key.upper()}-{random.randint(100, 999)}"
    
    return {
        "status": "success",
        "tool": "Jira Tool",
        "action": "create_jira_ticket",
        "details": {
            "ticket_id": ticket_id,
            "project_key": project_key.upper(),
            "summary": summary,
            "description": description,
            "issue_type": issue_type,
            "priority": priority,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "log": f"Jira ticket {ticket_id} created successfully. Type: {issue_type}, Priority: {priority}."
    }
