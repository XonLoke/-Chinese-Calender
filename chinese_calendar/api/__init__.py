# api: 统一 API 层 (Sprint 8)
#
# 提供 Calendar 统一入口类，封装万年历引擎的全部功能。
#
# 用法:
#   from chinese_calendar.api import Calendar
#   cal = Calendar.from_solar(2026, 5, 21)
#   cal.lunar_date
#   cal.full_bazi

from __future__ import annotations

from .calendar_api import Calendar
from .solar_date import SolarDate
from .lunar_date import LunarDate

__all__ = [
    "Calendar",
    "SolarDate",
    "LunarDate",
]
