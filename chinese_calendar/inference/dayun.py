# inference/dayun.py — 大运排盘系统
#
# 大运是八字推演的核心时间轴：每十年一运，决定人生各阶段的运势趋势。
#
# 规则:
#   1. 阳男阴女 → 顺排（从月柱顺数到下一个节气）
#   2. 阴男阳女 → 逆排（从月柱逆数到上一个节气）
#   3. 起运岁数 = (出生到换月节的间隔天数) / 3
#
# 参考:
#   《渊海子平》大运章
#   虚岁起运法

from __future__ import annotations

from typing import Optional

from ..core.rata_die import RataDie, Moment
from ..calendar.converters import gregorian_from_fixed, fixed_from_gregorian
from ..calendar.ganzhi import (
    HEAVENLY_STEMS_ZH,
    EARTHLY_BRANCHES_ZH,
    HEAVENLY_STEMS_EN,
    EARTHLY_BRANCHES_EN,
    STEM_YIN_YANG,
    sexagenary_index_from_ganzhi,
    sexagenary_name,
    year_ganzhi_by_year,
)


# ===========================================================================
# 大运排盘规则常量
# ===========================================================================

# 年干阴阳判定: 0=阳(甲丙戊庚壬), 1=阴(乙丁己辛癸)
# 阳年: 甲丙戊庚壬 → stem index 0,2,4,6,8
# 阴年: 乙丁己辛癸 → stem index 1,3,5,7,9
YANG_STEMS: set[int] = {0, 2, 4, 6, 8}
YIN_STEMS: set[int] = {1, 3, 5, 7, 9}


# ===========================================================================
# 换月节气表（用于大运顺逆排的边界判定）
# ===========================================================================

# 每月对应的"节"（奇数索引节气）
# 子月(11) → 大雪, 丑月(0) → 小寒, 寅月(1) → 立春, ...
# 这里的月支以节气月为准
MONTH_JIE_TERM: dict[int, int] = {
    2: 2,   # 寅月 → 立春 (term 2)
    3: 4,   # 卯月 → 惊蛰 (term 4)
    4: 6,   # 辰月 → 清明 (term 6)
    5: 8,   # 巳月 → 立夏 (term 8)
    6: 10,  # 午月 → 芒种 (term 10)
    7: 12,  # 未月 → 小暑 (term 12)
    8: 14,  # 申月 → 立秋 (term 14)
    9: 16,  # 酉月 → 白露 (term 16)
    10: 18, # 戌月 → 寒露 (term 18)
    11: 20, # 亥月 → 立冬 (term 20)
    0: 22,  # 子月 → 大雪 (term 22)
    1: 0,   # 丑月 → 小寒 (term 0)
}

# 节气近似日期表（月首日，用于人工计算，非精确值）
# 这里的节气月支 → 约的公历日期
MONTH_JIE_APPROX: dict[int, tuple[int, int]] = {
    2: (2, 4),   # 寅月立春约 2/4
    3: (3, 6),   # 卯月惊蛰约 3/6
    4: (4, 5),   # 辰月清明约 4/5
    5: (5, 6),   # 巳月立夏约 5/6
    6: (6, 6),   # 午月芒种约 6/6
    7: (7, 7),   # 未月小暑约 7/7
    8: (8, 7),   # 申月立秋约 8/7
    9: (9, 8),   # 酉月白露约 9/8
    10: (10, 8), # 戌月寒露约 10/8
    11: (11, 7), # 亥月立冬约 11/7
    0: (12, 7),  # 子月大雪约 12/7
    1: (1, 6),   # 丑月小寒约 1/6
}


# ===========================================================================
# 核心函数
# ===========================================================================


def is_yang_year(year_stem: int) -> bool:
    """判断年干是否为阳。

    Args:
        year_stem: 年干索引 (0-9)。

    Returns:
        True 为阳年（甲丙戊庚壬）。
    """
    return year_stem in YANG_STEMS


def is_shun_pai(year_stem: int, gender: str) -> bool:
    """判断大运为顺排还是逆排。

    阳男阴女 → 顺排
    阴男阳女 → 逆排

    Args:
        year_stem: 年干索引。
        gender:    "male" 或 "female"。

    Returns:
        True 为顺排，False 为逆排。
    """
    yang = is_yang_year(year_stem)
    if gender == "male":
        return yang
    else:
        return not yang


