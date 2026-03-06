# Requirements: Bitbucket PR Manager MCP Server

**Defined:** 2025-03-06
**Core Value:** AI agents can perform complete PR workflows (open, review, comment, approve, merge) without human intervention

## v1 Requirements

### Foundation (CONFIG)

- [x] **CONFIG-01**: Server validates all 4 required environment variables on startup (BITBUCKET_USERNAME, BITBUCKET_API_TOKEN, BITBUCKET_WORKSPACE, BITBUCKET_REPO_SLUG)
- [x] **CONFIG-02**: Server fails gracefully with clear error message if any environment variable is missing
- [x] **CONFIG-03**: Server uses HTTPBasicAuth with API Token for Bitbucket authentication
- [x] **CONFIG-04**: Server initializes FastMCP with proper tool registration

### Read Operations (READ)

- [x] **READ-01**: User can list pull requests with optional state filter (open/merged/declined)
- [x] **READ-02**: User can get detailed information about a specific pull request by ID
- [x] **READ-03**: User can fetch PR diff with automatic truncation at 10,000 characters
- [x] **READ-04**: User can check CI/CD commit status for a given commit hash

### PR Lifecycle (LIFECYCLE)

- [ ] **LIFECYCLE-01**: User can create a new pull request with title, description, source branch, and target branch
- [ ] **LIFECYCLE-02**: User can merge an open pull request
- [ ] **LIFECYCLE-03**: User can approve a pull request
- [ ] **LIFECYCLE-04**: User can decline/reject a pull request
- [ ] **LIFECYCLE-05**: User can request changes on a pull request (via comment pattern)

### Commenting (COMMENT)

- [ ] **COMMENT-01**: User can add a general comment to a pull request
- [ ] **COMMENT-02**: User can add an inline comment to a specific line in a pull request diff

### Error Handling (ERROR)

- [x] **ERROR-01**: All tool functions return clear string messages (never JSON objects or tracebacks)
- [x] **ERROR-02**: Error messages include context (e.g., "Failed to fetch PR #123: Authentication failed")
- [x] **ERROR-03**: All logging goes to stderr (never stdout to avoid MCP protocol corruption)

## v2 Requirements

### Additional Read Operations

- **READ-05**: User can list files changed in a pull request
- **READ-06**: User can list PRs assigned to them
- **READ-07**: User can view existing comments on a pull request
- **READ-08**: User can view PR activity/audit trail

### Extended Lifecycle

- **LIFECYCLE-06**: User can reopen a declined pull request

## Out of Scope

| Feature | Reason |
|---------|--------|
| Webhook handling | Poll-based only as per spec; webhooks out of scope |
| Multi-workspace support | Single workspace per server instance per spec |
| OAuth/App Password authentication | API Token only as explicitly specified |
| File/branch management | Focus on PR operations only |
| Issue tracking | Bitbucket issues not part of PR workflow |
| Repository administration | Outside scope of PR management |
| Real-time updates | Polling-based architecture only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONFIG-01 | Phase 1 | Complete |
| CONFIG-02 | Phase 1 | Complete |
| CONFIG-03 | Phase 1 | Complete |
| CONFIG-04 | Phase 1 | Complete |
| ERROR-03 | Phase 1 | Complete |
| READ-01 | Phase 2 | Complete |
| READ-02 | Phase 2 | Complete |
| READ-03 | Phase 2 | Complete |
| READ-04 | Phase 2 | Complete |
| ERROR-01 | Phase 2 | Complete |
| ERROR-02 | Phase 2 | Complete |
| LIFECYCLE-01 | Phase 3 | Pending |
| LIFECYCLE-02 | Phase 3 | Pending |
| LIFECYCLE-03 | Phase 3 | Pending |
| LIFECYCLE-04 | Phase 3 | Pending |
| LIFECYCLE-05 | Phase 3 | Pending |
| COMMENT-01 | Phase 4 | Pending |
| COMMENT-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

**Phase Distribution:**
- Phase 1 (Foundation): 5 requirements — CONFIG-01 through CONFIG-04, ERROR-03
- Phase 2 (Read Operations): 6 requirements — READ-01 through READ-04, ERROR-01, ERROR-02
- Phase 3 (PR Lifecycle): 5 requirements — LIFECYCLE-01 through LIFECYCLE-05
- Phase 4 (Commenting): 2 requirements — COMMENT-01, COMMENT-02

---
*Requirements defined: 2025-03-06*
*Last updated: 2025-03-06 after auto-generation from research*
