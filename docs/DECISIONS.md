# Decision Log — Chinese Calendar Engine (万年历引擎)

> This log records key architectural and implementation decisions with their rationale.
> Each entry should include: Context → Decision → Rationale → Consequences.
>
> Keep entries at the top (reverse chronological). Limit the log to ~20 entries;
> older entries move to `docs/archive/` when needed.

---

## 2026-05-15: `ganzhi.py` — CR T Formula for Sexagenary Index

**Context:** Needed a way to convert (stem, branch) pairs to a unique sexagenary index (0-59) for the sixty-cycle table lookup, and vice versa.

**Decision:** Use the Chinese Remainder Theorem formula `(6*stem - 5*branch) % 60` rather than a hardcoded lookup table.

**Rationale:** The CRT formula is mathematically rigorous (solves `index % 10 = stem` and `index % 12 = branch` simultaneously), works for all 60 combinations without exception, and requires zero storage. A lookup table would be 60 entries that duplicate what arithmetic provides.

**Consequences:** The reverse direction uses `stem = index % 10, branch = index % 12`, a simple O(1) decomposition. Verified all 60 indices round-trip correctly in tests.

---

## 2026-05-15: `ganzhi.py` — Nayin Table (60-Entry Hardcode)

**Context:** Nayin (纳音五行) is a traditional assignment of the five elements to each sexagenary pair. It cannot be derived algorithmically — it is a pre-computed cultural table.

**Decision:** Hardcode all 60 entries as a tuple `NAYIN = ("海中金", "海中金", "炉中火", ...)`.

**Rationale:** Nayin is arbitrary cultural knowledge, not a derivable function. A 60-entry hardcoded tuple is the simplest correct representation. Any formula attempting to "compute" nayin would introduce errors.

**Consequences:** Module-level constant, O(1) lookup by sexagenary index, zero maintenance. Verified first and last entries match standard values in tests.

---

## 2026-05-15: `ganzhi.py` — Lichun Boundary for Year Stem/Branch

**Context:** Traditional Ba Zi assigns the year pillar (年柱) based on the solar year, not the lunar year. The boundary is Lichun (立春, solar longitude 315°), which falls around Feb 3-5. There was a choice between using a fixed-date heuristic (approx Feb 4) or computing the exact astronomical Lichun moment.

**Decision:** Use the actual computed Lichun moment via `solve_solar_longitude(315.0)` for the canonical `year_ganzhi(rd, lichun_moment)` function, while also providing a simplified `year_ganzhi_by_year(year)` for cases where only the year-based formula is needed.

**Rationale:** Accuracy matters for boundary cases: someone born on Feb 3, 2026 might still be in the previous zodiac year (乙巳/蛇) if Lichun hasn't occurred yet. A fixed-date heuristic (±1 day) would produce errors near the boundary.

**Consequences:** `year_ganzhi(rd, lichun_moment)` requires PyMeeus for the astronomical computation. The simplified `year_ganzhi_by_year(year)` uses the pure formula `(year+6)%10, (year+8)%12` for non-boundary cases. Tests cover three scenarios: before Lichun, on Lichun, after Lichun.

---

## 2026-05-15: `ganzhi.py` — Four Pillars Design (Separate Functions vs. Single API)

**Context:** Need to represent the four pillars (年柱/月柱/日柱/时柱) of Ba Zi calculation. Each pillar has different dependencies and boundary conditions.

**Decision:** Implement each pillar as an independent function (`day_ganzhi`, `year_ganzhi`, `month_ganzhi`, `hour_ganzhi`), with a composite `full_bazi()` function that assembles them together.

**Rationale:** The four pillars are independent sub-problems with different algorithms:
- 日柱: Pure 60-day cycle, no astronomical input needed
- 年柱: Requires Lichun boundary (astronomy)
- 月柱: Requires 12 major solar terms (astronomy)
- 时柱: Pure formula based on day stem + local time

Separate functions allow testing each pillar independently and using only the pillars needed.

**Consequences:** `full_bazi()` takes `lichun_moment` as a parameter (must be computed by the caller). The function returns a structured dict with stem/branch/nayin for each pillar.

---

## 2026-05-15: Sprint 5-6 — Dead Code Cleanup in `ganzhi.py`

**Context:** During Sprint 6 development, an incomplete `NAYIN_TABLE` placeholder was discovered alongside the completed `NAYIN` constant. This was leftover from an earlier failed approach.

**Decision:** Remove `NAYIN_TABLE` placeholder entirely; fix 3 `HIDDEN_STEMS` index errors (丑/午/未 had off-by-one index values).

**Rationale:** Dead code creates confusion for future maintainers. The index errors (where `己=4` instead of `己=5`) would cause wrong Ba Zi calculations.

**Consequences:** All 4 fixed entries verified against standard references (《渊海子平》). Index corrections tested explicitly.

---

## 2026-05-14: Sprint 5 — Circular Import Resolution (time_systems ↔ converters ↔ chinese)

