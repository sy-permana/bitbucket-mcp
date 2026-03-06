# Project Research Summary

**Project:** Bitbucket PR Manager MCP Server  
**Domain:** Python MCP Server with Bitbucket REST API Integration  
**Researched:** 2025-03-06  
**Confidence:** HIGH

## Executive Summary

This project is a Model Context Protocol (MCP) server that enables AI agents to manage Bitbucket pull requests programmatically. Following the official MCP Python SDK patterns and Bitbucket REST API v2 best practices, the server wraps Bitbucket's PR operations in a clean tool-based interface for LLM consumption.

The recommended approach is a **layered Python architecture** using FastMCP for protocol handling, a dedicated Bitbucket API client layer for HTTP operations, and strict environment-based configuration. The server must return all responses as human-readable strings (not JSON objects) to optimize for LLM comprehension. Key technical constraints include: HTTPBasicAuth with API tokens (App Passwords are deprecated), mandatory 10,000 character diff truncation to protect context windows, and single-workspace/single-repo scope per server instance.

**Key risks** center on MCP protocol compliance: stdout corruption breaks the server entirely (all logging must go to stderr), inline comment line number handling is complex and error-prone, and pagination handling is easy to overlook but critical for accurate results. These risks are mitigatable through careful architecture and the phased approach outlined below.

## Key Findings

### Recommended Stack

The stack is straightforward and well-established for Python MCP servers. **FastMCP** (from `mcp[cli] ^1.26.0`) provides the server framework with automatic tool schema generation from type hints and docstrings. **Requests** (`^2.32.5`) handles HTTP with built-in HTTPBasicAuth support—simpler than async alternatives and fully sufficient for MCP tool calls. **Pydantic** (`^2.12.5`) powers data validation and structured outputs. **Python-dotenv** enables local development with `.env` files, while **responses** provides HTTP mocking for unit tests. The project requires **Python 3.10+** for modern type hint support.

Authentication uses **HTTPBasicAuth** with the user's Atlassian email as username and an **API Token** (not deprecated App Passwords) as the password. Environment variables are the only configuration mechanism—`BITBUCKET_USERNAME`, `BITBUCKET_API_TOKEN`, `BITBUCKET_WORKSPACE`, and `BITBUCKET_REPO_SLUG` must all be set and validated strictly on server startup.

### Expected Features

**Must have (P0 — launch requirements):**
- **List PRs** — Filter by state (open/merged/declined), discover PRs
- **Get PR Details** — Foundation metadata for all operations
- **Create PR** — Open new pull requests
- **Merge PR** — Complete PR lifecycle
- **Approve/Decline PR** — Review workflow basics
- **Request Changes** — Feedback loop via comment + unapprove pattern
- **Get PR Diff** — Context for code review (mandatory 10k char truncation)
- **Add PR Comment** — General PR feedback
- **Add Inline Comment** — Line-specific feedback (complex: requires proper to/from line mapping)
- **Check Commit Status** — CI/CD gate verification

**Should have (P1 — add after validation):**
- Get PR Files — List modified files without full diff
- List My PRs — Quick "assigned to me" filter
- Get PR Comments — See existing discussion
- Get PR Activity — Audit trail for debugging
- Reopen PR — Recover mistakenly declined PRs

**Defer to v2+ (P2):**
- Smart Diff Summarization — Intelligent truncation beyond hard cutoff
- Add/Remove Reviewers — Team workflow management
- Update PR Description — Convenience feature

**Explicitly NOT building:** Webhook support (poll-based only per spec), multi-workspace support, OAuth/App Password auth, file/branch management, issue tracking, or repository administration.

### Architecture Approach

The architecture follows a **three-layer pattern** proven in MCP server implementations:

1. **FastMCP Server Layer** — Protocol handling, tool registration, message routing. Uses `@mcp.tool()` decorator with type hints and docstrings for automatic schema generation.

2. **Tool Functions Layer** — LLM-facing interface. Each tool validates parameters, calls the client layer, processes responses (truncating diffs), and returns formatted strings. All error handling happens here—never leak tracebacks or raw exceptions.

