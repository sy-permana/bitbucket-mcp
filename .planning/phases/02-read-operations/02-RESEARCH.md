# Phase 2: Read Operations - Research

**Researched:** 2026-03-07
**Domain:** Bitbucket Cloud REST API v2 (Read Operations)
**Confidence:** HIGH

## Summary

This phase implements read-only MCP tools for querying Bitbucket pull requests. The tools provide safe, side-effect-free operations that form the foundation for all PR interactions. All read operations use the existing `BitbucketClient.get()` method with proper error handling that returns string messages (never JSON objects or tracebacks).

**Primary recommendation:** Use Bitbucket Cloud REST API v2 endpoints with `requests` library via the existing `BitbucketClient` class. Implement breadth-first diff truncation to maximize context within 10,000 character limit.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Error Message Style:** Helpful level of detail — include not just the error but suggestions for fixing
  - Format: "[tool_name] Failed to X: reason" + context + suggestion
  - Multiple errors: Summary count + details ("3 errors occurred: 1) ..., 2) ..., 3) ...")
  - Different formats for API errors (HTTP status + message) vs client errors (validation issues)

- **List Presentation:**
  - PR fields: number, title, author, state, source/target branches, creation date, comment count
  - Format: Multi-line blocks (each PR takes 2-3 lines with labeled fields)
  - Limit: Show 20 most recent PRs
  - Sorting: Newest first (chronological)

