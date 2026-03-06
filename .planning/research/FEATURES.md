# Feature Landscape: Bitbucket PR Manager MCP Server

**Domain:** MCP Server for Bitbucket Pull Request Management  
**Researched:** 2025-03-06  
**Confidence:** HIGH

## Research Summary

Based on analysis of the official GitHub MCP server (reference implementation), Bitbucket REST API v2 capabilities, and MCP protocol patterns, this document maps the feature landscape for a Bitbucket-focused PR Manager MCP server. The project explicitly scopes to single-workspace, API Token authentication, and poll-based operations only.

---

## Table Stakes (Must-Have)

Features users expect from any PR management MCP server. Missing these makes the product unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **List PRs** | Basic discovery — users need to see open PRs | LOW | Support filtering by state (open/merged/declined), author. Bitbucket API: `GET /pull-requests` |
| **Get PR Details** | Core inspection — view PR metadata, description, author | LOW | Returns PR state, branches, participants, timestamps. Required by all other PR operations |
| **Create PR** | Essential workflow — open a new pull request | LOW | POST to `/pull-requests` with title, description, source/dest branches |
| **Merge PR** | Complete the lifecycle | LOW | POST to `/merge` endpoint. Handle merge conflicts gracefully with clear error messages |
| **Approve PR** | Code review basic — mark PR as approved | LOW | POST to `/approve`. Idempotent — can be called multiple times safely |
| **Decline PR** | Reject changes — close without merging | LOW | POST to `/decline`. Irreversible in Bitbucket (no reopen after decline) |
| **Request Changes** | Review feedback — request modifications before merge | MEDIUM | Bitbucket uses "UNAPPROVE" + comment workflow. Return string: "Changes requested on PR #123" |
| **Get PR Diff** | Review context — see what changed | MEDIUM | GET `/diff`. **Critical:** Truncate to 10,000 chars max per PROJECT.md requirements |
| **Add PR Comment** | General feedback — comment on PR overall | LOW | POST to `/comments`. General comments (not line-specific) |
| **Add Inline Comment** | Code review precision — comment on specific lines | MEDIUM | POST to `/comments` with anchor (line numbers). Complex: requires `from`/`to` line mapping |
| **Check Commit Status** | CI/CD gate — verify builds/tests pass | LOW | GET `/commits/{sha}/status` or PR status endpoint. Return clear pass/fail/pending |
| **Get PR Files** | Change overview — list modified files | LOW | GET `/changes` endpoint. Returns file paths, change types (added/modified/deleted) |

---

## Differentiators (Competitive Advantage)

Features that set this Bitbucket MCP server apart. Not strictly required, but add significant value for AI agent workflows.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Smart Diff Summarization** | When diff exceeds 10k chars, provide AI-friendly summary | MEDIUM | Truncate intelligently (show file list + summary stats) rather than hard cutoff |
| **List My PRs** | Quick filter — "show PRs assigned to me" | LOW | Uses Bitbucket `/inbox/pull-requests` or filter by participant/author |
| **Get PR Activity Log** | Audit trail — see all actions on PR | LOW | GET `/activities` endpoint. Useful for agent context |
| **Update PR Description** | Edit metadata — update PR title/body | LOW | PUT to PR endpoint. Useful for AI-generated PR descriptions |
| **Add Reviewers** | Delegate review — assign specific users | LOW | POST to `/participants` with role REVIEWER |
| **Remove Reviewers** | Manage assignments — unassign reviewers | LOW | DELETE from `/participants/{userSlug}` |
| **List PR Comments** | Context gathering — fetch existing comments | LOW | GET `/comments`. Useful for agent to see prior discussion |
| **Reopen PR** | Workflow recovery — reopen declined PRs | LOW | POST to `/reopen`. Note: Bitbucket allows reopen only if not merged |

---

## Anti-Features (Explicitly NOT Building)

Features that seem appealing but create problems or are out of scope per PROJECT.md.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Webhook Support** | Real-time updates without polling | PROJECT.md explicitly excludes: "Webhook handling — Out of scope, poll-based only" | Use polling pattern: client periodically checks status |
| **Multi-Workspace Support** | Manage PRs across workspaces | PROJECT.md constraint: "Multi-workspace support — Single workspace per server instance" | Launch multiple server instances with different env vars |
| **OAuth/App Password Auth** | Alternative auth methods | PROJECT.md constraint: "OAuth/App Password auth — API Token only as specified" | Use HTTPBasicAuth with API Token as required |
| **File/Content Editing** | "Why not let AI edit files directly?" | Scope creep — this is a PR manager, not a file editor. Git MCP server handles file operations | Use separate Git MCP server or git CLI for file changes |
| **Branch Management** | Create/delete branches outside PRs | Out of scope — Bitbucket API supports it but this is PR-focused server | Use git CLI or separate branch management tools |
| **Repository Management** | Create repos, manage settings | Scope creep — PR lifecycle only | Use Bitbucket UI or separate admin tools |
| **Issue Tracking** | Link to Jira/Bitbucket issues | Too broad — keep focus on PRs only | Use Atlassian's official MCP server for Jira/Confluence |
| **User/Group Management** | Admin users, permissions | Security risk and out of scope | Restrict to PR operations only |

