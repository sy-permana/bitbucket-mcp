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


def _format_error(
    tool_name: str,
    action: str,
    error: Exception,
    context: dict | None = None
) -> str:
    """Format error message with context and suggestions.

    Format: "[tool_name] Failed to X: reason" + context + suggestion

    Args:
        tool_name: Name of the MCP tool
        action: Description of what was being attempted (e.g., "fetch PR #123")
        error: The exception that occurred
        context: Optional dict with additional context for error message

    Returns:
        Formatted error string with helpful suggestions
    """
    import requests

    # Build context string from dict
    ctx_str = ""
    if context:
        ctx_str = " " + " ".join(f"{k}={v}" for k, v in context.items())

    if isinstance(error, requests.exceptions.HTTPError):
        status_code = error.response.status_code

        if status_code == 401:
            return (
                f"[{tool_name}] Failed to {action}: Authentication failed.{ctx_str} "
                "Check your BITBUCKET_API_TOKEN and BITBUCKET_USERNAME are correct."
            )
        elif status_code == 403:
            return (
                f"[{tool_name}] Failed to {action}: Permission denied.{ctx_str} "
                "Ensure your API token has access to this repository."
            )
        elif status_code == 404:
            resource = context.get('resource', 'Resource') if context else 'Resource'
            return (
                f"[{tool_name}] Failed to {action}: {resource} not found.{ctx_str} "
                "Verify the ID/identifier is correct."
            )
        elif status_code == 429:
            return (
                f"[{tool_name}] Failed to {action}: Rate limited.{ctx_str} "
                "Wait a moment and try again."
            )
        elif status_code >= 500:
            return (
                f"[{tool_name}] Failed to {action}: Bitbucket server error (HTTP {status_code}).{ctx_str} "
                "This is a temporary issue. Please retry in a moment."
            )
        else:
            return f"[{tool_name}] Failed to {action}: HTTP {status_code}.{ctx_str}"

    elif isinstance(error, requests.exceptions.ConnectionError):
        return (
            f"[{tool_name}] Failed to {action}: Connection error.{ctx_str} "
            "Check your internet connection and try again."
        )

    elif isinstance(error, requests.exceptions.Timeout):
        return (
            f"[{tool_name}] Failed to {action}: Request timed out.{ctx_str} "
            "Bitbucket may be slow. Please retry."
        )

    else:
        return f"[{tool_name}] Failed to {action}: {str(error)}{ctx_str}"


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


def _format_pr_detail(pr: dict) -> str:
    """Format single PR details as multi-line string.

    Args:
        pr: PR dictionary from Bitbucket API

    Returns:
        Formatted string with PR details
    """
    pr_id = pr.get('id', 'unknown')
    title = pr.get('title', 'No title')
    author = pr.get('author', {}).get('display_name', 'Unknown')
    state = pr.get('state', 'unknown')
    source_branch = pr.get('source', {}).get('branch', {}).get('name', 'unknown')
    target_branch = pr.get('destination', {}).get('branch', {}).get('name', 'unknown')
    created = pr.get('created_on', 'unknown')
    updated = pr.get('updated_on', 'unknown')
    comments = pr.get('comment_count', 0)
    description = pr.get('description', '')

    lines = [
        f"PR #{pr_id}: {title}",
        f"State: {state}",
        f"Author: {author}",
        f"Source: {source_branch} → Target: {target_branch}",
        f"Created: {created}",
        f"Updated: {updated}",
        f"Comments: {comments}",
    ]

    # Add reviewers if present
    reviewers = pr.get('reviewers', [])
    if reviewers:
        reviewer_names = [r.get('display_name', 'Unknown') for r in reviewers]
        lines.append(f"Reviewers: {', '.join(reviewer_names)}")

    # Add description if present
    if description:
        lines.append(f"\nDescription:\n{description}")

    return '\n'.join(lines)


