"""MCP Server entry point for Bitbucket PR Manager.

Initializes FastMCP server with validated configuration and authenticated client.
All logging output goes to stderr to avoid corrupting stdio protocol.
"""

# CRITICAL: Configure logging to stderr BEFORE any other imports
# This ensures all logs (including from imported modules) go to stderr
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Now import other modules (their logs will also go to stderr)
from mcp.server.fastmcp import FastMCP
from src.config import BitbucketConfig
from src.client import BitbucketClient

# Validate configuration on import (fail fast)
try:
    config = BitbucketConfig.from_env()
    logger.info(f"Configuration loaded for workspace: {config.bitbucket_workspace}")
except ValueError as e:
    logger.error(str(e))
    sys.exit(1)

# Initialize Bitbucket client
bitbucket_client = BitbucketClient(config)

def _truncate_diff(diff_text: str, max_chars: int = 10000) -> str:
    """Truncate diff to max_chars using breadth-first strategy.
    
    Strategy: Include as many complete files as possible.
    Files are separated by 'diff --git' lines.
    
    Args:
        diff_text: Raw git diff text
        max_chars: Maximum characters to return (default 10000)
        
    Returns:
        Truncated diff with indicator if needed
    """
    if not diff_text or len(diff_text) <= max_chars:
        return diff_text
    
    # Split by file boundaries
    files = diff_text.split('\ndiff --git ')
    if files[0].startswith('diff --git '):
        files[0] = files[0][11:]  # Remove prefix from first file
    
    result = []
    current_length = 0
    separator_len = len('\ndiff --git ')
    
    for i, file_diff in enumerate(files):
        file_content = ('diff --git ' if i > 0 else '') + file_diff
        
        # Reserve 100 chars for truncation message
        if current_length + len(file_content) + 100 <= max_chars:
            result.append(file_content)
            current_length += len(file_content) if i == 0 else len(file_content) + separator_len
        else:
            # Add truncation indicator
            result.append(
                f"\n\n[... truncated ...]\n"
                f"Additional files not shown due to {max_chars:,} character limit.\n"
                f"Use specific file paths to review remaining changes."
            )
            break
    
    return ''.join(result)


# Initialize FastMCP server
mcp = FastMCP("bitbucket-pr-manager")


def _format_error(tool_name: str, action: str, error: Exception, context: str = "") -> str:
    """Format error message with context and suggestions.
    
    Format: "[tool_name] Failed to X: reason" + context + suggestion
    
    Args:
        tool_name: Name of the tool that failed
        action: Description of the action that failed
        error: The exception that occurred
        context: Additional context (e.g., PR ID)
        
    Returns:
        Formatted error string
    """
    import requests
    
    if isinstance(error, requests.exceptions.HTTPError):
        status_code = error.response.status_code
        if status_code == 401:
            return f"[{tool_name}] Failed to {action}: Authentication failed. Check your BITBUCKET_API_TOKEN."
        elif status_code == 403:
            return f"[{tool_name}] Failed to {action}: Access forbidden. Check your permissions."
        elif status_code == 404:
            ctx = f" {context}" if context else ""
            return f"[{tool_name}] Failed to {action}: Not found.{ctx} Verify the value is correct."
        elif status_code >= 500:
            return f"[{tool_name}] Failed to {action}: Bitbucket server error ({status_code}). Try again later."
        else:
            return f"[{tool_name}] Failed to {action}: HTTP {status_code}"
    
    return f"[{tool_name}] Failed to {action}: {str(error)}"


def _format_pr_list(prs: list[dict]) -> str:
    """Format PR list as multi-line blocks.
    
    Args:
        prs: List of PR dictionaries from Bitbucket API
        
    Returns:
        Formatted string with PR details
    """
    if not prs:
        return "No pull requests found."
    
    lines = [f"Found {len(prs)} pull request(s):\n"]
    
    for pr in prs[:20]:  # Limit to 20
        pr_id = pr.get('id', 'unknown')
        title = pr.get('title', 'No title')
        author = pr.get('author', {}).get('display_name', 'Unknown')
        state = pr.get('state', 'unknown')
        source_branch = pr.get('source', {}).get('branch', {}).get('name', 'unknown')
        target_branch = pr.get('destination', {}).get('branch', {}).get('name', 'unknown')
        created = pr.get('created_on', 'unknown')
        comments = pr.get('comment_count', 0)
        
        lines.append(f"PR #{pr_id}: {title}")
        lines.append(f"  Author: {author}")
        lines.append(f"  State: {state}")
        lines.append(f"  Branch: {source_branch} → {target_branch}")
        lines.append(f"  Created: {created}")
        lines.append(f"  Comments: {comments}")
        lines.append("")  # Blank line between PRs
    
    return '\n'.join(lines)


@mcp.tool()
def bitbucket_list_pull_requests(state: str | None = None) -> str:
    """List pull requests with optional state filter.
    
    Args:
        state: Optional state filter - 'open', 'merged', or 'declined'
    
    Returns:
        Formatted list of up to 20 most recent PRs
    """
    try:
        params = {'pagelen': 20}
        if state:
            state_map = {'open': 'OPEN', 'merged': 'MERGED', 'declined': 'DECLINED'}
            if state.lower() in state_map:
                params['state'] = state_map[state.lower()]
        
        response = bitbucket_client.get('/pullrequests', params=params)
        prs = response.get('values', [])
        
        if not prs:
            state_msg = f" with state '{state}'" if state else ""
            return f"No pull requests found{state_msg}."
        
        return _format_pr_list(prs)
        
    except Exception as e:
        return _format_error("bitbucket_list_pull_requests", "list PRs", e)


if __name__ == "__main__":
    logger.info("Starting Bitbucket PR Manager MCP server...")
    mcp.run(transport="stdio")
