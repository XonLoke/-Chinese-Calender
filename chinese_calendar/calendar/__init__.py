# calendar: 历法算法层
#
# 包含:
#   converters.py — 公历/儒略历/ISO ↔ R.D. 转换
#   chinese.py    — 农历核心算法 (D&R) — Sprint 5
#   ganzhi.py     — 干支系统 — Sprint 6
#
# 算法均基于 Dershowitz & Reingold《Calendrical Calculations》

from .converters import (
    fixed_from_gregorian,
    gregorian_from_fixed,
    fixed_from_julian,
    julian_from_fixed,
    fixed_from_iso,
    iso_from_fixed,
    is_gregorian_leap_year,
    is_julian_leap_year,
)

__all__ = [
    "fixed_from_gregorian",
    "gregorian_from_fixed",
    "fixed_from_julian",
    "julian_from_fixed",
    "fixed_from_iso",
    "iso_from_fixed",
    "is_gregorian_leap_year",
    "is_julian_leap_year",
]

# 注意: chinese 模块因循环依赖问题不在此处导入。
# 使用 from chinese_calendar.calendar.chinese import ... 直接引用。