3. **Bitbucket API Client Layer** — Wraps `requests` with session reuse, HTTPBasicAuth, retry logic, and centralized error handling. Handles endpoint construction and response parsing.

**Key patterns to follow:**
- **String Response Pattern** — All tools return strings, never JSON objects or raw exceptions
- **Diff Truncation Pattern** — 10,000 character hard limit with clear truncation indicators
- **Fail-Fast Config** — Validate all 4 env vars on startup with clear error messages
- **Namespaced Tool Names** — Use `bitbucket_` prefix to avoid collisions (e.g., `bitbucket_get_pr_diff`)

### Critical Pitfalls

**1. STDIO Output Corruption**  
Writing to stdout (via `print()`, logging misconfiguration) corrupts JSON-RPC messages and breaks the server completely. **Avoid:** All output must go to stderr. Use `logging` module configured for stderr or `print(..., file=sys.stderr)`.

**2. Context Window Overflow from Large Diffs**  
Bitbucket diffs can be megabytes. Without truncation, they exceed LLM token limits. **Avoid:** Mandatory 10k character truncation on all diff-returning tools with clear "[... truncated ...]" indicators.

**3. Returning Raw Exceptions**  
Unhandled exceptions or JSON error objects confuse the LLM. **Avoid:** Wrap all tool calls in try/except, return clear string messages like `"Failed to fetch PR #123: Authentication failed."`

**4. Inline Comment Payload Complexity**  
Bitbucket requires precise `to`/`from` line numbers that depend on diff context. **Avoid:** Validate line numbers against the diff first, handle edge cases (new files: `from=null`, deleted files: `to=null`), test with all line types.

**5. Environment Variable Handling Failures**  
Missing vars, trailing whitespace, or poor error messages cause cryptic failures. **Avoid:** Strict validation on startup with explicit listing of which vars are missing. Trim whitespace from all values.

**6. Pagination Ignored**  
Bitbucket paginates all collections (default 10 items). Returning only `values` misses data. **Avoid:** Always check for `next` field, follow pages automatically for small datasets, expose pagination params for large ones.

