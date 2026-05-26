# calendar/ganzhi.py — 天干地支系统
#
# 实现四柱（年柱/月柱/日柱/时柱）的全部干支计算。
#
# 规则:
#   年柱 — 以立春为界（λ=315°），非正月初一
#   月柱 — 以节（奇数节气索引）为界，正月寅月
#   日柱 — 连续 60 日周期，R.D. 直接映射
#   时柱 — 一日 12 时辰，以日干起时（五鼠遁）
#
# 参考:
#   《渊海子平》四柱理论
#   D&R (2007) Ch. 4: 干支历
#   紫金山天文台 节气发布数据

from __future__ import annotations

from typing import Optional

from ..core.rata_die import RataDie, Moment
from ..calendar.converters import gregorian_from_fixed, fixed_from_gregorian
from ..astronomy.solar_terms import (
    term_name,
    solar_term_time,
    SOLAR_TERM_NAMES_ZH,
)


# ===========================================================================
# 常量
# ===========================================================================

# 天干（0-9）
HEAVENLY_STEMS_ZH: list[str] = [
    "甲",  # 0
    "乙",  # 1
    "丙",  # 2
    "丁",  # 3
    "戊",  # 4
    "己",  # 5
    "庚",  # 6
    "辛",  # 7
    "壬",  # 8
    "癸",  # 9
]

HEAVENLY_STEMS_EN: list[str] = [
    "Jia",   # 0
    "Yi",    # 1
    "Bing",  # 2
    "Ding",  # 3
    "Wu",    # 4
    "Ji",    # 5
    "Geng",  # 6
    "Xin",   # 7
    "Ren",   # 8
    "Gui",   # 9
]

HEAVENLY_STEMS_WUXING: list[str] = [
    "木",  # 甲
    "木",  # 乙
    "火",  # 丙
    "火",  # 丁
    "土",  # 戊
    "土",  # 己
    "金",  # 庚
    "金",  # 辛
    "水",  # 壬
    "水",  # 癸
]

# 地支（0-11）
EARTHLY_BRANCHES_ZH: list[str] = [
    "子",  # 0  Rat
    "丑",  # 1  Ox
    "寅",  # 2  Tiger
    "卯",  # 3  Rabbit
    "辰",  # 4  Dragon
    "巳",  # 5  Snake
    "午",  # 6  Horse
    "未",  # 7  Goat
    "申",  # 8  Monkey
    "酉",  # 9  Rooster
    "戌",  # 10 Dog
    "亥",  # 11 Pig
]

EARTHLY_BRANCHES_EN: list[str] = [
    "Zi",    # 0
    "Chou",  # 1
    "Yin",   # 2
    "Mao",   # 3
    "Chen",  # 4
    "Si",    # 5
    "Wu",    # 6
    "Wei",   # 7
    "Shen",  # 8
    "You",   # 9
    "Xu",    # 10
    "Hai",   # 11
]

# 生肖
SHENGXIAO_ZH: list[str] = [
    "鼠", "牛", "虎", "兔", "龙", "蛇",
    "马", "羊", "猴", "鸡", "狗", "猪",
]

SHENGXIAO_EN: list[str] = [
    "Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake",
    "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig",
]

# 地支五行
BRANCH_WUXING: list[str] = [
    "水",  # 子
    "土",  # 丑
    "木",  # 寅
    "木",  # 卯
    "土",  # 辰
    "火",  # 巳
    "火",  # 午
    "土",  # 未
    "金",  # 申
    "金",  # 酉
    "土",  # 戌
    "水",  # 亥
]

# 地支藏干: 每个地支包含的藏干（天干索引列表）
HIDDEN_STEMS: dict[int, list[int]] = {
    0:  [9],           # 子 → 癸
    1:  [5, 9, 7],     # 丑 → 己(5), 癸(9), 辛(7)
    2:  [0, 2, 4],     # 寅 → 甲, 丙, 戊
    3:  [1],           # 卯 → 乙
    4:  [4, 1, 9],     # 辰 → 戊, 乙, 癸
    5:  [2, 6, 4],     # 巳 → 丙, 庚, 戊
    6:  [3, 5],        # 午 → 丁(3), 己(5)
    7:  [5, 3, 1],     # 未 → 己(5), 丁(3), 乙(1)
    8:  [6, 8, 4],     # 申 → 庚, 壬, 戊
    9:  [7],           # 酉 → 辛
    10: [4, 7, 3],     # 戌 → 戊, 辛, 丁
    11: [8, 0],        # 亥 → 壬, 甲
}