@mcp.tool()
def bitbucket_get_pull_request(pr_id: int) -> str:
    """Get detailed information about a specific pull request.

    Args:
        pr_id: Pull request ID number

    Returns:
        Formatted PR details or error message
    """
    try:
        pr_id_int = int(pr_id)
        response = bitbucket_client.get(f'/pullrequests/{pr_id_int}')
        return _format_pr_detail(response)

    except Exception as e:
        return _format_error(
            "bitbucket_get_pull_request",
            f"fetch PR #{pr_id}",
            e,
            {'pr_id': pr_id, 'resource': 'PR'}
        )


def _build_diff_metadata(pr: dict) -> str:
    """Build metadata header for PR diff.
    
    Args:
        pr: PR dictionary from Bitbucket API
        
    Returns:
        Formatted metadata header string
    """
    pr_id = pr.get('id', 'unknown')
    title = pr.get('title', 'No title')
    author = pr.get('author', {}).get('display_name', 'Unknown')
    state = pr.get('state', 'unknown')
    source_branch = pr.get('source', {}).get('branch', {}).get('name', 'unknown')
    target_branch = pr.get('destination', {}).get('branch', {}).get('name', 'unknown')
    
    lines = [
        f"PR #{pr_id}: {title}",
        f"Author: {author} | State: {state}",
        f"Branch: {source_branch} → {target_branch}",
    ]
    
    return '\n'.join(lines)


@mcp.tool()
def bitbucket_get_pr_diff(pr_id: int) -> str:
    """Get PR diff with automatic truncation at 10,000 characters.
    
    Args:
        pr_id: Pull request ID number
    
    Returns:
        Formatted diff with metadata header, truncated if needed
    """
    import requests
    
    try:
        # Get PR details for metadata
        pr = bitbucket_client.get(f'/pullrequests/{pr_id}')
        
        # Get diff as text/plain (NOT JSON!)
        diff_url = f"{bitbucket_client.repo_url}/pullrequests/{pr_id}/diff"
        diff_response = bitbucket_client.session.get(diff_url, timeout=30)
        diff_response.raise_for_status()
        diff_text = diff_response.text
        
        # Build metadata header
        metadata = _build_diff_metadata(pr)
        
        # Truncate if needed
        was_truncated = len(diff_text) > 10000
        if was_truncated:
            diff_text = _truncate_diff(diff_text, 10000)
        
        # Assemble result
        result = metadata + "\n\n" + diff_text
        if was_truncated:
            result += "\n\n[Note: Diff truncated to 10,000 characters]"
        
        return result
        
    except Exception as e:
        return _format_error(
            "bitbucket_get_pr_diff",
            f"fetch diff for PR #{pr_id}",
            e,
            {'pr_id': pr_id, 'resource': 'PR'}
        )


def _format_commit_statuses(commit_hash: str, statuses: list[dict]) -> str:
    """Format commit CI/CD statuses as readable string.

    Args:
        commit_hash: The commit hash (shortened for display)
        statuses: List of status dictionaries from Bitbucket API

    Returns:
        Formatted string with state indicators and details
    """
    # State to emoji/indicator mapping
    state_indicators = {
        'SUCCESSFUL': '✓',
        'FAILED': '✗',
        'INPROGRESS': '○',
        'STOPPED': '−'
    }

    short_hash = commit_hash[:12] if len(commit_hash) > 12 else commit_hash

    lines = [f"CI/CD Statuses for commit {short_hash}:", ""]

    for status in statuses:
        state = status.get('state', 'UNKNOWN')
        name = status.get('name', 'Unknown Build')
        description = status.get('description', '')
        url = status.get('url', '')
        updated = status.get('updated_on', '')

        indicator = state_indicators.get(state, '?')

        lines.append(f"{indicator} {name}")
        lines.append(f"  State: {state}")

        if description:
            lines.append(f"  Description: {description}")
        if url:
            lines.append(f"  URL: {url}")
        if updated:
            lines.append(f"  Updated: {updated}")

        lines.append("")  # Blank line between statuses

    return '\n'.join(lines)


