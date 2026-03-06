# Architecture Research: Python MCP Server for Bitbucket Integration

**Domain:** Model Context Protocol (MCP) Server with External REST API Integration  
**Researched:** 2025-03-06  
**Confidence:** HIGH

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP Transport Layer                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         FastMCP Server                               │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │ @mcp.tool()  │  │ @mcp.tool()  │  │ @mcp.tool()  │  ... (N tools) │    │
│  │  │ PR Tools     │  │ Comment      │  │ Merge Tools  │               │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │    │
│  └─────────┼─────────────────┼─────────────────┼─────────────────────────┘    │
├────────────┼─────────────────┼─────────────────┼──────────────────────────────┤
│            │                 │                 │                              │
│            ▼                 ▼                 ▼                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Bitbucket API Client Layer                      │    │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │    │
│  │  │ PR Operations   │  │ Comment Service │  │ Commit Status   │      │    │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘      │    │
│  │           │                    │                    │                │    │
│  │           └────────────────────┴────────────────────┘                │    │
│  │                              │                                       │    │
│  │                              ▼                                       │    │
│  │           ┌─────────────────────────────────────┐                    │    │
│  │           │     HTTP Client (requests library)   │                    │    │
│  │           │  ┌───────────────────────────────┐    │                    │    │
│  │           │  │ HTTPBasicAuth (API Token)     │    │                    │    │
│  │           │  │ Base URL: api.bitbucket.org   │    │                    │    │
│  │           │  │ Timeout / Retry Logic         │    │                    │    │
│  │           │  └───────────────────────────────┘    │                    │    │
│  │           └─────────────────────────────────────┘                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────────────┤
│                           Configuration Layer                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ USERNAME    │  │ API_TOKEN   │  │ WORKSPACE   │  │ REPO_SLUG   │        │
│  │ (env var)   │  │ (env var)   │  │ (env var)   │  │ (env var)   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Implementation Pattern |
|-----------|----------------|------------------------|
| **FastMCP Server** | Protocol handling, tool registration, message routing | `@mcp.tool()` decorator pattern with type hints |
| **Tool Functions** | LLM-facing interface, parameter validation, response formatting | Pure functions with docstrings → tool schemas, return `str` |
| **Bitbucket API Client** | HTTP request construction, authentication, response parsing | Class-based wrapper around `requests` with session reuse |
| **Error Handler** | Exception catching, traceback suppression, user-friendly messages | Try/except at tool boundaries, format as strings |
| **Config Manager** | Environment variable loading, validation, defaults | `os.environ.get()` with strict validation on startup |
| **Diff Processor** | Context window protection, truncation at 10k chars | String manipulation before API return |

## Recommended Project Structure

```
bitbucket-mcp/
├── src/
│   ├── __init__.py
│   ├── server.py              # FastMCP server initialization, main entry point
│   ├── tools/                 # MCP tool definitions
│   │   ├── __init__.py
│   │   ├── pr_tools.py        # PR lifecycle: create, merge, approve, decline
│   │   ├── comment_tools.py   # Commenting: PR comments, inline comments
│   │   └── info_tools.py      # Info fetching: diff, commits, status
│   ├── client/                # Bitbucket API integration
│   │   ├── __init__.py
│   │   ├── bitbucket_client.py # Core HTTP client with auth
│   │   ├── pr_operations.py   # PR-specific API calls
│   │   └── comment_service.py # Comment-related API calls
│   ├── config.py              # Environment configuration, validation
│   └── utils.py               # Helpers: diff truncation, error formatting
├── tests/
│   ├── test_tools/
│   ├── test_client/
│   └── test_utils.py
├── pyproject.toml             # Dependencies: mcp[cli], requests
└── .env.example               # Template for required env vars
```

### Structure Rationale

- **`server.py`:** Single entry point, FastMCP instance creation. Keeps transport concerns (stdio vs HTTP) isolated.
- **`tools/`:** Grouped by functional domain. Each module uses `@mcp.tool()` decorator. Tools don't call Bitbucket directly—they use the client layer.
- **`client/`:** Clean separation between MCP protocol and external API. Makes testing easier (mock client) and allows client reuse.
- **`config.py`:** Centralized env var handling. Fails fast on startup if required vars missing.
- **`utils.py`:** Shared helpers like diff truncation that aren't tool-specific.

## Architectural Patterns

### Pattern 1: FastMCP Decorator Pattern (Tools)

**What:** Use `@mcp.tool()` decorator with type hints and docstrings to automatically generate tool schemas.

**When to use:** For every MCP tool. This is the canonical FastMCP pattern.

**Trade-offs:** 
- ✅ Automatic schema generation from type hints
- ✅ Docstrings become tool descriptions for LLM
- ✅ Minimal boilerplate
- ⚠️ Must return string format (not JSON objects) per requirement

