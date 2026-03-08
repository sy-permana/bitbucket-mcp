# Phase 4: Commenting - Research

**Researched:** 2026-03-08
**Domain:** Bitbucket Cloud REST API v2 - Pull Request Comments (General and Inline)
**Confidence:** HIGH

## Summary

Phase 4 implements PR commenting functionality: general comments for discussion and inline comments for specific code lines. The Bitbucket Cloud REST API uses a single endpoint (`POST /pullrequests/{id}/comments`) for both types—general comments omit the `inline` property, while inline comments include it with `path`, `from`/`to` line mappings.

The critical complexity is the `to`/`from` line mapping for inline comments. Bitbucket uses `to` for lines in the new file (added/modified lines) and `from` for lines in the old file (deleted lines). The tool must translate simple user input (file + line number) into the correct API format based on whether the line was added, modified, or deleted.

**Primary recommendation:** Create two separate tools (`bitbucket_add_comment` and `bitbucket_add_inline_comment`) per CONTEXT.md decisions. For inline comments, fetch the PR diff to determine line type and construct the correct `inline` object. Use minimal validation—let the API reject invalid targets.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Two separate tools**: `bitbucket_add_comment` for general comments, `bitbucket_add_inline_comment` for line-specific
- **File path + line number interface**: User provides file='src/main.py', line=42 — simple interface
- **Auto-detect line type**: Tool figures out if line is added/modified/deleted from diff context
- **Minimal validation**: Don't preview or confirm — just validate file/line exist, then post
- **Simple confirmation response**: "Comment added to PR #123" for both tools (no ID/URL)
- **Pass-through markdown**: Bitbucket supports markdown, pass whatever user provides
- **No client-side length limit**: Let Bitbucket API reject if too long, return clear error
- **Validate non-empty**: Check for empty/whitespace-only before hitting API
- **File + line in errors**: "Failed to add comment to src/main.py line 42: Line not found in diff"
- **Use existing `_format_error()` pattern**: Consistent with other tools

### Claude's Discretion
- Exact implementation of `to`/`from` line mapping for Bitbucket API
- How to detect if a line is added vs modified vs deleted
- Parameter naming for file path (file_path, path, filepath)
- Whether to fetch diff for validation or let API reject invalid targets

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMMENT-01 | User can add a general comment to a pull request | POST /pullrequests/{id}/comments with `content.raw` only (no inline object) |
| COMMENT-02 | User can add an inline comment to a specific line in a pull request diff | POST /pullrequests/{id}/comments with `inline` object containing `path`, `from`/`to` |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | 2.32.5+ | HTTP client for Bitbucket API | Already used in BitbucketClient |
| mcp | 1.26.0+ | FastMCP framework for tool registration | Project standard |

### Existing Assets (No New Dependencies)
| Component | Usage |
|-----------|-------|
| BitbucketClient.post() | POST /pullrequests/{id}/comments |
| BitbucketClient.get() | GET /pullrequests/{id}/diff for line type detection |
| _format_error() | Error formatting with HTTP status handling |
| @mcp.tool() decorator | FastMCP tool registration |

## Architecture Patterns

### API Endpoint Pattern

Both general and inline comments use the same endpoint:

```python
# Source: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/#api-repositories-workspace-repo-slug-pullrequests-pull-request-id-comments-post
# Base URL: https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}

# General Comment (no inline object)
POST /pullrequests/{pr_id}/comments
{
    "content": {
        "raw": "This looks good overall!"  # Markdown supported
    }
}

# Inline Comment (with inline object)
POST /pullrequests/{pr_id}/comments
{
    "content": {
        "raw": "Consider using a constant here"
    },
    "inline": {
        "path": "src/main.py",
        "to": 42,            # For added/modified lines (new file)
        "from": null         # Or set "from": 42, "to": null for deleted lines
    }
}
```

### Inline Comment `to`/`from` Mapping

This is the core complexity. Bitbucket's `inline` object uses:
- `to`: Line number in the **new** file (destination) — use for **added** or **modified** lines
- `from`: Line number in the **old** file (source) — use for **deleted** lines
- `path`: File path as it appears in the diff

**Line Type Detection Logic:**

```python
# Source: Bitbucket activity log examples + API behavior
# Line types in unified diff format:
# - Lines starting with "+" = ADDED (use "to" only)
# - Lines starting with "-" = DELETED (use "from" only)  
# - Lines starting with " " = CONTEXT (use either, prefer "to")
# - MODIFIED = line deleted then added (use "to" for the new version)

# Mapping strategy:
# User gives: file="src/main.py", line=42
# Tool must determine:
#   1. Is this line added/modified? → {"to": 42, "from": null, "path": "src/main.py"}
#   2. Is this line deleted? → {"to": null, "from": 42, "path": "src/main.py"}
```