**7. Authentication Scope Misconfiguration**  
Tokens need explicit scopes (`pullrequest`, `pullrequest:write`, `repository`). **Avoid:** Document required scopes, implement scope-aware error messages directing users to token settings.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation
**Rationale:** Config validation and client layer are dependencies for everything else. Must establish logging (stderr-only) and auth patterns before any tools work.
**Delivers:** Server initialization, env var validation, Bitbucket API client with auth, stderr logging infrastructure
**Addresses:** Environment setup, authentication pattern
**Avoids:** STDIO corruption (#1), Env var failures (#5), Auth format issues (#11)
**Research Flag:** Standard patterns — skip additional research

### Phase 2: Read Operations (Context Fetching)
**Rationale:** Read operations validate the client layer end-to-end without side effects. Diff truncation must be implemented before any diff tools are exposed.
**Delivers:** List PRs, Get PR Details, Get PR Diff (with truncation), Get PR Files, Check Commit Status
**Addresses:** P0 features: List PRs, Get PR Details, Get PR Diff, Check Commit Status
**Avoids:** Context overflow (#3), Pagination ignored (#7), UUID format confusion (#10)
**Research Flag:** Standard patterns — pagination and truncation are well-documented

### Phase 3: PR Lifecycle (Write Operations)
**Rationale:** Build on read operations with side-effect tools. Error handling wrapper critical here since failures have real consequences.
**Delivers:** Create PR, Merge PR, Approve PR, Decline PR, Request Changes, Reopen PR
**Addresses:** P0 features: Create PR, Merge PR, Approve, Decline, Request Changes; P1 feature: Reopen PR
**Avoids:** Error handling failures (#2), PR state value confusion (#12)
**Research Flag:** Standard patterns — Bitbucket API docs are clear on these endpoints

### Phase 4: Commenting
**Rationale:** Most complex due to inline comment line number mapping. Depends on PR lifecycle (need PRs to comment on) and diff understanding (for line validation).
**Delivers:** Add PR Comment (general), Add Inline Comment (line-specific)
**Addresses:** P0 features: Add PR Comment, Add Inline Comment; P1 features: Get PR Comments, Get PR Activity
**Avoids:** Inline comment complexity (#4), Auth scope issues (#6 — write scopes needed)
**Research Flag:** **Needs research** — Inline comment payload structure and line mapping requires validation

### Phase 5: Hardening & Polish
**Rationale:** Add resilience features that aren't required for MVP but needed for production use. Rate limiting, tool naming conventions, error message refinement.
**Delivers:** Rate limit handling, tool description improvements, edge case handling
**Addresses:** P1 features: List My PRs; Production readiness
**Avoids:** Rate limiting (#9), Tool name collisions (#8)
**Research Flag:** Standard patterns — retry logic and rate limiting are well-established

### Phase Ordering Rationale

The order follows **dependency chains** identified in research:
1. Config/client layer must exist before any tools
2. Read operations validate the stack before write operations introduce side effects
3. PR lifecycle must work before commenting (can't comment on non-existent PRs)
4. Inline comments require understanding of diffs (from Phase 2)

This grouping **minimizes risk** by tackling the highest-complexity items (inline comments) only after the foundation is solid, and by separating read vs write operations to allow safe validation.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 4 (Commenting):** Inline comment `to`/`from` line mapping is complex and may need API exploration to validate exact payload structure for added/modified/deleted lines

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation):** FastMCP patterns, HTTPBasicAuth, and env var validation are well-documented
- **Phase 2 (Read Operations):** Pagination and truncation are standard patterns
- **Phase 3 (PR Lifecycle):** Bitbucket REST API v2 documentation is comprehensive for these endpoints
- **Phase 5 (Hardening):** Rate limiting and retry logic are established patterns

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Official MCP Python SDK, requests, and pydantic are mature with clear documentation. Versions verified from PyPI. |
| Features | HIGH | Based on official GitHub MCP server reference implementation and Bitbucket API v2 docs. P0 features are standard PR operations. |
| Architecture | HIGH | FastMCP decorator pattern is the canonical approach. Layered architecture is standard for API-wrapping MCP servers. |
| Pitfalls | HIGH | MCP protocol behavior (stdio transport) verified from official spec. Bitbucket API quirks verified from Atlassian docs. |

**Overall confidence:** HIGH

All areas are backed by official documentation (MCP spec, Bitbucket API docs, SDK READMEs). The primary uncertainty is the exact payload structure for inline comments with complex line mapping, which is flagged for Phase 4 research.

### Gaps to Address

| Gap | How to Handle |
|-----|---------------|
| Inline comment line mapping | Research during Phase 4 planning—validate exact `to`/`from` behavior for added/modified/deleted lines |
| Real-world diff sizes | Monitor during Phase 2—if 10k chars is too restrictive, may need smarter truncation |
| Token scope requirements | Document clearly in setup instructions—test with minimally-scoped token during development |
| Rate limit thresholds | Monitor during Phase 5—Bitbucket's 1000 req/hour may need adjustment based on usage patterns |

## Sources

### Primary (HIGH confidence)
- **MCP Python SDK GitHub** — FastMCP patterns, tool decorator usage, server initialization — https://github.com/modelcontextprotocol/python-sdk
- **MCP Specification** — Protocol requirements, stdio transport, tool result format — https://modelcontextprotocol.io/specification/
- **Bitbucket Cloud REST API v2** — Endpoint documentation, authentication, pagination — https://developer.atlassian.com/cloud/bitbucket/rest/intro/
- **Bitbucket API Authentication Docs** — HTTPBasicAuth confirmation, API Token vs App Password deprecation — https://developer.atlassian.com/cloud/bitbucket/rest/intro/#authentication
- **PyPI Package Repositories** — Version verification for mcp 1.26.0, requests 2.32.5, pydantic 2.12.5

### Secondary (MEDIUM confidence)
- **GitHub MCP Server Reference** — Feature comparison, tool naming patterns — https://github.com/modelcontextprotocol/servers-archived/tree/main/src/github
- **MCP Quickstart Guide** — Server implementation patterns — https://modelcontextprotocol.io/quickstart/server

### Tertiary (LOW confidence)
- None — all sources are official documentation

---

*Research completed: 2025-03-06*  
*Ready for roadmap: yes*