**Example:**
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("bitbucket-pr-manager")

@mcp.tool()
def get_pr_diff(pr_id: int) -> str:
    """Get the diff for a pull request.
    
    Args:
        pr_id: The pull request ID number
        
    Returns:
        A string containing the diff content (truncated if >10k chars)
    """
    # Call client layer, handle errors, return string
    try:
        diff = client.get_pr_diff(pr_id)
        return truncate_diff(diff, max_chars=10000)
    except BitbucketAPIError as e:
        return f"Error fetching diff: {e.message}"
```

### Pattern 2: Client Abstraction Layer

**What:** Wrap `requests` library in a dedicated client class that handles auth, base URL, and common error patterns.

**When to use:** Always when calling external APIs from MCP servers. Prevents auth logic duplication.

**Trade-offs:**
- ✅ Single place for auth configuration (HTTPBasicAuth with API token)
- ✅ Easy to mock for testing
- ✅ Retry logic centralized
- ⚠️ Small upfront cost vs direct requests calls

**Example:**
```python
import requests
from requests.auth import HTTPBasicAuth

class BitbucketClient:
    def __init__(self, username: str, api_token: str, workspace: str, repo_slug: str):
        self.auth = HTTPBasicAuth(username, api_token)
        self.base_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}"
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
    
    def get(self, endpoint: str, **kwargs) -> dict:
        """Make authenticated GET request."""
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint: str, data: dict, **kwargs) -> dict:
        """Make authenticated POST request."""
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(url, json=data, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()
```

### Pattern 3: String Response Wrapper

**What:** All tools return strings, not raw JSON/dict objects. Errors become informative string messages.

**When to use:** Required per project constraints. MCP clients (like Claude) work better with readable text.

**Trade-offs:**
- ✅ User-friendly output for LLM consumption
- ✅ No stack traces leaked to user
- ✅ Clear success/failure messages
- ⚠️ Loses structured data (but can format nicely as text)

**Example:**
```python
# ❌ Don't do this (returns JSON to LLM, hard to read)
@mcp.tool()
def list_prs() -> dict:
    return client.get_prs()  # Returns raw JSON

# ✅ Do this (returns formatted string)
@mcp.tool()
def list_prs() -> str:
    try:
        prs = client.get_prs()
        if not prs:
            return "No open pull requests found."
        
        lines = ["Open Pull Requests:", "-" * 40]
        for pr in prs:
            lines.append(f"#{pr['id']}: {pr['title']} by {pr['author']}")
        return "\n".join(lines)
    except BitbucketAPIError as e:
        return f"Failed to list PRs: {e.message}"
```

### Pattern 4: Diff Truncation (Context Window Protection)

**What:** Truncate diffs at 10,000 characters to protect LLM context window.

**When to use:** Any tool that returns large text content (diffs, logs, file contents).

**Trade-offs:**
- ✅ Prevents context overflow
- ✅ LLM can still understand changes
- ⚠️ Very large diffs may be incomplete (document this limitation)

**Example:**
```python
def truncate_diff(diff_content: str, max_chars: int = 10000) -> str:
    """Truncate diff to protect LLM context window."""
    if len(diff_content) <= max_chars:
        return diff_content
    
    truncated = diff_content[:max_chars]
    remaining = len(diff_content) - max_chars
    return f"{truncated}\n\n[... {remaining} characters truncated for context window protection]"
```

## Data Flow

### Tool Invocation Flow

```
┌─────────────────┐
│   MCP Client    │  (Claude, Claude Code, etc.)
│  (requests tool)│
└────────┬────────┘
         │ 1. JSON-RPC: tools/call with params
         ▼
┌─────────────────┐
│   FastMCP       │  2. Route to correct tool function
│   Server        │     based on tool name
└────────┬────────┘
         │ 3. Call tool function with validated params
         ▼
┌─────────────────┐
│  Tool Function  │  4. Validate parameters (Pydantic from type hints)
│  (@mcp.tool)    │  5. Call BitbucketClient method
└────────┬────────┘
         │ 6. HTTP request with auth
         ▼
┌─────────────────┐
│ BitbucketClient │  7. requests.Session with HTTPBasicAuth
│  (client/)      │  8. Handle response/raise exception
└────────┬────────┘
         │ 9. Return dict from API
         ▼
┌─────────────────┐
│  Tool Function  │  10. Process response (truncate if needed)
│  (@mcp.tool)    │  11. Format as string
└────────┬────────┘
         │ 12. Return string
         ▼
┌─────────────────┐
│   FastMCP       │  13. Wrap in CallToolResult, serialize to JSON-RPC
│   Server        │
└────────┬────────┘
         │ 14. Return to client
         ▼
┌─────────────────┐
│   MCP Client    │  15. Display result to user
└─────────────────┘
```

### Error Handling Flow

```
Tool Function Called
        │
        ▼
┌───────────────┐
│ try:          │
│   call client │
└───────┬───────┘
        │
    ┌───┴───┐
    │       │
    ▼       ▼
Success   Exception
    │       │
    ▼       ▼
Format    Format error message
result    (no traceback!)
    │       │
    └───┬───┘
        ▼
   Return string
   to MCP server
```

**Key Error Handling Rules:**
1. Catch exceptions at tool function boundary
2. Never return raw exceptions or tracebacks
3. Format errors as clear, actionable strings
4. Distinguish between API errors ("PR not found") and system errors ("Network timeout")

### Inline Comment Data Flow

Inline comments require careful handling of `to`/`from` line numbers in the Bitbucket API payload:

```
User provides: file_path, line_number, comment_text
                        │
                        ▼
Tool maps line_number ──┬──► inline.to = line_number
  to Bitbucket format   │    inline.from = line_number (or line_number - 1 for context)
                        │
                        ▼
              ┌─────────────────────┐
              │ Build JSON payload  │
              │ with proper nesting │
              └─────────────────────┘
                        │
                        ▼
              POST to /pullrequests/{id}/comments
```

## Build Order & Dependencies

### Phase 1: Foundation (Week 1)

**Dependencies:** None

**Components:**
1. `config.py` - Environment variable loading and validation
2. `client/bitbucket_client.py` - Core HTTP client with auth
3. `server.py` - FastMCP server initialization

**Why this order:**
- Config must be validated before server starts (fail fast)
- Client layer is dependency for all tools
- Server needs both to initialize

**Deliverable:** Server starts without errors, validates env vars

### Phase 2: Read Operations (Week 1-2)

**Dependencies:** Phase 1

**Components:**
1. `tools/info_tools.py` - Get PR, get diff, check status
2. `utils.py` - Diff truncation helper

**Why this order:**
- Read operations are safer (no side effects)
- Validates client layer works end-to-end
- Diff truncation can be tested independently

**Deliverable:** Can fetch PR info and diffs via MCP tools

### Phase 3: PR Lifecycle (Week 2)

**Dependencies:** Phase 2

**Components:**
1. `client/pr_operations.py` - PR-specific API methods
2. `tools/pr_tools.py` - Create, merge, approve, decline PRs

**Why this order:**
- Requires understanding of PR data structures from read operations
- Write operations have side effects—want stable foundation first

**Deliverable:** Can manage PR lifecycle via MCP tools

### Phase 4: Commenting (Week 2-3)

**Dependencies:** Phase 3

**Components:**
1. `client/comment_service.py` - Comment API methods
2. `tools/comment_tools.py` - PR comments, inline comments

**Why this order:**
- Inline comments require understanding of diff/line number mapping
- Commenting on PRs requires PR to exist (depends on lifecycle)

**Deliverable:** Can add comments to PRs (general and inline)

### Phase 5: Polish (Week 3)

**Dependencies:** All above

**Components:**
- Error message refinement
- Tool descriptions/documentation
- Edge case handling (large diffs, deleted PRs, etc.)

**Deliverable:** Production-ready server with clear error messages

## Configuration Management

### Required Environment Variables

| Variable | Purpose | Validation |
|----------|---------|------------|
| `BITBUCKET_USERNAME` | Atlassian account email | Required, must be valid email format |
| `BITBUCKET_API_TOKEN` | API token for authentication | Required, minimum length check |
| `BITBUCKET_WORKSPACE` | Bitbucket workspace name | Required, no spaces |
| `BITBUCKET_REPO_SLUG` | Repository slug | Required, no spaces |

### Configuration Pattern

```python
# config.py
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class BitbucketConfig:
    username: str
    api_token: str
    workspace: str
    repo_slug: str
    
    @classmethod
    def from_env(cls) -> "BitbucketConfig":
        """Load and validate configuration from environment."""
        required_vars = [
            "BITBUCKET_USERNAME",
            "BITBUCKET_API_TOKEN", 
            "BITBUCKET_WORKSPACE",
            "BITBUCKET_REPO_SLUG"
        ]
        
        missing = [var for var in required_vars if not os.environ.get(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return cls(
            username=os.environ["BITBUCKET_USERNAME"],
            api_token=os.environ["BITBUCKET_API_TOKEN"],
            workspace=os.environ["BITBUCKET_WORKSPACE"],
            repo_slug=os.environ["BITBUCKET_REPO_SLUG"]
        )
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Single user / single repo | Current architecture is optimal. Stateless, no caching needed. |
| Team / multiple repos | Consider adding connection pooling to requests.Session, add per-repo client instances |
| High-frequency operations | Add response caching for read operations (ETag-based), implement rate limit handling |

**Current constraints that limit scaling:**
- Single workspace/repo per server instance (by design)
- No persistent state (good for scaling horizontally)
- Each tool call is independent (stateless)

### Rate Limiting

Bitbucket API has rate limits. The client should handle 429 responses:

```python
# In BitbucketClient
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def __init__(self, ...):
    self.session = requests.Session()
    # Add retry logic for rate limits
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    self.session.mount("https://", adapter)
```

## Anti-Patterns

### Anti-Pattern 1: Returning JSON Objects from Tools

**What people do:** Return `dict` or `list` directly from tool functions.

**Why it's wrong:** 
- MCP clients receive structured content but LLMs work better with formatted text
- Raw JSON is hard for LLM to read and interpret
- Violates project constraint (string format required)

**Do this instead:**
```python
# Format as readable string with clear sections
result = f"""Pull Request #{pr['id']}: {pr['title']}
Author: {pr['author']['display_name']}
Status: {pr['state']}
Branch: {pr['source']['branch']['name']} → {pr['destination']['branch']['name']}
Description:
{pr.get('description', 'No description')}"""
```

### Anti-Pattern 2: Direct requests Calls in Tools

**What people do:** Use `requests.get()` directly in tool functions.

**Why it's wrong:**
- Auth logic duplicated everywhere
- Hard to test (can't mock easily)
- No centralized error handling

**Do this instead:** Use the `BitbucketClient` abstraction layer.

### Anti-Pattern 3: Ignoring Context Window Limits

**What people do:** Return full diffs regardless of size.

**Why it's wrong:**
- Large diffs (>100k chars) can overwhelm LLM context window
- Wastes tokens on irrelevant content
- May cause truncation by client

**Do this instead:** Always truncate diffs at 10k characters with clear indication of truncation.

### Anti-Pattern 4: Silent Failures

**What people do:** Return generic "Error" message without details.

**Why it's wrong:**
- User can't tell if it's auth error, not found, or server error
- Makes debugging impossible
- Poor user experience

**Do this instead:** 
```python
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        return f"Pull request #{pr_id} not found."
    elif e.response.status_code == 401:
        return "Authentication failed. Check your BITBUCKET_USERNAME and BITBUCKET_API_TOKEN."
    else:
        return f"Bitbucket API error ({e.response.status_code}): {e.response.text}"
```

## Integration Points

### External: Bitbucket REST API v2

| Aspect | Details |
|--------|---------|
| Base URL | `https://api.bitbucket.org/2.0` |
| Authentication | HTTPBasicAuth (username + API token) |
| Content-Type | `application/json` |
| Rate Limiting | 1000 requests/hour for most endpoints |
| Pagination | Cursor-based, use `next` links |

**Key endpoints:**
- `GET /repositories/{workspace}/{repo_slug}/pullrequests` - List PRs
- `GET /repositories/{workspace}/{repo_slug}/pullrequests/{id}` - Get PR
- `GET /repositories/{workspace}/{repo_slug}/pullrequests/{id}/diff` - Get diff
- `POST /repositories/{workspace}/{repo_slug}/pullrequests/{id}/comments` - Add comment
- `POST /repositories/{workspace}/{repo_slug}/pullrequests/{id}/approve` - Approve PR
- `POST /repositories/{workspace}/{repo_slug}/pullrequests/{id}/merge` - Merge PR

### Internal: MCP Protocol

| Aspect | Details |
|--------|---------|
| Transport | stdio (for Claude Code), Streamable HTTP (optional) |
| Protocol | JSON-RPC 2.0 |
| Capabilities | tools (primary), resources (optional), prompts (optional) |

## Testing Strategy

### Unit Testing

```python
# Test tools with mocked client
from unittest.mock import Mock, patch

def test_get_pr_success():
    mock_client = Mock()
    mock_client.get_pr.return_value = {"id": 1, "title": "Test PR"}
    
    with patch('tools.pr_tools.client', mock_client):
        result = get_pr(1)
        assert "Test PR" in result
        assert "#1" in result
```

### Integration Testing

- Use `mcp` CLI test mode
- Validate tool schemas match expectations
- Test error scenarios with real API responses

## Sources

- **MCP Python SDK Documentation:** https://github.com/modelcontextprotocol/python-sdk (official, HIGH confidence)
- **MCP Quickstart Guide:** https://modelcontextprotocol.io/quickstart/server (official, HIGH confidence)
- **Bitbucket REST API v2 Docs:** https://developer.atlassian.com/cloud/bitbucket/rest/intro/ (official, HIGH confidence)
- **Bitbucket API Authentication:** https://developer.atlassian.com/cloud/bitbucket/rest/intro/#authentication (official, HIGH confidence)

---
*Architecture research for: Bitbucket PR Manager MCP Server*  
*Researched: 2025-03-06*
