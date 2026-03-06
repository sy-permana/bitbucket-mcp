# Technology Stack

**Project:** Bitbucket PR Manager MCP Server  
**Domain:** Python MCP server wrapping Bitbucket REST API v2  
**Researched:** 2025-03-06  
**Overall Confidence:** HIGH

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `mcp[cli]` | ^1.26.0 | MCP SDK with FastMCP | Official Anthropic Python SDK. FastMCP provides decorator-based tool/resource/prompt definitions with automatic schema generation. v1.26.0 is current stable (Jan 2026). Requires Python 3.10+. |
| `requests` | ^2.32.5 | HTTP client library | Industry standard for Python HTTP. Production-stable (Aug 2025), battle-tested with 30M+ weekly downloads. Built-in HTTPBasicAuth support for Bitbucket API. Synchronous only — sufficient for MCP tools. |
| `pydantic` | ^2.12.5 | Data validation | Powers FastMCP's structured output. V2 is current (Nov 2025), significantly faster than V1. Provides automatic JSON schema generation for tool responses. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-dotenv` | ^1.2.2 | Environment variable loading | Load `.env` files in development. Essential for local testing with Bitbucket credentials. Production deployments use actual env vars. |
| `responses` | ^0.26.0 | HTTP mocking for tests | Mock Bitbucket API responses in unit tests. Native `requests` integration. Use pytest-responses plugin for fixture support. |

### Infrastructure

| Technology | Purpose | Notes |
|------------|---------|-------|
| `uv` | Python package manager | Recommended by MCP SDK docs. Faster than pip, better dependency resolution. Use `uv add "mcp[cli]"` instead of pip. |
| `pytest` | Testing framework | Mature (v9.0.2, Dec 2025), fixture-based, async support via pytest-asyncio. Standard for Python projects. |

## Installation

### Using uv (recommended)
```bash
# Initialize project
uv init bitbucket-mcp-server
cd bitbucket-mcp-server

# Core dependencies
uv add "mcp[cli]" requests pydantic python-dotenv

# Development dependencies
uv add --dev pytest pytest-responses responses
```

### Using pip
```bash
# Core dependencies
pip install "mcp[cli]" requests pydantic python-dotenv

# Development dependencies
pip install pytest pytest-responses responses
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| HTTP Client | `requests` | `httpx` (v0.28.1) | `httpx` supports async/HTTP2 but adds complexity. `requests` is simpler, battle-tested, and sufficient for MCP tool calls. User explicitly specified `requests`. |
| HTTP Client | `requests` | `aiohttp` | Overkill for this use case. MCP tools are invoked synchronously via stdio. Async adds complexity without benefit. |
| Auth | HTTPBasicAuth | OAuth 2.0 | OAuth requires token refresh flows and callback handling. API Token + Basic Auth is simpler and sufficient for server-to-server automation. |
| Config | Environment vars | YAML/JSON config files | Environment variables are 12-factor app compliant. No config files to manage in containerized deployments. User requirement: "strict env var validation". |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `httpx` for this project | While modern, it's unnecessary complexity. `requests` handles all Bitbucket API requirements (Basic Auth, JSON, timeouts). User explicitly specified `requests`. | `requests` |
| App Passwords | Deprecated by Atlassian (as of the auth docs). Will be removed in future. | API Tokens (OAuth 2.0 alternative for Basic Auth) |
| `pytest-mock` alone | Doesn't mock HTTP layer. Need to intercept `requests` calls at the adapter level. | `responses` library |
| Global config files | Violates 12-factor app principles. Harder to manage in containers/serverless. | Environment variables (with `python-dotenv` for dev) |
| Custom auth classes | Unnecessary abstraction. `requests.auth.HTTPBasicAuth` handles API Token auth correctly. | `requests.auth.HTTPBasicAuth(username, api_token)` |

## Stack Patterns

### Authentication Pattern

Bitbucket API uses HTTP Basic Auth per RFC-2617:

```python
from requests.auth import HTTPBasicAuth
import os

auth = HTTPBasicAuth(
    os.environ["BITBUCKET_USERNAME"],  # Atlassian email
    os.environ["BITBUCKET_API_TOKEN"]  # API Token (not App Password)
)

response = requests.get(
    "https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}",
    auth=auth
)
```

**Critical:** App Passwords are deprecated. Use API Tokens only.

### Environment Variable Pattern

Strict validation at startup (fail fast):

```python
import os
from pydantic import BaseSettings, ValidationError

