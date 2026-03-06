# Phase 2: Read Operations - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Query PRs and get contextual information without side effects. Includes: listing PRs with state filters, getting detailed PR information, fetching diffs with truncation, and checking CI/CD commit status.

</domain>

<decisions>
## Implementation Decisions

### Error Message Style
- Helpful level of detail — include not just the error but suggestions for fixing
- Format: "[tool_name] Failed to X: reason" + context + suggestion
- Multiple errors: Summary count + details ("3 errors occurred: 1) ..., 2) ..., 3) ...")
- Different formats for API errors (HTTP status + message) vs client errors (validation issues)

### List Presentation
- PR fields to display: number, title, author, state, source/target branches, creation date, comment count
- Format: Multi-line blocks (each PR takes 2-3 lines with labeled fields)
- Limit: Show 20 most recent PRs
- Sorting: Newest first (chronological)

### Diff Presentation
- Full git diff format with line numbers and +/- markers
- Truncation indicator "[... truncated ...]" at:
  - End of the entire diff output
  - End of each truncated file (for multi-file diffs)
- Metadata header includes: PR info (#, title, author, state), stats (files changed, additions, deletions), branches, commit info
- Truncation strategy: Show as many files as possible (breadth-first) within 10k limit

### Output Formatting (Single PR Details)
- Claude's Discretion — follow established patterns from list presentation

### Claude's Discretion
- Exact spacing and indentation in multi-line blocks
- Date format for creation dates
- Exact wording of error suggestions
- Truncation logic implementation details

</decisions>

<specifics>
## Specific Ideas

- Error messages should feel helpful, not just report failures
- PR lists should feel like a concise dashboard — enough info to decide which to open
- Diff presentation should match what developers expect from git diff, just with protection

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BitbucketClient.get()` — already handles authenticated GET requests with session reuse
- `BitbucketClient.post()` — available for future POST operations
- Error handling pattern from config.py — multi-line messages with context

### Established Patterns
- stderr-only logging (configured before other imports in server.py)
- String return format (requirement from PROJECT.md)
- Module-level validation with fail-fast (sys.exit on config error)
- FastMCP tool registration pattern (mcp.tool decorator)

### Integration Points
- New read tools register in `src/server.py` using `@mcp.tool()` decorator
- Tools access `bitbucket_client` instance (already initialized in server.py)
- All tools must return strings (never JSON objects or tracebacks)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-read-operations*
*Context gathered: 2026-03-06*