@mcp.tool()
def bitbucket_check_commit_status(commit_hash: str) -> str:
    """Check CI/CD commit status for a given commit hash.

    Args:
        commit_hash: Full or partial commit hash (e.g., 'abc123' or full 40-char)

    Returns:
        Formatted list of build statuses or message if none found
    """
    try:
        response = bitbucket_client.get(f'/commit/{commit_hash}/statuses')
        statuses = response.get('values', [])

        if not statuses:
            short_hash = commit_hash[:12] if len(commit_hash) > 12 else commit_hash
            return f"No CI/CD statuses found for commit {short_hash}."

        return _format_commit_statuses(commit_hash, statuses)

    except Exception as e:
        return _format_error(
            "bitbucket_check_commit_status",
            f"check status for commit {commit_hash[:12] if len(commit_hash) > 12 else commit_hash}",
            e,
            {'commit_hash': commit_hash[:12] if len(commit_hash) > 12 else commit_hash, 'resource': 'Commit'}
        )


@mcp.tool()
def bitbucket_create_pr(
    title: str,
    source_branch: str,
    target_branch: str | None = None,
    description: str | None = None,
    close_source_branch: bool = False
) -> str:
    """Create a new pull request.

    Args:
        title: Pull request title (required)
        source_branch: Branch containing changes (required)
        target_branch: Branch to merge into (optional, defaults to repository default branch)
        description: Pull request description (optional)
        close_source_branch: Whether to delete source branch after merge (optional, default False)

    Returns:
        Formatted success message with PR details and URL
    """
    try:
        data = {
            "title": title,
            "source": {"branch": {"name": source_branch}},
            "close_source_branch": close_source_branch
        }
        if target_branch:
            data["destination"] = {"branch": {"name": target_branch}}
        if description:
            data["description"] = description

        response = bitbucket_client.post('/pullrequests', data=data)
        pr_id = response.get('id')
        pr_title = response.get('title')
        source = response.get('source', {}).get('branch', {}).get('name', 'unknown')
        target = response.get('destination', {}).get('branch', {}).get('name', 'unknown')
        html_url = response.get('links', {}).get('html', {}).get('href', '')

        return (
            f"Created PR #{pr_id}: {pr_title}\n"
            f"Source: {source} → Target: {target}\n"
            f"URL: {html_url}"
        )
    except Exception as e:
        return _format_error("bitbucket_create_pr", "create PR", e)


@mcp.tool()
def bitbucket_merge_pr(
    pr_id: int,
    strategy: str = "merge_commit",
    close_source_branch: bool = False,
    message: str | None = None
) -> str:
    """Merge an open pull request.
    
    Args:
        pr_id: Pull request ID number
        strategy: Merge strategy - 'merge_commit' (default), 'fast_forward', or 'squash'
        close_source_branch: Whether to delete source branch after merge (default False)
        message: Custom merge commit message (optional)
    
    Returns:
        Formatted success message with merged PR details
    """
    try:
        # Get PR details for state validation and branch info
        pr = bitbucket_client.get(f'/pullrequests/{pr_id}')
        state = pr.get('state')
        
        if state == 'MERGED':
            return f"[bitbucket_merge_pr] Failed to merge PR #{pr_id}: PR is already merged (state=MERGED)."
        if state == 'DECLINED':
            return f"[bitbucket_merge_pr] Failed to merge PR #{pr_id}: PR is declined (state=DECLINED)."
        
        source = pr.get('source', {}).get('branch', {}).get('name', 'unknown')
        target = pr.get('destination', {}).get('branch', {}).get('name', 'unknown')
        pr_title = pr.get('title', 'No title')
        
        data = {
            "type": "string",
            "merge_strategy": strategy,
            "close_source_branch": close_source_branch
        }
        if message:
            data["message"] = message
            
        bitbucket_client.post(f'/pullrequests/{pr_id}/merge', data=data)
        
        return (
            f"Successfully merged PR #{pr_id}: {pr_title}\n"
            f"{source} → {target}"
        )
    except Exception as e:
        return _format_error(
            "bitbucket_merge_pr", 
            f"merge PR #{pr_id}", 
            e,
            {'pr_id': pr_id}
        )


