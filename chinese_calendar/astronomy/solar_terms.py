# astronomy/solar_terms.py — 二十四节气判定
#
# 根据太阳黄经计算 24 节气的精确时刻。
# 每个节气对应太阳到达特定黄经的时刻：
#   小寒(285°) → 大寒(300°) → 立春(315°) → ... → 冬至(270°)
#
# 使用 Newton 法逆向求解（依赖 solve_solar_longitude），
# 精度目标：每个节气时刻 < 60 秒误差。
#
# API:
#   solar_term_time(year, term_index) → Moment
#   solar_terms_of_year(year) → list[Moment]
#   major_solar_terms_of_year(year) → list[Moment]
#   term_longitude(term_index) → float
#
# Reference:
#   D&R 节气定义: 太阳黄经每 15° 一个节气
#   Meeus Ch. 27: 太阳黄经计算
#   紫金山天文台《天文年历》: 官方节气发布标准
#
# 节气索引表:
#   idx  name_zh  name_en          longitude  approx_date
#   0    小寒     Minor Cold       285°       Jan  6
#   1    大寒     Major Cold       300°       Jan 20
#   2    立春     Spring Begins    315°       Feb  4
#   3    雨水     Rain Water       330°       Feb 19
#   4    惊蛰     Waking Insects   345°       Mar  6
#   5    春分     Vernal Equinox     0°       Mar 21
#   6    清明     Pure Brightness   15°       Apr  5
#   7    谷雨     Grain Rain        30°       Apr 20
#   8    立夏     Summer Begins     45°       May  6
#   9    小满     Grain Buds        60°       May 21
#  10    芒种     Grain in Ear      75°       Jun  6
#  11    夏至     Summer Solstice   90°       Jun 21
#  12    小暑     Minor Heat       105°       Jul  7
#  13    大暑     Major Heat       120°       Jul 23
#  14    立秋     Autumn Begins    135°       Aug  7
#  15    处暑     Limit of Heat    150°       Aug 23
#  16    白露     White Dew        165°       Sep  8
#  17    秋分     Autumnal Equinox 180°       Sep 23
#  18    寒露     Cold Dew         195°       Oct  8
#  19    霜降     Frost Descends   210°       Oct 23
#  20    立冬     Winter Begins    225°       Nov  7
#  21    小雪     Minor Snow       240°       Nov 22
#  22    大雪     Major Snow       255°       Dec  7
#  23    冬至     Winter Solstice  270°       Dec 21

from __future__ import annotations

from ..core.rata_die import Moment, RataDie
from ..calendar.converters import gregorian_from_fixed
from ..core.time_systems import dynamical_time, universal_time, moment_from_utc
from ..astronomy.sun import solve_solar_longitude


# ===========================================================================
# 节气常数
# ===========================================================================

# 二十四节气名称（中文）
SOLAR_TERM_NAMES_ZH: list[str] = [
    "小寒",     # 0
    "大寒",     # 1
    "立春",     # 2
    "雨水",     # 3
    "惊蛰",     # 4
    "春分",     # 5
    "清明",     # 6
    "谷雨",     # 7
    "立夏",     # 8
    "小满",     # 9
    "芒种",     # 10
    "夏至",     # 11
    "小暑",     # 12
    "大暑",     # 13
    "立秋",     # 14
    "处暑",     # 15
    "白露",     # 16
    "秋分",     # 17
    "寒露",     # 18
    "霜降",     # 19
    "立冬",     # 20
    "小雪",     # 21
    "大雪",     # 22
    "冬至",     # 23
]

# 二十四节气名称（英文）
SOLAR_TERM_NAMES_EN: list[str] = [
    "Minor Cold",          # 0: 小寒
    "Major Cold",          # 1: 大寒
    "Spring Begins",       # 2: 立春
    "Rain Water",          # 3: 雨水
    "Waking of Insects",   # 4: 惊蛰
    "Vernal Equinox",      # 5: 春分
    "Pure Brightness",     # 6: 清明
    "Grain Rain",          # 7: 谷雨
    "Summer Begins",       # 8: 立夏
    "Grain Buds",          # 9: 小满
    "Grain in Ear",        # 10: 芒种
    "Summer Solstice",     # 11: 夏至
    "Minor Heat",          # 12: 小暑
    "Major Heat",          # 13: 大暑
    "Autumn Begins",       # 14: 立秋
    "Limit of Heat",       # 15: 处暑
    "White Dew",           # 16: 白露
    "Autumnal Equinox",    # 17: 秋分
    "Cold Dew",            # 18: 寒露
    "Frost Descends",      # 19: 霜降
    "Winter Begins",       # 20: 立冬
    "Minor Snow",          # 21: 小雪
    "Major Snow",          # 22: 大雪
    "Winter Solstice",     # 23: 冬至
]

