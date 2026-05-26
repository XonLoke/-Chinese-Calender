# api/lunar_date.py — 农历日期类型
#
# 提供 LunarDate 数据类，封装农历日期的核心字段。

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LunarDate:
    """农历日期。

    Attributes:
        year:    农历年份。
        month:   农历月份 (1-12，1=正月)。
        day:     农历日 (1-29/30)。
        is_leap: 是否为闰月。
    """
    year: int
    month: int
    day: int
    is_leap: bool = False
