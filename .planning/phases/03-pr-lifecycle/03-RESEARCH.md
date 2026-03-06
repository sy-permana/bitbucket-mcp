# Phase 3: PR Lifecycle - Research

**Researched:** 2026-03-07
**Domain:** Bitbucket Cloud REST API v2 - Pull Request Lifecycle Operations
**Confidence:** HIGH

## Summary

Phase 3 implements the complete PR lifecycle workflow for Bitbucket Cloud: creating PRs, merging with strategy selection, approving/declining, and requesting changes. The Bitbucket Cloud REST API provides straightforward POST endpoints for all these operations with consistent response patterns.

**Primary recommendation:** Use native Bitbucket Cloud endpoints for all operations. The `request-changes` endpoint (POST/DELETE /pullrequests/{id}/request-changes) is the modern, native way to handle change requests—no need for the legacy unapprove+comment pattern.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Success Response Format (Tiered Detail)**
  - Create PR: Summary + URL — show PR ID, title, source/target branches, and Bitbucket web URL
  - Merge PR: Confirmation + branches — show what was merged (source → target)
  - Approve/Decline: Confirmation only — simple message like "PR #123 approved"
  - URL inclusion: Only for create operations (when you'd want to view the new PR)
  - State in errors: Error messages show current PR state to explain why operation failed
  - Metadata only: No description preview in success responses

- **Merge Strategy Options**
  - Supported strategies: All three — `merge_commit`, `fast_forward`, `squash`
  - Default strategy: `merge_commit` (equivalent to `git merge --no-ff`)
  - Parameter name: `strategy` (simple and concise)
  - Branch cleanup: Separate `close_source_branch` parameter (boolean, default false)

- **State Change Validation**
  - PR state validation: Tool validates state before operations
    - Can't merge already-merged/declined PRs
    - Can't approve/decline already-closed PRs
    - Error messages include current state
  - Duplicate action prevention: Tool checks if user already approved/declined to prevent redundant calls
  - Branch existence: Let API handle (don't pre-validate source branch exists)

- **Request Changes Pattern**
  - Approach: Use native Bitbucket Cloud endpoints (not unapprove + comment)
  - Request changes: `POST /pullrequests/{id}/request-changes`
  - Cancel/reset: `DEL /pullrequests/{id}/request-changes`
  - Comment optional: Can include explanatory comment, but not required
  - Comment delivery: Posted separately via comment API when provided

### Claude's Discretion
- Exact parameter naming for optional merge fields
- Error message phrasing for state validation failures
- Order of information in success messages
- How to handle API errors for state transitions

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LIFECYCLE-01 | User can create a new pull request with title, description, source branch, and target branch | POST /pullrequests endpoint with title, source.branch.name, destination.branch.name, description fields |
| LIFECYCLE-02 | User can merge an open pull request | POST /pullrequests/{id}/merge with merge_strategy parameter (merge_commit, fast_forward, squash) |
| LIFECYCLE-03 | User can approve a pull request | POST /pullrequests/{id}/approve endpoint returns participant object |
| LIFECYCLE-04 | User can decline/reject a pull request | POST /pullrequests/{id}/decline endpoint returns updated PR object |
| LIFECYCLE-05 | User can request changes on a pull request (via comment pattern) | POST /pullrequests/{id}/request-changes native endpoint (not unapprove+comment) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | 2.32.5+ | HTTP client for Bitbucket API | Already used in BitbucketClient |
| mcp | 1.26.0+ | FastMCP framework for tool registration | Project standard |
| pydantic | 2.12.5+ | Data validation | Already used for config |

### Existing Assets (No New Dependencies)
| Component | Usage |
|-----------|-------|
| BitbucketClient.post() | POST operations for merge, approve, decline, create |
| _format_error() | Error formatting with HTTP status handling |
| @mcp.tool() decorator | FastMCP tool registration |

## Architecture Patterns

### API Endpoint Patterns

All lifecycle operations use POST endpoints following consistent patterns:

```python
# Source: Bitbucket Cloud REST API docs
# Base URL: https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}

# Create PR
POST /pullrequests
{
    "title": "string",              # Required
    "source": {
        "branch": {"name": "feature-branch"}  # Required
    },
    "destination": {
        "branch": {"name": "main"}  # Optional, defaults to repo.mainbranch
    },
    "description": "string",         # Optional
    "close_source_branch": true      # Optional, default false
}

# Merge PR
POST /pullrequests/{id}/merge
{
    "type": "string",
    "message": "string",             # Optional, custom merge commit message
    "close_source_branch": true,     # Optional, separate from create
    "merge_strategy": "merge_commit" # Options: merge_commit, fast_forward, squash
}

# Approve PR (simple POST, no body)
POST /pullrequests/{id}/approve
# Returns: Participant object

# Decline PR (simple POST, no body)  
POST /pullrequests/{id}/decline
# Returns: Pull Request object

# Request Changes (simple POST, no body)
POST /pullrequests/{id}/request-changes
# Returns: Participant object

# Cancel Request Changes
DELETE /pullrequests/{id}/request-changes
# Returns: 204 No Content
```

### State Validation Pattern

Tools must validate PR state before operations:

```python
# Source: CONTEXT.md + Bitbucket API behavior
# PR states: OPEN, MERGED, DECLINED

# Invalid transitions:
# - OPEN → (already merged) = Error
# - OPEN → (already declined) = Error
# - MERGED → merge = Error
# - DECLINED → merge = Error
# - MERGED → approve/decline = Error (already closed)
# - DECLINED → approve/decline = Error (already closed)

# Valid transitions:
# - OPEN → merge = OK
# - OPEN → approve = OK
# - OPEN → decline = OK
# - OPEN → request-changes = OK
```

### Success Response Formatting Pattern

Per CONTEXT.md tiered detail requirements:

```python
# Create PR - Full details + URL
"""Created PR #123: Add user authentication
Source: feature/auth → Target: main
URL: https://bitbucket.org/workspace/repo/pull-requests/123"""

# Merge PR - Confirmation + branches
"""Successfully merged PR #123: Add user authentication
feature/auth → main"""

# Approve/Decline - Confirmation only
"""PR #123 approved"""
"""PR #123 declined"""
```

### Error Handling Pattern

```python
# Source: Existing _format_error() in server.py + CONTEXT.md requirements
# Format: "[tool_name] Failed to X: reason" + context + suggestion

# State validation errors (must include current state):
"[bitbucket_merge_pr] Failed to merge PR #123: PR is already merged (state=MERGED)."

# HTTP 409 Conflict (merge conflict or invalid state):
"[bitbucket_merge_pr] Failed to merge PR #123: Merge conflict or PR not in mergeable state."

# HTTP 401/403/404/429/500 - Handled by existing _format_error()
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request changes workflow | Custom unapprove+comment logic | Native `POST /request-changes` endpoint | Bitbucket has dedicated endpoints; cleaner semantics |
| Merge strategy implementation | Custom git operations | API's `merge_strategy` parameter | API handles branch permissions, hooks, merge checks |
| State machine | Complex state transition logic | Simple pre-check + let API validate | API returns clear error messages; avoid duplicating logic |
| PR creation validation | Pre-validating branch existence | Let API validate | API checks branch permissions, existence, conflicts |
| Close source branch | Manual branch deletion after merge | `close_source_branch` parameter | Atomic with merge operation; handles permissions |

**Key insight:** Bitbucket's PR lifecycle endpoints are mature and handle edge cases (permissions, hooks, merge checks, race conditions). Custom implementations would miss these and create maintenance burden.

## Common Pitfalls

### Pitfall 1: Merge Strategy Confusion
**What goes wrong:** Users expect `fast_forward` to always work; it fails when branches have diverged
**Why it happens:** `fast_forward` requires linear history; API returns 409 if not possible
**How to avoid:** Default to `merge_commit`; document that `fast_forward` may fail
**Warning signs:** 409 Conflict responses on merge attempts

### Pitfall 2: State Validation Race Conditions
**What goes wrong:** PR state changes between check and operation
**Why it happens:** Another user merges/declines PR between our GET and POST
**How to avoid:** Always handle API error responses gracefully; don't rely solely on pre-checks
**Warning signs:** Intermittent 409 errors under load

### Pitfall 3: Duplicate Action Errors
**What goes wrong:** Approving an already-approved PR returns error
**Why it happens:** Bitbucket returns error for redundant approve/decline operations
**How to avoid:** Check participant state before approving; handle 409 as "already done"
**Warning signs:** Error when user tries to approve twice

### Pitfall 4: Confusing Request Changes with Unapprove
**What goes wrong:** Implementing "request changes" as unapprove+comment
**Why it happens:** Legacy workaround before native endpoint existed
**How to avoid:** Use native `POST /request-changes` endpoint per CONTEXT.md
**Warning signs:** Inconsistent UI state between API and Bitbucket web interface

### Pitfall 5: Missing close_source_branch on Merge
**What goes wrong:** Branch not deleted after merge even when user wanted it
**Why it happens:** Parameter only on merge endpoint, not create
**How to avoid:** Expose `close_source_branch` on merge tool; default to False per CONTEXT.md
**Warning signs:** User reports branches not being cleaned up

## Code Examples

### Create PR

```python
# Source: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/#api-repositories-workspace-repo-slug-pullrequests-post
@mcp.tool()
def bitbucket_create_pr(
    title: str,
    source_branch: str,
    target_branch: str | None = None,
    description: str | None = None,
    close_source_branch: bool = False
) -> str:
    """Create a new pull request."""
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
```

### Merge PR

```python
# Source: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/#api-repositories-workspace-repo-slug-pullrequests-pull-request-id-merge-post
@mcp.tool()
def bitbucket_merge_pr(
    pr_id: int,
    strategy: str = "merge_commit",
    close_source_branch: bool = False,
    message: str | None = None
) -> str:
    """Merge an open pull request."""
    try:
        # Get PR details first for state validation and branch info
        pr = bitbucket_client.get(f'/pullrequests/{pr_id}')
        state = pr.get('state')
        
        if state == 'MERGED':
            return f"[bitbucket_merge_pr] Failed to merge PR #{pr_id}: PR is already merged."
        if state == 'DECLINED':
            return f"[bitbucket_merge_pr] Failed to merge PR #{pr_id}: PR is declined."
        
        source = pr.get('source', {}).get('branch', {}).get('name', 'unknown')
        target = pr.get('destination', {}).get('branch', {}).get('name', 'unknown')
        
        data = {
            "type": "string",
            "merge_strategy": strategy,
            "close_source_branch": close_source_branch
        }
        if message:
            data["message"] = message
            
        bitbucket_client.post(f'/pullrequests/{pr_id}/merge', data=data)
        
        return (
            f"Successfully merged PR #{pr_id}: {pr.get('title')}\n"
            f"{source} → {target}"
        )
    except Exception as e:
        return _format_error(
            "bitbucket_merge_pr", 
            f"merge PR #{pr_id}", 
            e,
            {'pr_id': pr_id}
        )
```

### Approve PR

```python
# Source: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/#api-repositories-workspace-repo-slug-pullrequests-pull-request-id-approve-post
@mcp.tool()
def bitbucket_approve_pr(pr_id: int) -> str:
    """Approve a pull request."""
    try:
        # Get current PR state
        pr = bitbucket_client.get(f'/pullrequests/{pr_id}')
        state = pr.get('state')
        
        if state in ('MERGED', 'DECLINED'):
            return (
                f"[bitbucket_approve_pr] Failed to approve PR #{pr_id}: "
                f"PR is already {state.lower()}."
            )
        
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
```

### Decline PR

```python
# Source: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/#api-repositories-workspace-repo-slug-pullrequests-pull-request-id-decline-post
@mcp.tool()
def bitbucket_decline_pr(pr_id: int) -> str:
    """Decline/reject a pull request."""
    try:
        # Get current PR state
        pr = bitbucket_client.get(f'/pullrequests/{pr_id}')
        state = pr.get('state')
        
        if state == 'MERGED':
            return (
                f"[bitbucket_decline_pr] Failed to decline PR #{pr_id}: "
                f"PR is already merged."
            )
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
```

### Request Changes

```python
# Source: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/#api-repositories-workspace-repo-slug-pullrequests-pull-request-id-request-changes-post
@mcp.tool()
def bitbucket_request_changes(pr_id: int, comment: str | None = None) -> str:
    """Request changes on a pull request."""
    try:
        # Get current PR state
        pr = bitbucket_client.get(f'/pullrequests/{pr_id}')
        state = pr.get('state')
        
        if state in ('MERGED', 'DECLINED'):
            return (
                f"[bitbucket_request_changes] Failed to request changes on PR #{pr_id}: "
                f"PR is already {state.lower()}."
            )
        
        # Request changes via native endpoint
        bitbucket_client.post(f'/pullrequests/{pr_id}/request-changes')
        
        # Optionally add explanatory comment
        if comment:
            bitbucket_client.post(
                f'/pullrequests/{pr_id}/comments',
                data={'content': {'raw': comment}}
            )
        
        return f"Requested changes on PR #{pr_id}"
        
    except Exception as e:
        return _format_error(
            "bitbucket_request_changes",
            f"request changes on PR #{pr_id}",
            e,
            {'pr_id': pr_id}
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Unapprove + comment for "request changes" | Native `POST /request-changes` endpoint | Bitbucket Cloud 2020+ | Cleaner semantics; matches GitHub PR review experience |
| Manual branch cleanup | `close_source_branch` parameter on merge | Always available | Atomic operation; handles permissions correctly |
| Custom merge logic | API `merge_strategy` parameter | Always available | Respects branch permissions, hooks, merge checks |

**Deprecated/outdated:**
- **Unapprove+comment pattern:** Use native request-changes endpoint instead
- **Manual git merge:** Use API merge endpoint for proper permission/hook handling

## Open Questions

1. **Merge Conflict Handling**
   - What we know: API returns 409 for merge conflicts
   - What's unclear: Exact error message format for merge conflicts vs other 409s
   - Recommendation: Treat all 409s as "not mergeable" with generic message, or parse error response for specifics

2. **Async Merge Behavior**
   - What we know: API supports `async=true` query parameter for large merges
   - What's unclear: Whether we need to poll task status or if synchronous is sufficient
   - Recommendation: Use synchronous (async=false/default) for simplicity; add async handling if needed later

3. **Request Changes + Comment Atomicity**
   - What we know: Two separate API calls (request-changes + comment)
   - What's unclear: Whether partial failure (request-changes succeeds, comment fails) is acceptable
   - Recommendation: Document behavior; attempt both but report success if request-changes succeeds

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml |
| Quick run command | `pytest tests/test_lifecycle.py -x -v` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| LIFECYCLE-01 | Create PR with title/source/target/description | unit | `pytest tests/test_lifecycle.py::test_create_pr -x` | ❌ Wave 0 |
| LIFECYCLE-01 | Create PR validates required fields | unit | `pytest tests/test_lifecycle.py::test_create_pr_validation -x` | ❌ Wave 0 |
| LIFECYCLE-02 | Merge PR with strategy selection | unit | `pytest tests/test_lifecycle.py::test_merge_pr -x` | ❌ Wave 0 |
| LIFECYCLE-02 | Merge PR validates state (can't merge merged/declined) | unit | `pytest tests/test_lifecycle.py::test_merge_pr_state_validation -x` | ❌ Wave 0 |
| LIFECYCLE-03 | Approve PR | unit | `pytest tests/test_lifecycle.py::test_approve_pr -x` | ❌ Wave 0 |
| LIFECYCLE-03 | Approve PR prevents duplicate approval | unit | `pytest tests/test_lifecycle.py::test_approve_pr_duplicate -x` | ❌ Wave 0 |
| LIFECYCLE-04 | Decline PR | unit | `pytest tests/test_lifecycle.py::test_decline_pr -x` | ❌ Wave 0 |
| LIFECYCLE-04 | Decline PR validates state | unit | `pytest tests/test_lifecycle.py::test_decline_pr_state_validation -x` | ❌ Wave 0 |
| LIFECYCLE-05 | Request changes via native endpoint | unit | `pytest tests/test_lifecycle.py::test_request_changes -x` | ❌ Wave 0 |
| LIFECYCLE-05 | Request changes with optional comment | unit | `pytest tests/test_lifecycle.py::test_request_changes_with_comment -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_lifecycle.py -x`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_lifecycle.py` — covers LIFECYCLE-01 through LIFECYCLE-05
- [ ] Add PR lifecycle fixtures to `tests/conftest.py` (mock PR responses)
- [ ] Add mock responses for POST endpoints in tests

*(Existing test infrastructure in tests/conftest.py provides bitbucket_client fixture; need to add PR-specific fixtures)*

## Sources

### Primary (HIGH confidence)
- Bitbucket Cloud REST API docs: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/
  - Create PR: POST /repositories/{workspace}/{repo_slug}/pullrequests
  - Merge PR: POST /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}/merge
  - Approve PR: POST /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}/approve
  - Decline PR: POST /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}/decline
  - Request Changes: POST /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}/request-changes

### Secondary (MEDIUM confidence)
- Context7: /websites/developer_atlassian_cloud_bitbucket_rest_intro - OAuth scopes (pullrequest:write required)
- Context7: /websites/developer_atlassian_cloud_bitbucket_rest_intro - Error response format

### Tertiary (LOW confidence)
- None — all key findings verified with official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — No new dependencies; existing BitbucketClient.post() pattern
- Architecture: HIGH — Official Bitbucket API documentation with clear endpoint specs
- Pitfalls: HIGH — Based on API behavior and CONTEXT.md decisions

**Research date:** 2026-03-07
**Valid until:** 2026-06-07 (90 days — Bitbucket API is stable)
