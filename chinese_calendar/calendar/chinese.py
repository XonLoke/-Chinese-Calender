# calendar/chinese.py — 农历核心算法 (Dershowitz & Reingold)
#
# 基于 Dershowitz & Reingold《Calendrical Calculations》第 4 章算法，
# 实现公历 ←→ 农历双向转换。
#
# 算法流程:
#   1. 冬至定位 — winter_solstice_on_or_before()
#      给定日期之前（或当天）的冬至（黄经 270°）时刻
#
#   2. 岁中新年 — new_year_in_sui()
#      冬至之后第一个新月 = 十一月朔日
#      冬至之后第二个新月 = 十二月朔日
#      冬至之后第三个新月 = 次年正月朔日（或闰月）
#
#   3. 月份结构 — leap_month_in_sui()
#      从正月初一到次年正月初一，逐月检查中气
#      "无中气则闰" — 没有中气的月份为闰月
#
#   4. 农历 ↔ R.D. — chinese_from_fixed() / fixed_from_chinese()
#
# 依赖:
#   astronomy/sun.py       — 太阳黄经 (solve_solar_longitude)
#   astronomy/moon.py      — 新月合朔 (new_moon_before/after)
#   astronomy/solar_terms.py — 中气 (major_solar_terms_of_year)
#   calendar/converters.py — 公历 ↔ R.D.
#   core/rata_die.py       — RataDie / Moment
#   core/time_systems.py   — 时间系统转换
#
# Reference:
#   D&R (2007) Ch. 4: Chinese Calendar
#   D&R (2007) Ch. 3: Winter Solstice
#   Meeus (1998) Ch. 47: New Moon
#
# 农历规则:
#   · 冬至 (黄经 270°) 必须在十一月
#   · 无中气则闰（没有中气的月份为闰月）
#   · 一个农历年有 12 或 13 个月

from __future__ import annotations

import warnings
from typing import Optional

from ..core.rata_die import Moment, RataDie
from ..calendar.converters import gregorian_from_fixed, fixed_from_gregorian
from ..astronomy.sun import solve_solar_longitude
from ..astronomy.moon import (
    new_moon_before,
    new_moon_after,
    SYNODIC_MONTH_DAYS,
    pymeeus_moon_available,
)
from ..astronomy.solar_terms import major_solar_terms_of_year


# 延迟导入（避免 core/time_systems ↔ calendar/chinese 循环导入）
# core/time_systems → calendar/converters → calendar/__init__ → chinese → core/time_systems
def _time_systems():
    """延迟加载 time_systems 模块。"""
    from ..core import time_systems as ts
    return ts


# ===========================================================================
# 冬至定位
# ===========================================================================


def winter_solstice_on_or_before(rd: int | RataDie) -> Moment:
    """找给定 R.D. 之前（或当天）的冬至（黄经 270°）精确时刻。

    冬至约在每年 12 月 21-23 日。先用公历年份估算，
    再用 Newton 法求解。

    Args:
        rd: 参考 R.D. 日期。

    Returns:
        冬至的精确 UTC Moment（在 rd 之前或当天）。

    Raises:
        ImportError: 如果 PyMeeus 未安装。
    """
    if isinstance(rd, RataDie):
        rd_val = rd.day
    elif isinstance(rd, Moment):
        rd_val = int(rd.day)
    else:
        rd_val = rd

    # 获取参考日期所在的公历年份
    y, _, _ = gregorian_from_fixed(RataDie(int(rd_val)))
    ts = _time_systems()

    # 初始猜测：该年 12 月 22 日正午 UTC
    approx = ts.moment_from_utc(y, 12, 22, 12.0)
    approx_tt = ts.dynamical_time(approx)
    result_tt = solve_solar_longitude(270.0, approx_tt)
    result = ts.universal_time(result_tt)

    # 如果结果在 rd 之后，说明冬至在上一公历年，回退一年再找
    if result.day > float(rd_val):
        approx = ts.moment_from_utc(y - 1, 12, 22, 12.0)
        approx_tt = ts.dynamical_time(approx)
        result_tt = solve_solar_longitude(270.0, approx_tt)
        result = ts.universal_time(result_tt)

    return result


# ===========================================================================
# 新月辅助
# ===========================================================================


