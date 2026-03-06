---
phase: 02
slug: read-operations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/test_read_operations.py -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_read_operations.py -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | READ-01 | unit | `pytest tests/test_read_operations.py::test_list_prs -v` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | READ-02 | unit | `pytest tests/test_read_operations.py::test_get_pr -v` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | READ-03 | unit | `pytest tests/test_read_operations.py::test_get_diff -v` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | READ-04 | unit | `pytest tests/test_read_operations.py::test_get_commit_status -v` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | ERROR-01 | unit | `pytest tests/test_read_operations.py::test_error_format -v` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | ERROR-02 | unit | `pytest tests/test_read_operations.py::test_error_context -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_read_operations.py` — stubs for READ-01 through READ-04, ERROR-01, ERROR-02
- [ ] `tests/conftest.py` — shared fixtures (Bitbucket client mock, sample PR data)
- [ ] `pytest-responses` — already installed per pyproject.toml

Wave 0 creates the test scaffold that all read operation tasks depend on.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | All behaviors have automated verification via mocked API responses |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
