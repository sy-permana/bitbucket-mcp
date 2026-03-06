# Domain Pitfalls: MCP Server with Bitbucket Integration

**Domain:** MCP Server / Bitbucket API Integration  
**Researched:** 2025-03-06  
**Confidence:** HIGH (verified with official MCP spec and Bitbucket API docs)

---

## Critical Pitfalls

### Pitfall 1: STDIO Output Corruption

**What goes wrong:**  
Writing to stdout (via `print()`, `console.log()`, `System.out.println()`) corrupts JSON-RPC messages and breaks the MCP server completely. The client cannot communicate with the server.

**Why it happens:**  
MCP uses stdio transport for JSON-RPC communication. Any non-protocol output on stdout interferes with message framing. Developers habitually use print statements for debugging without realizing stdout is the communication channel.

**How to avoid:**  
- **Python**: Use `print("message", file=sys.stderr)` or the `logging` module
- **TypeScript**: Use `console.error()` instead of `console.log()`
- **Java**: Use `System.err.println()` or a logging library configured for stderr
- **C#**: Use `Console.Error.WriteLine()` instead of `Console.WriteLine()`
- Configure logging libraries to write to stderr or files only

**Warning signs:**  
- Server connects but tools don't appear in client
- "Invalid JSON" or "Parse error" in client logs
- Intermittent connection failures after adding debug code

**Phase to address:**  
**Phase 1: Foundation** — Implement logging infrastructure before any other features. Add a lint rule or code review checklist item to catch stdout writes.

---

### Pitfall 2: Returning Raw Exceptions Instead of String Messages

**What goes wrong:**  
Tools return unhandled exceptions, tracebacks, or JSON objects instead of clear string error messages. The LLM receives confusing technical output that it cannot interpret or act upon.

**Why it happens:**  
Developers let exceptions bubble up uncaught, or return structured error objects thinking they're being "proper." MCP expects tool results as human-readable strings for the LLM to process.

**How to avoid:**  
- Wrap all tool handlers in try/except blocks
- Catch specific exceptions (connection errors, auth errors, validation errors)
- Return clear, actionable string messages:
  - Good: `"Failed to fetch PR #123: Authentication failed. Check your BITBUCKET_API_TOKEN."`
  - Bad: `{"error": "401 Unauthorized", "traceback": "..."}`
- Use `isError: true` in the tool result for execution errors (not protocol errors)

**Warning signs:**  
- LLM responds with "I encountered an error but I'm not sure what went wrong"
- Tool outputs contain Python/Java stack traces
- Client logs show JSON parse errors on tool results

**Phase to address:**  
**Phase 1: Foundation** — Implement error handling wrapper in base tool class. Every tool must return strings, never raw exceptions.

---

### Pitfall 3: Context Window Overflow from Large Diffs

**What goes wrong:**  
Fetching PR diffs for large changes returns massive payloads that exceed LLM context limits (typically 100K-200K tokens), causing token limit errors or truncated, unusable output.

**Why it happens:**  
Bitbucket diffs can be enormous (megabytes for refactors). Without size limits, the server returns complete diffs that overwhelm the LLM context window. The PROJECT.md specifies 10,000 character truncation but this is easy to miss.

**How to avoid:**  
- **Mandatory truncation at 10,000 characters** as specified in PROJECT.md
- Implement intelligent truncation:
  - Keep file headers and context
- Truncate individual file diffs, not the entire response
- Add clear truncation indicator: `"\n[... diff truncated at 10,000 characters ...]"`
- Consider pagination: offer to fetch specific file ranges

**Warning signs:**  
- LLM responds with "The diff is too long for me to process"
- Token limit errors in client logs
- Slow response times on large PRs

**Phase to address:**  
**Phase 2: Context Fetching** — Implement diff truncation as a core utility function before any diff-returning tools are built.

---

### Pitfall 4: Inline Comment Payload Complexity

**What goes wrong:**  
Inline PR comments fail because of incorrect `to`/`from` line number handling or missing required fields in the inline object. The API returns 400 errors that are hard to debug.

