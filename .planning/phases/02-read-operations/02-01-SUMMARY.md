---
phase: 02-read-operations
plan: 01
subsystem: api
tags: [bitbucket, pull-requests, mcp-tools]

requires:
  - phase: 01-foundation
    provides: BitbucketClient with authenticated GET/POST, stderr logging

provides:
  - bitbucket_list_pull_requests tool with state filtering
  - bitbucket_get_pull_request tool with full details
  - _format_error() helper for consistent error formatting
  - _format_pr_list() helper for multi-line PR formatting
  - _format_pr_detail() helper for single PR display

affects:
  - 02-02 (diff operations - depends on error formatting patterns)
  - 02-03 (commit status - uses same client patterns)
  - 03-lifecycle (needs PR discovery via list_prs)

tech-stack:
  added: []
  patterns:
    - "Error format: [tool_name] Failed to X: reason + context + suggestion"
    - "Safe nested dict access using .get() chains"
    - "State parameter normalization (lowercase to API uppercase)"

key-files:
  created:
    - tests/test_read_operations.py
  modified:
    - src/server.py

key-decisions:
  - "Multi-line PR formatting with labeled fields for readability"
  - "State normalization: user-friendly lowercase ('open') to API uppercase ('OPEN')"
  - "Error strings include tool name for debugging context"
  - "Safe nested access prevents KeyError on deleted branches"

requirements-completed: [READ-01, READ-02, ERROR-01, ERROR-02]

duration: 5min
completed: 2026-03-06
---

# Phase 2 Plan 1: Core PR Read Tools Summary

**Two MCP tools for PR discovery and inspection: list_prs with state filtering and get_pr with full details**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-06T18:55:05Z
- **Completed:** 2026-03-06T19:01:03Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Created Wave 0 test scaffold with 7 test cases for list/get PR operations
- Implemented `bitbucket_list_pull_requests` with state filter support (open/merged/declined)
- Implemented `bitbucket_get_pull_request` with full PR details including reviewers and description
- Established error formatting pattern: `[tool_name] Failed to X: reason + context + suggestion`

## Task Commits

Each task was committed atomically:

1. **Task 0: Create test scaffold** - `d2efeca` (test)
2. **Task 1: Implement list_prs tool** - `8daf18e` (feat)
3. **Task 2: Implement get_pr tool** - `00f98d5` (feat) - *Note: committed as part of 02-02 but implements this plan's requirements*

**Plan metadata:** *(part of ongoing Phase 2)*

## Files Created/Modified

- `tests/test_read_operations.py` - Test scaffold with 7 test cases and fixtures
- `src/server.py` - Added tools and helper functions:
  - `_format_error()` - Consistent error formatting with context
  - `_format_pr_list()` - Multi-line PR list formatting
  - `_format_pr_detail()` - Single PR detail formatting
  - `bitbucket_list_pull_requests()` - List PRs with optional state filter
  - `bitbucket_get_pull_request()` - Get single PR details by ID

## Decisions Made

1. **State parameter normalization**: Accept lowercase ('open', 'merged', 'declined') from users, convert to API uppercase ('OPEN', 'MERGED', 'DECLINED')
2. **Multi-line PR formatting**: Each PR displayed as labeled fields (Author, State, Branch, etc.) for readability
3. **Safe nested access**: Use `.get()` chains to handle missing data (e.g., deleted branches)
4. **Error format consistency**: All tools use `[tool_name] Failed to X: reason` pattern with helpful suggestions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adjusted commit scope for get_pr tool**
- **Found during:** Task 2
- **Issue:** The get_pr tool was implemented in commit 00f98d5 (labeled as 02-02 feat) but fulfills 02-01 requirements
- **Fix:** Tool was implemented successfully; documentation notes the commit location
- **Files modified:** src/server.py
- **Verification:** All 7 tests from 02-01 plan pass

---

**Total deviations:** 1 auto-fixed (1 blocking scope adjustment)
**Impact on plan:** No functional impact. All requirements fulfilled, all tests pass.

## Issues Encountered

None - all tests pass on first implementation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Read tools are complete and tested
- Error formatting patterns established for reuse
- Ready for 02-02 (diff operations) which builds on these patterns
- Ready for 03-lifecycle which will use list_prs for PR discovery

---
*Phase: 02-read-operations*
*Completed: 2026-03-06*