**Context:** `core/time_systems.py` imports from `calendar/converters.py` for `moment_from_datetime` and `fixed_from_gregorian`. `calendar/converters.py` imports from `core/rata_die.py`. `calendar/chinese.py` needs both `astronomy/sun.py` and `core/time_systems.py`. This creates an import cycle: time_systems → converters → (implicitly) chinese → time_systems.

**Decision:** Use lazy imports inside the calling function. In `chinese.py`, a `_time_systems()` function performs the import at call time rather than module load time.

**Rationale:** Lazy import is the simplest fix that doesn't require restructuring the module hierarchy. The alternative — refactoring `time_systems.py` to not depend on `converters.py` — would be a larger change with no behavioral benefit.

**Consequences:** Import pattern in `chinese.py` is slightly non-standard but well-documented. `calendar/__init__.py` does not export `chinese` module to avoid triggering the cycle at package init; users must `from chinese_calendar.calendar.chinese import ...` directly.

---

## 2026-05-14: Sprint 5 — Chinese Year Determination Logic

**Context:** Given a lunar date, we need to determine which "Chinese year" it belongs to. The Chinese year (e.g., 2026年) starts at 正月初一, not Jan 1, and the month structure is determined by the winter solstice of the previous Gregorian year.

**Decision:** First find the 正月 index in the month structure, then determine if the target month falls before or after it. Months before 正月 belong to the previous Chinese year; months 正月 and after belong to the current Chinese year. If no 正月 is found (defensive), fall back to the Gregorian year.

**Rationale:** This correctly handles the case where months 十一月 and 十二月 of a Chinese year (e.g., 2026年) occur in the Gregorian year 2025, while 正月 through 十月 occur in Gregorian year 2026.

**Consequences:** Years with 11/2025 dates correctly return 2026 as the Chinese year. Edge case where a year might not have 正月 is theoretically impossible but handled defensively.

---

## 2026-05-14: Sprint 5 — "November Determining the Leap" vs. Full-Year Scan

**Context:** The D&R Chinese calendar algorithm determines leap months by checking which lunar month lacks a major solar term within the winter-solstice-defined "sui" (岁).

**Decision:** Use the full "岁内月份收集" approach: collect all months between two consecutive winter solstices, then check each for the presence of a major solar term. A month missing one is designated the leap month.

**Rationale:** This is the canonical D&R algorithm. It handles all historical and future leap month placements correctly, unlike heuristic approaches that try to predict leap months based on fixed rules.

**Consequences:** Algorithm is correct but requires PyMeeus for the astronomical computations (solar terms and new moons). All 14 astronomical tests skip without PyMeeus.

---

## 2026-05-14: Sprint 4 — Newton-Raphson for New Moon Solving

**Context:** Need to find the exact moment of conjunction (Moon longitude = Sun longitude) for new moon calculation.

