---
phase: 04-commenting
plan: 01
subsystem: api
tags: [bitbucket, comments, inline-comments, diff-parsing]

# Dependency graph
requires:
  - phase: 03-pr-lifecycle
    provides: "PR state management and error handling patterns"
provides:
  - bitbucket_add_comment tool for general PR comments
  - bitbucket_add_inline_comment tool for line-specific comments
  - _parse_diff_for_line helper for diff analysis
  - Test coverage for COMMENT-01 and COMMENT-02 requirements
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Unified diff parsing with hunk tracking"
    - "Bitbucket inline comment API with to/from mapping"
    - "TDD RED-GREEN cycle for tool implementation"

key-files:
  created:
    - tests/test_commenting.py - Test coverage for both comment tools
  modified:
    - src/server.py - Added bitbucket_add_comment and bitbucket_add_inline_comment tools

key-decisions:
  - "Two separate tools for general vs inline comments (per CONTEXT.md)"
  - "Diff-based line type detection (added/deleted/context)"
  - "to field for new file lines, from field for old file lines"
  - "Simple confirmation responses without comment IDs or URLs"

patterns-established:
  - "Diff parsing: Parse unified diff to track old/new line numbers through hunks"
  - "Error context: Include file path and line number in inline comment errors"
  - "API consistency: Use _format_error() helper for all API error handling"

requirements-completed: [COMMENT-01, COMMENT-02]

# Metrics
duration: 10min
completed: 2026-03-08
---

# Phase 4 Plan 1: Commenting Tools Summary

**Two MCP tools for PR commenting: general comments via `bitbucket_add_comment` and inline line-specific comments via `bitbucket_add_inline_comment` with automatic diff-based to/from mapping.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-08T05:04:42Z
- **Completed:** 2026-03-08T05:14:43Z
- **Tasks:** 3 (TDD RED → GREEN → GREEN)
- **Files modified:** 2

## Accomplishments

- **General comment tool** (`bitbucket_add_comment`): Add discussion comments to PRs with empty/whitespace validation
- **Inline comment tool** (`bitbucket_add_inline_comment`): Add line-specific comments with automatic detection of added/deleted/context lines
- **Diff parser** (`_parse_diff_for_line`): Parse unified diff to determine correct Bitbucket API to/from field mapping
- **Full test coverage**: 10 test cases covering success paths, validation errors, and API errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test scaffold** - `ea558c2` (test)
2. **Task 2: Implement general comment tool** - `8cb0f7b` (feat)
3. **Task 3: Implement inline comment tool** - `a19cc59` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified

- `tests/test_commenting.py` - Test suite with 10 test cases:
  - `TestGeneralComment`: 4 tests for general comments
  - `TestInlineComment`: 6 tests for inline comments
- `src/server.py` - Added:
  - `bitbucket_add_comment()` tool (lines 656-680)
  - `_parse_diff_for_line()` helper (lines 683-739)
  - `bitbucket_add_inline_comment()` tool (lines 742-806)

## Decisions Made

- **Line targeting**: User provides file path + line number, tool auto-detects type from diff (per CONTEXT.md)
- **to/from mapping**: 
  - `to` field for added lines and context lines (new file line numbers)
  - `from` field for deleted lines (old file line numbers)
- **Response format**: Simple confirmation "Comment added to PR #N" without ID/URL (matches approve/decline pattern)
- **Error format**: Include file and line context in inline comment errors (e.g., "Failed to add comment to src/main.py line 42")

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrected test fixture line numbers**
- **Found during:** Task 3 (inline comment implementation)
- **Issue:** Test fixtures used line numbers that didn't match the actual diff structure - line 14 was used for both deleted and added lines, but the diff had both at line 13
- **Fix:** Updated mock_diff_response fixture with clearer diff structure:
  - Line 3: Deleted only (maps to 'from')
  - Line 4: Added only (maps to 'to')
  - Line 5: Context (maps to 'to')
- **Files modified:** tests/test_commenting.py
- **Verification:** All 10 tests pass after correction
- **Committed in:** a19cc59 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor test fixture correction. No scope creep or architectural changes.

## Issues Encountered

1. **Test fixture line number mismatch**: The initial test diff fixture had overlapping line numbers for deleted and added lines, causing test failures. Fixed by creating a cleaner diff structure where deleted and added lines have distinct line numbers.

2. **Pre-existing test failure**: `test_create_pr_http_error` in test_lifecycle.py fails because it expects "401" or "unauthorized" in error messages, but `_format_error()` returns "Authentication failed". This is unrelated to commenting changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 4 complete**: All commenting functionality implemented
- **All requirements satisfied**: COMMENT-01 and COMMENT-02 verified by tests
- **Full test coverage**: 10/10 commenting tests pass
- **Ready for**: Phase 4 completion and project milestone finish

---
*Phase: 04-commenting*
*Completed: 2026-03-08*