### Diff Parsing Strategy

Fetch the diff and parse to determine line type:

```python
def _get_line_type(diff_text: str, file_path: str, line_number: int) -> tuple[str, int | None, int | None]:
    """Determine line type and correct to/from values.
    
    Returns:
        tuple: (line_type, to_line, from_line)
        - line_type: 'added', 'deleted', 'context', or None if not found
        - to_line: Line number for "to" field (or None)
        - from_line: Line number for "from" field (or None)
    """
    # Parse diff to find the file section
    # Track both old (from) and new (to) line numbers through hunk headers
    # Identify if target line is +/- or context
    pass
```

### Tool Implementation Pattern

```python
# Source: CONTEXT.md decisions + existing tool patterns

@mcp.tool()
def bitbucket_add_comment(pr_id: int, content: str) -> str:
    """Add a general comment to a pull request.
    
    Args:
        pr_id: Pull request ID number
        content: Comment text (markdown supported)
    
    Returns:
        Confirmation message or error
    """
    # Validate non-empty
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


@mcp.tool()
def bitbucket_add_inline_comment(
    pr_id: int,
    file_path: str,
    line: int,
    content: str
) -> str:
    """Add an inline comment to a specific line in a pull request diff.
    
    Args:
        pr_id: Pull request ID number
        file_path: Path to the file (e.g., "src/main.py")
        line: Line number to comment on
        content: Comment text (markdown supported)
    
    Returns:
        Confirmation message or error
    """
    # Validate non-empty
    if not content or not content.strip():
        return (
            f"[bitbucket_add_inline_comment] Failed to add comment to {file_path} line {line}: "
            "Comment content cannot be empty."
        )
    
    try:
        # Get diff to determine line type
        diff_text = _get_pr_diff_text(pr_id)
        line_type, to_line, from_line = _get_line_type(diff_text, file_path, line)
        
        if line_type is None:
            return (
                f"[bitbucket_add_inline_comment] Failed to add comment to {file_path} line {line}: "
                "Line not found in PR diff."
            )
        
        inline = {'path': file_path}
        if to_line is not None:
            inline['to'] = to_line
        if from_line is not None:
            inline['from'] = from_line
            
        bitbucket_client.post(
            f'/pullrequests/{pr_id}/comments',
            data={
                'content': {'raw': content},
                'inline': inline
            }
        )
        return f"Comment added to PR #{pr_id}"
        
    except Exception as e:
        return _format_error(
            "bitbucket_add_inline_comment",
            f"add comment to {file_path} line {line}",
            e,
            {'pr_id': pr_id, 'file': file_path, 'line': line}
        )
```

### Error Message Pattern

Per CONTEXT.md, include file + line in errors:

```python
# File not found
"[bitbucket_add_inline_comment] Failed to add comment: File src/main.py not found in PR diff."

# Line not found  
"[bitbucket_add_inline_comment] Failed to add comment to src/main.py line 42: Line not found in diff."

# Empty content
"[bitbucket_add_inline_comment] Failed to add comment to src/main.py line 42: Comment content cannot be empty."

# API error (via _format_error)
"[bitbucket_add_inline_comment] Failed to add comment to src/main.py line 42: Authentication failed. ..."
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Diff parsing | Full git diff parser | Simple line-by-line with hunk tracking | Only need to identify line type, not full semantic understanding |
| Content validation | Regex-based markdown validator | Empty string check + let API validate | Bitbucket handles markdown parsing; we just pass through |
| File path normalization | Path manipulation library | Pass through as-is | Bitbucket accepts paths as they appear in diff |
| Line range comments | Multi-line selection logic | Single line only | CONTEXT.md specifies single line interface for v1 |

**Key insight:** The inline comment API is simpler than it appears. The tool's job is just to translate (file, line) → (path, to/from). Let Bitbucket handle all other validation.

## Common Pitfalls

### Pitfall 1: Wrong `to`/`from` Assignment
**What goes wrong:** Comment appears on wrong line or API returns error
**Why it happens:** Confusion about when to use `to` vs `from`
**How to avoid:** 
- `to` = new file line (added/modified) 
- `from` = old file line (deleted)
- Never set both for single-line comments
**Warning signs:** 400 Bad Request, comment on unexpected line

### Pitfall 2: Line Numbers Off By One
**What goes wrong:** User says line 42, comment appears on line 41 or 43
**Why it happens:** Diff parsers may use 0-indexed or 1-indexed counting inconsistently
**How to avoid:** Carefully track line numbers from diff hunk headers (`@@ -a,b +c,d @@`)
**Warning signs:** Off-by-one errors during testing

### Pitfall 3: File Path Mismatch
**What goes wrong:** "File not found in diff" error
**Why it happens:** User provides full path but diff uses relative, or vice versa
**How to avoid:** Match path format exactly as it appears in the diff
**Warning signs:** 400 errors when file clearly exists in diff

### Pitfall 4: Empty Content Not Caught
**What goes wrong:** API error for empty comment content
**Why it happens:** Whitespace-only strings pass falsy check
**How to avoid:** Use `if not content or not content.strip()`
**Warning signs:** 400 Bad Request on submit

### Pitfall 5: Deleted File Comments
**What goes wrong:** Can't comment on deleted files
**Why it happens:** Deleted files only have `from` lines in the "old" version
**How to avoid:** Support `from`-only inline objects for deleted content
**Warning signs:** Tests failing for deleted file scenarios

## Code Examples

### General Comment

```python
# Source: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/#api-repositories-workspace-repo-slug-pullrequests-pull-request-id-comments-post

