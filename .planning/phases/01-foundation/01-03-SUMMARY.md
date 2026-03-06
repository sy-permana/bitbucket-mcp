---
phase: 01-foundation
plan: 03
subsystem: mcp-server
tags: [mcp, fastmcp, logging, stderr, stdio, initialization]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "BitbucketConfig from 01-01 and BitbucketClient from 01-02"
provides:
  - FastMCP server entry point with validated config and authenticated client
  - stderr-only logging configured before all other imports
  - Graceful exit with clear error message on config validation failure
  - pytest fixtures for shared test resources
  - Project dependencies and test configuration in pyproject.toml
affects:
  - Phase 2 (Read Operations - server provides mcp instance for tools)
  - Phase 3 (PR Lifecycle - server provides client for write operations)
  - Phase 4 (Commenting - server provides foundation for all tools)

# Tech tracking
tech-stack:
  added: [mcp, fastmcp]
  patterns:
    - stderr-only logging for stdio protocol safety
    - Config validation on module import (fail fast)
    - FastMCP initialization with descriptive name
    - pytest fixtures for dependency injection in tests

key-files:
  created:
    - src/server.py - FastMCP server with stderr logging and config validation
    - tests/conftest.py - Shared pytest fixtures
    - tests/test_server.py - 6 unit tests for server initialization
    - pyproject.toml - Project dependencies and pytest configuration
  modified:
    - pyproject.toml - Added pytest options including -p no:logging for stdio tests

key-decisions:
  - "Logging MUST be configured BEFORE importing other modules to capture all logs to stderr"
  - "pytest -p no:logging flag required to prevent pytest from interfering with stdio logging tests"
  - "Server uses module-level execution for config validation - fails fast on import"
  - "FastMCP instance exported as 'mcp' for tool registration in subsequent phases"

patterns-established:
  - "stderr-only logging: All logging output goes to stderr, never stdout (critical for MCP stdio protocol)"
  - "Fail-fast initialization: Config validation happens at import time, exits with code 1 on failure"
  - "Test fixtures: mock_env_vars, bitbucket_config, bitbucket_client, mock_missing_env for reusable test setup"
  - "pytest configuration: -p no:logging flag to prevent pytest logging capture from interfering with stdio tests"

requirements-completed:
  - CONFIG-04
  - ERROR-03

# Metrics
duration: 8min
completed: 2026-03-06
---

# Phase 1 Plan 03: MCP Server Initialization Summary

**FastMCP server entry point with stderr-only logging, validated configuration on import, and graceful error handling - 6 unit tests covering initialization and stdio protocol safety**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-06T22:50:00Z
- **Completed:** 2026-03-06T22:58:00Z
- **Tasks:** 3 (1 TDD task with RED-GREEN-REFACTOR cycle)
- **Files created:** 4

## Accomplishments

- Created `src/server.py` with FastMCP initialization and stderr-only logging
- Implemented config validation on module import with graceful exit (sys.exit 1) on failure
- Initialized BitbucketClient with validated config, exported as `bitbucket_client`
- Exported FastMCP instance as `mcp` with name "bitbucket-pr-manager" for tool registration
- Created `tests/conftest.py` with 4 shared fixtures for test dependency injection
- Wrote 6 comprehensive unit tests covering logging, initialization, and error handling
- Created `pyproject.toml` with mcp[cli], requests, pydantic dependencies and pytest config
- Added `-p no:logging` pytest flag to prevent logging capture from breaking stdio tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Create pyproject.toml** - `68ad1df` (chore)
2. **Task 2: Create shared pytest fixtures** - `8452c93` (test)
3. **Task 3 RED: Add failing tests** - `1619507` (test)
4. **Task 3 GREEN: Implement MCP server** - `603608d` (feat)

**Plan metadata:** To be committed

## Files Created

