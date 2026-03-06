# Phase 3: PR Lifecycle - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can manage complete PR workflows from creation to merge. Includes: create PR with title/description/branches, merge open PRs (with strategy selection), approve/decline PRs, and request changes pattern. All operations return clear string messages indicating success or failure.

</domain>

<decisions>
## Implementation Decisions

### Success Response Format (Tiered Detail)
- **Create PR**: Summary + URL — show PR ID, title, source/target branches, and Bitbucket web URL
- **Merge PR**: Confirmation + branches — show what was merged (source → target)
- **Approve/Decline**: Confirmation only — simple message like "PR #123 approved"
- **URL inclusion**: Only for create operations (when you'd want to view the new PR)
- **State in errors**: Error messages show current PR state to explain why operation failed
- **Metadata only**: No description preview in success responses

### Merge Strategy Options
- **Supported strategies**: All three — `merge_commit`, `fast_forward`, `squash`
- **Default strategy**: `merge_commit` (equivalent to `git merge --no-ff`)
- **Parameter name**: `strategy` (simple and concise)
- **Branch cleanup**: Separate `close_source_branch` parameter (boolean, default false)

### State Change Validation
- **PR state validation**: Tool validates state before operations
  - Can't merge already-merged/declined PRs
  - Can't approve/decline already-closed PRs
  - Error messages include current state
- **Duplicate action prevention**: Tool checks if user already approved/declined to prevent redundant calls
- **Branch existence**: Let API handle (don't pre-validate source branch exists)

### Request Changes Pattern
- **Approach**: Use native Bitbucket Cloud endpoints (not unapprove + comment)
- **Request changes**: `POST /pullrequests/{id}/request-changes`
- **Cancel/reset**: `DEL /pullrequests/{id}/request-changes`
- **Comment optional**: Can include explanatory comment, but not required
- **Comment delivery**: Posted separately via comment API when provided

### Claude's Discretion
- Exact parameter naming for optional merge fields
- Error message phrasing for state validation failures
- Order of information in success messages
- How to handle API errors for state transitions

</decisions>

<specifics>
## Specific Ideas

- Error messages should always include the current PR state when an operation fails due to wrong state
- Merge strategy follows common Git patterns: merge_commit (no-ff), fast_forward (ff-only when possible), squash (single commit)
- The "request changes" flow mirrors GitHub's PR review experience for familiarity
- Keep success messages concise for approve/decline since these are quick actions, more detail for create/merge since they're significant milestones

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BitbucketClient.post()` — already available for POST operations (merge, approve, decline, create)
- `_format_error()` — error formatting utility with HTTP status handling
- State parameter normalization pattern — convert lowercase ('open', 'merged') to API uppercase

### Established Patterns
- String return format (not JSON objects) — requirement from PROJECT.md
- FastMCP tool registration with `@mcp.tool()` decorator
- Error message format: "[tool_name] Failed to X: reason" + context + suggestion
- stderr-only logging (configured before other imports)

### Integration Points
- New lifecycle tools register in `src/server.py` using `@mcp.tool()` decorator
- Tools access `bitbucket_client` instance (already initialized)
- All tools must return strings, never raise exceptions to caller
- POST endpoints for merge, approve, decline, create at `/pullrequests/{id}/[action]` or `/pullrequests`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-pr-lifecycle*
*Context gathered: 2026-03-07*
