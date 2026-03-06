# Phase 1: Foundation - Research

**Researched:** 2025-03-06  
**Domain:** Python MCP Server with FastMCP, Bitbucket API Authentication, Environment Configuration  
**Confidence:** HIGH

## Summary

Phase 1 establishes the server foundation for the Bitbucket PR Manager MCP server. This research covers FastMCP initialization patterns, Bitbucket API authentication using HTTPBasicAuth with API tokens, strict environment variable validation, and the critical requirement to log only to stderr to avoid corrupting the MCP stdio transport.

**Primary recommendation:** Use FastMCP decorator pattern with Pydantic-based config validation, implement HTTPBasicAuth with Bitbucket API tokens, and ensure all logging outputs to stderr only.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONFIG-01 | Validate 4 required env vars on startup | Pydantic BaseSettings or dataclass with strict validation pattern |
| CONFIG-02 | Graceful failure with clear message if env vars missing | Early validation in server.py before FastMCP initialization |
| CONFIG-03 | HTTPBasicAuth with API Token for Bitbucket auth | RFC-2617 Basic Auth with username=email, password=API token |
| CONFIG-04 | FastMCP initialization with proper tool registration | `@mcp.tool()` decorator pattern, `bitbucket_` namespace prefix |
| ERROR-03 | All logging to stderr (never stdout) | `logging` module with StreamHandler(sys.stderr) or print(file=sys.stderr) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp[cli]` | ^1.26.0 | MCP SDK with FastMCP | Official Anthropic Python SDK, decorator-based tool registration, auto schema generation |
| `requests` | ^2.32.5 | HTTP client library | Industry standard, built-in HTTPBasicAuth support, 30M+ weekly downloads |
| `pydantic` | ^2.12.5 | Data validation | Powers FastMCP structured output, V2 significantly faster than V1 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-dotenv` | ^1.2.2 | Environment variable loading | Local development with `.env` file, production uses actual env vars |
| `responses` | ^0.26.0 | HTTP mocking for tests | Mock Bitbucket API in unit tests, pytest-responses for fixtures |

### Infrastructure
| Technology | Purpose | Notes |
|------------|---------|-------|
| `uv` | Python package manager | Recommended by MCP SDK docs, faster than pip, better dependency resolution |
| `pytest` | Testing framework | Mature (v9.0.2), fixture-based, async support via pytest-asyncio |

**Installation:**
```bash
# Using uv (recommended)
uv init bitbucket-mcp-server
cd bitbucket-mcp-server
uv add "mcp[cli]" requests pydantic python-dotenv
uv add --dev pytest pytest-responses responses
```

## Architecture Patterns

### Recommended Project Structure
```
bitbucket-mcp/
├── src/
│   ├── __init__.py
│   ├── server.py              # FastMCP server initialization, main entry point
│   ├── config.py              # Environment configuration, validation
│   ├── client/
│   │   ├── __init__.py
│   │   └── bitbucket_client.py # Core HTTP client with auth
│   └── tools/
│       ├── __init__.py
│       └── __tools__.py       # Tool registration (Phase 2+)
├── tests/
│   ├── __init__.py
│   ├── test_config.py         # Config validation tests
│   └── test_client.py         # Bitbucket client tests
├── pyproject.toml             # Dependencies
└── .env.example               # Template for required env vars
```

### Pattern 1: FastMCP Server Initialization

**What:** Create FastMCP instance with proper name and initialization in `server.py`

**When to use:** Every MCP server entry point

**Example:**
```python
# src/server.py
from mcp.server.fastmcp import FastMCP
from src.config import BitbucketConfig

# Validate config BEFORE creating server (fail fast)
config = BitbucketConfig.from_env()

# Initialize FastMCP with namespaced name
mcp = FastMCP("bitbucket-pr-manager")

# Tool registration happens in separate modules
# from src.tools import pr_tools, comment_tools  # Phase 2+

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### Pattern 2: Pydantic-Based Environment Validation

**What:** Use Pydantic BaseSettings or dataclass for strict env var validation with clear error messages

**When to use:** Required - all 4 env vars must be validated before server starts

**Example:**
```python
# src/config.py
from pydantic import BaseModel, Field, ValidationError
import os
from typing import Self