# 时辰地支（按小时划分）
# 23:00-00:59 → 子(0), 01:00-02:59 → 丑(1), ...
HOUR_BRANCHES: list[tuple[float, float, int]] = [
    (23.0, 1.0,  0),   # 子时
    (1.0,  3.0,  1),   # 丑时
    (3.0,  5.0,  2),   # 寅时
    (5.0,  7.0,  3),   # 卯时
    (7.0,  9.0,  4),   # 辰时
    (9.0,  11.0, 5),   # 巳时
    (11.0, 13.0, 6),   # 午时
    (13.0, 15.0, 7),   # 未时
    (15.0, 17.0, 8),   # 申时
    (17.0, 19.0, 9),   # 酉时
    (19.0, 21.0, 10),  # 戌时
    (21.0, 23.0, 11),  # 亥时
]

# 六十甲子纳音表（按六十甲子索引 0-59）
# 60 组分为 30 对，每对同纳音，五行循环 6 轮。
NAYIN: list[str] = [
    # 甲子 乙丑 → 海中金 (Metal in Sea)
    "海中金", "海中金",
    # 丙寅 丁卯 → 炉中火 (Fire in Furnace)
    "炉中火", "炉中火",
    # 戊辰 己巳 → 大林木 (Wood in Great Forest)
    "大林木", "大林木",
    # 庚午 辛未 → 路旁土 (Earth by Road)
    "路旁土", "路旁土",
    # 壬申 癸酉 → 剑锋金 (Sword Metal)
    "剑锋金", "剑锋金",
    # 甲戌 乙亥 → 山头火 (Fire on Mountain)
    "山头火", "山头火",
    # 丙子 丁丑 → 涧下水 (Water in Stream)
    "涧下水", "涧下水",
    # 戊寅 己卯 → 城头土 (Earth on City Wall)
    "城头土", "城头土",
    # 庚辰 辛巳 → 白蜡金 (White Wax Metal)
    "白蜡金", "白蜡金",
    # 壬午 癸未 → 杨柳木 (Willow Wood)
    "杨柳木", "杨柳木",
    # 甲申 乙酉 → 泉中水 (Water in Spring)
    "泉中水", "泉中水",
    # 丙戌 丁亥 → 屋上土 (Earth on Roof)
    "屋上土", "屋上土",
    # 戊子 己丑 → 霹雳火 (Thunder Fire)
    "霹雳火", "霹雳火",
    # 庚寅 辛卯 → 松柏木 (Pine Wood)
    "松柏木", "松柏木",
    # 壬辰 癸巳 → 长流水 (Flowing Water)
    "长流水", "长流水",
    # 甲午 乙未 → 沙中金 (Metal in Sand)
    "沙中金", "沙中金",
    # 丙申 丁酉 → 山下火 (Fire at Mountain Foot)
    "山下火", "山下火",
    # 戊戌 己亥 → 平地木 (Wood on Plain)
    "平地木", "平地木",
    # 庚子 辛丑 → 壁上土 (Earth on Wall)
    "壁上土", "壁上土",
    # 壬寅 癸卯 → 金箔金 (Gold Foil Metal)
    "金箔金", "金箔金",
    # 甲辰 乙巳 → 覆灯火 (Covered Lamp Fire)
    "覆灯火", "覆灯火",
    # 丙午 丁未 → 天河水 (Water in Sky River)
    "天河水", "天河水",
    # 戊申 己酉 → 大驿土 (Earth on Great Road)
    "大驿土", "大驿土",
    # 庚戌 辛亥 → 钗钏金 (Hairpin Metal)
    "钗钏金", "钗钏金",
    # 壬子 癸丑 → 桑柘木 (Mulberry Wood)
    "桑柘木", "桑柘木",
    # 甲寅 乙卯 → 大溪水 (Water in Great Stream)
    "大溪水", "大溪水",
    # 丙辰 丁巳 → 沙中土 (Earth in Sand)
    "沙中土", "沙中土",
    # 戊午 己未 → 天上火 (Fire in Heaven)
    "天上火", "天上火",
    # 庚申 辛酉 → 石榴木 (Pomegranate Wood)
    "石榴木", "石榴木",
    # 壬戌 癸亥 → 大海水 (Water in Great Ocean)
    "大海水", "大海水",
]