- **Diff Presentation:**
  - Full git diff format with line numbers and +/- markers
  - Truncation indicator "[... truncated ...]" at end of diff and end of each truncated file
  - Metadata header includes: PR info (#, title, author, state), stats (files changed, additions, deletions), branches, commit info
  - Truncation strategy: Show as many files as possible (breadth-first) within 10k limit

- **Output Formatting (Single PR Details):** Follow established patterns from list presentation

### Claude's Discretion
- Exact spacing and indentation in multi-line blocks
- Date format for creation dates
- Exact wording of error suggestions
- Truncation logic implementation details

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| READ-01 | User can list pull requests with optional state filter (open/merged/declined) | `GET /repositories/{workspace}/{repo_slug}/pullrequests` with `state` query param |
| READ-02 | User can get detailed information about a specific pull request by ID | `GET /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}` |
| READ-03 | User can fetch PR diff with automatic truncation at 10,000 characters | `GET /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}/diff` returns text/plain |
| READ-04 | User can check CI/CD commit status for a given commit hash | `GET /repositories/{workspace}/{repo_slug}/commit/{commit}/statuses` |
| ERROR-01 | All tool functions return clear string messages (never JSON objects or tracebacks) | Wrap all exceptions, format as strings with context |
| ERROR-02 | Error messages include context (e.g., "Failed to fetch PR #123: Authentication failed") | Use pattern: `[tool_name] Failed to X: {reason}` + context + suggestion |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | 2.32.5+ | HTTP client | Already configured with session pooling and auth |
| BitbucketClient | existing | API wrapper | Reuse Phase 1 implementation with `.get()` and `.post()` |
| FastMCP | 1.26.0+ | MCP server framework | Already initialized in server.py |

### Bitbucket API Endpoints
| Operation | Endpoint | Method | Response Type |
|-----------|----------|--------|---------------|
| List PRs | `/pullrequests` | GET | application/json |
| Get PR details | `/pullrequests/{id}` | GET | application/json |
| Get PR diff | `/pullrequests/{id}/diff` | GET | text/plain (NOT JSON!) |
| Get commit statuses | `/commit/{hash}/statuses` | GET | application/json |

### API Details

#### List Pull Requests (READ-01)
```
GET /repositories/{workspace}/{repo_slug}/pullrequests
```

**Query Parameters:**
- `state`: Filter by state. Valid values: `OPEN`, `MERGED`, `DECLINED`, `SUPERSEDED`
  - Can repeat parameter for multiple states: `?state=OPEN&state=MERGED`
  - Default: only `OPEN` PRs are returned

**Key Response Fields:**
```json
{
  "values": [
    {
      "id": 123,
      "title": "PR Title",
      "state": "OPEN",
      "author": {"display_name": "User Name"},
      "source": {"branch": {"name": "feature-branch"}},
      "destination": {"branch": {"name": "main"}},
      "created_on": "2026-03-07T10:00:00Z",
      "comment_count": 5,
      "task_count": 2
    }
  ],
  "size": 50,
  "page": 1,
  "pagelen": 10
}
```

**Pagination Notes:**
- Default `pagelen`: 10 items per page
- Use `?pagelen=50` to get more items (max recommended: 100)
- For Phase 2, limit to 20 most recent (no pagination handling needed yet)

#### Get Single PR (READ-02)
```
GET /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}
```

Returns full PR object with all fields including:
- `id`, `title`, `description`, `state`
- `author` (with `display_name`, `uuid`, `links`)
- `source` and `destination` (branch names, commit hashes)
- `reviewers` array
- `participants` array
- `comment_count`, `task_count`
- `created_on`, `updated_on`
- `merge_commit` (if merged)
- `closed_by` (if declined/merged)
- `reason` (decline reason)

#### Get PR Diff (READ-03)
```
GET /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}/diff
```

**CRITICAL:** Returns `text/plain` (NOT JSON!) containing unified diff format:
```
diff --git a/file.py b/file.py
index 1234567..abcdefg 100644
--- a/file.py
+++ b/file.py
@@ -10,7 +10,7 @@ def old_function():
-    old_line
+    new_line
```

**Implementation Notes:**
- Use `response.text` not `response.json()`
- Diff can be very large (MBs for big PRs)
- Must implement truncation at 10,000 characters
- Breadth-first truncation: include as many complete files as possible

#### Get Commit Statuses (READ-04)
```
GET /repositories/{workspace}/{repo_slug}/commit/{commit}/statuses
```

**Response Fields:**
```json
{
  "values": [
    {
      "key": "build-name",
      "name": "Build Name",
      "state": "SUCCESSFUL",
      "description": "42 tests passed",
      "url": "https://ci.example.com/build/123",
      "created_on": "2026-03-07T10:00:00Z",
      "updated_on": "2026-03-07T10:05:00Z"
    }
  ]
}
```

**State Values:** `SUCCESSFUL`, `FAILED`, `INPROGRESS`, `STOPPED`

## Architecture Patterns

### Tool Registration Pattern
```python
@mcp.tool()
def bitbucket_list_pull_requests(state: str | None = None) -> str:
    """List pull requests with optional state filter.
    
    Args:
        state: Optional filter - 'open', 'merged', or 'declined'
    
    Returns:
        Formatted list of PRs or error message
    """
    try:
        # Implementation
        pass
    except Exception as e:
        return _format_error("bitbucket_list_pull_requests", "list PRs", e)
```

### Error Handling Pattern
```python
def _format_error(tool_name: str, action: str, error: Exception, context: dict | None = None) -> str:
    """Format error message with context and suggestions.
    
    Format: "[tool_name] Failed to X: reason" + context + suggestion
    """
    if isinstance(error, requests.exceptions.HTTPError):
        status_code = error.response.status_code
        if status_code == 401:
            return f"[{tool_name}] Failed to {action}: Authentication failed. Check your BITBUCKET_API_TOKEN."
        elif status_code == 404:
            return f"[{tool_name}] Failed to {action}: Not found. {context or ''}"
        # ... more status codes
    return f"[{tool_name}] Failed to {action}: {str(error)}"
```

### Diff Truncation Algorithm (Breadth-First)
```python
def _truncate_diff(diff_text: str, max_chars: int = 10000) -> str:
    """Truncate diff to max_chars using breadth-first strategy.
    
    Strategy: Include as many complete files as possible.
    Files are separated by 'diff --git' lines.
    """
    if len(diff_text) <= max_chars:
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
        
        if current_length + len(file_content) + 50 <= max_chars:  # 50 for truncation message
            result.append(file_content)
            current_length += len(file_content) if i == 0 else len(file_content) + separator_len
        else:
            # Add truncation indicator
            result.append(f"\n[... truncated ...]\n\nAdditional files not shown due to size limit.")
            break
    
    return ''.join(result)
```

### PR List Formatting Pattern
```python
def _format_pr_list(prs: list[dict]) -> str:
    """Format PR list as multi-line blocks."""
    if not prs:
        return "No pull requests found."
    
    lines = [f"Found {len(prs)} pull request(s):\n"]
    
    for pr in prs[:20]:  # Limit to 20
        lines.append(f"PR #{pr['id']}: {pr['title']}")
        lines.append(f"  Author: {pr['author']['display_name']}")
        lines.append(f"  State: {pr['state']}")
        lines.append(f"  Branch: {pr['source']['branch']['name']} → {pr['destination']['branch']['name']}")
        lines.append(f"  Created: {pr['created_on']}")
        lines.append(f"  Comments: {pr.get('comment_count', 0)}")
        lines.append("")  # Blank line between PRs
    
    return '\n'.join(lines)
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP requests | Raw `urllib` or `httpx` | `BitbucketClient.get()` | Already handles auth, session pooling, base URL |
| Authentication | Custom auth headers | `HTTPBasicAuth` in client | Correct parameter order (email=username, token=password) |
| Error formatting | Simple `str(e)` | `_format_error()` helper | Consistent format with context and suggestions |
| Diff parsing | Manual line parsing | Text truncation only | API returns raw git diff, no parsing needed |
| State validation | Manual string checks | Pydantic validators | Type safety and clear error messages |
| JSON formatting | `json.dumps()` for output | String formatting | Requirement: never return JSON objects to LLM |
| Pagination | Full pagination logic | `pagelen=50` param | Phase 2 only needs first 20 results |

## Common Pitfalls

### Pitfall 1: Diff Returns Text, Not JSON
**What goes wrong:** Calling `.json()` on diff response causes `JSONDecodeError`
**Why it happens:** `/diff` endpoint returns `text/plain`, not `application/json`
**How to avoid:** Use `response.text` for diff endpoint
**Warning signs:** `json.decoder.JSONDecodeError: Expecting value`

```python
# WRONG
response = client.get(f"/pullrequests/{pr_id}/diff")
diff_data = response.json()  # ❌ Will fail

# CORRECT
response = bitbucket_client.session.get(url, timeout=30)
diff_text = response.text  # ✅ Plain text diff
```

### Pitfall 2: State Parameter Case Sensitivity
**What goes wrong:** Using lowercase state values returns wrong results
**Why it happens:** API expects uppercase: `OPEN`, `MERGED`, `DECLINED`
**How to avoid:** Validate and normalize state parameter before sending
**Warning signs:** All states returned when filtering expected

```python
# Normalize state parameter
state_map = {
    'open': 'OPEN',
    'merged': 'MERGED', 
    'declined': 'DECLINED'
}
if state and state.lower() in state_map:
    params['state'] = state_map[state.lower()]
```

### Pitfall 3: Commit Hash Variations
**What goes wrong:** Full commit hash (40 chars) vs short hash (7-12 chars) mismatch
**Why it happens:** Bitbucket accepts both but returns different results
**How to avoid:** Accept any length, document that full hash is recommended
**Warning signs:** 404 errors on valid-looking commits

### Pitfall 4: PR ID Type Confusion
**What goes wrong:** Passing PR ID as string causes URL construction issues
**Why it happens:** PR IDs are numeric but user input is string
**How to avoid:** Convert to int or use f-string formatting
**Warning signs:** `404 Not Found` for valid PR numbers

```python
# Safer approach
pr_id_int = int(pr_id)  # Validate it's numeric
endpoint = f"/pullrequests/{pr_id_int}"
```

### Pitfall 5: Empty Results vs Errors
**What goes wrong:** Empty PR list treated as error
**Why it happens:** No PRs with state filter is valid, not an error
**How to avoid:** Only treat HTTP 4xx/5xx as errors, empty `values` array is OK
**Warning signs:** Error message when repo has no open PRs

### Pitfall 6: Truncation Mid-File
**What goes wrong:** Cutting diff at exactly 10k chars can split in middle of line
**Why it happens:** Simple string truncation breaks diff format
**How to avoid:** Use breadth-first truncation (by file) with truncation indicators

### Pitfall 7: Nested Data Access
**What goes wrong:** KeyError on `pr['source']['branch']['name']` when branch deleted
**Why it happens:** Bitbucket keeps PR data but branch info may be missing
**How to avoid:** Use `.get()` with defaults for nested access

```python
# Safer nested access
source_branch = pr.get('source', {}).get('branch', {}).get('name', 'unknown')
```

## Code Examples

### READ-01: List Pull Requests
```python
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
            return f"No pull requests found" + (f" with state '{state}'" if state else "") + "."
        
        return _format_pr_list(prs)
        
    except requests.exceptions.HTTPError as e:
        return _format_http_error("bitbucket_list_pull_requests", "list PRs", e)
    except Exception as e:
        return f"[bitbucket_list_pull_requests] Failed to list PRs: {str(e)}"
```

### READ-03: Get PR Diff with Truncation
```python
@mcp.tool()
def bitbucket_get_pr_diff(pr_id: int) -> str:
    """Get PR diff with automatic truncation at 10,000 characters.
    
    Args:
        pr_id: Pull request ID number
    
    Returns:
        Formatted diff with metadata header, truncated if needed
    """
    try:
        # First get PR details for metadata
        pr_response = bitbucket_client.get(f'/pullrequests/{pr_id}')
        
        # Get diff (text/plain, not JSON)
        diff_url = f"{bitbucket_client.repo_url}/pullrequests/{pr_id}/diff"
        diff_response = bitbucket_client.session.get(diff_url, timeout=30)
        diff_response.raise_for_status()
        diff_text = diff_response.text
        
        # Build metadata header
        metadata = _build_diff_metadata(pr_response)
        
        # Truncate if needed
        if len(diff_text) > 10000:
            diff_text = _truncate_diff(diff_text, 10000)
            metadata += "\n[Note: Diff truncated to 10,000 characters]\n"
        
        return metadata + "\n" + diff_text
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"[bitbucket_get_pr_diff] Failed to fetch diff: PR #{pr_id} not found"
        return f"[bitbucket_get_pr_diff] Failed to fetch diff for PR #{pr_id}: {e.response.status_code}"
    except Exception as e:
        return f"[bitbucket_get_pr_diff] Failed to fetch diff for PR #{pr_id}: {str(e)}"
```

### READ-04: Check Commit Status
```python
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
            return f"No CI/CD statuses found for commit {commit_hash[:12]}."
        
        return _format_commit_statuses(commit_hash, statuses)
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"[bitbucket_check_commit_status] Failed to check status: Commit '{commit_hash[:12]}' not found"
        return f"[bitbucket_check_commit_status] Failed to check status for {commit_hash[:12]}: {e.response.status_code}"
    except Exception as e:
        return f"[bitbucket_check_commit_status] Failed to check status for {commit_hash[:12]}: {str(e)}"
```

## Validation Architecture

> Nyquist validation is enabled per `.planning/config.json`

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-responses |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/test_server.py -x -v` |
| Full suite command | `pytest tests/ -v --tb=short -p no:logging` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| READ-01 | List PRs with state filter | unit | `pytest tests/test_server.py::test_list_prs -x` | ❌ Wave 0 |
| READ-01 | State parameter validation | unit | `pytest tests/test_server.py::test_list_prs_state_filter -x` | ❌ Wave 0 |
| READ-02 | Get PR by ID | unit | `pytest tests/test_server.py::test_get_pr_details -x` | ❌ Wave 0 |
| READ-02 | Handle non-existent PR | unit | `pytest tests/test_server.py::test_get_pr_not_found -x` | ❌ Wave 0 |
| READ-03 | Fetch PR diff | unit | `pytest tests/test_server.py::test_get_pr_diff -x` | ❌ Wave 0 |
| READ-03 | Diff truncation at 10k | unit | `pytest tests/test_server.py::test_diff_truncation -x` | ❌ Wave 0 |
| READ-04 | Check commit status | unit | `pytest tests/test_server.py::test_check_commit_status -x` | ❌ Wave 0 |
| READ-04 | Handle commit without statuses | unit | `pytest tests/test_server.py::test_commit_no_statuses -x` | ❌ Wave 0 |
| ERROR-01 | String error messages (no JSON) | unit | `pytest tests/test_server.py::test_error_returns_string -x` | ❌ Wave 0 |
| ERROR-02 | Error context includes PR/commit info | unit | `pytest tests/test_server.py::test_error_includes_context -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_server.py -x -v -k "test_name"`
- **Per wave merge:** `pytest tests/ -v --tb=short -p no:logging`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_server.py` - server tool tests (currently only has protocol tests)
- [ ] `tests/test_read_operations.py` - dedicated read operations test file
- [ ] `tests/fixtures/pr_responses.py` - shared API response fixtures

### Mock Response Patterns
```python
# Example fixture for PR list response
@pytest.fixture
def mock_pr_list_response():
    return {
        "values": [
            {
                "id": 123,
                "title": "Test PR",
                "state": "OPEN",
                "author": {"display_name": "Test User"},
                "source": {"branch": {"name": "feature"}},
                "destination": {"branch": {"name": "main"}},
                "created_on": "2026-03-07T10:00:00Z",
                "comment_count": 3
            }
        ],
        "size": 1,
        "page": 1,
        "pagelen": 10
    }
```

## Sources

### Primary (HIGH confidence)
- Bitbucket Cloud REST API v2 Documentation: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/
- Commit Statuses API: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-commit-statuses/
- Existing `BitbucketClient` implementation in `src/client/bitbucket_client.py`

### Secondary (MEDIUM confidence)
- Phase 1 implementation patterns from `src/server.py` and `src/config.py`
- Test patterns from `tests/test_client.py` using `responses` library

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Bitbucket API is stable, existing client works
- Architecture: HIGH - Clear patterns from Phase 1, simple read operations
- Pitfalls: MEDIUM - Some edge cases only visible in production (deleted branches, large diffs)

**Research date:** 2026-03-07
**Valid until:** 2026-06-07 (Bitbucket API is stable, 90 days for major changes)

---

*Phase: 02-read-operations*
*Research completed: 2026-03-07*