class BitbucketConfig(BaseModel):
    """Configuration loaded from environment variables."""
    
    bitbucket_username: str = Field(
        description="Atlassian account email address"
    )
    bitbucket_api_token: str = Field(
        description="Bitbucket API token (NOT app password)"
    )
    bitbucket_workspace: str = Field(
        description="Bitbucket workspace name"
    )
    bitbucket_repo_slug: str = Field(
        description="Repository slug"
    )
    
    @classmethod
    def from_env(cls) -> Self:
        """Load and validate configuration from environment variables.
        
        Raises:
            ValueError: If any required environment variable is missing
        """
        required_vars = [
            "BITBUCKET_USERNAME",
            "BITBUCKET_API_TOKEN",
            "BITBUCKET_WORKSPACE",
            "BITBUCKET_REPO_SLUG"
        ]
        
        # Check for missing variables
        missing = [var for var in required_vars if not os.environ.get(var)]
        if missing:
            raise ValueError(
                f"Configuration error: Missing required environment variables: "
                f"{', '.join(missing)}\n\n"
                f"Please set the following environment variables:\n"
                f"- BITBUCKET_USERNAME (your Atlassian email)\n"
                f"- BITBUCKET_API_TOKEN (from https://bitbucket.org/[workspace]/workspace/settings/app-passwords)\n"
                f"- BITBUCKET_WORKSPACE (your workspace name)\n"
                f"- BITBUCKET_REPO_SLUG (repository slug)"
            )
        
        try:
            return cls(
                bitbucket_username=os.environ["BITBUCKET_USERNAME"],
                bitbucket_api_token=os.environ["BITBUCKET_API_TOKEN"],
                bitbucket_workspace=os.environ["BITBUCKET_WORKSPACE"],
                bitbucket_repo_slug=os.environ["BITBUCKET_REPO_SLUG"]
            )
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e}")
```

### Pattern 3: HTTPBasicAuth with Bitbucket API Token

**What:** Use `requests.auth.HTTPBasicAuth` with username (email) and API token as password

**When to use:** All Bitbucket API requests

**Example:**
```python
# src/client/bitbucket_client.py
import requests
from requests.auth import HTTPBasicAuth
from src.config import BitbucketConfig


class BitbucketClient:
    """Bitbucket API client with authentication."""
    
    BASE_URL = "https://api.bitbucket.org/2.0"
    
    def __init__(self, config: BitbucketConfig):
        self.config = config
        self.auth = HTTPBasicAuth(
            config.bitbucket_username,  # Atlassian email
            config.bitbucket_api_token  # API token (not password!)
        )
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        
        # Construct base URL for this workspace/repo
        self.repo_url = (
            f"{self.BASE_URL}/repositories/"
            f"{config.bitbucket_workspace}/{config.bitbucket_repo_slug}"
        )
    
    def get(self, endpoint: str, **kwargs) -> dict:
        """Make authenticated GET request."""
        url = f"{self.repo_url}{endpoint}"
        response = self.session.get(url, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint: str, data: dict, **kwargs) -> dict:
        """Make authenticated POST request."""
        url = f"{self.repo_url}{endpoint}"
        response = self.session.post(url, json=data, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()
```

### Pattern 4: Stderr-Only Logging

**What:** Configure Python logging to write only to stderr, never stdout

**When to use:** Critical for all STDIO-based MCP servers - stdout corruption breaks protocol

**Example:**
```python
# src/server.py (at the top, before other imports)
import sys
import logging

# Configure logging to stderr ONLY before anything else
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]  # stderr only!
)

logger = logging.getLogger(__name__)