---

## Feature Dependencies

```
Get PR Details
    └── requires ──> List PRs (to get PR ID)
    └── enhances ──> All other PR operations

Get PR Diff
    └── requires ──> Get PR Details
    └── requires ──> Get PR Files (for context)

Add Inline Comment
    └── requires ──> Get PR Diff (to validate line numbers)
    └── requires ──> Get PR Details (for current state)

Check Commit Status
    └── requires ──> Get PR Details (to get commit SHA)

Merge PR
    └── conflicts ──> Decline PR (mutually exclusive states)
    └── requires ──> Check Commit Status (typically want green builds)

Request Changes
    └── requires ──> Add PR Comment (explanation of requested changes)
    └── enhances ──> Unapprove PR (if previously approved)

Smart Diff Summarization
    └── requires ──> Get PR Diff
    └── requires ──> Get PR Files
```

### Dependency Notes

- **Add Inline Comment requires Get PR Diff:** Inline comments need valid line numbers from the diff. The agent should fetch diff first to understand line mapping.
- **Merge PR conflicts with Decline PR:** These are terminal states — a PR cannot be both merged and declined. API will return 409 Conflict if attempted.
- **Check Commit Status is advisory:** Unlike GitHub's protected branches, Bitbucket doesn't enforce status checks at API level. Server returns status but doesn't block merge.

---

## MVP Definition

### Launch With (v1.0)

Minimum viable product — core PR lifecycle per PROJECT.md Active requirements.

| Priority | Feature | Rationale |
|----------|---------|-----------|
| P0 | List PRs | Discovery — agents need to find PRs |
| P0 | Get PR Details | Foundation — metadata for all operations |
| P0 | Create PR | Open lifecycle — essential workflow start |
| P0 | Merge PR | Close lifecycle — complete the workflow |
| P0 | Approve PR | Review workflow — basic approval |
| P0 | Decline PR | Review workflow — basic rejection |
| P0 | Request Changes | Review workflow — feedback loop |
| P0 | Get PR Diff | Context — **with 10k char truncation** per PROJECT.md |
| P0 | Check Commit Status | CI/CD gate — verify build status |
| P0 | Add PR Comment | Communication — general PR feedback |
| P0 | Add Inline Comment | Communication — line-specific feedback |

### Add After Validation (v1.1)

Features to add once core PR lifecycle is stable.

| Priority | Feature | Trigger for Adding |
|----------|---------|-------------------|
| P1 | Get PR Files | Need to show what files changed without full diff |
| P1 | List My PRs | Users want quick "assigned to me" filter |
| P1 | Get PR Comments | Agents need to see existing discussion |
| P1 | List PR Activity | Debugging — understand PR history |
| P1 | Reopen PR | Recovery — handle mistakenly declined PRs |

### Future Consideration (v2.0)

Features to defer until product-market fit established.

| Priority | Feature | Why Deferred |
|----------|---------|--------------|
| P2 | Smart Diff Summarization | Complex — requires intelligent truncation logic |
| P2 | Add/Remove Reviewers | Team workflow — less critical for single-agent use |
| P2 | Update PR Description | Convenience — can edit via Bitbucket UI if needed |

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| List PRs | HIGH | LOW | P0 |
| Get PR Details | HIGH | LOW | P0 |
| Create PR | HIGH | LOW | P0 |
| Merge PR | HIGH | LOW | P0 |
| Approve PR | HIGH | LOW | P0 |
| Decline PR | HIGH | LOW | P0 |
| Request Changes | HIGH | MEDIUM | P0 |
| Get PR Diff | HIGH | MEDIUM | P0 |
| Check Commit Status | HIGH | LOW | P0 |
| Add PR Comment | HIGH | LOW | P0 |
| Add Inline Comment | HIGH | MEDIUM | P0 |
| Get PR Files | MEDIUM | LOW | P1 |
| List My PRs | MEDIUM | LOW | P1 |
| Get PR Comments | MEDIUM | LOW | P1 |
| Get PR Activity | MEDIUM | LOW | P1 |
| Reopen PR | LOW | LOW | P1 |
| Smart Diff Summarization | MEDIUM | MEDIUM | P2 |
| Add/Remove Reviewers | LOW | LOW | P2 |
| Update PR Description | LOW | LOW | P2 |

**Priority Key:**
- P0: Must have for launch (PROJECT.md Active requirements)
- P1: Should have, add after validation
- P2: Nice to have, future consideration

---

## Comparison: GitHub MCP Server vs Bitbucket PR Manager