# 日柱参考点: Jan 1, 1900 = R.D. 693596 = 甲戌 (sexagenary index 10)
DAY_REFERENCE_RD: int = 693596
DAY_REFERENCE_INDEX: int = 10  # 甲戌


# ===========================================================================
# 六十甲子工具函数
# ===========================================================================


def sexagenary_index_from_ganzhi(stem: int, branch: int) -> int:
    """从天干地支索引计算六十甲子索引。

    Args:
        stem:   天干索引 (0-9)。
        branch: 地支索引 (0-11)。

    Returns:
        六十甲子索引 (0-59)。

    Note:
        只有 stem % 2 == branch % 2 的组合才有效。
        公式: index = (6 * stem - 5 * branch) % 60
    """
    return (6 * stem - 5 * branch) % 60


def stem_branch_from_sexagenary_index(index: int) -> tuple[int, int]:
    """从六十甲子索引计算天干地支索引。

    Args:
        index: 六十甲子索引 (0-59)。

    Returns:
        (stem, branch) 元组。
    """
    return (index % 10, index % 12)


def sexagenary_name(index: int, lang: str = "zh") -> str:
    """返回六十甲子的中文或英文名称。

    Args:
        index: 六十甲子索引 (0-59)。
        lang:  "zh" 中文, "en" 英文。

    Returns:
        名称字符串，如 "甲子" 或 "Jia-Zi"。
    """
    stem, branch = stem_branch_from_sexagenary_index(index)
    if lang == "zh":
        return f"{HEAVENLY_STEMS_ZH[stem]}{EARTHLY_BRANCHES_ZH[branch]}"
    else:
        return f"{HEAVENLY_STEMS_EN[stem]}-{EARTHLY_BRANCHES_EN[branch]}"


def nayin(index: int) -> str:
    """返回指定六十甲子索引的纳音五行。

    Args:
        index: 六十甲子索引 (0-59)。

    Returns:
        纳音五行名称，如 "海中金"。
    """
    return NAYIN[index % 60]


# ===========================================================================
# 日柱: 连续 60 日周期
# ===========================================================================


def day_ganzhi(rd: int | RataDie) -> tuple[int, int]:
    """计算指定 R.D. 的日柱干支索引。

    日柱是连续的 60 日周期，与月相/节气无关。
    参考点: Jan 1, 1900 = R.D. 693596 = 甲戌 (index 10)。

    Args:
        rd: R.D. 日期。

    Returns:
        (stem, branch) 元组。
    """
    if isinstance(rd, RataDie):
        rd_val = rd.day
    else:
        rd_val = rd

    index = (DAY_REFERENCE_INDEX + (rd_val - DAY_REFERENCE_RD)) % 60
    return stem_branch_from_sexagenary_index(index)


def day_ganzhi_index(rd: int | RataDie) -> int:
    """计算指定 R.D. 的日柱六十甲子索引。

    Args:
        rd: R.D. 日期。

    Returns:
        六十甲子索引 (0-59)。
    """
    if isinstance(rd, RataDie):
        rd_val = rd.day
    else:
        rd_val = rd

    return (DAY_REFERENCE_INDEX + (rd_val - DAY_REFERENCE_RD)) % 60


# ===========================================================================
# 年柱: 以立春为界
# ===========================================================================