**Why it happens:**  
Bitbucket's inline comment API requires precise line references that depend on diff context:
- `from`: Line number in the destination (target) file
- `to`: Line number in the source file
- Line numbers are 1-indexed
- For new files: `from` is null
- For deleted files: `to` is null
- Path must match exactly (case-sensitive)

**How to avoid:**  
- Fetch the diff first to understand file structure
- Validate line numbers exist in the file
- Use the correct fields:
```json
{
  "content": {"raw": "Comment text"},
  "inline": {
    "path": "src/file.py",
    "from": 42,  // destination line
    "to": 42     // source line
  }
}
```
- Test with both added and modified lines
- Provide clear error messages when line refs are invalid

**Warning signs:**  
- "Bad request" or 400 errors when posting comments
- Comments appear on wrong lines
- Comments fail silently

**Phase to address:**  
**Phase 3: Commenting** — Build inline comment utility with line validation before exposing the tool.

---

### Pitfall 5: Environment Variable Handling Failures

**What goes wrong:**  
Server crashes or fails silently when required environment variables are missing, malformed, or have trailing whitespace. Poor error messages make debugging difficult.

**Why it happens:**  
The project requires 4 strict env vars: `USERNAME`, `API_TOKEN`, `WORKSPACE`, `REPO_SLUG`. Developers:
- Forget to validate on startup
- Don't trim whitespace from token values
- Provide cryptic "NoneType has no attribute" errors

**How to avoid:**  
- **Strict validation on server initialization** — fail fast with clear message
- Validate all 4 vars exist and are non-empty
- Trim whitespace from all values
- Provide helpful error listing which vars are missing:
```
"Configuration error: Required environment variable BITBUCKET_API_TOKEN is not set. \
Please set the following environment variables:\n\
- BITBUCKET_USERNAME\n\
- BITBUCKET_API_TOKEN\n\
- BITBUCKET_WORKSPACE\n\
- BITBUCKET_REPO_SLUG"
```

**Warning signs:**  
- Server starts but tools fail with auth errors
- "401 Unauthorized" on all API calls (indicates bad token format)
- Silent failures (empty responses)

**Phase to address:**  
**Phase 1: Foundation** — Implement env var validation in server initialization before any tools are registered.

---

### Pitfall 6: Authentication Scope Misconfiguration

**What goes wrong:**  
API calls fail with 403 Forbidden even though credentials are correct, because the API token lacks required scopes for the operation.

**Why it happens:**  
Bitbucket API tokens require explicit scopes. Common mismatches:
- `pullrequest` scope needed to read PRs, `pullrequest:write` to merge/decline
- `repository` scope needed for diff access
- `pullrequest:write` implies `repository:write` but NOT vice versa
- Token created with wrong scope set

**How to avoid:**  
- Document required scopes in tool descriptions
- Implement scope-aware error handling:
```
"Authentication failed: Your API token lacks the 'pullrequest:write' scope \
required to merge pull requests. Create a new token at:\
https://bitbucket.org/[workspace]/workspace/settings/oauth"
```
- Test with minimally-scoped token during development
- Use API token (not deprecated app passwords)

**Warning signs:**  
- Some tools work, others return 403
- "Forbidden" errors on write operations
- Read operations succeed but write fails

**Phase to address:**  
**Phase 1: Foundation** — Document scope requirements. Add auth error detection that suggests scope fixes.

---

### Pitfall 7: Pagination Ignored Causing Incomplete Results

**What goes wrong:**  
Tools return only the first page of results (typically 10-50 items), missing PRs, comments, or commits. Users think data is missing.

**Why it happens:**  
Bitbucket API paginates all collection endpoints. The response includes:
```json
{
  "size": 142,
  "page": 1,
  "pagelen": 10,
  "next": "https://api.bitbucket.org/2.0/...",
  "values": [...]
}
```
Developers return `values` only and ignore `next`.

