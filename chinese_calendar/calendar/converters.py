# calendar/converters.py — 公历/儒略历/ISO ↔ R.D. 转换
#
# 实现 Dershowitz & Reingold《Calendrical Calculations》中的历法转换算法。
#
# 所有转换通过 R.D. (Rata Die) 作为统一桥梁：
#   公历 ←→ R.D. ←→ 儒略历
#                    ←→ ISO 周历
#
# 约定：
#   - R.D. 1 = 公元 1 年 1 月 1 日 (Gregorian proleptic) = 星期一
#   - 儒略历使用 4 年一闰的规则
#   - ISO 周历: 周一为每周第一天，每年第一周包含该年第一个周四
#
# References:
#   Dershowitz & Reingold, "Calendrical Calculations", Chapter 2-3
#   - fixed_from_gregorian():  D&R Eq. 2.17
#   - gregorian_from_fixed():  D&R Eq. 2.19
#   - fixed_from_julian():     D&R Eq. 3.2
#   - julian_from_fixed():     D&R Eq. 3.4
#   - fixed_from_iso():        D&R Eq. 2.23
#   - iso_from_fixed():        D&R Eq. 2.24

from __future__ import annotations

from math import floor

from ..core.rata_die import RataDie, Moment


# ===========================================================================
# 公历 (Gregorian) 闰年判断
# ===========================================================================


def is_gregorian_leap_year(year: int) -> bool:
    """判断公历年份是否为闰年。

    格里高利历闰年规则：
      年数能被 4 整除，但不能被 100 整除；
      或者能被 400 整除。

    Args:
        year: 公历年份（1 或更大）。

    Returns:
        如果是闰年返回 True，否则返回 False。

    Reference:
        D&R Eq. 2.16: (year % 4 == 0) and (year % 100 != 0) or (year % 400 == 0)
    """
    return (year % 4 == 0) and (year % 100 != 0) or (year % 400 == 0)


# ===========================================================================
# 儒略历 (Julian) 闰年判断
# ===========================================================================


def is_julian_leap_year(year: int) -> bool:
    """判断儒略历年份是否为闰年。

    儒略历闰年规则：年数能被 4 整除即为闰年。

    Args:
        year: 儒略历年份。

    Returns:
        如果是闰年返回 True，否则返回 False。

    Reference:
        D&R Eq. 3.1: year % 4 == 0
    """
    return year % 4 == 0


# ===========================================================================
# 公历 (Gregorian) ↔ R.D.
# ===========================================================================