def _new_moon_on_or_after(m: Moment) -> Moment:
    """找给定时刻之后或当天第一个新月。

    Args:
        m: 参考时刻（UTC）。

    Returns:
        之后或当天第一个新月 UTC Moment。
    """
    nm = new_moon_after(Moment(m.day - 0.5))
    if nm.day < m.day - 0.001:
        # 如果结果太早，再找下一个
        nm = new_moon_after(m)
    return nm


def _new_moon_on_or_before(m: Moment) -> Moment:
    """找给定时刻之前或当天最后一个新月。

    这是找到"包含给定时刻的农历月朔日"的关键函数。
    用于确定冬至所在月份（十一月）的月初。

    Args:
        m: 参考时刻（UTC）。

    Returns:
        之前或当天最后一个新月 UTC Moment。
    """
    return new_moon_before(Moment(m.day + 0.1))


# ===========================================================================
# 中气判定
# ===========================================================================


def _has_major_solar_term(start: Moment, end: Moment) -> bool:
    """判断区间 [start, end) 内是否包含中气（major solar term）。

    用于"无中气则闰"的闰月判定。

    Args:
        start: 区间起始时刻（朔日，UTC）。
        end:   区间结束时刻（下一朔日，UTC）。

    Returns:
        True 如果该区间内至少有一个中气。
    """
    # 获取起止日期所在的公历年份范围
    start_year, _, _ = gregorian_from_fixed(RataDie(int(start.day)))
    end_year, _, _ = gregorian_from_fixed(RataDie(int(end.day)))

    # 在起止年份前后各扩展一年进行搜索
    # （中气可能跨年，如 2026-12 的冬至和 2027-01 的大寒）
    for y in range(start_year - 1, end_year + 2):
        for term in major_solar_terms_of_year(y):
            if start.day < term.day < end.day:
                return True
    return False


# ===========================================================================
# 月份结构（岁内）
# ===========================================================================


def _month_starts_in_sui(s1: Moment, s2: Moment) -> list[Moment]:
    """收集从冬至 s1 到冬至 s2 之间所有农历月的朔日列表。

    十一月朔日 = new_moon_on_or_before(s1) 之后的第一个新月。
    更精确的说：十一月朔日 = 包含 s1 的农历月的第一天。

    Args:
        s1: 第一个冬至（UTC Moment）。
        s2: 第二个冬至（UTC Moment）。

    Returns:
        从十一月到次年十月的朔日 Moment 列表，长度 12 或 13。
    """
    # 十一月朔日 = 包含冬至 s1 的农历月的第一天
    # 用 new_moon_before(s1 + epsilon) 找到该新月
    m11 = _new_moon_on_or_before(s1)

    # 如果该新月远在 s1 之前（> 28 天），说明 s1 在月底，
    # 那么实际包含 s1 的月份是至 THE NEXT 新月
    # 但这个情况极少，暂且用当前逻辑

    # 下一岁的十一月朔日（用于限定区间上界）
    m11_next = _new_moon_on_or_before(s2)

    # 从十一月朔日开始，逐个收集新月
    month_starts: list[Moment] = [m11]
    while True:
        next_nm = new_moon_after(month_starts[-1])
        if next_nm.day >= m11_next.day - 1e-6:
            break
        month_starts.append(next_nm)

    return month_starts  # 12 或 13 个月


def _assign_month_numbers(
    n_months: int, leap_month: int
) -> list[int]:
    """为农历月分配月份编号。

    编号规则:
       索引 0  → 十一月 (11)
       索引 1  → 十二月 (12)
       索引 2  → 正月   (1)
       索引 3+ → 二月至十月 (2-10)
       闰月 → 与前一月同号（由 leap_month 索引标记）

    Args:
        n_months:  月份总数（12 或 13）。
        leap_month: 闰月索引（-1=无闰月）。

    Returns:
        月份编号列表（1-12），长度 = n_months。
    """
    numbers: list[int] = []
    counter = 11  # 从十一月开始
    for i in range(n_months):
        if i == leap_month:
            # 闰月与前一月同号
            numbers.append(numbers[-1])
        else:
            numbers.append(counter)
            counter += 1
            if counter > 12:
                counter = 1  # 十二月之后是正月
    return numbers


# ===========================================================================
# 公历 → 农历
# ===========================================================================