# Alternative for simple debug output
# print("Debug message", file=sys.stderr)  # ✅ Safe
# print("Debug message")                   # ❌ NEVER - goes to stdout
```

### Pattern 5: Error Handling Wrapper

**What:** Wrap all tool functions to catch exceptions and return clear string messages

**When to use:** Every MCP tool function

**Example:**
```python
from functools import wraps
import requests


def handle_errors(func):
    """Decorator to catch exceptions and return string error messages."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return "[ERROR] Authentication failed. Check BITBUCKET_USERNAME and BITBUCKET_API_TOKEN."
            elif e.response.status_code == 403:
                return "[ERROR] Access denied. Your API token may lack required scopes."
            elif e.response.status_code == 404:
                return f"[ERROR] Resource not found: {e.response.url}"
            else:
                return f"[ERROR] Bitbucket API error ({e.response.status_code}): {e.response.text}"
        except requests.exceptions.RequestException as e:
            return f"[ERROR] Network error: {str(e)}"
        except Exception as e:
            # Never expose tracebacks
            return f"[ERROR] Unexpected error: {type(e).__name__}: {str(e)}"
    return wrapper
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP protocol handling | Custom JSON-RPC parser | `FastMCP` from `mcp[cli]` | Handles all protocol details, transport management |
| Environment validation | Manual `os.environ.get()` checks | Pydantic `BaseModel` or `BaseSettings` | Type validation, clear error messages, schema generation |
| Bitbucket API auth | Custom auth header construction | `requests.auth.HTTPBasicAuth` | RFC-2617 compliant, battle-tested, handles encoding |
| HTTP client | Raw `urllib` usage | `requests` library | Connection pooling, timeout handling, auth support |
| Configuration management | YAML/JSON config files | Environment variables | 12-factor app compliant, container-friendly, no files to manage |

**Key insight:** FastMCP abstracts all MCP protocol concerns, allowing focus on tool logic. The SDK handles stdio transport, JSON-RPC framing, and tool schema generation from type hints and docstrings.

## Common Pitfalls

### Pitfall 1: STDIO Output Corruption (CRITICAL)

**What goes wrong:** Writing to stdout (via `print()`, logging misconfiguration) corrupts JSON-RPC messages and breaks MCP server communication.

**Why it happens:** MCP uses stdio transport. Any non-protocol output on stdout interferes with message framing.

**How to avoid:**
- Use `logging` with `StreamHandler(sys.stderr)`
- Never use bare `print()` statements
- Always use `print("msg", file=sys.stderr)` for debug output

**Warning signs:**
- Server connects but tools don't appear in client
- "Invalid JSON" errors in client logs
- Intermittent connection failures

### Pitfall 2: App Passwords vs API Tokens

**What goes wrong:** Using deprecated App Passwords instead of API Tokens.

**Why it happens:** App passwords were the previous standard but are now deprecated by Atlassian.

**How to avoid:**
- Use API Tokens exclusively
- Document token creation at: `https://bitbucket.org/[workspace]/workspace/settings/app-passwords`
- Note: URL says "app-passwords" but API tokens are created there

**Warning signs:**
- 401 Unauthorized on all requests
- Authentication works in browser but not API

### Pitfall 3: HTTPBasicAuth Parameter Order

**What goes wrong:** Passing token as username and email as password.

**Why it happens:** Confusion about Basic Auth format for Bitbucket API tokens.

**How to avoid:**
```python
# Correct:
HTTPBasicAuth(
    username="user@example.com",  # Atlassian email
    password="ATCTT3xFf..."       # API token
)

# Wrong:
HTTPBasicAuth(
    username="ATCTT3xFf...",      # ❌ Token as username
    password="user@example.com"   # ❌ Email as password
)
```

### Pitfall 4: Missing Required Scopes

**What goes wrong:** API token lacks required scopes for operations (403 errors).

**Why it happens:** Tokens created with minimal scopes that don't cover PR operations.

**How to avoid:**
- Read operations: `pullrequest`, `repository` scopes
- Write operations: `pullrequest:write` (implies `repository:write`)
- Full PR lifecycle: `pullrequest:write`, `pullrequest`

**Warning signs:**
- Some tools work, others return 403
- Read operations succeed, write fails

### Pitfall 5: Delayed Configuration Validation

**What goes wrong:** Server starts but fails later when env vars accessed.

**Why it happens:** Lazy validation in client code instead of at startup.

**How to avoid:**
- Validate config in `server.py` before creating FastMCP instance
- Use `BitbucketConfig.from_env()` at module level
- Fail fast with clear, actionable error messages

**Warning signs:**
- Server starts but tools fail with "NoneType" errors
- Authentication errors after server appears healthy

## Code Examples

### Server Initialization (server.py)

```python
#!/usr/bin/env python3
"""Bitbucket PR Manager MCP Server.