class Settings(BaseSettings):
    bitbucket_username: str
    bitbucket_api_token: str
    bitbucket_workspace: str
    bitbucket_repo_slug: str
    
    class Config:
        env_prefix = ""  # No prefix for these 4 vars
        
try:
    settings = Settings()
except ValidationError as e:
    # Return clear error string to MCP client
    raise RuntimeError(f"Missing required environment variables: {e}")
```

### Error Handling Pattern

All tools must return clear string messages:

```python
@mcp.tool()
def get_pr(pr_id: int) -> str:
    """Get pull request details."""
    try:
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        data = response.json()
        return format_pr_response(data)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"[ERROR] Pull request #{pr_id} not found"
        return f"[ERROR] Bitbucket API error: {e.response.status_code} - {e.response.text}"
    except requests.exceptions.RequestException as e:
        return f"[ERROR] Network error: {str(e)}"
    except Exception as e:
        # Never expose tracebacks
        return f"[ERROR] Unexpected error: {type(e).__name__}"
```

### Diff Truncation Pattern

Protect LLM context window:

```python
DIFF_TRUNCATION_LIMIT = 10000  # Characters

def truncate_diff(diff_text: str) -> str:
    if len(diff_text) > DIFF_TRUNCATION_LIMIT:
        return diff_text[:DIFF_TRUNCATION_LIMIT] + "\n\n[TRUNCATED: Diff exceeded 10,000 character limit]"
    return diff_text
```

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| mcp 1.26.0 | Python 3.10+ | FastMCP requires Python 3.10+ for modern type hints |
| requests 2.32.5 | Python 3.9+ | v2.32.5 fixes CVE-2024-35195. Avoid 2.32.0-2.32.1 (yanked). |
| pydantic 2.12.5 | Python 3.9+ | V2 has breaking changes from V1. Ensure no V1 code in project. |
| responses 0.26.0 | requests >=2.30.0 | Mock library keeps pace with requests. |

## Testing Strategy

### Unit Tests with Mocked API

```python
import responses
import pytest

@responses.activate
def test_get_pr_success():
    responses.get(
        "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/1",
        json={"id": 1, "title": "Test PR"},
        status=200
    )
    
    result = get_pr(1)
    assert "Test PR" in result

@responses.activate  
def test_get_pr_not_found():
    responses.get(
        "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests/999",
        json={"error": "Not found"},
        status=404
    )
    
    result = get_pr(999)
    assert "[ERROR]" in result
    assert "not found" in result.lower()
```

### Integration Tests

Use environment variables for real API calls (CI only):

```python
import pytest
import os

@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("BITBUCKET_INTEGRATION_TEST"),
    reason="Integration tests require BITBUCKET_INTEGRATION_TEST=1"
)
def test_real_api_call():
    # Make actual API call to Bitbucket
    pass
```

## Security Considerations

| Concern | Mitigation |
|---------|-----------|
| API Token exposure | Never log tokens. Use env vars only. |
| Token in error messages | Sanitize all error outputs |
| .env file committed | Add `.env` to `.gitignore` |
| Token expiration | Handle 401 responses gracefully |

## Sources

- **MCP Python SDK GitHub** (https://github.com/modelcontextprotocol/python-sdk) — Official docs, installation instructions, FastMCP patterns — HIGH confidence
- **PyPI - mcp 1.26.0** (https://pypi.org/project/mcp/) — Version verification, Python 3.10+ requirement — HIGH confidence  
- **PyPI - requests 2.32.5** (https://pypi.org/project/requests/) — Version verification, security patches noted — HIGH confidence
- **PyPI - httpx 0.28.1** (https://pypi.org/project/httpx/) — Alternative research — HIGH confidence
- **PyPI - pydantic 2.12.5** (https://pypi.org/project/pydantic/) — Version verification, V2 features — HIGH confidence
- **PyPI - pytest 9.0.2** (https://pypi.org/project/pytest/) — Testing framework version — HIGH confidence
- **PyPI - python-dotenv 1.2.2** (https://pypi.org/project/python-dotenv/) — Environment management — HIGH confidence
- **PyPI - responses 0.26.0** (https://pypi.org/project/responses/) — Mocking library version — HIGH confidence
- **Bitbucket Cloud REST API Auth Docs** (https://developer.atlassian.com/cloud/bitbucket/rest/intro/#authentication) — HTTPBasicAuth confirmation, API Token vs App Password deprecation — HIGH confidence

---

*Stack research for: Python MCP server with Bitbucket API integration*  
*Researched: 2025-03-06*