# 各节气的近似日期（月，日）——用于 Newton 法的初始猜测
# 这些值可以有 ±2 天的误差，Newton 法会自动校正
_SOLAR_TERM_APPROX: list[tuple[int, int]] = [
    (1, 6),    # 0: 小寒 ~Jan 6
    (1, 20),   # 1: 大寒 ~Jan 20
    (2, 4),    # 2: 立春 ~Feb 4
    (2, 19),   # 3: 雨水 ~Feb 19
    (3, 6),    # 4: 惊蛰 ~Mar 6
    (3, 21),   # 5: 春分 ~Mar 21
    (4, 5),    # 6: 清明 ~Apr 5
    (4, 20),   # 7: 谷雨 ~Apr 20
    (5, 6),    # 8: 立夏 ~May 6
    (5, 21),   # 9: 小满 ~May 21
    (6, 6),    # 10: 芒种 ~Jun 6
    (6, 21),   # 11: 夏至 ~Jun 21
    (7, 7),    # 12: 小暑 ~Jul 7
    (7, 23),   # 13: 大暑 ~Jul 23
    (8, 7),    # 14: 立秋 ~Aug 7
    (8, 23),   # 15: 处暑 ~Aug 23
    (9, 8),    # 16: 白露 ~Sep 8
    (9, 23),   # 17: 秋分 ~Sep 23
    (10, 8),   # 18: 寒露 ~Oct 8
    (10, 23),  # 19: 霜降 ~Oct 23
    (11, 7),   # 20: 立冬 ~Nov 7
    (11, 22),  # 21: 小雪 ~Nov 22
    (12, 7),   # 22: 大雪 ~Dec 7
    (12, 21),  # 23: 冬至 ~Dec 21
]

# 中气对应的节气索引（按 0°, 30°, 60°, ..., 330° 黄经排列）
# 中气在农历置闰中用于"无中气则闰"的判定
_MAJOR_TERM_INDICES: list[int] = [
    5,   # 春分   0°
    7,   # 谷雨  30°
    9,   # 小满  60°
    11,  # 夏至  90°
    13,  # 大暑 120°
    15,  # 处暑 150°
    17,  # 秋分 180°
    19,  # 霜降 210°
    21,  # 小雪 240°
    23,  # 冬至 270°
    1,   # 大寒 300°
    3,   # 雨水 330°
]


# ===========================================================================
# 节气 黄经 ↔ 索引 转换
# ===========================================================================


def term_longitude(term_index: int) -> float:
    """返回指定节气的太阳黄经（度）。

    公式: longitude = (term_index * 15 + 285) % 360

    Args:
        term_index: 节气索引 (0-23)
            0=小寒(285°), 2=立春(315°), 5=春分(0°),
            11=夏至(90°), 17=秋分(180°), 23=冬至(270°)

    Returns:
        太阳黄经（度），范围 [0, 360).

    Raises:
        ValueError: 如果 term_index 不在 0-23 范围内。
    """
    if not 0 <= term_index <= 23:
        raise ValueError(
            f"term_index must be in 0-23, got {term_index}"
        )
    return (term_index * 15 + 285) % 360.0


def term_index_from_longitude(longitude: float) -> int:
    """根据太阳黄经返回最近的节气索引。

    注意：由于节气间隔为 15°，同一个黄经可能对应两个节气
    （如 0°=春分=360°），本函数返回最接近的那个。

    Args:
        longitude: 太阳黄经（度），范围 [0, 360)。

    Returns:
        最接近的节气索引 (0-23)。
    """
    # 将黄经归一化到 [285, 645) 范围
    lon = longitude % 360.0
    if lon < 285:
        lon += 360.0

    # 计算最近的 15° 倍数
    idx = int(round((lon - 285) / 15.0)) % 24
    return idx


# ===========================================================================
# 节气时刻计算
# ===========================================================================


def solar_term_time(year: int, term_index: int) -> Moment:
    """计算指定年份指定节气的精确时刻（UTC）。

    使用 Newton 法逆向求解太阳黄经到达目标值的时刻。
    对于给定的公历年份和节气索引，在当年内搜索。

    Args:
        year:  公历年份。
        term_index: 节气索引 (0=小寒, 1=大寒, ..., 23=冬至)。

    Returns:
        该节气发生的精确 UTC Moment。

    Raises:
        ValueError: 如果 term_index 不在 0-23 范围内。

    Note:
        - 对于 term 0 (小寒, 285°，~Jan 6) 在 year 中搜索
        - 对于 term 23 (冬至, 270°，~Dec 21) 同样在 year 中搜索
        - 除极小概率下节气日期偏移 ±2 天外，所有 24 节气都在同一年内
    """
    if not 0 <= term_index <= 23:
        raise ValueError(
            f"term_index must be in 0-23, got {term_index}"
        )

    # 1. 目标黄经
    target_lon = term_longitude(term_index)

    # 2. 初始猜测（使用近似日期，正午 12:00 UTC）
    month, day = _SOLAR_TERM_APPROX[term_index]
    approx_utc = moment_from_utc(year, month, day, 12.0)

    # 3. 转换为力学时 (TT) — VSOP87 需要 TT 输入
    approx_tt = dynamical_time(approx_utc)

    # 4. Newton 法求解
    result_tt = solve_solar_longitude(target_lon, approx_tt)

    # 5. 转换回 UTC
    result_utc = universal_time(result_tt)

    return result_utc