def year_ganzhi(rd: int | RataDie | Moment,
                lichun_moment: Optional[Moment] = None) -> tuple[int, int]:
    """计算指定日期的年柱干支索引。

    年柱以立春（黄经 315°）为界，非正月初一。
    立春前属上一干支年，立春后（含）属本干支年。

    Args:
        rd:             R.D. 日期。
        lichun_moment:  可选。本年立春的精确 Moment（UTC）。
                        如不提供，自动调用 solar_term_time 计算。

    Returns:
        (stem, branch) 元组。

    Note:
        自动计算立春时刻需要 PyMeeus 支持。
    """
    if isinstance(rd, RataDie):
        rd_val = rd.day
    elif isinstance(rd, Moment):
        rd_val = int(rd.day)
    else:
        rd_val = rd

    # 获取该日期所在的公历年份
    year, _, _ = gregorian_from_fixed(RataDie(rd_val))

    # 获取立春时刻（如果未提供则自动计算）
    if lichun_moment is None:
        lichun_moment = solar_term_time(year, 2)  # 立春 = term index 2

    # 立春前属上一干支年
    if float(rd_val) < lichun_moment.day:
        effective_year = year - 1
    else:
        effective_year = year

    # 年干: (year + 6) % 10
    stem = (effective_year + 6) % 10
    # 年支: (year + 8) % 12
    branch = (effective_year + 8) % 12

    return (stem, branch)


def year_ganzhi_by_year(year: int) -> tuple[int, int]:
    """按公历年份直接计算年柱（不考虑立春边界）。

    适用于不需要精确立春判定的场景。
    精确判定请使用 year_ganzhi()。

    Args:
        year: 公历年份。

    Returns:
        (stem, branch) 元组。
    """
    stem = (year + 6) % 10
    branch = (year + 8) % 12
    return (stem, branch)


# ===========================================================================
# 月柱: 以节（奇数节气）为界
# ===========================================================================