def chinese_from_fixed(rd: int | RataDie | Moment) -> tuple[int, int, int, bool]:
    """将 R.D. 转换为农历日期。

    Args:
        rd: R.D. 数值（整数或 RataDie 或 Moment）。

    Returns:
        (chinese_year, month, day, is_leap) 元组:
            chinese_year: 农历年（近似公历年）。
            month:        农历月份（1-12）。
            day:          农历日（1-29/30）。
            is_leap:      True 表示闰月。

    Raises:
        ImportError: 如果 PyMeeus 未安装。
        RuntimeError: 如果转换失败。
    """
    # 统一为整数 R.D.
    if isinstance(rd, Moment):
        rd_val = int(rd.day)
    elif isinstance(rd, RataDie):
        rd_val = rd.day
    else:
        rd_val = rd

    # ========== 1. 找到包含 rd 的"岁" ==========

    s1 = winter_solstice_on_or_before(rd_val)
    s2 = winter_solstice_on_or_before(Moment(s1.day + 370.0))

    # 十一月朔日（包含 s1 的农历月首）
    m11 = _new_moon_on_or_before(s1)

    # 如果 rd 在十一月朔日之前，说明 rd 在上一岁的十月
    if float(rd_val) < m11.day:
        # 回溯到上一岁
        s1 = winter_solstice_on_or_before(Moment(s1.day - 1.0))
        while s1.day >= winter_solstice_on_or_before(Moment(s1.day + 370.0)).day:
            s1 = winter_solstice_on_or_before(Moment(s1.day - 1.0))
        s2 = winter_solstice_on_or_before(Moment(s1.day + 370.0))
        m11 = _new_moon_on_or_before(s1)

    # 如果 rd 在 m11_next 之后（或等于），说明 rd 在下一岁的十月/十一月
    # 当使用 astronomy-engine 精化后，这种情况更可能出现
    while True:
        _m11_next = _new_moon_on_or_before(s2)
        if _m11_next.day <= m11.day:
            s2 = winter_solstice_on_or_before(Moment(s2.day + 370.0))
            continue
        if float(rd_val) >= _m11_next.day - 1e-6 and _m11_next.day > m11.day:
            # 推进到下一岁
            s1 = s2
            s2 = winter_solstice_on_or_before(Moment(s1.day + 370.0))
            m11 = _m11_next
        m11_next = _m11_next
        break

    # ========== 2. 收集岁内所有月份朔日 ==========

    if m11_next.day <= m11.day:
        # 安全检查：如果下一岁的十一月朔日不晚于当前，扩大搜索范围
        s2 = winter_solstice_on_or_before(Moment(s2.day + 370.0))
        m11_next = _new_moon_on_or_before(s2)

    month_starts: list[Moment] = [m11]
    while True:
        next_nm = new_moon_after(month_starts[-1])
        if next_nm.day >= m11_next.day - 1e-6:
            break
        month_starts.append(next_nm)

    n_months = len(month_starts)

    # ========== 3. 闰月判定 ==========

    leap_month = -1
    if n_months == 13:
        for i in range(n_months):
            next_start = (
                month_starts[i + 1] if i < n_months - 1 else m11_next
            )
            if not _has_major_solar_term(month_starts[i], next_start):
                leap_month = i
                break

    # ========== 4. 月份编号 ==========

    month_numbers = _assign_month_numbers(n_months, leap_month)

    # ========== 5. 找到 rd 所在的月份 ==========

    for i in range(n_months):
        start_day_float = month_starts[i].day
        end_float = (
            month_starts[i + 1].day
            if i < n_months - 1
            else m11_next.day
        )

        # 传统农历以朔日（新月发生的整日）为月首。
        # 注意：中国历法以 UTC+8（北京时间）为日界，
        # 而非 UTC。新月在北京时间 00:00-24:00 内发生，
        # 则当天即为朔日。UTC+8 = UTC + 1/3 天。
        # D&R 算法用 UTC，需修正为中国时区。
        _CHINA_TZ = 8.0 / 24.0  # UTC+8 偏移（天）
        start_day = int(start_day_float + _CHINA_TZ)
        end_day = int(end_float + _CHINA_TZ)

        if start_day <= float(rd_val) < end_day:
            month = month_numbers[i]
            day = int(rd_val - start_day) + 1
            is_leap = (i == leap_month)

            # ========== 6. 确定农历年份 ==========

            # 找到月份编号为 1（正月）的索引
            zheng_yue_idx: Optional[int] = None
            for j, mn in enumerate(month_numbers):
                if mn == 1:
                    zheng_yue_idx = j
                    break

            if zheng_yue_idx is not None:
                zheng_yue_rd = int(month_starts[zheng_yue_idx].day + _CHINA_TZ)
                gy, _, _ = gregorian_from_fixed(RataDie(zheng_yue_rd))
                if i >= zheng_yue_idx:
                    chinese_year = gy
                else:
                    chinese_year = gy - 1
            else:
                # 极罕见情况：一年中没有正月（不可能发生，但防御性编程）
                gy, _, _ = gregorian_from_fixed(RataDie(rd_val))
                chinese_year = gy

            return (chinese_year, month, day, is_leap)

    # 不应到达此处
    raise RuntimeError(
        f"chinese_from_fixed: cannot convert RD {rd_val} "
        f"(month_starts={len(month_starts)}, "
        f"m11={m11.day}, m11_next={m11_next.day})"
    )


