# Handoff: Chinese Calendar Engine — Bug Fix Round

**Handoff ID:** HO-20260610-002  
**Date:** 2026-06-10  
**Engine Root:** D:\c_wannianli

---

## Session Context

The previous round of testing (HO-20260610-001) found several issues. One was fixed (1976-12-21 boundary bug). Remaining issues fall into two categories that need code fixes:

1. **1920-11-15 ±1 day:** Boundary condition bug similar to 1976-12-21, but still happening
2. **Leap month判定差异:** Engine disagrees with lunar_python on which month is the leap month in certain years (1993, 1995, 2020, 1922, 2047, 2096). This affects ~1.4% of dates.

---

## What's Already Done (this session)

- [x] Comprehensive test script (`test_comprehensive.py`) — 500 random + Spring Festival + leap years + edge dates
- [x] Analysis of all errors (see `test_results_comprehensive.md` and `debug_test_errors.py`)
- [x] Fixed 1976-12-21 boundary bug (RD exactly at m11_next boundary)
- [x] Root cause identified: leap month determination uses PyMeeus solar longitude, which may disagree with lunar_python's algorithm

---

## Tasks for Claude Code

### Task 1: Fix 1920-11-15 ±1 Day Boundary Bug

- **Priority:** High
- **Files:** `D:\c_wannianli\chinese_calendar\calendar\chinese.py`
- **What to do:**

The date 1920-11-15 gives engine=(1920,10,5) vs lunar_python=(1920,10,6) — off by 1 day. This is the same class of bug as 1976-12-21 (month boundary condition).

1. First, reproduce and debug:
   ```python
   from chinese_calendar.api import Calendar
   from chinese_calendar.core.rata_die import RataDie, Moment
   from chinese_calendar.calendar.converters import gregorian_from_fixed
   from chinese_calendar.calendar import chinese as chn
   from chinese_calendar.astronomy.moon import _estimate_new_moon_jde
   from chinese_calendar.core.time_systems import jd_from_moment, J2000_MOMENT
   import astronomy

   rd_val = 701776  # RD for 1920-11-15
   s1 = chn.winter_solstice_on_or_before(rd_val)
   s2 = chn.winter_solstice_on_or_before(Moment(s1.day + 370.0))
   m11 = chn._new_moon_on_or_before(s1)
   m11_next = chn._new_moon_on_or_before(s2)
   print(f"rd={rd_val}, m11={m11.day}, m11_next={m11_next.day}")
   print(f"int(m11+8/24)={int(m11.day+8/24)}, int(m11_next+8/24)={int(m11_next.day+8/24)}")
   
   # Check with astronomy-engine for precise new moon
   ae_nm = astronomy.SearchMoonPhase(0, astronomy.Time(rd_val - J2000_MOMENT - 730.0), 1500.0)
   print(f"AE new moon: {ae_nm}")
   ```

2. Then identify the fix. Likely causes:
   - The month boundary interval `[start_day, end_day)` excludes `end_day` exactly when the RD equals `end_day` in China timezone
   - Or: the `while True` loop at lines ~297-310 incorrectly advances/doesn't advance to next year

3. Apply the fix and verify:
   ```bash
   python -c "
   from chinese_calendar.api import Calendar
   cal = Calendar.from_solar(1920, 11, 15)
   print(cal.lunar_str)
   "
   ```
   Should say 农历1920年十月初六, not 十月初五.

4. Run edge-case verification after fix:
   ```bash
   python -c "
   from chinese_calendar.api import Calendar
   from lunar_python import Lunar
   from datetime import datetime
   for y,m,d in [(1920,11,14),(1920,11,15),(1920,11,16),(1976,12,20),(1976,12,21),(1976,12,22)]:
       c = Calendar.from_solar(y,m,d)
       l = Lunar.fromDate(datetime(y,m,d,12,0,0))
       same = '✅' if c.lunar and c.lunar.day == l.getDay() else '⚠️'
       print(f'{y}-{m:02d}-{d:02d}: {c.lunar_str}  lp={l.getYear()}.{abs(l.getMonth()):02d}.{l.getDay():02d} {same}')
   "
   ```

- **Acceptance criteria:**
  - [ ] 1920-11-15 matches lunar_python
  - [ ] 1976-12-21 still works (no regression)
  - [ ] All edge dates around month boundaries still pass

---

### Task 2: Fix Leap Month Determination Discrepancies

- **Priority:** High
- **Files:** `D:\c_wannianli\chinese_calendar\calendar\chinese.py` (function `_has_major_solar_term`)

- **What to do:**

The function `_has_major_solar_term()` at line ~152 uses `major_solar_terms_of_year(y)` which calls `solar_term_time()` → `solve_solar_longitude()` → PyMeeus. The solar term moments from PyMeeus may differ from lunar_python's internal calculation, causing disagreement on whether a month contains a major solar term.

