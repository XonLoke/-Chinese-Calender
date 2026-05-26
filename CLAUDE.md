# CLAUDE.md — Chinese Calendar Engine (万年历引擎)

## Project Identity

- **Name:** chinese-calendar
- **Description:** Accurate, verifiable, bilingual (Chinese/English) Python Chinese calendar calculation engine
- **Algorithms:** Dershowitz & Reingold《Calendrical Calculations》, Meeus《Astronomical Algorithms》
- **Version:** 0.6.0 (Sprint 6 completed), targeting 1.0.0
- **Python:** >=3.10, zero runtime dependencies (PyMeeus optional for astronomy)
- **Status:** Pre-Alpha — core algorithms implemented, API/locale/packaging pending

---

## Source-of-Truth Files

| File | Purpose | Always Load? |
|------|---------|-------------|
| `CLAUDE.md` (this file) | Project guide and context rules | **Yes** (default) |
| `SPRINT_REPORT.md` | Full sprint-by-sprint development history with test results | **Yes** (default, ~540 lines) |
| `pyproject.toml` | Package metadata, dependencies, pytest config | **Yes** (default) |
| `chinese_calendar/_version.py` | Version number | **Yes** (default) |
| `万年历引擎_技术报告_v1.0.md` | Architecture overview, layer diagram, design rationale | **On demand** (~200+ lines, detailed) |
| `docs/DECISIONS.md` | Decision log with rationale for every architectural choice | **Yes** (default, ~current) |

### Module-level source-of-truth (load only when working in that module)

| Module | Primary File | Purpose |
|--------|-------------|---------|
| core | `core/rata_die.py` | RataDie/Moment types — numerical foundation of the entire engine |
| core | `core/time_systems.py` | JD/TT/UTC/ΔT conversions |
| core | `core/constants.py` | Astronomical constants |
| astronomy | `astronomy/sun.py` | VSOP87 solar longitude via PyMeeus |
| astronomy | `astronomy/moon.py` | New moon / conjunction calculation |
| astronomy | `astronomy/solar_terms.py` | 24 solar terms calculation |
| astronomy | `astronomy/corrections.py` | Nutation, precession, aberration corrections |
| calendar | `calendar/converters.py` | Gregorian/Julian/ISO ↔ R.D. conversion |
| calendar | `calendar/chinese.py` | Chinese lunisolar calendar core algorithm |
| calendar | `calendar/ganzhi.py` | Sexagenary cycle / Four Pillars system |
| tests | `tests/*.py` | All test files |

---

## Architecture (4-Layer Stack)

```
api/locale/data  (Sprint 7-8 — not yet built)
      ↑
calendar layer   (converters, chinese, ganzhi)
      ↑
astronomy layer  (sun, moon, solar_terms, corrections)
      ↑
core layer       (rata_die, time_systems, constants)
```

**Key architectural invariant:** Rata Die (R.D.) is the universal bridge. Every calendar system converts to/from R.D., never directly to each other. This prevents cross-module coupling.

---

## Module Dependency Graph

```
core/rata_die.py              ← zero dependencies
core/constants.py             ← zero dependencies
core/time_systems.py          ← core/rata_die.py, calendar/converters.py (circular — uses lazy import)
  │
astronomy/sun.py              ← core/time_systems, core/rata_die
astronomy/corrections.py      ← core/time_systems
astronomy/solar_terms.py      ← astronomy/sun, core/time_systems, core/rata_die
astronomy/moon.py             ← core/time_systems, core/rata_die
  │
calendar/converters.py        ← core/rata_die, core/constants
calendar/chinese.py           ← astronomy/sun, astronomy/moon, astronomy/solar_terms,
│                                  calendar/converters, core/rata_die, core/time_systems (lazy)
calendar/ganzhi.py            ← core/rata_die, calendar/converters, astronomy/sun
```

**Known circular dependency:** `core/time_systems` ↔ `calendar/converters` ↔ `calendar/chinese`. Handled via lazy import (`_time_systems()` function in `chinese.py`). See DECISIONS.md for rationale.

---

## Coding Conventions

### Style
- Type hints on every function signature (`from __future__ import annotations`)
- Google-style docstrings with Args/Returns/Raises sections
- Module-level header comments explaining purpose, algorithm reference, and dependencies
- Error messages are descriptive, mentioning module context and values

### Error Handling
- Every public function documents its Raises
- Internal helper functions (`_prefixed`) may raise for invalid inputs
- PyMeeus-dependent code uses `try/except ImportError` at function level (not module level)
- `RuntimeError` for unexpected states (should-not-reach-here)

### Testing Patterns
- Every module has a corresponding test file in `tests/`
- Tests that require PyMeeus use `@pytest.mark.skipif` with a `pymeeus` marker
- Pure logic tests (no astronomy) must not require PyMeeus
- Round-trip tests (`rd → lunar → rd`) for every conversion function
- Edge case coverage: year boundaries, leap month boundaries, cross-century

### Naming
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private functions: `_prefixed`
- Files match module name (one logical module per file)

---

## Build / Run / Test Commands

```bash
# Install dev dependencies (PyMeeus + pytest)
pip install -e ".[dev]"    # from project root
# OR
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=chinese_calendar

# Run specific test file
pytest chinese_calendar/tests/test_rata_die.py

# Run specific test class
pytest chinese_calendar/tests/test_chinese.py::TestMonthNumbering

# Run without PyMeeus tests
pytest -m "not pymeeus"
```

---

## Context Budget Rules

### Always Load (default)
1. `CLAUDE.md` — this file
2. `SPRINT_REPORT.md` — sprint history and current status
3. `docs/DECISIONS.md` — architectural decision log
4. `pyproject.toml` — project metadata and config

### Load on Demand (only when the task references them)
1. `万年历引擎_技术报告_v1.0.md` — full architecture reference (~200+ lines)
2. Any `chinese_calendar/core/*.py` or `chinese_calendar/astronomy/*.py` source file — read when implementing or debugging that subsystem
3. `docs/archive/*` — historical context, not for routine work
4. HKO data (`.db` file) — only for validation tasks

### Never Load Automatically
1. `__pycache__/*` — compiled bytecode
2. `.pytest_cache/*` — test cache
3. `.gitkeep` — placeholder files

---

## Current Development Status

### Completed (Sprints 1-6)
- Sprint 1 — RataDie + Gregorian/Julian/ISO ↔ R.D. conversion
- Sprint 2 — VSOP87 solar engine via PyMeeus + time systems (JD/TT/UTC/ΔT)
- Sprint 3 — 24 solar terms calculation
- Sprint 4 — New moon / conjunction calculation
- Sprint 5 — Chinese lunisolar calendar core (D&R Ch.4)
- Sprint 6 — Full sexagenary cycle / Four Pillars (ganzhi, nayin, shengxiao, hidden stems)

### Next (Sprint 7-8)
- Sprint 7 — Caching layer + data optimization
- Sprint 8 — Bilingual locale system + public API + packaging

### Known Issues
- 14 astronomical tests skip without PyMeeus installed (winter solstice, leap month, round-trip)
- `calendar/__init__.py` does not export `chinese` module (circular dependency)
- HKO full lunar verification (1901-2100, ~25,000 entries) pending `.db` import