| Feature | GitHub MCP Server | Bitbucket PR Manager | Notes |
|---------|-------------------|---------------------|-------|
| List PRs | ✅ `list_pull_requests` | ✅ Planned | Similar functionality |
| Get PR | ✅ `get_pull_request` | ✅ Planned | Similar |
| Create PR | ✅ `create_pull_request` | ✅ Planned | Similar |
| Merge PR | ✅ `merge_pull_request` | ✅ Planned | Bitbucket doesn't support merge_method options like GitHub |
| Approve | ✅ `create_pull_request_review` with APPROVE | ✅ Planned | Bitbucket has separate `/approve` endpoint |
| Request Changes | ✅ `create_pull_request_review` with REQUEST_CHANGES | ✅ Planned | Bitbucket uses comment + unapprove pattern |
| Decline | ❌ Not applicable (GitHub doesn't decline) | ✅ Planned | Bitbucket-specific feature |
| Get Diff | ✅ Implicit in `get_pull_request` | ✅ Planned with explicit truncation | PROJECT.md requires 10k char limit |
| Get Files | ✅ `get_pull_request_files` | ✅ Planned P1 | Similar |
| Get Comments | ✅ `get_pull_request_comments` | ✅ Planned P1 | Similar |
| Add Comment | ✅ `add_issue_comment` | ✅ Planned | Similar |
| Inline Comment | ✅ `create_pull_request_review` with comments array | ✅ Planned | Bitbucket uses `/comments` with anchor |
| Status Checks | ✅ `get_pull_request_status` | ✅ Planned | Similar |
| Update Branch | ✅ `update_pull_request_branch` | ❌ Not planned | Out of scope for v1 |
| Create Branch | ✅ `create_branch` | ❌ Not planned | Use git CLI |
| File Operations | ✅ `create_or_update_file`, `push_files` | ❌ Not planned | Use git CLI or Git MCP server |
| Search | ✅ `search_issues`, `search_code` | ❌ Not planned | Out of scope |

**Key Differences:**
1. **Bitbucket has "Decline"** — GitHub only has close/merge. Bitbucket's decline is terminal (no reopen after merge).
2. **GitHub has richer review model** — GitHub reviews bundle approve/request_changes/comment with inline comments. Bitbucket separates these into distinct endpoints.
3. **Bitbucket API v2 uses different paths** — `/projects/{key}/repos/{slug}/pull-requests` vs GitHub's `/repos/{owner}/{repo}/pulls`.
4. **Bitbucket uses "participant" model** — Reviewers are managed via participants endpoint with roles.

---

## Bitbucket API Endpoint Mapping

| MCP Tool | Bitbucket REST API v2 Endpoint | Method |
|----------|-------------------------------|--------|
| list_prs | `/rest/api/1.0/projects/{key}/repos/{slug}/pull-requests` | GET |
| get_pr | `/rest/api/1.0/projects/{key}/repos/{slug}/pull-requests/{id}` | GET |
| create_pr | `/rest/api/1.0/projects/{key}/repos/{slug}/pull-requests` | POST |
| merge_pr | `/rest/api/1.0/projects/{key}/repos/{slug}/pull-requests/{id}/merge` | POST |
| approve_pr | `/rest/api/1.0/projects/{key}/repos/{slug}/pull-requests/{id}/approve` | POST |
| decline_pr | `/rest/api/1.0/projects/{key}/repos/{slug}/pull-requests/{id}/decline` | POST |
| reopen_pr | `/rest/api/1.0/projects/{key}/repos/{slug}/pull-requests/{id}/reopen` | POST |
| get_pr_diff | `/rest/api/1.0/projects/{key}/repos/{slug}/pull-requests/{id}/diff` | GET |
| get_pr_files | `/rest/api/1.0/projects/{key}/repos/{slug}/pull-requests/{id}/changes` | GET |
| add_pr_comment | `/rest/api/1.0/projects/{key}/repos/{slug}/pull-requests/{id}/comments` | POST |
| list_pr_comments | `/rest/api/1.0/projects/{key}/repos/{slug}/pull-requests/{id}/comments` | GET |
| get_commit_status | `/rest/api/1.0/projects/{key}/repos/{slug}/commits/{sha}/build-status` | GET |

---

## Sources

- **GitHub MCP Server Reference:** https://github.com/modelcontextprotocol/servers-archived/tree/main/src/github (Official reference implementation, archived May 2025)
- **Bitbucket REST API v2:** https://docs.atlassian.com/bitbucket-server/rest/5.16.0/bitbucket-rest.html (Official Atlassian documentation)
- **PROJECT.md Requirements:** Local project documentation specifying: PR Lifecycle, Context Fetching with 10k truncation, Commenting, and Out of Scope constraints
- **MCP Protocol Specification:** https://modelcontextprotocol.io/ (Protocol patterns and SDK usage)

---

*Feature research for: Bitbucket PR Manager MCP Server*  
*Researched: 2025-03-06*  
*Confidence: HIGH — based on official reference implementations and API documentation*