# ===========================================================================
# 获取指定农历年的完整月份结构
# ===========================================================================


def _get_chinese_year_info(chinese_year: int) -> tuple[
    int,             # month count (12 or 13)
    list[Moment],    # month start RDs
    list[int],       # month numbers (1-12)
    int,             # leap month index (-1 if none)
]:
    """获取指定农历年的完整月份结构信息。

    农历年从正月初一到次年正月初一前一天。
    月份结构由前一个冬至所在"岁"决定。

    Args:
        chinese_year: 农历年（如 2026）。

    Returns:
        (month_count, month_starts, month_numbers, leap_month_index)。
    """
    # 农历年 N 的月份结构由公历 N-1 年的冬至决定
    # （因为十一月、十二月在前，正月在后）
    ts = _time_systems()
    approx = ts.moment_from_utc(chinese_year - 1, 12, 22, 12.0)
    approx_tt = ts.dynamical_time(approx)
    s1_tt = solve_solar_longitude(270.0, approx_tt)
    s1 = ts.universal_time(s1_tt)

    s2 = winter_solstice_on_or_before(Moment(s1.day + 370.0))
    m11 = _new_moon_on_or_before(s1)
    m11_next = _new_moon_on_or_before(s2)

    if m11_next.day <= m11.day:
        s2 = winter_solstice_on_or_before(Moment(s2.day + 370.0))
        m11_next = _new_moon_on_or_before(s2)

    month_starts: list[Moment] = [m11]
    while True:
        next_nm = new_moon_after(month_starts[-1])
        if next_nm.day >= m11_next.day - 1e-6:
            break
        month_starts.append(next_nm)

    n_months = len(month_starts)

    leap_month = -1
    if n_months == 13:
        for i in range(n_months):
            next_start = (
                month_starts[i + 1] if i < n_months - 1 else m11_next
            )
            if not _has_major_solar_term(month_starts[i], next_start):
                leap_month = i
                break

    month_numbers = _assign_month_numbers(n_months, leap_month)

    return (n_months, month_starts, month_numbers, leap_month)


# ===========================================================================
# 农历 → 公历
# ===========================================================================


def fixed_from_chinese(
    year: int, month: int, day: int, is_leap: bool = False
) -> RataDie:
    """将农历日期转换为 R.D.

    Args:
        year:   农历年。
        month:  农历月份（1-12，其中 1=正月）。
        day:    农历日（1-29/30）。
        is_leap: True 表示闰月。

    Returns:
        对应 R.D. 日期。

    Raises:
        ImportError: 如果 PyMeeus 未安装。
        ValueError:  如果输入的农历日期无效。
    """
    # 尝试在 year 对应的岁中查找
    # 先假设这一年由前一个冬至决定岁结构
    # 如果找不到对应月份，再尝试后一个岁

    # 第一次尝试：年 N 的前一个冬至（公历 N-1 年 12 月）
    candidates: list[int] = [year - 1, year]

    for base_year in candidates:
        try:
            ts = _time_systems()
            approx = ts.moment_from_utc(base_year, 12, 22, 12.0)
            approx_tt = ts.dynamical_time(approx)
            s1_tt = solve_solar_longitude(270.0, approx_tt)
            s1 = ts.universal_time(s1_tt)

            s2 = winter_solstice_on_or_before(Moment(s1.day + 370.0))
            m11 = _new_moon_on_or_before(s1)
            m11_next = _new_moon_on_or_before(s2)

            if m11_next.day <= m11.day:
                continue

            month_starts: list[Moment] = [m11]
            while True:
                next_nm = new_moon_after(month_starts[-1])
                if next_nm.day >= m11_next.day - 1e-6:
                    break
                month_starts.append(next_nm)

            n = len(month_starts)

            leap_idx = -1
            if n == 13:
                for i in range(n):
                    next_s = month_starts[i + 1] if i < n - 1 else m11_next
                    if not _has_major_solar_term(month_starts[i], next_s):
                        leap_idx = i
                        break

            nums = _assign_month_numbers(n, leap_idx)

            for i in range(n):
                if nums[i] == month and (i == leap_idx) == is_leap:
                    rd_start = int(month_starts[i].day)
                    return RataDie(rd_start + day - 1)

        except Exception:
            continue

    raise ValueError(
        f"fixed_from_chinese: invalid date "
        f"{year}-{month}-{'闰' if is_leap else ''}{day}"
    )


