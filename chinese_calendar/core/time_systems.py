# core/time_systems.py — 时间系统：JD / TT / UTC / ΔT 转换
#
# 天文计算需要统一的时间基准。本模块提供：
#   1. Julian Day (JD) — 天文学标准时间坐标
#   2. Julian Centuries — 从 J2000.0 起算的儒略世纪数
#   3. ΔT — TT 与 UT 的时差（用于 UTC→TT 转换）
#   4. Dynamical Time (TT) — 力学时间，VSOP87 等天文算法需要 TT 输入
#
# 时标层级:
#   UTC (民用时) ──[+ΔT]──→ TT (力学时)
#                                 ↓
#                          VSOP87 计算
#
# Reference:
#   Meeus, "Astronomical Algorithms" (1998):
#     - Chapter 7: Julian Day
#     - Chapter 10: Dynamical Time
#     - Chapter 24: Precession, Nutation (in corrections.py)
#   Stephenson, Morrison & Hohenkerk (2016):
#     - https://royalsocietypublishing.org/doi/10.1098/rspa.2016.0404

from __future__ import annotations

from math import floor

from ..core.rata_die import Moment, RataDie
from ..calendar.converters import (
    fixed_from_gregorian,
    gregorian_from_fixed,
    moment_from_datetime,
)


# ===========================================================================
# 常数
# ===========================================================================

# J2000.0 历元对应的儒略日 (2000-01-01 12:00 TT)
J2000_JD: float = 2451545.0

# J2000.0 历元对应的 Moment 值
# 2000-01-01 12:00 TT → Moment(730120.5)
J2000_MOMENT: float = 730120.5

# 儒略世纪的天数
JULIAN_CENTURY_DAYS: float = 36525.0

# R.D. 与 JD 的偏移常数:
# JD = Moment + JD_EPOCH_OFFSET
# 验证: J2000.0 = JD 2451545.0 = Moment 730120.5
#       2451545.0 = 730120.5 + JD_EPOCH_OFFSET
#       JD_EPOCH_OFFSET = 2451545.0 - 730120.5 = 1721424.5
JD_EPOCH_OFFSET: float = 1721424.5

# 一天的秒数
SECONDS_PER_DAY: int = 86400


# ===========================================================================
# Julian Day 转换
# ===========================================================================


def moment_from_jd(jd: float) -> Moment:
    """将儒略日 (JD) 转换为 Moment。

    JD 是天文标准时间坐标，从公元前 4713 年 1 月 1 日正午起算。

    Args:
        jd: 儒略日值。

    Returns:
        对应的 Moment。

    Reference:
        D&R Eq. 1.4 / Meeus Ch. 7
    """
    return Moment(jd - JD_EPOCH_OFFSET)


def jd_from_moment(m: Moment) -> float:
    """将 Moment 转换为儒略日 (JD)。

    Args:
        m: Moment 值。

    Returns:
        对应的儒略日。

    Reference:
        D&R Eq. 1.4 / Meeus Ch. 7
    """
    return m.day + JD_EPOCH_OFFSET


# ===========================================================================
# 儒略世纪数 (Julian Centuries from J2000.0)
# ===========================================================================


def julian_centuries(m: Moment) -> float:
    """计算从 J2000.0 到给定时刻的儒略世纪数。

    这是许多天文算法（包括 VSOP87）的标准输入参数。
    用 t 表示，以儒略世纪（36525 天）为单位。

    Args:
        m: 目标时刻（Moment）。

    Returns:
        从 J2000.0 起算的儒略世纪数。J2000.0 时为 0.0。

    Reference:
        Meeus (1998) Eq. 22.1: t = (JD - 2451545.0) / 36525
    """
    jd = jd_from_moment(m)
    return (jd - J2000_JD) / JULIAN_CENTURY_DAYS


# ===========================================================================
# ΔT 计算 (Delta T = TT - UT)
# ===========================================================================


def delta_t(year: float) -> float:
    """计算 ΔT = TT - UT，单位：秒。

    ΔT 是力学时 (TT) 与协调世界时 (UTC) 之间的累积时差。
    由于地球自转减速，ΔT 随时间增加。

    本实现使用多项式拟合，覆盖 1620-2100 年范围。

    Args:
        year: 年份（浮点数，允许小数年份）。

    Returns:
        ΔT 值（秒）。

    Reference:
        Meeus (1998) Ch. 10:
          - 1620-1900: 线性近似 ΔT = 8.83 + 0.0449*(year-1700)
          - 1900-2000: 四次多项式
          - 2000-2100: 二次多项式
        Morrison & Stephenson (2004) 更新
    """
    if year < 1620:
        # 远年粗略近似（节气精度会下降，冷数据范围）
        return 120.0

    elif year < 1900:
        # 线性近似 (1620-1900)
        # Source: Espenak & Meeus (2006), Table 1
        t = year - 1700.0
        return 8.83 + 0.0449 * t

    elif year < 1920:
        # 连续二次多项式 (1900-2000)
        #
        # NASA Espenak & Meeus (2006) 给出的 1900-1920 四次多项式
        # 在 1900 年处产生 -2.79s 的不连续跳跃。为保证连续性，
        # 使用经拟合的二次多项式通过三个控制点:
        #   f(1900) = 17.81 (接续 1620-1900 线性公式)
        #   f(1950) = 28.8  (历史平均值)
        #   f(2000) = 63.8  (接续 2005-2050 二次公式)
        # ΔT(t) = 17.81 - 2.03·u + 48.02·u², u = (year-1900)/100
        u = (year - 1900.0) / 100.0
        return 17.81 - 2.03 * u + 48.02 * u ** 2

    elif year < 1941:
        # 三次多项式 (1920-1941)
        # Source: Espenak & Meeus (2006), Table 1
        t = year - 1920.0
        return (21.20
                + 0.84493 * t
                - 0.076100 * t ** 2
                + 0.0020936 * t ** 3)

    elif year < 1961:
        # 三次多项式 (1941-1961)
        # Source: Espenak & Meeus (2006), Table 1
        t = year - 1950.0
        return (29.07
                + 0.40700 * t
                - 0.000233 * t ** 2
                + 0.0001527 * t ** 3)

    elif year < 1986:
        # 三次多项式 (1961-1986)
        # Source: Espenak & Meeus (2006), Table 1
        t = year - 1975.0
        return (45.45
                + 1.06700 * t
                - 0.005400 * t ** 2
                - 0.000677 * t ** 3)

    elif year < 2005:
        # 五次多项式 (1986-2005)
        # Source: Espenak & Meeus (2006), Table 1
        t = year - 2000.0
        return (63.86
                + 0.3345 * t
                - 0.060374 * t ** 2
                + 0.0017275 * t ** 3
                + 0.000651814 * t ** 4
                + 0.00002373599 * t ** 5)

    elif year < 2050:
        # 二次多项式 (2005-2050)
        # Source: Espenak & Meeus (2006), Table 1
        t = year - 2000.0
        return 62.92 + 0.32217 * t + 0.005589 * t ** 2

    else:
        # 抛物线 + 线性修正 (2050-2150)
        # Source: Espenak & Meeus (2006), Table 1
        u = (year - 1820.0) / 100.0
        return -20.0 + 32.0 * u ** 2 - 0.5628 * (2150.0 - year)