def _next_jie_approx(year: int, month_branch: int) -> tuple[int, int, int]:
    """获取下一个换月节气的近似日期（用于无 PyMeeus 时）。

    大运从月柱开始，顺排时找下一个换月节气；
    逆排时找上一个换月节气。

    Args:
        year:         公历年份。
        month_branch: 月支索引 (0-11)，八字月柱的月支。

    Returns:
        (year, month, day) 近似日期。
    """
    # 月支对应的节气索引
    jie_term = MONTH_JIE_TERM.get(month_branch, 2)

    # 下一个节气的月支
    next_branch = (month_branch + 1) % 12
    next_jie_term = MONTH_JIE_TERM.get(next_branch, 2)

    # 从近似表获取日期
    next_month, next_day = MONTH_JIE_APPROX.get(next_branch, (2, 4))

    # 处理跨年（丑月→寅月时 year+1可能... 实际上节气月已经包含了跨年）
    # 对于小寒(term 0)在次年1月的情况
    if next_branch == 1:  # 丑月的小寒在次年1月
        # 小寒约在 1/6，大多数情况仍在同年
        adj_year = year
    elif next_branch == 2 and month_branch == 1:  # 丑→寅
        adj_year = year
    elif month_branch > next_branch and next_branch <= 1:
        adj_year = year + 1
    else:
        adj_year = year

    # 对于大雪(term 22, 约12/7)在子月(0)，属于次年的子月
    # 实际上节气月(major solar term months)跨公历年
    # 大雪约12/7 → 小寒约1/6 → 立春约2/4
    if month_branch == 11 and next_branch == 0:  # 亥月→子月
        pass  # 仍在同年12月
    elif month_branch == 0 and next_branch == 1:  # 子月→丑月
        adj_year = year  # 丑月小寒在次年1月
    elif month_branch == 1 and next_branch == 2:  # 丑月→寅月
        adj_year = year  # 寅月立春在2月

    return (adj_year, next_month, next_day)


def _prev_jie_approx(year: int, month_branch: int) -> tuple[int, int, int]:
    """获取上一个换月节气的近似日期。

    Args:
        year:         公历年份。
        month_branch: 月支索引。

    Returns:
        (year, month, day) 近似日期。
    """
    prev_branch = (month_branch - 1) % 12
    prev_month, prev_day = MONTH_JIE_APPROX.get(prev_branch, (1, 6))

    # 处理跨年
    if prev_branch == 1 and month_branch == 2:  # 丑→寅
        adj_year = year
    elif prev_branch == 0 and month_branch == 1:  # 子→丑
        adj_year = year
    elif prev_branch == 11 and month_branch == 0:  # 亥→子
        adj_year = year
    elif prev_branch > month_branch:
        adj_year = year - 1 if month_branch <= 1 else year
    else:
        adj_year = year

    return (adj_year, prev_month, prev_day)


def _days_to_next_jie(birth_rd: int, month_branch: int) -> int:
    """计算出生日到下一个换月节气的天数（近似）。

    注意：精确计算需要 PyMeeus 的 solar_term_time()。
    此处使用近似日期表，精度 ~2 天，对于架构演示已足够。

    精确版本应在有 PyMeeus 时使用 solar_term_time(year, term_index)。

    Args:
        birth_rd:   出生日的 R.D. 值。
        month_branch: 月支索引。

    Returns:
        天数（近似值）。
    """
    year, _, _ = gregorian_from_fixed(RataDie(birth_rd))

    # 下一个节气的年月日
    ny, nm, nd = _next_jie_approx(year, month_branch)
    jie_rd = fixed_from_gregorian(ny, nm, nd).day

    days = jie_rd - birth_rd
    if days < 0:
        # 下一个节气可能在次年
        ny2, nm2, nd2 = _next_jie_approx(year + 1, month_branch)
        jie_rd2 = fixed_from_gregorian(ny2, nm2, nd2).day
        days = jie_rd2 - birth_rd

    return max(days, 1)