This module initializes the FastMCP server with Bitbucket API integration.
All logging is directed to stderr to avoid corrupting the MCP stdio transport.
"""

import sys
import logging

# CRITICAL: Configure logging to stderr BEFORE any other imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Now import other modules
from mcp.server.fastmcp import FastMCP
from src.config import BitbucketConfig
from src.client.bitbucket_client import BitbucketClient

# Validate configuration on import (fail fast)
try:
    config = BitbucketConfig.from_env()
    logger.info(f"Configuration loaded for workspace: {config.bitbucket_workspace}")
except ValueError as e:
    # Log to stderr and exit cleanly
    logger.error(str(e))
    sys.exit(1)

# Initialize Bitbucket client
bitbucket_client = BitbucketClient(config)

# Initialize FastMCP server
mcp = FastMCP("bitbucket-pr-manager")

# Tool modules will import this 'mcp' instance for registration
# (import happens after server creation to avoid circular imports)

if __name__ == "__main__":
    logger.info("Starting Bitbucket PR Manager MCP server...")
    mcp.run(transport="stdio")
```

### Configuration Module (config.py)

```python
"""Configuration management for Bitbucket PR Manager.

Loads and validates environment variables required for Bitbucket API access.
"""

import os
from pydantic import BaseModel, Field, ValidationError
from typing import Self


class BitbucketConfig(BaseModel):
    """Bitbucket configuration loaded from environment variables.
    
    Required environment variables:
    - BITBUCKET_USERNAME: Atlassian account email
    - BITBUCKET_API_TOKEN: API token for authentication
    - BITBUCKET_WORKSPACE: Bitbucket workspace name
    - BITBUCKET_REPO_SLUG: Repository slug
    """
    
    bitbucket_username: str = Field(
        description="Atlassian account email address"
    )
    bitbucket_api_token: str = Field(
        description="Bitbucket API token (NOT app password)"
    )
    bitbucket_workspace: str = Field(
        description="Bitbucket workspace name"
    )
    bitbucket_repo_slug: str = Field(
        description="Repository slug"
    )
    
    @classmethod
    def from_env(cls) -> Self:
        """Load configuration from environment variables.
        
        Performs strict validation and provides clear error messages
        for missing or invalid configuration.
        
        Returns:
            BitbucketConfig: Validated configuration instance
            
        Raises:
            ValueError: If required environment variables are missing
        """
        required_vars = [
            "BITBUCKET_USERNAME",
            "BITBUCKET_API_TOKEN",
            "BITBUCKET_WORKSPACE",
            "BITBUCKET_REPO_SLUG"
        ]
        
        missing = [var for var in required_vars if not os.environ.get(var)]
        if missing:
            raise ValueError(
                f"Configuration error: Missing required environment variables: "
                f"{', '.join(missing)}\n\n"
                f"Please set the following environment variables:\n"
                f"  - BITBUCKET_USERNAME (your Atlassian email)\n"
                f"  - BITBUCKET_API_TOKEN (create at: https://bitbucket.org/[workspace]/workspace/settings/app-passwords)\n"
                f"  - BITBUCKET_WORKSPACE (your workspace name)\n"
                f"  - BITBUCKET_REPO_SLUG (repository slug)"
            )
        
        try:
            return cls(
                bitbucket_username=os.environ["BITBUCKET_USERNAME"],
                bitbucket_api_token=os.environ["BITBUCKET_API_TOKEN"],
                bitbucket_workspace=os.environ["BITBUCKET_WORKSPACE"],
                bitbucket_repo_slug=os.environ["BITBUCKET_REPO_SLUG"]
            )
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e}")
```

### Bitbucket Client (client/bitbucket_client.py)

```python
"""Bitbucket API client with HTTPBasicAuth authentication.