def fixed_from_gregorian(year: int, month: int, day: int) -> RataDie:
    """将公历日期转换为 R.D. (Rata Die)。

    算法 (D&R Eq. 2.17):
      1. 计算该日是一年中的第几天 (day-of-year)
      2. 加上之前所有年的天数：365*(y-1) + 闰年修正

    闰年修正公式：
      (y-1)//4 - (y-1)//100 + (y-1)//400

    Args:
        year:  公历年份 (>= 1)
        month: 月份 (1-12)
        day:   日期 (1-31)

    Returns:
        对应的 RataDie 值。

    Example:
        >>> fixed_from_gregorian(1, 1, 1)
        RataDie(1)
        >>> fixed_from_gregorian(2000, 1, 1)
        RataDie(730120)
    """
    # 计算该日是一年中的第几天
    # day + 之前所有完整月份的天数
    month_days = _gregorian_month_days(year)

    n = day
    # 累加之前月份的天数
    for m in range(1, month):
        n += month_days[m - 1]

    # 之前所有年的天数
    prev_year = year - 1
    total = (n
             + 365 * prev_year
             + prev_year // 4
             - prev_year // 100
             + prev_year // 400)

    return RataDie(total)


def gregorian_from_fixed(rd: RataDie) -> tuple[int, int, int]:
    """将 R.D. 转换为公历日期 (year, month, day)。

    算法 (D&R Eq. 2.19):
      1. 估算年份: year ≈ rd // 366
      2. 递增年份到正确值
      3. 确定月份和日期

    Args:
        rd: RataDie 值。

    Returns:
        (year, month, day) 元组。

    Example:
        >>> gregorian_from_fixed(RataDie(1))
        (1, 1, 1)
        >>> gregorian_from_fixed(RataDie(730120))
        (2000, 1, 1)
    """
    d = rd.day

    # 估算年份：用 366（最大年天数）确保估计值 ≤ 实际年份
    year = d // 366

    # 递增到正确年份
    while d >= fixed_from_gregorian(year + 1, 1, 1).day:
        year += 1

    # 获取该年月天数，确定月份
    month_days = _gregorian_month_days(year)

    # 计算 day-of-year (从 1 开始)
    # doy = d - fixed_from_gregorian(year, 1, 1).day + 1
    jan1_rd = fixed_from_gregorian(year, 1, 1).day
    doy = d - jan1_rd + 1

    # 确定月份
    month = 1
    cum_days = 0
    for m in range(12):
        if doy <= cum_days + month_days[m]:
            month = m + 1
            break
        cum_days += month_days[m]

    # 确定日期
    day = doy - cum_days

    return (year, month, day)


def _gregorian_month_days(year: int) -> list[int]:
    """返回公历指定年份各月的天数列表。

    Args:
        year: 公历年份。

    Returns:
        包含 12 个月天数的列表。
    """
    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if is_gregorian_leap_year(year):
        days[1] = 29
    return days


# ===========================================================================
# 儒略历 (Julian) ↔ R.D.
# ===========================================================================


def fixed_from_julian(year: int, month: int, day: int) -> RataDie:
    """将儒略历日期转换为 R.D. (Rata Die)。

    算法 (D&R Eq. 3.2):
      与公历类似，但闰年规则不同（每 4 年一闰）。
      闰年修正: (y-1)//4

    Args:
        year:  儒略历年份
        month: 月份 (1-12)
        day:   日期 (1-31)

    Returns:
        对应的 RataDie 值。

    Note:
        对于公元 1582 年 10 月 15 日之前的日期，儒略历是实际使用的历法。
        此函数对任何年份都使用儒略历规则计算。
    """
    # 计算该日是一年中的第几天
    month_days = _julian_month_days(year)

    n = day
    for m in range(1, month):
        n += month_days[m - 1]

    # 之前所有年的天数
    prev_year = year - 1
    total = n + 365 * prev_year + prev_year // 4

    return RataDie(total)


def julian_from_fixed(rd: RataDie) -> tuple[int, int, int]:
    """将 R.D. 转换为儒略历日期 (year, month, day)。

    算法 (D&R Eq. 3.4):
      与 gregorian_from_fixed 类似，但闰年规则不同。

    Args:
        rd: RataDie 值。

    Returns:
        (year, month, day) 元组。
    """
    d = rd.day

    # 估算年份
    year = d // 366

    # 递增到正确年份
    while d >= fixed_from_julian(year + 1, 1, 1).day:
        year += 1

    # 计算 day-of-year
    jan1_rd = fixed_from_julian(year, 1, 1).day
    doy = d - jan1_rd + 1

    # 确定月份和日期
    month_days = _julian_month_days(year)

    month = 1
    cum_days = 0
    for m in range(12):
        if doy <= cum_days + month_days[m]:
            month = m + 1
            break
        cum_days += month_days[m]

    day = doy - cum_days

    return (year, month, day)


def _julian_month_days(year: int) -> list[int]:
    """返回儒略历指定年份各月的天数列表。

    Args:
        year: 儒略历年份。

    Returns:
        包含 12 个月天数的列表。
    """
    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if is_julian_leap_year(year):
        days[1] = 29
    return days


# ===========================================================================
# ISO 周历 ↔ R.D.
# ===========================================================================


def fixed_from_iso(cycle: int, year: int, week: int, day: int) -> RataDie:
    """将 ISO 周历日期转换为 R.D. (Rata Die)。

    ISO 周历：
      - 每年有 52 或 53 周
      - 周一为每周第一天 (day=1)
      - 周日为每周最后一天 (day=7)
      - 每年第一周包含该年第一个周四

    算法 (D&R Eq. 2.23):
      1. 找到该年 ISO 第一周周一的 R.D.
      2. 加上 (week-1)*7 + (day-1)

    Args:
        cycle: ISO 周期（通常可忽略，传入 0）
        year:  ISO 年份
        week:  周数 (1-53)
        day:   星期 (1=周一, ..., 7=周日)

    Returns:
        对应的 RataDie 值。
    """
    # 找到 ISO 年 year 的第一周周一
    # 即：该年 1 月 4 日所在的周的周一
    # 1 月 4 日总是落在 ISO 年的第一周
    jan4 = fixed_from_gregorian(year, 1, 4)

    # 向前推到周一 (day=1 in ISO = Monday)
    # D&R: Monday = 1, Sunday = 7
    # jan4 的 ISO day-of-week: (jan4 - 1) % 7 + 1  (因为 R.D. 1 = Monday)
    # D&R Eq. 2.23: winter = jan4 - (day_of_week_from_fixed(jan4) - 1)
    dow = _day_of_week_from_fixed_iso(jan4)
    winter = jan4 - (dow - 1)

    return winter + 7 * (week - 1) + (day - 1)


def iso_from_fixed(rd: RataDie) -> tuple[int, int, int, int]:
    """将 R.D. 转换为 ISO 周历日期。

    算法 (D&R Eq. 2.24):
      1. 估算 ISO 年份
      2. 计算天数在该年内的偏差
      3. 计算周数和星期

    Returns:
        (cycle, year, week, day) 元组。
        day: 1=周一, ..., 7=周日
    """
    d = rd.day

    # 估算 ISO 年份
    # 近似: ISO 年份 ≈ Gregorian 年份
    # 但对于 1 月初的日期，ISO 年份可能比 Gregorian 年份小 1
    approx = gregorian_from_fixed(rd)[0]

    # 调整到正确的 ISO 年
    # 检查该年是否已被覆盖在正确的 ISO 年中
    if d >= fixed_from_iso(0, approx + 1, 1, 1).day:
        year = approx + 1
    elif d >= fixed_from_iso(0, approx, 1, 1).day:
        year = approx
    else:
        year = approx - 1

    # 找到该年 ISO 第一周的周一
    jan4 = fixed_from_gregorian(year, 1, 4)
    dow = _day_of_week_from_fixed_iso(jan4)
    winter = jan4 - (dow - 1)

    # 计算周数和星期
    # D&R Eq. 2.24: week = 1 + (d - winter) // 7
    #               day = dow_from_fixed(d)  (ISO 星期, 1=周一)
    week = 1 + (d - winter) // 7
    iso_day = _day_of_week_from_fixed_iso(rd)

    return (0, year, week, iso_day)


def _day_of_week_from_fixed_iso(rd: RataDie) -> int:
    """从 R.D. 计算 ISO 星期（1=周一, 7=周日）。

    由于 R.D. 1 = 星期一 (Monday)，所以:
      ISO day-of-week = ((rd - 1) % 7) + 1

    Args:
        rd: RataDie 值。

    Returns:
        ISO 星期（1=周一, ..., 7=周日）。
    """
    return ((rd.day - 1) % 7) + 1


# ===========================================================================
# 星期 (Weekday) 辅助函数
# ===========================================================================


def day_of_week(rd: RataDie) -> int:
    """返回星期索引。

    因 R.D. 1 = 星期一，所以星期索引直接来自 R.D. mod 7:
    0=星期一, 1=星期二, ..., 6=星期日。

    Args:
        rd: RataDie 值。

    Returns:
        星期索引 (0-6)。
    """
    return (rd.day - 1) % 7


def day_of_week_name(rd: RataDie, lang: str = "en") -> str:
    """返回星期名称。

    Args:
        rd:   RataDie 值。
        lang: 语言代码 ("en" 或 "zh")。

    Returns:
        星期名称字符串。
    """
    from ..core.constants import WEEKDAY_NAMES_EN, WEEKDAY_NAMES_ZH

    idx = day_of_week(rd)
    if lang == "zh":
        return WEEKDAY_NAMES_ZH[idx]
    return WEEKDAY_NAMES_EN[idx]


# ===========================================================================
# Moment 与 R.D. 的附加工具
# ===========================================================================


def moment_from_datetime(year: int, month: int, day: int,
                         hour: float = 0.0) -> Moment:
    """从公历日期和时间创建 Moment。

    将 (year, month, day, hour_of_day) 转换为 Moment，
    其中 hour_of_day 是 24 小时制的小时数（含小数）。

    Args:
        year:  公历年份
        month: 月份 (1-12)
        day:   日期 (1-31)
        hour:  小时（含小数，0-24）。例如 14.5 = 14:30

    Returns:
        对应的 Moment 值。

    Example:
        >>> moment_from_datetime(2000, 1, 1, 12.0)  # 2000-01-01 中午
        Moment(730120.5)
    """
    rd = fixed_from_gregorian(year, month, day)
    fractional_day = hour / 24.0
    return Moment(float(rd.day) + fractional_day)


def fixed_from_gregorian_moment(year: int, month: int, day: int,
                                 hour: float = 0.0) -> Moment:
    """同 moment_from_datetime，返回 Moment 类型。"""
    return moment_from_datetime(year, month, day, hour)