def _days_to_prev_jie(birth_rd: int, month_branch: int) -> int:
    """计算出生日到上一个换月节气的天数（近似）。

    Args:
        birth_rd:   出生日的 R.D. 值。
        month_branch: 月支索引。

    Returns:
        天数（近似值）。
    """
    year, _, _ = gregorian_from_fixed(RataDie(birth_rd))

    py, pm, pd = _prev_jie_approx(year, month_branch)
    jie_rd = fixed_from_gregorian(py, pm, pd).day

    days = birth_rd - jie_rd
    if days < 0:
        py2, pm2, pd2 = _prev_jie_approx(year - 1, month_branch)
        jie_rd2 = fixed_from_gregorian(py2, pm2, pd2).day
        days = birth_rd - jie_rd2

    return max(days, 1)


def qiyun_age(birth_rd: int, month_branch: int,
              year_stem: int, gender: str,
              use_approximate: bool = True) -> int:
    """计算起运岁数。

    天数 / 3 = 起运岁数。余数1天=4个月，2天=8个月。
    此处简化返回整数岁。

    Args:
        birth_rd:      出生日的 R.D. 值。
        month_branch:  月支索引（八字月柱）。
        year_stem:     年干索引。
        gender:        "male" 或 "female"。
        use_approximate: 是否使用近似节气日期（True=近似，False=精确需PyMeeus）。

    Returns:
        起运年龄（整数）。
    """
    shun = is_shun_pai(year_stem, gender)

    if shun:
        days = _days_to_next_jie(birth_rd, month_branch)
    else:
        days = _days_to_prev_jie(birth_rd, month_branch)

    # 天数 / 3 = 起运岁数
    age = days // 3
    return max(age, 1)


def dayun_pillars(month_stem: int, month_branch: int,
                  year_stem: int, gender: str,
                  num_decades: int = 8) -> list[dict]:
    """计算大运干支序列。

    从月柱开始，顺排则干支各 +1；逆排则干支各 -1。
    每十年一大运。

    Args:
        month_stem:   月干索引。
        month_branch: 月支索引。
        year_stem:    年干索引。
        gender:       "male" 或 "female"。
        num_decades:  计算的大运数量（默认 8 步，管 80 年）。

    Returns:
        大运列表，每项包含 stem, branch, name_zh, name_en, index, age_range。
    """
    shun = is_shun_pai(year_stem, gender)
    step = 1 if shun else -1

    result = []
    for i in range(num_decades):
        stem = (month_stem + step * (i + 1)) % 10
        branch = (month_branch + step * (i + 1)) % 12
        index = sexagenary_index_from_ganzhi(stem, branch)

        result.append({
            "decade": i + 1,
            "stem": stem,
            "branch": branch,
            "name_zh": f"{HEAVENLY_STEMS_ZH[stem]}{EARTHLY_BRANCHES_ZH[branch]}",
            "name_en": f"{HEAVENLY_STEMS_EN[stem]}-{EARTHLY_BRANCHES_EN[branch]}",
            "sexagenary_index": index,
            "sexagenary_name": sexagenary_name(index, "zh"),
        })

    return result


def dayun_full(bazi: dict, gender: str,
               birth_rd: int | None = None,
               use_approximate: bool = True) -> dict:
    """计算完整的大运信息。

    Args:
        bazi:            full_bazi() 返回的四柱字典。
        gender:          "male" 或 "female"。
        birth_rd:        出生日的 R.D. 值（用于计算起运岁数）。
        use_approximate: 是否使用近似节气日期。

    Returns:
        完整的大运信息字典：
            {
                "gender": str,
                "is_shun_pai": bool,
                "qiyun_age": int,
                "dayun": [...],
                "current_dayun": ...,
            }
    """
    year_stem = bazi["year"]["stem"]
    month_stem = bazi["month"]["stem"]
    month_branch = bazi["month"]["branch"]

    # 计算起运年龄
    age = 0
    if birth_rd is not None:
        age = qiyun_age(birth_rd, month_branch, year_stem, gender, use_approximate)

    # 排大运
    pillars = dayun_pillars(month_stem, month_branch, year_stem, gender)

    # 标注年龄范围
    for i, p in enumerate(pillars):
        start_age = age + i * 10
        end_age = age + (i + 1) * 10
        p["age_range"] = f"{start_age}-{end_age}岁"
        p["start_age"] = start_age

    return {
        "gender": gender,
        "year_stem": year_stem,
        "is_shun_pai": is_shun_pai(year_stem, gender),
        "qiyun_age": age,
        "dayun": pillars,
    }
