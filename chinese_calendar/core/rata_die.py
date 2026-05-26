# core/rata_die.py — RataDie / Moment 核心类型
#
# Rata Die (R.D.) 系统是整个万年历引擎的"通用桥梁"。
# 所有历法系统都通过 R.D. 互相转换。
#
# 约定（遵循 Dershowitz & Reingold）:
#   R.D. 1 = 公元 1 年 1 月 1 日 (Gregorian proleptic) = 星期一
#   R.D. day 是整数，从 1 开始计数
#   Moment = R.D. + 日小数（用于亚日精度，如节气时刻）
#
# References:
#   Dershowitz & Reingold, "Calendrical Calculations"
#   - Chapter 1: "The Rata Die" fixed-date system
#   - Appendix C: Sample data

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Union


# ---------------------------------------------------------------------------
# RataDie
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RataDie:
    """Rata Die (R.D.) 固定日数。

    R.D. 是一个整数，表示自公元前 1 年 1 月 1 日（Gregorian proleptic）以来的天数。
    R.D. 1 = 公元 1 年 1 月 1 日（星期一）。

    Attributes:
        day: R.D. 整数值。必须为整数。
    """

    day: int

    def __post_init__(self) -> None:
        """确保 day 是整数。"""
        d = self.day
        # 如果传入的是 RataDie，提取其 .day
        if isinstance(d, RataDie):
            object.__setattr__(self, 'day', d.day)
        elif isinstance(d, float) and d == int(d):
            # 如果是 float 且没有小数部分，自动修正
            object.__setattr__(self, 'day', int(d))
        elif not isinstance(d, int):
            raise TypeError(f"RataDie day must be an int, got {type(d).__name__}")

    # -- 算术运算符 -------------------------------------------------------

    def __add__(self, n: int) -> RataDie:
        """R.D. + 整数 = 新的 R.D."""
        if not isinstance(n, int):
            return NotImplemented
        return RataDie(self.day + n)

    def __radd__(self, n: int) -> RataDie:
        """整数 + R.D. = 新的 R.D."""
        return self.__add__(n)

    def __sub__(self, other: Union[RataDie, int]) -> Union[RataDie, int]:
        """R.D. - R.D. = 天数差 (int); R.D. - int = 新的 R.D."""
        if isinstance(other, RataDie):
            return self.day - other.day
        if isinstance(other, int):
            return RataDie(self.day - other)
        return NotImplemented

    def __rsub__(self, n: int) -> RataDie:
        """int - R.D. = 新的 R.D."""
        if isinstance(n, int):
            return RataDie(n - self.day)
        return NotImplemented

    # -- 比较运算符 -------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if isinstance(other, RataDie):
            return self.day == other.day
        if isinstance(other, int):
            return self.day == other
        return NotImplemented

    def __lt__(self, other: RataDie) -> bool:
        if isinstance(other, RataDie):
            return self.day < other.day
        if isinstance(other, int):
            return self.day < other
        return NotImplemented

    def __le__(self, other: RataDie) -> bool:
        if isinstance(other, RataDie):
            return self.day <= other.day
        if isinstance(other, int):
            return self.day <= other
        return NotImplemented

    def __gt__(self, other: RataDie) -> bool:
        if isinstance(other, RataDie):
            return self.day > other.day
        if isinstance(other, int):
            return self.day > other
        return NotImplemented

    def __ge__(self, other: RataDie) -> bool:
        if isinstance(other, RataDie):
            return self.day >= other.day
        if isinstance(other, int):
            return self.day >= other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.day)

    # -- 模运算和整除 ----------------------------------------------------

    def __mod__(self, n: int) -> int:
        """R.D. % int = 余数。"""
        if not isinstance(n, int):
            return NotImplemented
        return self.day % n

    def __floordiv__(self, n: int) -> int:
        """R.D. // int = 整除。"""
        if not isinstance(n, int):
            return NotImplemented
        return self.day // n

    # -- 类型转换 ---------------------------------------------------------

    def __int__(self) -> int:
        """转换为 int（返回 R.D. 值）。"""
        return self.day

    def __float__(self) -> float:
        """转换为 float（返回 R.D. 值的浮点数）。"""
        return float(self.day)

    def __repr__(self) -> str:
        return f"RataDie({self.day})"

    def __str__(self) -> str:
        return str(self.day)