# ===========================================================================
# 便捷函数
# ===========================================================================


def chinese_new_year(year: int) -> RataDie:
    """返回指定农历年正月初一的 R.D.

    Args:
        year: 农历年。

    Returns:
        正月初一的 RataDie。
    """
    # 查找月份编号为 1（正月）的第一个月首
    _, month_starts, month_numbers, _ = _get_chinese_year_info(year)

    for ms, mn in zip(month_starts, month_numbers):
        if mn == 1:
            return RataDie(int(ms.day))

    raise RuntimeError(f"chinese_new_year: year {year} has no month 1")


def is_chinese_leap_year(year: int) -> bool:
    """判断指定农历年是否有闰月。

    Args:
        year: 农历年。

    Returns:
        True 如果有闰月。
    """
    _, _, _, leap_month = _get_chinese_year_info(year)
    return leap_month >= 0


def format_lunar_date(
    year: int, month: int, day: int, is_leap: bool = False,
    lang: str = "zh",
) -> str:
    """将农历日期格式化为字符串。

    Args:
        year:    农历年。
        month:   农历月份（1=正月）。
        day:     农历日。
        is_leap: 是否闰月。
        lang:    "zh" 中文, "en" 英文。

    Returns:
        格式化字符串。
    """
    if lang == "zh":
        # 月份名称
        month_names = [
            "", "正月", "二月", "三月", "四月", "五月", "六月",
            "七月", "八月", "九月", "十月", "十一月", "十二月",
        ]
        # 日期名称
        day_names = [
            "", "初一", "初二", "初三", "初四", "初五", "初六", "初七",
            "初八", "初九", "初十", "十一", "十二", "十三", "十四", "十五",
            "十六", "十七", "十八", "十九", "二十", "廿一", "廿二", "廿三",
            "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
        ]

        prefix = "闰" if is_leap else ""
        month_str = month_names[month] if 1 <= month <= 12 else f"{month}月"
        day_str = day_names[day] if 1 <= day <= 30 else f"{day}日"
        return f"农历{year}年{prefix}{month_str}{day_str}"
    else:
        prefix = "leap " if is_leap else ""
        return (
            f"Chinese {year}-{month:02d}-{day:02d}"
            f"{' (leap)' if is_leap else ''}"
        )


def format_lunar_date_short(
    year: int, month: int, day: int, is_leap: bool = False,
) -> str:
    """简短格式（不含农历年）。

    Args:
        year:    农历年。
        month:   农历月份。
        day:     农历日。
        is_leap: 是否闰月。

    Returns:
        "正月廿八" 或 "(闰)二月十五"。
    """
    month_names = [
        "", "正月", "二月", "三月", "四月", "五月", "六月",
        "七月", "八月", "九月", "十月", "十一月", "十二月",
    ]
    day_names = [
        "", "初一", "初二", "初三", "初四", "初五", "初六", "初七",
        "初八", "初九", "初十", "十一", "十二", "十三", "十四", "十五",
        "十六", "十七", "十八", "十九", "二十", "廿一", "廿二", "廿三",
        "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
    ]

    prefix = "闰" if is_leap else ""
    month_str = month_names[month] if 1 <= month <= 12 else f"{month}月"
    day_str = day_names[day] if 1 <= day <= 30 else f"{day}日"
    return f"{prefix}{month_str}{day_str}"