@mcp.tool()
def bitbucket_add_comment(pr_id: int, content: str) -> str:
    """Add a general comment to a pull request."""
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
```

### Inline Comment with Line Type Detection

```python
# Source: Bitbucket API + diff parsing logic

def _parse_diff_for_line(diff_text: str, target_path: str, target_line: int) -> dict | None:
    """Parse diff to find line type and correct to/from mapping.
    
    Args:
        diff_text: Raw diff text from PR
        target_path: File path to find
        target_line: Line number user wants to comment on
        
    Returns:
        dict with 'path', 'to', 'from' or None if not found
    """
    current_file = None
    old_line = 0
    new_line = 0
    in_target_file = False
    
    for line in diff_text.split('\n'):
        # File header: diff --git a/path/to/file b/path/to/file
        if line.startswith('diff --git '):
            parts = line.split(' ')
            if len(parts) >= 4:
                # Extract path from "b/path/to/file"
                current_file = parts[3][2:] if parts[3].startswith('b/') else parts[3]
                in_target_file = (current_file == target_path)
                old_line = 0
                new_line = 0
            continue
            
        if not in_target_file:
            continue
            
        # Hunk header: @@ -old_start,old_count +new_start,new_count @@
        if line.startswith('@@'):
            import re
            match = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
            if match:
                old_line = int(match.group(1)) - 1  # -1 because we increment before checking
                new_line = int(match.group(2)) - 1
            continue
        
        # Content lines
        if line.startswith('-'):
            old_line += 1
            if new_line == target_line - 1:  # Deleted line case
                return {'path': target_path, 'from': old_line, 'to': None}
        elif line.startswith('+'):
            new_line += 1
            if new_line == target_line:  # Added line
                return {'path': target_path, 'from': None, 'to': new_line}
        elif line.startswith(' ') or line == '':
            old_line += 1
            new_line += 1
            if new_line == target_line:  # Context line (use 'to')
                return {'path': target_path, 'from': None, 'to': new_line}
    
    return None