**How to avoid:**  
- Always check for `next` field in paginated responses
- For small datasets: follow all pages automatically
- For large datasets: expose pagination parameters to LLM with defaults
- Document pagination behavior in tool descriptions
- Consider adding `limit` parameter (max 100 per Bitbucket)

**Warning signs:**  
- "I only see 10 PRs but there should be more"
- Missing recent activity
- Inconsistent results across calls

**Phase to address:**  
**Phase 2: Context Fetching** — Implement pagination helper that all list tools use.

---

### Pitfall 8: Tool Name Collisions and Descriptions

**What goes wrong:**  
Tools have vague names like `get_pr` or `comment` that collide with other MCP servers, or descriptions that don't explain when to use them, causing the LLM to use wrong tools.

**Why it happens:**  
- Generic names: `get`, `list`, `create`
- Missing descriptions or descriptions that describe "what" not "when"
- No examples in descriptions

**How to avoid:**  
- Use namespaced tool names: `bitbucket_get_pull_request`, `bitbucket_post_inline_comment`
- Follow MCP naming conventions (kebab-case or snake_case consistently)
- Write descriptions for LLM context:
```python
@mcp.tool()
async def bitbucket_get_pull_request_diff(
    pr_id: int,
    max_chars: int = 10000
) -> str:
    """
    Get the diff (code changes) for a specific pull request.
    
    Use this when:
    - The user asks to review code changes
    - You need to see what files were modified
    - You want to analyze the implementation
    
    The diff is automatically truncated to prevent context overflow.
    Returns: Formatted diff with file headers and change hunks.
    """
```

**Warning signs:**  
- LLM uses wrong tool for the job
- Tool not found errors when multiple servers are loaded
- LLM asks user "which tool should I use?"

**Phase to address:**  
**Phase 1: Foundation** — Establish naming convention and description template before writing tools.

---

## Moderate Pitfalls

### Pitfall 9: Bitbucket API Rate Limiting

**What goes wrong:**  
Heavy usage hits Bitbucket's rate limits (1000 requests/hour for authenticated requests), causing 429 errors and failed operations.

**How to avoid:**  
- Implement exponential backoff on 429 responses
- Cache responses where appropriate (PR metadata)
- Batch operations when possible
- Document rate limits in server docs

**Warning signs:**  
- Intermittent 429 Too Many Requests errors
- Operations succeed on retry
- Errors increase with usage

**Phase to address:**  
**Phase 4: Hardening** — Add rate limit handling after core features work.

---

### Pitfall 10: UUID Format Confusion

**What goes wrong:**  
Bitbucket uses UUIDs in format `{12345678-1234-1234-1234-123456789abc}` with curly braces. Developers strip braces or use wrong format, causing 404 errors.

**How to avoid:**  
- Preserve UUID format exactly as returned by API
- Document that UUIDs include curly braces
- Validate UUID format in parameters that expect them

**Warning signs:**  
- 404 Not Found for resources that exist
- "User not found" errors with valid usernames

**Phase to address:**  
**Phase 2: Context Fetching** — Handle when working with user/repository objects.

---

### Pitfall 11: Incorrect HTTPBasicAuth Format

**What goes wrong:**  
Authentication fails because username/token are passed in wrong order or wrong format for HTTPBasicAuth.

**How to avoid:**  
Bitbucket API Token auth requires:
- Username: Your Atlassian email address
- Password: The API token (NOT your account password)
- Uses HTTP Basic Auth (RFC 2617)

```python
import requests
from requests.auth import HTTPBasicAuth

auth = HTTPBasicAuth(
    username=os.environ["BITBUCKET_USERNAME"],  # Email
    password=os.environ["BITBUCKET_API_TOKEN"]   # Token
)
```

**Warning signs:**  
- 401 Unauthorized on all requests
- "Invalid credentials" even with correct token

**Phase to address:**  
**Phase 1: Foundation** — Get auth working before any other API calls.

---

## Minor Pitfalls

### Pitfall 12: Assuming PR State Values