def solar_terms_of_year(year: int) -> list[Moment]:
    """计算指定公历年份的 24 节气时刻表（UTC）。

    按时间顺序从小寒 (term 0) 到冬至 (term 23) 返回全部 24 个节气。

    Args:
        year: 公历年份。

    Returns:
        包含 24 个 UTC Moment 的列表，按时间升序排列。

    Example:
        >>> terms = solar_terms_of_year(2026)
        >>> len(terms)
        24
        >>> # terms[0] ≈ 2026-01-05 (小寒)
        >>> # terms[4] ≈ 2026-03-06 (惊蛰)
        >>> # terms[23] ≈ 2026-12-21 (冬至)
    """
    return [solar_term_time(year, i) for i in range(24)]


def major_solar_terms_of_year(year: int) -> list[Moment]:
    """计算指定公历年份的 12 个中气时刻（UTC）。

    中气是黄经为 0°, 30°, 60°, ..., 330° 的节气。
    在农历中，中气用于：
      1. 确定月份的地支（如春分在卯月）
      2. 闰月判定（无中气的月份为闰月）

    12 中气及其对应月份:
       春分(0°)  — 卯月(二月)
       谷雨(30°) — 辰月(三月)
       ...

    Args:
        year: 公历年份。

    Returns:
        包含 12 个中气 UTC Moment 的列表，按时间升序排列。
    """
    return [solar_term_time(year, idx) for idx in _MAJOR_TERM_INDICES]


# ===========================================================================
# 格式化与信息查询
# ===========================================================================


def term_name(term_index: int, lang: str = "zh") -> str:
    """返回指定索引的节气名称。

    Args:
        term_index: 节气索引 (0-23)。
        lang: "zh" 返回中文, "en" 返回英文。

    Returns:
        节气名称字符串。

    Raises:
        ValueError: 如果 term_index 或 lang 无效。
    """
    if not 0 <= term_index <= 23:
        raise ValueError(
            f"term_index must be in 0-23, got {term_index}"
        )
    if lang == "zh":
        return SOLAR_TERM_NAMES_ZH[term_index]
    elif lang == "en":
        return SOLAR_TERM_NAMES_EN[term_index]
    else:
        raise ValueError(f"lang must be 'zh' or 'en', got {lang!r}")


def format_term_datetime(moment: Moment, term_index: int,
                         lang: str = "zh") -> str:
    """将节气时刻格式化为可读字符串。

    Args:
        moment:   节气 Moment (UTC)。
        term_index: 节气索引 (0-23)。
        lang:     "zh" 中文格式, "en" 英文格式。

    Returns:
        "2026-小寒-01-05 15:30:00 (UTC)"
        "2026-Minor Cold-01-05 15:30:00 (UTC)"
    """
    # 从 Moment 提取公历日期
    rd = RataDie(int(moment.day))
    y, m, d = gregorian_from_fixed(rd)

    # 日小数 → 时分秒
    day_frac = moment.day - int(moment.day)
    total_seconds = int(round(day_frac * 86400))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    name = term_name(term_index, lang)
    return (f"{y}-{name}-{m:02d}-{d:02d} "
            f"{hours:02d}:{minutes:02d}:{seconds:02d} (UTC)")


def print_year_terms(year: int, lang: str = "zh") -> None:
    """打印指定年份的完整节气表（用于调试/验证）。

    Args:
        year: 公历年份。
        lang: "zh" 或 "en"。
    """
    terms = solar_terms_of_year(year)
    header = f"=== {year} 二十四节气表 ({year} Solar Terms) ==="
    print(header)
    print("=" * len(header))

    for i, m in enumerate(terms):
        formatted = format_term_datetime(m, i, lang)
        # 标记中气
        if i in _MAJOR_TERM_INDICES:
            formatted += " [中气]"
        # 标记四立
        if i in (2, 8, 14, 20):
            formatted += " [四立]"
        # 标记二分二至
        if i in (5, 11, 17, 23):
            formatted += " [二分二至]"
        print(formatted)