**Decision:** Use a Newton-Raphson solver (identical structure to Sprint 2's `solve_solar_longitude`) with the Meeus mean new moon formula providing the initial guess (~15 minute accuracy). The solver uses numerical differentiation for the rate of change of the Sun-Moon longitude difference (~12.19°/day).

**Rationale:** Newton's method converges in 2-3 iterations to < 0.1 second accuracy given the high-quality initial guess from Meeus Ch.47. The Meeus formula alone (±15 min) is insufficient for lunar calendar purposes where a 15-minute error at midnight could change the date.

**Consequences:** Fast convergence. Tested with 6 consecutive new moons, all converging with Sun-Moon longitude difference < 0.005°. Cross-year continuity verified.

---

## 2026-05-14: Sprint 4 — `new_moon_after`/`new_moon_before` API Design

**Context:** Needed a clean API for querying new moons relative to a given date — forward (after) and backward (before).

**Decision:** Implement two separate functions: `new_moon_after(moment)` returns the first new moon strictly after the given moment; `new_moon_before(moment)` returns the last new moon strictly before the given moment.

**Rationale:** The "strict" semantics (not >= or <=) avoid ambiguity at exact new moon boundaries. The round-trip property `new_moon_before(new_moon_after(X)) ≈ X` serves as a correctness invariant.

**Consequences:** Round-trip error tested at < 2 seconds, which is far below any practical threshold for calendar purposes. These functions are the backbone of Sprint 5's lunar month structure algorithm.

---

## 2026-05-14: Sprint 3 — 24 Solar Terms from Single Newton Solver

**Context:** Need to compute all 24 solar terms for a given year. Each term corresponds to a specific solar longitude (285°, 300°, 315°, ..., 270°).

**Decision:** Build a lookup table of approximate dates (`SOLAR_TERM_APPROX`) for initial guesses, then use Sprint 2's `solve_solar_longitude()` Newton solver for each of the 24 terms. Apply UTC→TT→UTC conversion for each.

**Rationale:** The Newton solver from Sprint 2 already handles the core "find time from longitude" problem. Reusing it for 24 calls is efficient (each solves independently) and guarantees consistent accuracy. The approximate date table (±2 days) ensures the Newton initial guess is always in the basin of convergence.

**Consequences:** All 24 terms computed independently with < 60s accuracy. The term order is deterministic (小寒→冬至). The 12 major solar terms (中气) are a simple subsequence extraction, used later for lunar leap month determination.

---

## 2026-05-14: Sprint 2 — PyMeeus Wrapping vs. Direct VSOP87 Implementation

**Context:** Need accurate solar position for solar term calculation. Two approaches: implement VSOP87 directly (thousands of terms, complex) or wrap the PyMeeus library.

**Decision:** Wrap PyMeeus as the primary solar engine, while implementing standalone nutation/precession/aberration corrections in `corrections.py` as a reference for future replacement.

**Rationale:** VSOP87 is ~3000 trigonometric terms across 6 series. A correct implementation is a significant project in itself. PyMeeus is a well-tested, maintained library that handles this correctly. The standalone corrections module preserves the option to swap out PyMeeus later without losing the correction logic.

**Consequences:** Runtime dependency on PyMeeus for astronomical calculations. All astronomy tests skip gracefully when PyMeeus is absent. The corrections module is not used by the production path but exists as a reference implementation.

---

## 2026-05-14: Sprint 2 — Time System Design (UTC ↔ TT Bridge)

**Context:** VSOP87 (and all ephemeris calculations) operate in Terrestrial Time (TT), while user-facing dates are in UTC. The difference (ΔT) varies historically and is predicted differently for past vs. future dates.

**Decision:** Implement a dedicated `time_systems.py` module with explicit UTC→TT→UTC round-trip conversion, using a polynomial ΔT approximation covering 1620-2100.

**Rationale:** Keeping the conversion in a single, well-tested module prevents conversion errors from being scattered across the codebase. The polynomial approximation (± a few seconds vs. historical ΔT) is sufficient for calendar purposes where sub-minute accuracy is acceptable.

**Consequences:** All astronomical functions accept/re-turn UTC `Moment` values but convert internally to TT for computation. The J2000.0 epoch (JD 2451545.0 = Moment 730120.5) serves as the fundamental reference point.

---

## 2026-05-14: Sprint 1 — Rata Die as Universal Bridge (Not JD)

**Context:** Every calendar conversion system needs a universal intermediate representation. Options: Julian Day Number (JD), Modified JD, or Rata Die (R.D.).

**Decision:** Use Rata Die (R.D.) as defined by Dershowitz & Reingold: R.D. 1 = January 1, 1 CE (Gregorian proleptic) = Monday. JD is used only within the astronomy layer.

**Rationale:** R.D. has integer day semantics (dates are whole numbers), starts from a meaningful epoch (Gregorian year 1), and aligns naturally with calendar dates. JD is a floating-point number starting from 4713 BCE, more natural for astronomical calculations but awkward for dates. The R.D. approach keeps the calendar layer in integer space and the astronomy layer in JD space, with `time_systems.py` bridging the two.

**Consequences:** All calendar ↔ calendar conversions pass through R.D. (never direct calendar-to-calendar). This is a strict architectural invariant. The `Moment` class handles fractional-day precision for astronomical times while `RataDie` handles integer-date calendrical operations.

---

## 2026-05-14: Sprint 1 — RataDie and Moment as Frozen Dataclasses

**Context:** Need a type-safe representation for R.D. dates (integer) and astronomical moments (floating-point with sub-day precision).

**Decision:** Implement `RataDie` as an `int`-based frozen dataclass (supports `+`, `-`, comparison, hash) and `Moment` as a `float`-based frozen dataclass with `rata_die()` truncation and `standard_time()` fractional-day methods.

**Rationale:** Frozen dataclasses provide immutability (critical for a numerical foundation — no accidental mutation), sensible defaults for comparison and hashing, and clean repr/str output. The `int` vs. `float` distinction enforces the architecture: dates are integer R.D., times are float Moment.

**Consequences:** Clean duality between integer-date operations (calendar layer) and floating-point time operations (astronomy layer). The `from_rata_die()` constructor provides a clean boundary between the two.

---

## 2026-05-14: Sprint 1 — Four-Layer Architecture

**Context:** The calendar engine needs to separate concerns between numerical foundation, astronomical computation, calendar algorithms, and user-facing API.

**Decision:** Organize into four layers:
1. **core** — RataDie/Moment, time systems, constants (zero-dependency foundation)
2. **astronomy** — sun, moon, solar terms, corrections (depends on core, optionally on PyMeeus)
3. **calendar** — converters, chinese, ganzhi (depends on core + astronomy)
4. **api / locale / data** — public API, internationalization, caching (planned for Sprint 7-8)

**Rationale:** Strict layering prevents circular dependencies at the architectural level (the core→astronomy→calendar→api flow is unidirectional). Each layer can be developed, tested, and replaced independently. The R.D. type in the core layer is the only type that crosses layer boundaries.

**Consequences:** The circular dependency between `time_systems` and `converters` was discovered later (see above entry). Testing at each layer is independent: core tests need no astronomy, astronomy tests need no calendar logic.
