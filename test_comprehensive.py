#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task 1: Comprehensive Lunar Cross-Validation
============================================
Compares the Calendar engine vs lunar_python (6tail) across:
  1. 500+ random dates 1900-2100
  2. All Spring Festival (正月初一) dates 1900-2100
  3. Known leap years (2023, 2025, 2028, 2033, 2042)
  4. Edge dates (Dec 31, Jan 1, Feb 29, 1582 transition)
"""

import sys, os, random, datetime, json

sys.path.insert(0, r"D:\c_wannianli")
from chinese_calendar.api import Calendar
from lunar_python import Lunar

random.seed(20260610)

results = {
    "random": {"total": 0, "exact": 0, "diff1": 0, "diff2plus": 0, "errors": []},
    "spring_festival": {"total": 0, "exact": 0, "diff": 0, "errors": []},
    "leap_years": {"total": 0, "exact": 0, "diff": 0, "details": []},
    "edge": {"total": 0, "exact": 0, "diff": 0, "errors": []},
}

# ========== 1. Random Date Generation ==========
print("=" * 60)
print("1. Random date cross-validation (500+ dates 1900-2100)")
print("=" * 60)

all_dates = set()
while len(all_dates) < 520:
    y = random.randint(1900, 2100)
    m = random.randint(1, 12)
    max_d = [31, 29 if (y%4==0 and (y%100!=0 or y%400==0)) else 28, 31,30,31,30,31,31,30,31,30,31][m-1]
    d = random.randint(1, max_d)
    all_dates.add((y, m, d))

dates_list = sorted(all_dates)[:500]

for y, m, d in dates_list:
    cal = Calendar.from_solar(y, m, d)
    lun = cal.lunar
    lp = Lunar.fromDate(datetime.datetime(y, m, d, 12, 0, 0))
    lp_year = lp.getYear()
    lp_month = abs(lp.getMonth())  # Lunar month (absolute, negative=leap)
    lp_day = lp.getDay()
    lp_is_leap = lp.getMonth() < 0  # Negative month = leap month

    results["random"]["total"] += 1

    if lun is None:
        results["random"]["diff2plus"] += 1
        results["random"]["errors"].append(f"{y}-{m:02d}-{d:02d}: engine=None, lunar_python={lp_year}-{lp_month}-{lp_day}")
        continue

    eng = (lun.year, lun.month, lun.day, lun.is_leap)
    lib = (lp_year, lp_month, lp_day, lp_is_leap)

    if eng == lib:
        results["random"]["exact"] += 1
    else:
        # Check if ±1 day
        try:
            e_date = datetime.date(lun.year or 1, lun.month or 1, lun.day or 1)
            l_date = datetime.date(lp_year or 1, lp_month or 1, lp_day or 1)
            diff_days = abs((e_date - l_date).days)
        except:
            diff_days = 99

        if diff_days <= 1 and lun.is_leap == lp_is_leap:
            results["random"]["diff1"] += 1
        else:
            results["random"]["diff2plus"] += 1
            results["random"]["errors"].append(
                f"{y}-{m:02d}-{d:02d}: engine=({lun.year},{lun.month},{lun.day},{lun.is_leap}) "
                f"lunar_python=({lp_year},{lp_month},{lp_day},{lp_is_leap})"
            )

r = results["random"]
print(f"  Total: {r['total']}, Exact: {r['exact']} ({r['exact']/r['total']*100:.1f}%)")
print(f"  ±1 day: {r['diff1']} ({r['diff1']/r['total']*100:.1f}%)")
print(f"  Major error: {r['diff2plus']} ({r['diff2plus']/r['total']*100:.1f}%)")
if r['errors']:
    print(f"  First 5 errors:")
    for err in r['errors'][:5]:
        print(f"    {err}")

# ========== 2. Spring Festival ==========
print()
print("=" * 60)
print("2. Spring Festival (正月初一) verification 1900-2100")
print("=" * 60)

for y in range(1900, 2101):
    # Use lunar_python to find Spring Festival date (lunar 1/1 → solar)
    lp = Lunar.fromYmd(y, 1, 1)
    sol = lp.getSolar()
    sy, sm, sd = sol.getYear(), sol.getMonth(), sol.getDay()
    cal = Calendar.from_solar(sy, sm, sd)
    lun = cal.lunar

    results["spring_festival"]["total"] += 1

    if lun is None or (lun.year, lun.month, lun.day) != (y, 1, 1):
        results["spring_festival"]["diff"] += 1
        eng_str = f"({lun.year},{lun.month},{lun.day})" if lun else "None"
        results["spring_festival"]["errors"].append(
            f"{y}: Spring Festival solar={sy}-{sm:02d}-{sd:02d}, engine gave {eng_str}"
        )
    else:
        results["spring_festival"]["exact"] += 1

r2 = results["spring_festival"]
print(f"  Total: {r2['total']}, Exact: {r2['exact']} ({r2['exact']/r2['total']*100:.1f}%)")
if r2['errors']:
    print(f"  Errors ({len(r2['errors'])}):")
    for err in r2['errors'][:5]:
        print(f"    {err}")

# ========== 3. Known Leap Years ==========
print()
print("=" * 60)
print("3. Known leap year verification")
print("=" * 60)

leap_year_cases = {
    2023: (2, "闰二月"),
    2025: (6, "闰六月"),
    2028: (5, "闰五月"),
    2033: (11, "闰十一月"),  # Complex case
    2042: (2, "闰二月"),
}

for year, (leap_m, desc) in sorted(leap_year_cases.items()):
    # Use negative month for leap month in lunar_python
    lp = Lunar.fromYmd(year, -leap_m, 1)
    sol = lp.getSolar()
    sy, sm, sd = sol.getYear(), sol.getMonth(), sol.getDay()

    cal = Calendar.from_solar(sy, sm, sd)
    lun = cal.lunar

    results["leap_years"]["total"] += 1

    # Verify engine correctly identifies this as the leap month
    is_leap_ok = lun and lun.is_leap == True and lun.month == leap_m

    status = "✅" if is_leap_ok else "❌"
    eng_str = f"({lun.year},{lun.month},{lun.day},leap={lun.is_leap})" if lun else "None"
    results["leap_years"]["details"].append({
        "year": year, "leap_month": leap_m, "description": desc,
        "solar_date": f"{sy}-{sm:02d}-{sd:02d}",
        "engine": eng_str,
        "match": is_leap_ok
    })
    if is_leap_ok:
        results["leap_years"]["exact"] += 1
    else:
        results["leap_years"]["diff"] += 1
        print(f"  ❌ {year} {desc}: solar={sy}-{sm:02d}-{sd:02d}, engine={eng_str}")
    print(f"  {status} {year} {desc}: solar={sy}-{sm:02d}-{sd:02d} → engine={eng_str}")

# ========== 4. Edge Dates ==========
print()
print("=" * 60)
print("4. Edge date verification")
print("=" * 60)

edge_dates = []
for y in range(1900, 2101):
    edge_dates.append((y, 1, 1))  # Jan 1
    edge_dates.append((y, 12, 31))  # Dec 31
    if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0):
        edge_dates.append((y, 2, 29))  # Feb 29 (leap years only)

# 1582 transition (special case)
edge_dates.append((1582, 10, 4))
edge_dates.append((1582, 10, 15))

for y, m, d in edge_dates:
    try:
        cal = Calendar.from_solar(y, m, d)
        lun = cal.lunar
        lp = Lunar.fromDate(datetime.datetime(y, m, d, 12, 0, 0))
        results["edge"]["total"] += 1

        lp_month = abs(lp.getMonth())
        lp_day = lp.getDay()
        if lun is None:
            results["edge"]["diff"] += 1
            results["edge"]["errors"].append(f"{y}-{m:02d}-{d:02d}: engine=None, lp={lp.getYear()}-{lp_month}-{lp_day}")
        elif (lun.year, lun.month, lun.day) != (lp.getYear(), lp_month, lp_day):
            results["edge"]["diff"] += 1
            results["edge"]["errors"].append(
                f"{y}-{m:02d}-{d:02d}: engine=({lun.year},{lun.month},{lun.day}) "
                f"lp=({lp.getYear()},{lp_month},{lp_day})"
            )
        else:
            results["edge"]["exact"] += 1
    except Exception as e:
        results["edge"]["total"] += 1
        results["edge"]["diff"] += 1
        results["edge"]["errors"].append(f"{y}-{m:02d}-{d:02d}: exception {e}")

r4 = results["edge"]
print(f"  Total: {r4['total']}, Exact: {r4['exact']} ({r4['exact']/r4['total']*100:.1f}%)")
if r4['errors']:
    print(f"  First 10 errors:")
    for err in r4['errors'][:10]:
        print(f"    {err}")

# ========== Summary ==========
print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  1. Random dates (500):    Exact: {r['exact']:>4d} ({r['exact']/r['total']*100:5.1f}%)  "
      f"±1d: {r['diff1']:>4d} ({r['diff1']/r['total']*100:5.1f}%)  "
      f"Err: {r['diff2plus']:>4d} ({r['diff2plus']/r['total']*100:5.1f}%)")
print(f"  2. Spring Festival (201): Exact: {r2['exact']:>4d} ({r2['exact']/r2['total']*100:5.1f}%)  "
      f"Err: {r2['diff']:>4d}")
print(f"  3. Leap years (5):        Exact: {results['leap_years']['exact']:>4d}  "
      f"Err: {results['leap_years']['diff']:>4d}")
print(f"  4. Edge dates (449):      Exact: {r4['exact']:>4d} ({r4['exact']/r4['total']*100:5.1f}%)  "
      f"Err: {r4['diff']:>4d}")

# Write results file
report = f"""# Comprehensive Lunar Cross-Validation Results

