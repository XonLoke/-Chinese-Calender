# api/solar_date.py — 公历日期类型
#
# 提供 SolarDate 数据类，封装公历日期的核心字段和基础操作。

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SolarDate:
    """公历日期。

    Attributes:
        year:  公历年份。
        month: 公历月份 (1-12)。
        day:   公历日 (1-31)。
        hours: 小时数 (0-24，可选，默认为 12:00 正午)。
    """
    year: int
    month: int
    day: int
    hours: float = 12.0

    def __post_init__(self) -> None:
        """基本校验。"""
        if not 1 <= self.month <= 12:
            raise ValueError(f"month must be 1-12, got {self.month}")
        if not 1 <= self.day <= 31:
            raise ValueError(f"day must be 1-31, got {self.day}")
        if not 0 <= self.hours <= 24:
            raise ValueError(f"hours must be 0-24, got {self.hours}")
