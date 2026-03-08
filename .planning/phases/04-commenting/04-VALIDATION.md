---
phase: 4
slug: commenting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ with responses |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_commenting.py -x -v` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_commenting.py -x`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | COMMENT-01, COMMENT-02 | unit | `pytest tests/test_commenting.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | COMMENT-01 | unit | `pytest tests/test_commenting.py::TestGeneralComment -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | COMMENT-02 | unit | `pytest tests/test_commenting.py::TestInlineComment -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_commenting.py` — test stubs for COMMENT-01, COMMENT-02
- [ ] Mock diff responses in test fixtures
- [ ] Mock comment POST responses in test fixtures

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
