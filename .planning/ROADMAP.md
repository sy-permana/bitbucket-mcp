# Roadmap: Bitbucket PR Manager MCP Server

## Overview

| Attribute | Value |
|-----------|-------|
| **Granularity** | Coarse (3-5 phases) |
| **Total Phases** | 4 |
| **v1 Requirements** | 17 mapped |
| **Coverage** | 100% ✓ |

## Phases

- [x] **Phase 1: Foundation** - Server initialization, auth, and client layer (completed 2026-03-06)
- [~] **Phase 2: Read Operations** - List PRs, get details, fetch diffs, check status (in progress)
- [ ] **Phase 3: PR Lifecycle** - Create, merge, approve, decline, request changes
- [ ] **Phase 4: Commenting** - General and inline PR comments

---

## Phase Details

### Phase 1: Foundation
**Goal:** MCP server boots with validated config, authenticated client, and proper logging
**Depends on:** Nothing (first phase)
**Requirements:** CONFIG-01, CONFIG-02, CONFIG-03, CONFIG-04, ERROR-03
**Success Criteria** (what must be TRUE):
1. Server exits cleanly with clear message if any of 4 required env vars are missing
2. Server initializes FastMCP with `bitbucket_` namespaced tool registration
3. Bitbucket API client authenticates successfully with HTTPBasicAuth + API Token
4. All log output goes to stderr (never stdout)
5. Server responds to MCP protocol initialization without errors
**Plans:** 3/3 plans complete
- Wave 1: 01-01 (config validation), 01-02 (Bitbucket client) - parallel
- Wave 2: 01-03 (MCP server) - depends on 01-01 and 01-02

### Phase 2: Read Operations
**Goal:** Users can query PRs and get contextual information without side effects
**Depends on:** Phase 1 (requires authenticated client)
**Requirements:** READ-01, READ-02, READ-03, READ-04, ERROR-01, ERROR-02
**Success Criteria** (what must be TRUE):
1. User can list PRs filtered by state (open/merged/declined)
2. User can get complete details for any PR by ID
3. User can fetch PR diff truncated at 10,000 characters with "[... truncated ...]" indicator
4. User can check CI/CD commit status for any commit hash
5. All tool errors return clear string messages (never JSON objects or tracebacks)
6. Error messages include context (e.g., "Failed to fetch PR #123: Not found")
**Plans:** 3 plans created
- Wave 1: 02-01 (list_prs, get_pr + Wave 0 test scaffold) - independent
- Wave 1: 02-02 (get_pr_diff) - depends on 02-01
- Wave 2: 02-03 (check_commit_status, error formatting) - depends on 02-01, 02-02

Plan List:
- [x] 02-01-PLAN.md — Core PR Read Tools (list_prs, get_pr_details) + test scaffold
- [x] 02-02-PLAN.md — PR Diff Tool (get_pr_diff with 10k truncation)
- [ ] 02-03-PLAN.md — Commit Status + Error Formatting Utility

### Phase 3: PR Lifecycle
**Goal:** Users can manage complete PR workflows from creation to merge
**Depends on:** Phase 2 (requires ability to read PRs to verify operations)
**Requirements:** LIFECYCLE-01, LIFECYCLE-02, LIFECYCLE-03, LIFECYCLE-04, LIFECYCLE-05
**Success Criteria** (what must be TRUE):
1. User can create PR with title, description, source branch, target branch
2. User can merge an open PR (with merge commit or fast-forward options)
3. User can approve a PR (and approval persists)
4. User can decline/reject a PR (and state changes to declined)
5. User can request changes on a PR (via native request-changes endpoint)
**Plans:** 3 plans created
- Wave 1: 03-01 (test scaffold), 03-02 (create_pr tool) - parallel
- Wave 2: 03-03 (merge, approve, decline, request_changes tools) - depends on 03-02

Plan List:
- [ ] 03-01-PLAN.md — Test Scaffold for PR Lifecycle Operations
- [ ] 03-02-PLAN.md — Create PR Tool (LIFECYCLE-01)
- [ ] 03-03-PLAN.md — State Transition Tools (merge, approve, decline, request changes)

### Phase 4: Commenting
**Goal:** Users can provide feedback on PRs via general and inline comments
**Depends on:** Phase 3 (requires existing PRs to comment on and diff understanding)
**Requirements:** COMMENT-01, COMMENT-02
**Success Criteria** (what must be TRUE):
1. User can add a general comment that appears in PR discussion
2. User can add an inline comment to a specific line with correct `to`/`from` mapping
3. Inline comments work for added, modified, and deleted lines
4. Comment errors include context about which PR and line failed
**Plans:** TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete    | 2026-03-06 |
| 2. Read Operations | 2/3 | In Progress | 2026-03-06 |
| 3. PR Lifecycle | 0/3 | Not started | - |
| 4. Commenting | 0/2 | Not started | - |

---

## Dependencies

```
Phase 1 (Foundation)
    ↓
Phase 2 (Read Operations) — validates client layer
    ↓
Phase 3 (PR Lifecycle) — requires working reads for verification
    ↓
Phase 4 (Commenting) — requires PRs exist, diff understanding from Phase 2
```

---

## Coverage Summary

| Category | Requirements | Phase |
|----------|--------------|-------|
| Foundation (CONFIG) | 4 | Phase 1 |
| Error Infrastructure (ERROR) | 3 | Phase 1 (ERROR-03), Phase 2 (ERROR-01, ERROR-02) |
| Read Operations (READ) | 4 | Phase 2 |
| PR Lifecycle (LIFECYCLE) | 5 | Phase 3 |
| Commenting (COMMENT) | 2 | Phase 4 |
| **Total** | **17** | **100% mapped** ✓ |

---

*Roadmap created: 2025-03-06*
*Granularity: Coarse (4 phases)*