**Fix strategy:** Replace the PyMeeus-based solar term check with astronomy-engine's `SearchSunLongitude()` for the six major terms that matter for leap month determination. Only applicable terms: 春分(0°), 谷雨(30°), 小满(60°), 夏至(90°), 大暑(120°), 处暑(150°), 秋分(180°), 霜降(210°), 小雪(240°), 冬至(270°), 大寒(300°), 雨水(330°).

```python
def _has_major_solar_term(start: Moment, end: Moment) -> bool:
    """判断区间 [start, end) 内是否包含中气。
    
    使用 astronomy-engine（VSOP87 精度）计算中气时刻。
    """
    _CHINA_TZ = 8.0 / 24.0
    start_cn = int(start.day + _CHINA_TZ)
    end_cn = int(end.day + _CHINA_TZ)
    
    # 只检查中气（偶数节气索引：5, 7, 9, ..., 1）
    import astronomy
    from ..core.time_systems import J2000_MOMENT
    
    for term_idx in [5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 1, 3]:
        target_lon = (term_idx * 15 + 285) % 360
        # 搜索范围从 start_cn 前几天到 end_cn 后几天
        t_start = astronomy.Time(start_cn - J2000_MOMENT - 5)
        t_limit = end_cn - start_cn + 10
        try:
            result = astronomy.SearchSunLongitude(target_lon, t_start, t_limit)
            if result is not None:
                result_cn = int(result.tt + J2000_MOMENT + _CHINA_TZ)
                if start_cn <= result_cn < end_cn:
                    return True
        except Exception:
            continue
    return False
```

Or, if SearchSunLongitude doesn't work well: compute the target solar term time using the existing `solar_term_time()` + astronomy-engine's `solve_solar_longitude()` (which already uses SearchSunLongitude when available). Check if `solar_term_time()` already uses AE — if so, the fix might be simpler.

**To verify which is correct:**
1. Check if `solar_term_time()` currently uses AE (it should after the previous integration)
2. If not, the fix is to make sure `solve_solar_longitude()` uses AE
3. If yes, then the issue is deeper — AE and lunar_python still disagree on the exact term moment

**After fixing:** Run the full cross-validation again.

- **Acceptance criteria:**
  - [ ] 1993-04-25: engine month matches lunar_python month
  - [ ] 1995-09-27: engine month matches lunar_python month  
  - [ ] 2020-06-05: engine month matches lunar_python month
  - [ ] Leap flag for 1922, 2047, 2096: if month/day match but leap flag differs, that's acceptable
  - [ ] Run comprehensive test: > 99% exact match

---

### Task 3: Re-run Full Test Suite

- **Priority:** Medium
- **Depends on:** Task 1, Task 2
- **What to do:**
  1. Run `python test_comprehensive.py` and confirm improvements
  2. Run `python cross_validate.py` (the original 15-date validation)
  3. Update `test_results_comprehensive.md` with new results

---

## Technical Notes

- **Keys to leap month rule:** A lunar month without a "major solar term" (中气) becomes a leap month. There are 12 major terms. The solar terms are computed from Sun ecliptic longitude.
- **PyMeeus + AE:** `solve_solar_longitude()` already prefers AE when available. Check if this is working.
- **solar_term_time()** calls `solve_solar_longitude()` which calls AE's `SearchSunLongitude()` if available.
- **Debug tools already created:** `debug_test_errors.py`, `debug_root_cause.py`, `debug_test_summary.py` — use these to verify fixes.

### cnlunar Reference (for future module work)

`pip install cnlunar` — Chinese calendar lib using Hong Kong Observatory data. Useful APIs:
- `a.get_the9FlyStar()` — 九宫飞星 (c_xuankong)
- `a.get_today12DayOfficer()` — 建除十二神 (c_zheri)
- `a.get_the28Stars()` — 二十八星宿 (culture)
- `a.get_twohourLuckyList()` — 时辰凶吉 (c_zheri)
- `a.get_luckyGodsDirection()` — 神煞方位 (culture)

---

## Status Tracking

| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| 1 | Fix 1920-11-15 boundary bug | ✅ Complete | Fixed: _MOON_BOUNDARY_EPSILON for midnight new moons |
| 2 | Fix leap month determination | ✅ Complete | Fixed: _has_major_solar_term now uses UTC+8 (China time) comparison |
| 3 | Re-run full test suite | 🟡 Partial | T1+T2 verified on all known edge + leap cases; full run pending |

---

## How to Proceed

Tell Claude Code: **"Read HANDOFF.md at D:\c_metaphysics\ and work through the tasks. The old handoff from HO-20260610-001 is stale — use this one (HO-20260610-002)."**