@mcp.tool()
def bitbucket_add_inline_comment(
    pr_id: int,
    file_path: str,
    line: int,
    content: str
) -> str:
    """Add an inline comment to a specific line in a pull request diff."""
    if not content or not content.strip():
        return (
            f"[bitbucket_add_inline_comment] Failed to add comment to {file_path} line {line}: "
            "Comment content cannot be empty."
        )
    
    try:
        # Get diff text
        diff_url = f"{bitbucket_client.repo_url}/pullrequests/{pr_id}/diff"
        diff_response = bitbucket_client.session.get(diff_url, timeout=30)
        diff_response.raise_for_status()
        diff_text = diff_response.text
        
        # Parse diff to get line mapping
        inline = _parse_diff_for_line(diff_text, file_path, line)
        
        if inline is None:
            return (
                f"[bitbucket_add_inline_comment] Failed to add comment to {file_path} line {line}: "
                "Line not found in PR diff."
            )
        
        # Build inline object (remove None values)
        inline_obj = {'path': inline['path']}
        if inline.get('to') is not None:
            inline_obj['to'] = inline['to']
        if inline.get('from') is not None:
            inline_obj['from'] = inline['from']
        
        bitbucket_client.post(
            f'/pullrequests/{pr_id}/comments',
            data={
                'content': {'raw': content},
                'inline': inline_obj
            }
        )
        return f"Comment added to PR #{pr_id}"
        
    except Exception as e:
        return _format_error(
            "bitbucket_add_inline_comment",
            f"add comment to {file_path} line {line}",
            e,
            {'pr_id': pr_id, 'file': file_path, 'line': line}
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| N/A | Single endpoint for general + inline comments | Current | Simpler API design—inline is just an optional field |
| Manual line tracking | `from`/`to` semantic mapping | Current | API handles the old/new file distinction |

**Note:** The Bitbucket Cloud API is stable; this endpoint hasn't changed significantly.

## Open Questions

1. **Renamed Files**
   - What we know: Diff shows rename with `similarity index` and `rename from`/`rename to`
   - What's unclear: Which path to use for inline comments—old or new?
   - Recommendation: Use the new path (appears as `b/new/path` in diff); test during implementation

2. **Binary Files**
   - What we know: Binary files show "Binary files differ"
   - What's unclear: Can you add inline comments to binary files?
   - Recommendation: Let API reject; no special handling needed

3. **Very Large Diffs**
   - What we know: PR diff may be truncated at 10k chars per existing tool
   - What's unclear: Will inline comment targeting work on truncated portions?
   - Recommendation: Fetch full diff for comment targeting (don't use truncation); handle error if file/line not found

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with responses |
| Config file | pyproject.toml |
| Quick run command | `pytest tests/test_commenting.py -x -v` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| COMMENT-01 | Add general comment success | unit | `pytest tests/test_commenting.py::TestGeneralComment::test_add_comment_success -x` | ❌ Wave 0 |
| COMMENT-01 | Add general comment empty content | unit | `pytest tests/test_commenting.py::TestGeneralComment::test_add_comment_empty -x` | ❌ Wave 0 |
| COMMENT-01 | Add general comment API error | unit | `pytest tests/test_commenting.py::TestGeneralComment::test_add_comment_error -x` | ❌ Wave 0 |
| COMMENT-02 | Add inline comment on added line | unit | `pytest tests/test_commenting.py::TestInlineComment::test_inline_added_line -x` | ❌ Wave 0 |
| COMMENT-02 | Add inline comment on deleted line | unit | `pytest tests/test_commenting.py::TestInlineComment::test_inline_deleted_line -x` | ❌ Wave 0 |
| COMMENT-02 | Add inline comment on context line | unit | `pytest tests/test_commenting.py::TestInlineComment::test_inline_context_line -x` | ❌ Wave 0 |
| COMMENT-02 | Inline comment file not found | unit | `pytest tests/test_commenting.py::TestInlineComment::test_inline_file_not_found -x` | ❌ Wave 0 |
| COMMENT-02 | Inline comment line not found | unit | `pytest tests/test_commenting.py::TestInlineComment::test_inline_line_not_found -x` | ❌ Wave 0 |
| COMMENT-02 | Inline comment empty content | unit | `pytest tests/test_commenting.py::TestInlineComment::test_inline_empty_content -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_commenting.py -x`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_commenting.py` — covers COMMENT-01, COMMENT-02
- [ ] Add mock diff responses to test fixtures
- [ ] Add mock comment POST responses to test fixtures

## Sources

### Primary (HIGH confidence)
- Bitbucket Cloud REST API docs: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/#api-repositories-workspace-repo-slug-pullrequests-pull-request-id-comments-post
  - POST /pullrequests/{id}/comments endpoint specification
  - Request body schema with `content` and `inline` objects
  - Response schema with comment structure
- Bitbucket activity log examples showing inline comment structure with `from`/`to` fields

### Secondary (MEDIUM confidence)
- Existing codebase patterns:
  - `_format_error()` function in server.py
  - Diff fetching in `bitbucket_get_pr_diff` tool
  - Comment posting in `bitbucket_request_changes` tool (server.py:636-639)

### Tertiary (LOW confidence)
- None — all key findings verified with official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — No new dependencies; reuses existing BitbucketClient
- Architecture: HIGH — Official Bitbucket API documentation
- Pitfalls: HIGH — Based on API behavior and CONTEXT.md decisions

**Research date:** 2026-03-08
**Valid until:** 2026-06-08 (90 days — Bitbucket API is stable)
