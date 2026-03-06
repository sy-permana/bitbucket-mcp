# Bitbucket PR Manager MCP Server

## What This Is

A Model Context Protocol (MCP) server that wraps the Atlassian Bitbucket REST API v2, enabling AI agents to autonomously manage, review, and merge Pull Requests. Built with Python using FastMCP, the server provides a standardized interface for PR lifecycle management, diff analysis, commenting, and CI/CD status checking.

## Core Value

AI agents can perform complete PR workflows (open, review, comment, approve, merge) without human intervention when configured properly.

## Requirements

### Validated

- ✓ Authentication & Environment: HTTPBasicAuth with API Token, strict 4-variable env validation, stderr-only logging — Phase 1

### Active

- [ ] PR Lifecycle Management: open, merge, approve, decline PRs
- [ ] Context Fetching: get diff with context window protection, check commit status
- [ ] Commenting: general PR comments and inline line-specific comments
- [ ] Return Format: All tools return clear string messages (success/failure)

### Out of Scope

- GitHub/GitLab support — Focus on Bitbucket only for v1
- Webhook handling — Out of scope, poll-based only
- Multi-workspace support — Single workspace per server instance
- OAuth/App Password auth — API Token only as specified
- GUI/CLI client — MCP server only, clients use stdio

## Context

**Technical Environment:**
- Python 3.8+ with `mcp[cli]` and FastMCP
- `requests` library for HTTP
- Bitbucket REST API v2
- Environment-based configuration (no config files)

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
| API Token over App Password | User explicitly specified API Token | ✓ Validated — Phase 1 |
| String return format | User requirement for clear success/failure messages | — In Progress |
| Diff truncation at 10k chars | Protect LLM context window as specified | — In Progress |
| Live API docs fetch | Ensure accurate payload structures | — In Progress |
| stderr-only logging | Prevent stdio protocol corruption | ✓ Validated — Phase 1 |
| Pydantic config validation | Type-safe environment handling | ✓ Validated — Phase 1 |

---
*Last updated: 2026-03-06 after Phase 1 complete*
