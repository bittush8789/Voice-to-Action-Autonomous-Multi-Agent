import time
import random
import logging

logger = logging.getLogger(__name__)

def create_github_issue(repo: str, title: str, body: str, labels: list = None) -> dict:
    """Mocks creating a GitHub issue in a repository."""
    logger.info(f"Creating GitHub issue in repository {repo}: '{title}'")
    time.sleep(1.0)  # Simulate API call
    
    issue_number = random.randint(1, 150)
    labels = labels or []
    
    return {
        "status": "success",
        "tool": "GitHub Tool",
        "action": "create_github_issue",
        "details": {
            "repo": repo,
            "issue_number": issue_number,
            "title": title,
            "body": body,
            "labels": labels,
            "url": f"https://github.com/{repo}/issues/{issue_number}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "log": f"GitHub issue #{issue_number} successfully opened in {repo}: '{title}'"
    }