- `src/server.py` - MCP server with:
  - stderr-only logging configured BEFORE any other imports (critical!)
  - Config validation on import with clear error messages
  - FastMCP("bitbucket-pr-manager") instance exported as `mcp`
  - BitbucketClient initialized with validated config
  - `if __name__ == "__main__"` block for running with stdio transport
- `tests/conftest.py` - Shared pytest fixtures:
  - `mock_env_vars`: Sets all 4 required env vars
  - `bitbucket_config`: BitbucketConfig instance with mocked env
  - `bitbucket_client`: BitbucketClient with test config
  - `mock_missing_env`: Unsets all env vars for error testing
- `tests/test_server.py` - 6 unit tests in 4 test classes:
  - TestLoggingConfiguration: stderr logging verification
  - TestServerInitialization: FastMCP instance, config loading
  - TestServerErrorHandling: Graceful exit on missing config
  - TestClientInitialization: BitbucketClient creation
- `pyproject.toml` - Project configuration:
  - Dependencies: mcp[cli]>=1.26.0, requests>=2.32.5, pydantic>=2.12.5
  - Dev dependencies: pytest, pytest-responses, responses
  - pytest.ini_options with `-p no:logging` flag

## Decisions Made

1. **stderr-only logging timing**: Logging MUST be configured with `logging.basicConfig()` before importing any other modules. This ensures logs from config and client modules also go to stderr, preventing stdio protocol corruption.

2. **pytest -p no:logging flag**: Required to prevent pytest's logging capture from modifying the root logger handlers. Without this flag, the stderr logging tests fail because pytest replaces the handlers.

3. **Module-level initialization**: Config validation happens at import time, not in a function. This provides fail-fast behavior - if config is invalid, the server exits immediately with a clear error message.

4. **Export naming convention**: FastMCP instance exported as `mcp` (lowercase) following FastMCP documentation patterns. Client exported as `bitbucket_client` for clarity.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

1. **pytest logging interference**: Initial stderr logging test failed because pytest's logging capture plugin modifies root logger handlers. Fixed by adding `-p no:logging` to pytest.ini_options.

2. **PYTHONPATH required**: Tests require PYTHONPATH to include project root for src.* imports. Conftest fixtures handle this in test context, but manual verification requires setting PYTHONPATH.

## User Setup Required

None - no external service configuration required. Environment variables will be needed when running the actual server, documented in `.env.example` from Plan 01-01.

## Verification Results

```bash
# CONFIG-04: FastMCP initialized
$ pytest tests/test_server.py::TestServerInitialization::test_mcp_instance_created -x
============================== 1 passed in 0.34s

# ERROR-03: stderr logging
$ pytest tests/test_server.py::TestLoggingConfiguration::test_logging_to_stderr -x
============================== 1 passed in 0.27s

# All tests (27 total across all modules)
$ pytest tests/ -x
============================== 27 passed in 0.99s

# Integration check - server imports with valid config
$ BITBUCKET_USERNAME=test BITBUCKET_API_TOKEN=test BITBUCKET_WORKSPACE=test \
  BITBUCKET_REPO_SLUG=test python -c "from src.server import mcp; print('OK')"
2026-03-06 22:58:38 - src.server - INFO - Configuration loaded for workspace: test
Server import OK

# Config failure check - exits with error
$ (unset BITBUCKET_USERNAME BITBUCKET_API_TOKEN BITBUCKET_WORKSPACE BITBUCKET_REPO_SLUG; \
  python -c "from src.server import mcp" 2>&1) | grep "Configuration error"
2026-03-06 22:58:56 - src.server - ERROR - Configuration error: Missing required...
Exit code: 1
```

## Next Phase Readiness

- MCP server foundation complete with validated config and authenticated client
- FastMCP instance ready for tool registration
- stderr-only logging ensures stdio protocol safety
- Ready for Phase 2: Read Operations (list PRs, get PR details, get diff)

---
*Phase: 01-foundation*
*Completed: 2026-03-06*