def _month_branch_from_term_index(term_index: int) -> int:
    """从节气索引获取对应的月支。

    每月以节（奇数索引节气）为界:
        小寒 (0) → 丑(1)
        立春 (2) → 寅(2)
        惊蛰 (4) → 卯(3)
        ...

    Args:
        term_index: 节气索引 (0, 2, 4, ..., 22)。

    Returns:
        地支索引 (0-11)。
    """
    return ((term_index // 2) + 1) % 12


def _find_month_branch(moment: Moment) -> int:
    """根据日期找到当前所在的月支。

    月支由最近一个奇数索引节气（节）决定。
    如日期在立春之后、惊蛰之前，则月支为寅(2)。

    Args:
        moment: 目标时刻（UTC Moment）。

    Returns:
        月支索引 (0-11)。

    Note:
        需要 PyMeeus 计算奇节气的时刻。
    """
    year, _, _ = gregorian_from_fixed(RataDie(int(moment.day)))

    # 检查该年及前后一年的奇数节气
    for check_year in (year - 1, year, year + 1):
        # 奇数索引：1, 3, 5, ..., 23
        for term_idx in range(1, 24, 2):
            term_time = solar_term_time(check_year, term_idx)
            if term_time.day <= moment.day:
                continue
            # 找到第一个在 moment 之后的奇数节气
            # 那么 moment 在 (term_time_prev, term_time) 区间
            # month branch = 前一个节气的月支
            # 前一个 term: term_idx - 2
            prev_term_idx = term_idx - 2
            return _month_branch_from_term_index(prev_term_idx)

    return 2  # 默认寅月


def month_ganzhi(year_stem: int, month_branch: int) -> tuple[int, int]:
    """根据年干和月支计算月柱干支。

    月干由年干决定（五虎遁）:
        甲己之年丙作首 → 寅月干 = 丙(2)
        乙庚之岁戊为头 → 寅月干 = 戊(4)
        丙辛必定寻庚起 → 寅月干 = 庚(6)
        丁壬壬位顺行流 → 寅月干 = 壬(8)
        戊癸何方发 → 寅月干 = 甲(0)

    Args:
        year_stem:    年干 (0-9)。
        month_branch: 月支 (0-11)。

    Returns:
        (stem, branch) 元组。
    """
    # 寅月（month branch = 2）的月干 = (year_stem * 2 + 2) % 10
    yin_month_stem = (year_stem * 2 + 2) % 10

    # 月相对于寅月的偏移
    month_offset = (month_branch - 2) % 12

    # 月干 = (寅月干 + 偏移) % 10
    month_stem = (yin_month_stem + month_offset) % 10

    return (month_stem, month_branch)


def month_ganzhi_for_date(rd: int | RataDie | Moment,
                          year_stem: Optional[int] = None) -> tuple[int, int]:
    """计算指定日期的月柱干支。

    自动确定月支（通过最近的奇数节气），然后计算月干。

    Args:
        rd:        日期。
        year_stem: 年干 (0-9)。如不提供，自动计算。

    Returns:
        (stem, branch) 元组。

    Note:
        需要 PyMeeus。
    """
    if isinstance(rd, RataDie):
        moment = Moment(float(rd.day))
    elif isinstance(rd, Moment):
        moment = rd
    else:
        moment = Moment(float(rd))

    month_branch = _find_month_branch(moment)

    if year_stem is None:
        year_stem_val, _ = year_ganzhi(moment)
    else:
        year_stem_val = year_stem

    return month_ganzhi(year_stem_val, month_branch)


# ===========================================================================
# 时柱: 一日 12 时辰
# ===========================================================================


def hour_branch_from_float(hours: float) -> int:
    """根据小时数（0-24）获取时支索引。

    时辰划分:
        23:00-00:59 → 子(0)
        01:00-02:59 → 丑(1)
        03:00-04:59 → 寅(2)
        ...

    Args:
        hours: 小时数（0-24 浮点数，如 14.5 = 14:30）。

    Returns:
        地支索引 (0-11)。

    Note:
        23:00-23:59 也归为子时(0)。
    """
    for start, end, branch in HOUR_BRANCHES:
        if start <= hours < end:
            return branch
        # 跨天处理：子时从 23:00 开始
        if start == 23.0 and hours >= 23.0:
            return branch
        if end == 1.0 and hours >= 0.0 and hours < 1.0:
            return branch
    return 0  # 默认子时


def hour_ganzhi(day_stem: int, hour_branch: int) -> tuple[int, int]:
    """根据日干和时支计算时柱干支。

    时干由日干决定（五鼠遁）:
        甲己还加甲 → 甲日/己日子时干 = 甲(0)
        乙庚丙作初 → 乙日/庚日子时干 = 丙(2)
        丙辛从戊起 → 丙日/辛日子时干 = 戊(4)
        丁壬庚子居 → 丁日/壬日子时干 = 庚(6)
        戊癸何方发 → 戊日/癸日子时干 = 壬(8)

    Args:
        day_stem:    日干 (0-9)。
        hour_branch: 时支 (0-11)。

    Returns:
        (stem, branch) 元组。
    """
    # 子时（branch=0）时干 = (day_stem * 2) % 10
    zi_stem = (day_stem * 2) % 10

    # 时干 = (子时干 + 时支偏移) % 10
    hour_stem = (zi_stem + hour_branch) % 10

    return (hour_stem, hour_branch)


# ===========================================================================
# 四柱合成
# ===========================================================================


def full_bazi(rd: int | RataDie | Moment,
              hours: float | None = None,
              lichun_moment: Optional[Moment] = None) -> dict:
    """计算指定日期（可选时辰）的完整四柱八字。

    Args:
        rd:            日期。
        hours:         小时数（0-24），如不提供则不计算时柱。
        lichun_moment: 立春时刻（可选，自动计算）。

    Returns:
        包含完整四柱的字典:
            {
                "year":  (stem, branch, name_zh, name_en, nayin),
                "month": (stem, branch, name_zh, name_en, nayin),
                "day":   (stem, branch, name_zh, name_en, nayin),
                "hour":  (stem, branch, name_zh, name_en, nayin) or None,
                "shengxiao": {zh, en},
                "hidden_stems": {...},
            }

    Note:
        需要 PyMeeus 计算节气时刻。
    """
    if isinstance(rd, RataDie):
        rd_val = rd.day
    elif isinstance(rd, Moment):
        rd_val = int(rd.day)
    else:
        rd_val = rd

    rd_obj = RataDie(rd_val)

    # 年柱
    y_stem, y_branch = year_ganzhi(rd_obj, lichun_moment)
    y_index = sexagenary_index_from_ganzhi(y_stem, y_branch)

    # 月柱
    m_stem, m_branch = month_ganzhi_for_date(rd_obj, y_stem)
    m_index = sexagenary_index_from_ganzhi(m_stem, m_branch)

    # 日柱
    d_stem, d_branch = day_ganzhi(rd_obj)
    d_index = sexagenary_index_from_ganzhi(d_stem, d_branch)

    result: dict = {
        "year": {
            "stem": y_stem,
            "branch": y_branch,
            "name_zh": sexagenary_name(y_index, "zh"),
            "name_en": sexagenary_name(y_index, "en"),
            "nayin": nayin(y_index),
        },
        "month": {
            "stem": m_stem,
            "branch": m_branch,
            "name_zh": sexagenary_name(m_index, "zh"),
            "name_en": sexagenary_name(m_index, "en"),
            "nayin": nayin(m_index),
        },
        "day": {
            "stem": d_stem,
            "branch": d_branch,
            "name_zh": sexagenary_name(d_index, "zh"),
            "name_en": sexagenary_name(d_index, "en"),
            "nayin": nayin(d_index),
        },
        "hour": None,
        "shengxiao": {
            "zh": SHENGXIAO_ZH[y_branch],
            "en": SHENGXIAO_EN[y_branch],
        },
        "hidden_stems": _hidden_stems_dict(d_branch),
    }

    if hours is not None:
        h_branch = hour_branch_from_float(hours)
        h_stem, h_branch_idx = hour_ganzhi(d_stem, h_branch)
        h_index = sexagenary_index_from_ganzhi(h_stem, h_branch_idx)
        result["hour"] = {
            "stem": h_stem,
            "branch": h_branch_idx,
            "name_zh": sexagenary_name(h_index, "zh"),
            "name_en": sexagenary_name(h_index, "en"),
            "nayin": nayin(h_index),
        }

    return result


def _hidden_stems_dict(branch: int) -> dict:
    """返回指定地支的藏干字典。"""
    stems = HIDDEN_STEMS.get(branch, [])
    return {
        "branch_zh": EARTHLY_BRANCHES_ZH[branch],
        "hidden_stems_zh": [HEAVENLY_STEMS_ZH[s] for s in stems],
        "hidden_stems_en": [HEAVENLY_STEMS_EN[s] for s in stems],
    }


# ===========================================================================
# 生肖
# ===========================================================================


def shengxiao(rd: int | RataDie | Moment,
              lichun_moment: Optional[Moment] = None) -> tuple[int, str, str]:
    """获取指定日期的生肖。

    以立春为界（同干支年），非正月初一。

    Args:
        rd:            日期。
        lichun_moment: 立春时刻（可选）。

    Returns:
        (branch_index, zh_name, en_name)。
    """
    _, branch = year_ganzhi(rd, lichun_moment)
    return (branch, SHENGXIAO_ZH[branch], SHENGXIAO_EN[branch])


# ===========================================================================
# 格式化
# ===========================================================================


def format_ganzhi(stem: int, branch: int, lang: str = "zh") -> str:
    """格式化天干地支对。

    Args:
        stem:   天干索引 (0-9)。
        branch: 地支索引 (0-11)。
        lang:   "zh" 或 "en"。

    Returns:
        "甲子" 或 "Jia-Zi"。
    """
    if lang == "zh":
        return f"{HEAVENLY_STEMS_ZH[stem]}{EARTHLY_BRANCHES_ZH[branch]}"
    return f"{HEAVENLY_STEMS_EN[stem]}-{EARTHLY_BRANCHES_EN[branch]}"


def format_bazi(bazi: dict, lang: str = "zh") -> str:
    """将四柱字典格式化为字符串。

    Args:
        bazi: full_bazi() 返回的字典。
        lang: "zh" 或 "en"。

    Returns:
        格式化的四柱字符串。
    """
    if lang == "zh":
        year_name = bazi["year"]["name_zh"]
        month_name = bazi["month"]["name_zh"]
        day_name = bazi["day"]["name_zh"]
        hour_str = f" {bazi['hour']['name_zh']}" if bazi["hour"] else ""
        shengxiao_str = bazi["shengxiao"]["zh"]
        return (
            f"八字: {year_name} {month_name} {day_name}{hour_str}"
            f" | 生肖: {shengxiao_str}"
        )
    else:
        year_name = bazi["year"]["name_en"]
        month_name = bazi["month"]["name_en"]
        day_name = bazi["day"]["name_en"]
        hour_str = f" {bazi['hour']['name_en']}" if bazi["hour"] else ""
        shengxiao_str = bazi["shengxiao"]["en"]
        return (
            f"Bazi: {year_name} {month_name} {day_name}{hour_str}"
            f" | Shengxiao: {shengxiao_str}"
        )