# ===========================================================================
# 力学时 (TT) ↔ 世界时 (UT)
# ===========================================================================


def dynamical_time(m: Moment) -> Moment:
    """将 UTC Moment 转换为力学时 TT Moment。

    VSOP87 等天文算法需要 TT（Terrestrial Time）输入，
    而非平时使用的 UTC。

    转换过程:
      TT = UTC + ΔT
      ΔT 单位是秒，需转换为日单位

    Args:
        m: UTC Moment。

    Returns:
        TT Moment（比 UTC 提前 ΔT 秒）。

    Example:
        对 J2000.0: 2000-01-01 12:00 TT = 2000-01-01 12:00 UTC + 63.8s
        验证: julian_centuries(dynamical_time(m)) 应接近 -0.000002
    """
    # 从 Moment 提取年份（近似值用于 ΔT 插值）
    year = _moment_year(m)

    # 转换为 TT ≈ UTC + ΔT
    dt_seconds = delta_t(year)
    dt_days = dt_seconds / SECONDS_PER_DAY

    return Moment(m.day + dt_days)


def universal_time(m: Moment) -> Moment:
    """将力学时 TT Moment 转换为 UTC Moment。

    Args:
        m: TT Moment。

    Returns:
        UTC Moment。
    """
    # 需要迭代求解（因为 ΔT 依赖于年份，而年份依赖于 TT-UTC）
    # 但对于 < 10 秒的 ΔT 误差，一次迭代已足够
    year = _moment_year(m)
    dt_seconds = delta_t(year)
    dt_days = dt_seconds / SECONDS_PER_DAY

    utc = Moment(m.day - dt_days)

    # 二次迭代修正
    year2 = _moment_year(utc)
    dt_seconds2 = delta_t(year2)
    dt_days2 = dt_seconds2 / SECONDS_PER_DAY

    return Moment(m.day - dt_days2)


def _moment_year(m: Moment) -> float:
    """从 Moment 提取近似年份（浮点数）。"""
    rd = int(floor(m.day))
    y, _, _ = gregorian_from_fixed(RataDie(rd))
    # 加上年内小数
    year_frac = (m.day - float(rd)) / 365.0
    return float(y) + year_frac


# ===========================================================================
# 恒星时 (Sidereal Time)
# ===========================================================================


def mean_sidereal_time_greenwich(m: Moment) -> float:
    """计算格林威治平恒星时 (GMST)，单位：度。

    恒星时用于将天球坐标与地球自转关联。
    GMST 是春分点相对于格林威治子午线的时角。

    Args:
        m: UTC Moment。

    Returns:
        格林威治平恒星时（度），范围 [0, 360)。

    Reference:
        Meeus (1998) Ch. 11:
          GMST = 280.46061837 + 360.98564736629*(JD-2451545.0)
                 + 0.000387933*t² - t³/38710000
    """
    from math import fmod

    jd = jd_from_moment(m)
    t = (jd - J2000_JD) / JULIAN_CENTURY_DAYS

    # JD 小数部分对应的恒星时增量
    gmst = (280.46061837
            + 360.98564736629 * (jd - J2000_JD)
            + 0.000387933 * t ** 2
            - (t ** 3) / 38710000.0)

    # 归化到 0-360 度
    gmst = fmod(gmst, 360.0)
    if gmst < 0:
        gmst += 360.0

    return gmst


# ===========================================================================
# 工具函数
# ===========================================================================


def moment_from_utc(year: int, month: int, day: int,
                    hour: float = 0.0) -> Moment:
    """从 UTC 公历日期和时间创建 Moment（别名，与 converters 一致）。"""
    return moment_from_datetime(year, month, day, hour)


def moment_from_tt(year: int, month: int, day: int,
                   hour: float = 0.0) -> Moment:
    """从 TT 公历日期和时间创建 Moment。

    该函数创建的时刻已经是在 TT 时间尺度上，
    所以直接转换为 Moment 即可（无需 ΔT 修正）。

    Args:
        year:  公历年份
        month: 月份 (1-12)
        day:   日期 (1-31)
        hour:  小时（含小数）

    Returns:
        对应 TT 时刻的 Moment。
    """
    return moment_from_datetime(year, month, day, hour)