**Date:** 2026-06-10
**Engine:** chinese_calendar
**Reference:** lunar_python (6tail)

---

## Results

| Category | Total | Exact | % | ±1 day | Major Error |
|----------|-------|-------|---|--------|-------------|
| Random dates (1900-2100) | {r['total']} | {r['exact']} | {r['exact']/r['total']*100:.1f}% | {r['diff1']} | {r['diff2plus']} |
| Spring Festival (1900-2100) | {r2['total']} | {r2['exact']} | {r2['exact']/r2['total']*100:.1f}% | — | {r2['diff']} |
| Known leap years | {results['leap_years']['total']} | {results['leap_years']['exact']} | — | — | {results['leap_years']['diff']} |
| Edge dates | {r4['total']} | {r4['exact']} | {r4['exact']/r4['total']*100:.1f}% | — | {r4['diff']} |

"""
if r['errors']:
    report += "\n## Random Date Errors\n\n"
    for err in r['errors'][:20]:
        report += f"- {err}\n"
if r2['errors']:
    report += "\n## Spring Festival Errors\n\n"
    for err in r2['errors'][:20]:
        report += f"- {err}\n"
if r4['errors']:
    report += "\n## Edge Date Errors\n\n"
    for err in r4['errors'][:20]:
        report += f"- {err}\n"

with open(r"D:\c_wannianli\test_results_comprehensive.md", "w", encoding="utf-8") as f:
    f.write(report)

print(f"\nResults saved to: D:\\c_wannianli\\test_results_comprehensive.md")
