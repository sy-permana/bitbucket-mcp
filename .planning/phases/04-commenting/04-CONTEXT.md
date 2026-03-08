# Phase 4: Commenting - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can provide feedback on PRs via general and inline comments. Includes: adding general PR comments, adding inline comments to specific lines in the diff with correct `to`/`from` mapping, handling added/modified/deleted lines, and clear error messages when targeting fails.

</domain>

<decisions>
## Implementation Decisions

### Tool Structure
- **Two separate tools**: `bitbucket_add_comment` for general comments, `bitbucket_add_inline_comment` for line-specific
- Separate tools make LLM tool discovery clearer and parameter requirements obvious
- General comments: pr_id + content
- Inline comments: pr_id + file_path + line_number + content

### Inline Comment Line Targeting
- **File path + line number**: User provides file='src/main.py', line=42 — simple interface
- **Auto-detect line type**: Tool figures out if line is added/modified/deleted from diff context
- **Minimal validation**: Don't preview or confirm — just validate file/line exist, then post
- Claude handles the complex Bitbucket `to`/`from` API mapping internally

### Comment Success Response Format
- **Simple confirmation for both**: "Comment added to PR #123"
- Matches the tiered response pattern from Phase 3 (approve/decline style)
- No comment ID or URL in response — these are quick actions
- Same response format for general and inline comments

### Comment Content Format
- **Pass-through markdown**: Bitbucket supports markdown, pass whatever user provides
- **No client-side length limit**: Let Bitbucket API reject if too long, return clear error
- **Validate non-empty**: Check for empty/whitespace-only before hitting API

### Error Handling
- **File + line in errors**: "Failed to add comment to src/main.py line 42: Line not found in diff"
- **Clear file not found**: "Failed to add comment: File src/main.py not found in PR diff"
- **Consistent with other tools**: Use existing `_format_error()` pattern for API errors
- No line range suggestions or nearby context — keep errors concise

### Claude's Discretion
- Exact implementation of `to`/`from` line mapping for Bitbucket API
- How to detect if a line is added vs modified vs deleted
- Parameter naming for file path (file_path, path, filepath)
- Whether to fetch diff for validation or let API reject invalid targets

</decisions>

<specifics>
## Specific Ideas

- Keep the interface simple — file + line is how developers think about code comments
- Don't make users understand Bitbucket's internal diff representation
- Success messages should be quick confirmations since commenting is a rapid workflow

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bitbucket_client.post()` — already used for posting comments in `request_changes` (server.py:636-639)
- `_format_error()` — established error formatting with HTTP status handling
- Comment endpoint pattern: `/pullrequests/{pr_id}/comments` with `{'content': {'raw': text}}`

### Established Patterns
- String return format (not JSON) — PROJECT.md requirement
- FastMCP tool registration with `@mcp.tool()` decorator
- Error format: `[tool_name] Failed to X: reason` + context + suggestion
- State validation before operations (check PR exists, is open)

### Integration Points
- New comment tools register in `src/server.py` using `@mcp.tool()` decorator
- Tools access `bitbucket_client` instance (already initialized)
- May need to call `get_pr_diff` internally to validate inline comment targets
- Bitbucket inline comment API requires `inline` object with `to`/`from` line numbers and `path`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-commenting*
*Context gathered: 2026-03-08*