Uses requests library with session reuse for efficient API calls.
"""

import requests
from requests.auth import HTTPBasicAuth
from src.config import BitbucketConfig


class BitbucketClient:
    """Client for Bitbucket Cloud REST API v2.
    
    Authenticates using HTTP Basic Auth with API token (RFC-2617).
    
    Attributes:
        config: BitbucketConfig instance with credentials
        auth: HTTPBasicAuth instance for requests
        session: requests.Session for connection pooling
        repo_url: Base URL for repository-specific endpoints
    """
    
    BASE_URL = "https://api.bitbucket.org/2.0"
    
    def __init__(self, config: BitbucketConfig):
        """Initialize client with configuration.
        
        Args:
            config: Validated BitbucketConfig with credentials
        """
        self.config = config
        
        # HTTPBasicAuth with email as username, token as password
        self.auth = HTTPBasicAuth(
            config.bitbucket_username,
            config.bitbucket_api_token
        )
        
        # Session for connection pooling and default headers
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        
        # Repository-specific base URL
        self.repo_url = (
            f"{self.BASE_URL}/repositories/"
            f"{config.bitbucket_workspace}/{config.bitbucket_repo_slug}"
        )
    
    def get(self, endpoint: str, **kwargs) -> dict:
        """Make authenticated GET request to Bitbucket API.
        
        Args:
            endpoint: API endpoint path (e.g., "/pullrequests")
            **kwargs: Additional arguments for requests.get()
            
        Returns:
            dict: JSON response from API
            
        Raises:
            requests.exceptions.HTTPError: On 4xx/5xx responses
        """
        url = f"{self.repo_url}{endpoint}"
        response = self.session.get(url, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint: str, data: dict | None = None, **kwargs) -> dict:
        """Make authenticated POST request to Bitbucket API.
        
        Args:
            endpoint: API endpoint path
            data: JSON-serializable request body
            **kwargs: Additional arguments for requests.post()
            
        Returns:
            dict: JSON response from API
        """
        url = f"{self.repo_url}{endpoint}"
        response = self.session.post(
            url, 
            json=data,
            timeout=30,
            **kwargs
        )
        response.raise_for_status()
        return response.json()
    
    def test_authentication(self) -> bool:
        """Test that authentication is working.
        
        Makes a lightweight API call to verify credentials.
        
        Returns:
            bool: True if authentication succeeds, False otherwise
        """
        try:
            # Lightweight call to verify auth
            self.session.get(
                f"{self.BASE_URL}/user",
                timeout=10
            ).raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| App Passwords | API Tokens | 2024 (deprecated) | API tokens are the future; app passwords will be removed |
| OAuth 2.0 flows for server-to-server | HTTPBasicAuth with API token | Current | Simpler auth for automation use cases |
| Manual JSON-RPC handling | FastMCP decorator pattern | MCP SDK v1.x | Declarative tools with auto schema generation |
| Direct `requests` calls in tools | Client abstraction layer | Best practice 2024+ | Testable, mockable, DRY |

**Deprecated/outdated:**
- App Passwords: Deprecated by Atlassian; use API Tokens
- OAuth 1.0a: No longer supported by Bitbucket
- MCP SDK v0.x: Use v1.26.0+ with FastMCP

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml (tool.pytest.ini_options) |
| Quick run command | `pytest tests/test_config.py -x -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONFIG-01 | Validate 4 env vars on startup | unit | `pytest tests/test_config.py::test_config_from_env -x` | ❌ Wave 0 |
| CONFIG-01 | Reject missing env vars | unit | `pytest tests/test_config.py::test_config_missing_vars -x` | ❌ Wave 0 |
| CONFIG-02 | Clear error message on missing vars | unit | `pytest tests/test_config.py::test_config_error_message -x` | ❌ Wave 0 |
| CONFIG-03 | HTTPBasicAuth with API token | unit | `pytest tests/test_client.py::test_client_auth -x` | ❌ Wave 0 |
| CONFIG-03 | Authenticate successfully | integration | Manual: `python -c "from src.server import bitbucket_client; print(bitbucket_client.test_authentication())"` | ❌ Wave 0 |
| CONFIG-04 | FastMCP initialization | unit | `pytest tests/test_server.py::test_server_init -x` | ❌ Wave 0 |
| CONFIG-04 | Tool namespaced with bitbucket_ | unit | `pytest tests/test_server.py::test_tool_names -x` | ❌ Wave 0 |
| ERROR-03 | Logging to stderr only | unit | `pytest tests/test_server.py::test_logging_to_stderr -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_config.py -x` (< 5 seconds)
- **Per wave merge:** `pytest tests/ -v` (full test suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_config.py` - CONFIG-01, CONFIG-02 validation tests
- [ ] `tests/test_client.py` - CONFIG-03 authentication tests
- [ ] `tests/test_server.py` - CONFIG-04, ERROR-03 server tests
- [ ] `tests/conftest.py` - Shared fixtures (mock config, mock client)
- [ ] Framework install: `uv add --dev pytest pytest-responses responses`
- [ ] pyproject.toml: Add `[tool.pytest.ini_options]` section

## Open Questions

1. **Should we use Pydantic BaseSettings or plain BaseModel?**
   - What we know: BaseSettings has automatic env parsing but adds dependency on `pydantic-settings`
   - What's unclear: Whether BaseSettings behavior is worth the extra dependency
   - Recommendation: Use BaseModel with explicit `from_env()` method for clarity and fewer dependencies

2. **Should config validation happen on import or explicit call?**
   - What we know: Early validation is required (fail fast)
   - What's unclear: Whether import-time validation impacts testability
   - Recommendation: Import-time validation in server.py, mockable via module-level fixtures

## Sources

### Primary (HIGH confidence)
- MCP Python SDK GitHub (https://github.com/modelcontextprotocol/python-sdk) - FastMCP patterns, error handling, logging requirements
- MCP Quickstart Guide (https://modelcontextprotocol.io/quickstart/server) - STDIO transport, stderr logging requirement
- Bitbucket REST API Auth Docs (https://developer.atlassian.com/cloud/bitbucket/rest/intro/#authentication) - HTTPBasicAuth confirmation, API token vs App Password
- PyPI - mcp 1.26.0 (https://pypi.org/project/mcp/) - Version verification, Python 3.10+ requirement
- PyPI - requests 2.32.5 (https://pypi.org/project/requests/) - HTTPBasicAuth usage

### Secondary (MEDIUM confidence)
- Project research files (STACK.md, ARCHITECTURE.md, PITFALLS.md) - Cross-referenced with official docs

### Tertiary (LOW confidence)
- None - all findings verified with official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official MCP SDK docs, PyPI verified
- Architecture: HIGH - Official FastMCP patterns, validated examples
- Pitfalls: HIGH - Verified with MCP spec and Bitbucket API docs

**Research date:** 2025-03-06
**Valid until:** 2025-04-06 (30 days for stable stack)

---

*Research for Phase 1: Foundation - MCP server initialization, authentication, and configuration*
