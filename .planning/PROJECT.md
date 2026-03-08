# Bitbucket PR Manager MCP Server

## What This Is

A Model Context Protocol (MCP) server that wraps the Atlassian Bitbucket REST API v2, enabling AI agents to autonomously manage, review, and merge Pull Requests. Built with Python using FastMCP, the server provides a standardized interface for PR lifecycle management, diff analysis, commenting, and CI/CD status checking.

## Core Value

AI agents can perform complete PR workflows (open, review, comment, approve, merge) without human intervention when configured properly.

## Requirements

### Validated

- ✓ Authentication & Environment: HTTPBasicAuth with API Token, strict 4-variable env validation, stderr-only logging — v1.0
- ✓ PR Lifecycle Management: create, merge, approve, decline PRs — v1.0
- ✓ Context Fetching: get diff with 10k truncation, check commit status — v1.0
- ✓ Commenting: general PR comments and inline line-specific comments with to/from mapping — v1.0
- ✓ Return Format: All tools return clear string messages (success/failure) — v1.0

### Out of Scope

- GitHub/GitLab support — Focus on Bitbucket only for v1
- Webhook handling — Out of scope, poll-based only
- Multi-workspace support — Single workspace per server instance
- OAuth/App Password auth — API Token only as specified
- GUI/CLI client — MCP server only, clients use stdio
- File/branch management — Focus on PR operations only
- Issue tracking — Bitbucket issues not part of PR workflow
- Repository administration — Outside scope of PR management
- Real-time updates — Polling-based architecture only

## Context

**Technical Environment:**
- Python 3.8+ with `mcp[cli]` and FastMCP
- `requests` library for HTTP
- Bitbucket REST API v2
- Environment-based configuration (no config files)
- Test coverage: 85 tests (84 passing, 1 pre-existing unrelated failure)

**v1.0 Shipped:**
- 10 MCP tools across 4 phases
- Complete PR lifecycle: create, merge, approve, decline, request changes
- PR commenting: general + inline with diff parsing
- Error handling: all errors return clear strings with context
- Diff truncation at 10,000 characters

**Key Considerations:**
- LLM context window protection is critical (diff truncation at 10k chars)
- API documentation must be fetched live before implementation
- Inline comment payloads require careful handling of `to`/`from` line numbers
- All errors must be surfaced as clear strings, never tracebacks

## Constraints

- **Tech Stack**: Python, mcp[cli], requests — Specified by user
- **Authentication**: HTTPBasicAuth with API Token only — User requirement
- **Environment Variables**: Strict 4-variable requirement (USERNAME, API_TOKEN, WORKSPACE, REPO_SLUG)
- **Return Format**: String messages only, no JSON objects or tracebacks
- **Context Window**: Diff truncation mandatory at 10,000 characters

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| API Token over App Password | User explicitly specified API Token | ✓ Validated — v1.0 |
| String return format | User requirement for clear success/failure messages | ✓ Validated — v1.0 |
| Diff truncation at 10k chars | Protect LLM context window as specified | ✓ Validated — v1.0 |
| Live API docs fetch | Ensure accurate payload structures | ✓ Validated — v1.0 |
| stderr-only logging | Prevent stdio protocol corruption | ✓ Validated — v1.0 |
| Pydantic config validation | Type-safe environment handling | ✓ Validated — v1.0 |
| Two separate tools for general vs inline comments | User preference for explicit distinction | ✓ Validated — v1.0 |
| Diff-based line type detection | Correct Bitbucket API to/from mapping | ✓ Validated — v1.0 |
| Simple confirmation responses | Match existing approve/decline patterns | ✓ Validated — v1.0 |

---

*Last updated: 2026-03-08 after v1.0 milestone*