**What goes wrong:**  
Code assumes PR states are "OPEN", "CLOSED", "MERGED" but Bitbucket uses "OPEN", "MERGED", "DECLINED", "SUPERSEDED".

**How to avoid:**  
- Use exact state strings from Bitbucket API
- Document valid states in tool schemas

---

### Pitfall 13: File Path Encoding Issues

**What goes wrong:**  
File paths with special characters (spaces, unicode) cause 404s when not properly URL-encoded.

**How to avoid:**  
- Always URL-encode path parameters
- Use `urllib.parse.quote()` in Python

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip pagination | Simpler code | Missing data for large repos | Never for list operations |
| No input validation | Faster dev | Security issues, unclear errors | Never — validate all inputs |
| Hard-coded URLs | Works now | Breaks when API changes | Only for v2.0 API base URL |
| No caching | Simpler | Rate limit issues, slow | MVP only, add caching in v2 |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Bitbucket Auth | Using App Passwords (deprecated) | Use API Tokens (as specified) |
| Bitbucket Auth | Wrong username format | Use Atlassian email, not username |
| Bitbucket API | Using v1.0 endpoints | Use v2.0 API exclusively |
| MCP Protocol | Returning JSON objects | Return strings for LLM |
| MCP Protocol | Writing to stdout | Write to stderr only |
| MCP Protocol | Generic tool names | Use namespaced names |

---

## "Looks Done But Isn't" Checklist

- [ ] **Diff tool:** Actually truncates at 10,000 chars, not just claims to
- [ ] **Auth:** Works with minimal scopes (not over-scoped token)
- [ ] **Error handling:** All tools return clear strings, never tracebacks
- [ ] **Pagination:** List tools handle or document pagination limits
- [ ] **Inline comments:** Tested on added, modified, and deleted lines
- [ ] **Env vars:** Validates all 4 required vars on startup with clear errors
- [ ] **Logging:** No stdout writes in any code path
- [ ] **Tool names:** All prefixed with `bitbucket_` to avoid collisions

---

## Phase-Specific Pitfall Mapping

| Phase | Key Pitfall | Mitigation |
|-------|-------------|------------|
| Phase 1: Foundation | STDIO corruption (#1) | stderr-only logging infrastructure |
| Phase 1: Foundation | Env var failures (#5) | Strict validation on init |
| Phase 2: Context Fetching | Context overflow (#3) | 10k char truncation implementation |
| Phase 2: Context Fetching | Pagination ignored (#7) | Pagination helper function |
| Phase 3: Commenting | Inline comment complexity (#4) | Line validation utilities |
| Phase 3: Commenting | Auth scope issues (#6) | Scope-aware error messages |
| Phase 4: PR Lifecycle | Error handling (#2) | String-only return wrapper |
| All phases | Tool naming (#8) | `bitbucket_` prefix convention |

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| STDIO corruption | LOW | Fix logging, restart server |
| Context overflow | LOW | Add truncation, redeploy |
| Auth scope issues | MEDIUM | Regenerate token with correct scopes |
| Tool naming collision | MEDIUM | Rename tools, update client configs |
| Pagination missing | LOW | Add pagination helper, redeploy |
| Env var validation missing | LOW | Add validation, redeploy |

---

## Sources

- [MCP Specification - Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) — Tool result format requirements
- [MCP Build Server Tutorial](https://modelcontextprotocol.io/docs/develop/build-server) — Logging best practices
- [MCP Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices) — Authorization patterns
- [Bitbucket REST API v2](https://developer.atlassian.com/cloud/bitbucket/rest/intro/) — Authentication, pagination, inline comments
- [Bitbucket Pull Request API](https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/) — Comment payloads, diff structure
- [Python MCP SDK README](https://github.com/modelcontextprotocol/python-sdk) — FastMCP patterns, error handling

---

*Research for: Bitbucket PR Manager MCP Server*  
*Focus: MCP protocol issues, Bitbucket API quirks, auth/security, context management, error handling*