@mcp.tool()
def bitbucket_approve_pr(pr_id: int) -> str:
    """Approve a pull request.
    
    Args:
        pr_id: Pull request ID number
    
    Returns:
        Formatted success message or error
    """
    try:
        # Get current PR state and participants
        pr = bitbucket_client.get(f'/pullrequests/{pr_id}')
        state = pr.get('state')
        
        if state == 'MERGED':
            return f"[bitbucket_approve_pr] Failed to approve PR #{pr_id}: PR is already merged (state=MERGED)."
        if state == 'DECLINED':
            return f"[bitbucket_approve_pr] Failed to approve PR #{pr_id}: PR is already declined (state=DECLINED)."
        
        # Check if already approved by current user
        participants = pr.get('participants', [])
        for p in participants:
            if p.get('approved') and p.get('role') == 'PARTICIPANT':
                return f"PR #{pr_id} is already approved by you."
        
        bitbucket_client.post(f'/pullrequests/{pr_id}/approve')
        return f"PR #{pr_id} approved"
        
    except Exception as e:
        return _format_error(
            "bitbucket_approve_pr",
            f"approve PR #{pr_id}",
            e,
            {'pr_id': pr_id}
        )


@mcp.tool()
def bitbucket_decline_pr(pr_id: int) -> str:
    """Decline/reject a pull request.
    
    Args:
        pr_id: Pull request ID number
    
    Returns:
        Formatted success message or error
    """
    try:
        # Get current PR state
        pr = bitbucket_client.get(f'/pullrequests/{pr_id}')
        state = pr.get('state')
        
        if state == 'MERGED':
            return f"[bitbucket_decline_pr] Failed to decline PR #{pr_id}: PR is already merged (state=MERGED)."
        if state == 'DECLINED':
            return f"PR #{pr_id} is already declined."
        
        bitbucket_client.post(f'/pullrequests/{pr_id}/decline')
        return f"PR #{pr_id} declined"
        
    except Exception as e:
        return _format_error(
            "bitbucket_decline_pr",
            f"decline PR #{pr_id}",
            e,
            {'pr_id': pr_id}
        )


@mcp.tool()
def bitbucket_request_changes(pr_id: int, comment: str | None = None) -> str:
    """Request changes on a pull request.
    
    Uses native Bitbucket request-changes endpoint. Optionally adds an explanatory comment.
    
    Args:
        pr_id: Pull request ID number
        comment: Optional explanatory comment to add with the request
    
    Returns:
        Formatted success message or error
    """
    try:
        # Get current PR state
        pr = bitbucket_client.get(f'/pullrequests/{pr_id}')
        state = pr.get('state')
        
        if state == 'MERGED':
            return f"[bitbucket_request_changes] Failed to request changes on PR #{pr_id}: PR is already merged (state=MERGED)."
        if state == 'DECLINED':
            return f"[bitbucket_request_changes] Failed to request changes on PR #{pr_id}: PR is already declined (state=DECLINED)."
        
        # Request changes via native endpoint
        bitbucket_client.post(f'/pullrequests/{pr_id}/request-changes')
        
        # Optionally add explanatory comment
        if comment:
            try:
                bitbucket_client.post(
                    f'/pullrequests/{pr_id}/comments',
                    data={'content': {'raw': comment}}
                )
            except Exception:
                # Comment failure shouldn't fail the request-changes
                pass
        
        return f"Requested changes on PR #{pr_id}"
        
    except Exception as e:
        return _format_error(
            "bitbucket_request_changes",
            f"request changes on PR #{pr_id}",
            e,
            {'pr_id': pr_id}
        )


@mcp.tool()
def bitbucket_add_comment(pr_id: int, content: str) -> str:
    """Add a general comment to a pull request.
    
    Args:
        pr_id: Pull request ID number
        content: Comment text (markdown supported)
    
    Returns:
        Confirmation message or error
    """
    # Validate non-empty (per CONTEXT.md decision)
    if not content or not content.strip():
        return "[bitbucket_add_comment] Failed to add comment: Comment content cannot be empty."
    
    try:
        bitbucket_client.post(
            f'/pullrequests/{pr_id}/comments',
            data={'content': {'raw': content}}
        )
        return f"Comment added to PR #{pr_id}"
    except Exception as e:
        return _format_error("bitbucket_add_comment", f"add comment to PR #{pr_id}", e)


if __name__ == "__main__":
    logger.info("Starting Bitbucket PR Manager MCP server...")
    mcp.run(transport="stdio")
