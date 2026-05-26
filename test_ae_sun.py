#!/usr/bin/env python3
"""测试 astronomy-engine 太阳 API 集成。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chinese_calendar.api import Calendar
from chinese_calendar.core.rata_die import RataDie
from chinese_calendar.calendar.converters import gregorian_from_fixed

cal = Calendar.from_solar(2026, 5, 24)
st = cal.current_solar_term
nst = cal.next_solar_term
print(f"当前节气: {st}")
print(f"下一节气: {nst}")
print(f"节气总数: {len(cal.solar_terms)}")

terms = cal.solar_terms
if terms:
    for t in terms:
        y, mo, d = gregorian_from_fixed(RataDie(int(t["moment"])))
        frac = t["moment"] - int(t["moment"])
        h = int(frac * 24)
        mi = int((frac * 24 - h) * 60)
        print(f"  {t['name_zh']:4s} ({t['name_en']:20s}): {y}-{mo:02d}-{d:02d} {h:02d}:{mi:02d} UTC")