# ---------------------------------------------------------------------------
# Moment
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Moment:
    """Moment（时刻），用于亚日精度。

    Moment 是 R.D. + 日小数，用于表示一天之内的精确时刻。
    例如：Moment(739750.5) 表示 R.D. 739750 的中午 12:00。

    Attributes:
        day: R.D. + 日小数（浮点数）。
    """

    day: float

    def __post_init__(self) -> None:
        """确保 day 是数值类型。"""
        if not isinstance(self.day, (int, float)):
            raise TypeError(f"Moment day must be numeric, got {type(self.day).__name__}")

    # -- 近似为 R.D. ------------------------------------------------------

    def rata_die(self) -> RataDie:
        """返回 Moment 的 R.D. 近似（向下取整）。

        例如：Moment(739750.5).rata_die() = RataDie(739750)
        """
        from math import floor
        return RataDie(int(floor(self.day)))

    def standard_time(self) -> float:
        """将 Moment 转换为标准时间（日小数表示，0.0 = 午夜）。

        例如：Moment(739750.25) → 0.25 (对应 06:00)
              739750.5 → 0.5 (对应 12:00)
        """
        from math import modf
        frac, _ = modf(self.day)
        if frac < 0:
            frac += 1.0
        return frac

    # -- 与 datetime 互转 --------------------------------------------------

    def to_datetime(self, tz: timezone = timezone.utc) -> datetime:
        """将 Moment 转换为 datetime 对象。

        注意：这是近似转换，使用平均日长 86400 秒。
        精确的时间转换需要 ΔT 修正（见 time_systems.py, Sprint 2）。

        Args:
            tz: 目标时区，默认为 UTC。

        Returns:
            对应日期时间的 datetime 对象。
        """
        # EPOCH: R.D. 719163 = 1970-01-01 (UNIX epoch)
        # 因为 R.D. 1 = 0001-01-01, R.D. 719163 = 1970-01-01
        unix_days = self.day - 719163.0
        unix_seconds = unix_days * 86400.0
        return datetime.fromtimestamp(unix_seconds, tz=tz)

    @staticmethod
    def from_datetime(dt: datetime) -> Moment:
        """从 datetime 对象创建 Moment。

        Args:
            dt: 日期时间对象。

        Returns:
            对应的 Moment。
        """
        unix_seconds = dt.timestamp()
        unix_days = unix_seconds / 86400.0
        return Moment(unix_days + 719163.0)

    # -- 与 RataDie 互转 ---------------------------------------------------

    @staticmethod
    def from_rata_die(rd: RataDie) -> Moment:
        """从 RataDie 创建 Moment（当日午夜）。"""
        return Moment(float(rd.day))

    def to_rata_die(self) -> RataDie:
        """同 rata_die()，类型安全的 R.D. 近似。"""
        return self.rata_die()

    # -- 运算符 ------------------------------------------------------------

    def __add__(self, n: float) -> Moment:
        """Moment + 天数 = 新的 Moment。"""
        if not isinstance(n, (int, float)):
            return NotImplemented
        return Moment(self.day + n)

    def __sub__(self, other: Union[Moment, float]) -> Union[Moment, float]:
        """Moment - Moment = 天数差 (float); Moment - float = 新的 Moment。"""
        if isinstance(other, Moment):
            return self.day - other.day
        if isinstance(other, (int, float)):
            return Moment(self.day - other)
        return NotImplemented

    def __lt__(self, other: Moment) -> bool:
        if isinstance(other, Moment):
            return self.day < other.day
        return NotImplemented

    def __le__(self, other: Moment) -> bool:
        if isinstance(other, Moment):
            return self.day <= other.day
        return NotImplemented

    def __gt__(self, other: Moment) -> bool:
        if isinstance(other, Moment):
            return self.day > other.day
        return NotImplemented

    def __ge__(self, other: Moment) -> bool:
        if isinstance(other, Moment):
            return self.day >= other.day
        return NotImplemented

    def __float__(self) -> float:
        return self.day

    def __repr__(self) -> str:
        return f"Moment({self.day})"

    def __str__(self) -> str:
        return str(self.day)
