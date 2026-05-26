# inference/relations.py — 刑冲合害六亲关系系统
#
# 实现地支间的全部相互作用规则：
#   六合、三合、半合、六冲、六害、三刑、自刑
#
# 全部为确定性查表规则，无需天文计算。
#
# 参考:
#   《渊海子平》
#   五行生克制化规则

from __future__ import annotations

from typing import Optional

from ..calendar.ganzhi import (
    EARTHLY_BRANCHES_ZH,
    HEAVENLY_STEMS_ZH,
)


# ===========================================================================
# 六合 (Liu He) — 地支两两相合
# ===========================================================================
# 子丑合土, 寅亥合木, 卯戌合火, 辰酉合金, 巳申合水, 午未合土（日月合）

LIU_HE_MAP: dict[int, int] = {
    0: 1,   # 子 → 丑
    1: 0,   # 丑 → 子
    2: 11,  # 寅 → 亥
    3: 10,  # 卯 → 戌
    4: 9,   # 辰 → 酉
    5: 8,   # 巳 → 申
    6: 7,   # 午 → 未
    7: 6,   # 未 → 午
    8: 5,   # 申 → 巳
    9: 4,   # 酉 → 辰
    10: 3,  # 戌 → 卯
    11: 2,  # 亥 → 寅
}

# 六合化五行: (支1, 支2) → 五行名
LIU_HE_ELEMENT: dict[frozenset[int], str] = {
    frozenset([0, 1]): "土",    # 子丑合土
    frozenset([2, 11]): "木",   # 寅亥合木
    frozenset([3, 10]): "火",   # 卯戌合火
    frozenset([4, 9]): "金",    # 辰酉合金
    frozenset([5, 8]): "水",    # 巳申合水
    frozenset([6, 7]): "土",    # 午未合土
}

# 六合中文名
LIU_HE_NAMES_ZH: dict[frozenset[int], str] = {
    frozenset([0, 1]): "子丑合土",
    frozenset([2, 11]): "寅亥合木",
    frozenset([3, 10]): "卯戌合火",
    frozenset([4, 9]): "辰酉合金",
    frozenset([5, 8]): "巳申合水",
    frozenset([6, 7]): "午未合土",
}


# ===========================================================================
# 三合 (San He) — 三地支合会
# ===========================================================================
# 申子辰合水, 亥卯未合木, 寅午戌合火, 巳酉丑合金

SAN_HE_GROUPS: list[list[int]] = [
    [8, 0, 4],   # 申子辰 → 水
    [11, 3, 7],  # 亥卯未 → 木
    [2, 6, 10],  # 寅午戌 → 火
    [5, 9, 1],   # 巳酉丑 → 金
]

SAN_HE_ELEMENT: list[str] = ["水", "木", "火", "金"]

# 三合 → 五行映射
SAN_HE_MAP: dict[int, tuple[int, str, list[int]]] = {}
for idx, group in enumerate(SAN_HE_GROUPS):
    for b in group:
        SAN_HE_MAP[b] = (idx, SAN_HE_ELEMENT[idx], group)


# ===========================================================================
# 半合 (Ban He) — 三合缺一
# ===========================================================================
# 半三合: 申子半合水, 子辰半合水, 申辰半合水（拱水）
# 只有三合中的任意两个构成半合，缺少一个

def is_ban_he(branches: list[int]) -> list[dict]:
    """检查一组地支中的半三合关系。

    Args:
        branches: 地支索引列表。

    Returns:
        半合关系列表，每项包含组合和五行。
    """
    results = []
    for idx, (group, element) in enumerate(zip(SAN_HE_GROUPS, SAN_HE_ELEMENT)):
        present = [b for b in group if b in branches]
        if len(present) == 2:
            missing = [b for b in group if b not in present]
            ban_he_type = "半合" if (group[0] in present and group[1] in present) or \
                                     (group[1] in present and group[2] in present) else "拱合"
            results.append({
                "group": present,
                "missing": missing,
                "element": element,
                "type_zh": ban_he_type,
            })
    return results


# ===========================================================================
# 六冲 (Liu Chong) — 地支相冲
# ===========================================================================
# 子午冲, 丑未冲, 寅申冲, 卯酉冲, 辰戌冲, 巳亥冲

LIU_CHONG_MAP: dict[int, int] = {
    0: 6,   # 子 → 午
    1: 7,   # 丑 → 未
    2: 8,   # 寅 → 申
    3: 9,   # 卯 → 酉
    4: 10,  # 辰 → 戌
    5: 11,  # 巳 → 亥
    6: 0,   # 午 → 子
    7: 1,   # 未 → 丑
    8: 2,   # 申 → 寅
    9: 3,   # 酉 → 卯
    10: 4,  # 戌 → 辰
    11: 5,  # 亥 → 巳
}

LIU_CHONG_NAMES_ZH: dict[frozenset[int], str] = {
    frozenset([0, 6]): "子午冲",
    frozenset([1, 7]): "丑未冲",
    frozenset([2, 8]): "寅申冲",
    frozenset([3, 9]): "卯酉冲",
    frozenset([4, 10]): "辰戌冲",
    frozenset([5, 11]): "巳亥冲",
}


# ===========================================================================
# 六害 (Liu Hai) — 地支相害
# ===========================================================================
# 子未害, 丑午害, 寅巳害, 卯辰害, 申亥害, 酉戌害

LIU_HAI_MAP: dict[int, int] = {
    0: 7,   # 子 → 未
    1: 6,   # 丑 → 午
    2: 5,   # 寅 → 巳
    3: 4,   # 卯 → 辰
    4: 3,   # 辰 → 卯
    5: 2,   # 巳 → 寅
    6: 1,   # 午 → 丑
    7: 0,   # 未 → 子
    8: 11,  # 申 → 亥
    9: 10,  # 酉 → 戌
    10: 9,  # 戌 → 酉
    11: 8,  # 亥 → 申
}

LIU_HAI_NAMES_ZH: dict[frozenset[int], str] = {
    frozenset([0, 7]): "子未害",
    frozenset([1, 6]): "丑午害",
    frozenset([2, 5]): "寅巳害",
    frozenset([3, 4]): "卯辰害",
    frozenset([8, 11]): "申亥害",
    frozenset([9, 10]): "酉戌害",
}


# ===========================================================================
# 三刑 (San Xing) — 地支相刑
# ===========================================================================
# 寅巳申三刑, 丑未戌三刑, 子卯刑, 辰/午/酉/亥自刑

# 三刑组
SAN_XING_GROUPS: list[list[int]] = [
    [2, 5, 8],    # 寅巳申
    [1, 7, 10],   # 丑未戌
    [0, 3],       # 子卯
]

# 自刑地支
ZI_XING_BRANCHES: list[int] = [4, 6, 9, 11]  # 辰午酉亥

# 三刑名称
SAN_XING_NAMES_ZH: dict[frozenset[int], str] = {
    frozenset([2, 5]): "寅巳刑",
    frozenset([5, 8]): "巳申刑",
    frozenset([2, 5, 8]): "寅巳申三刑",
    frozenset([1, 7]): "丑未刑",
    frozenset([7, 10]): "未戌刑",
    frozenset([1, 7, 10]): "丑未戌三刑",
    frozenset([0, 3]): "子卯刑",
}


# ===========================================================================
# 综合查询函数
# ===========================================================================


def is_liu_he(b1: int, b2: int) -> bool:
    """判断两个地支是否六合。

    Args:
        b1, b2: 地支索引 (0-11)。

    Returns:
        是否六合。
    """
    return LIU_HE_MAP.get(b1) == b2


def liu_he_element(b1: int, b2: int) -> Optional[str]:
    """返回六合化五行。

    Args:
        b1, b2: 地支索引。

    Returns:
        五行名称，如 "土"，不成合则返回 None。
    """
    return LIU_HE_ELEMENT.get(frozenset([b1, b2]))


def is_liu_chong(b1: int, b2: int) -> bool:
    """判断两个地支是否六冲。

    Args:
        b1, b2: 地支索引。

    Returns:
        是否六冲。
    """
    return LIU_CHONG_MAP.get(b1) == b2


def is_liu_hai(b1: int, b2: int) -> bool:
    """判断两个地支是否六害。

    Args:
        b1, b2: 地支索引。

    Returns:
        是否六害。
    """
    return LIU_HAI_MAP.get(b1) == b2


def is_san_xing(branches: list[int]) -> list[dict]:
    """检查一组地支中的三刑关系。

    Args:
        branches: 地支索引列表。

    Returns:
        三刑关系列表。
    """
    results = []
    branch_set = set(branches)

    # 检查寅巳申三刑
    yin_si_shen = {2, 5, 8}
    present = yin_si_shen & branch_set
    if len(present) >= 2:
        sorted_present = sorted(present)
        key = frozenset(sorted_present)
        if key in SAN_XING_NAMES_ZH:
            results.append({
                "branches": sorted_present,
                "type": "三刑",
                "name_zh": SAN_XING_NAMES_ZH[key],
            })

    # 检查丑未戌三刑
    chou_wei_xu = {1, 7, 10}
    present = chou_wei_xu & branch_set
    if len(present) >= 2:
        sorted_present = sorted(present)
        key = frozenset(sorted_present)
        if key in SAN_XING_NAMES_ZH:
            results.append({
                "branches": sorted_present,
                "type": "三刑",
                "name_zh": SAN_XING_NAMES_ZH[key],
            })

    # 检查子卯刑
    zi_mao = {0, 3}
    if zi_mao.issubset(branch_set):
        results.append({
            "branches": [0, 3],
            "type": "三刑",
            "name_zh": "子卯刑",
        })

    # 检查自刑
    for b in ZI_XING_BRANCHES:
        # 需要至少出现两次才构成自刑（四柱中同一地支出现两次）
        if branches.count(b) >= 2:
            results.append({
                "branches": [b, b],
                "type": "自刑",
                "name_zh": f"{EARTHLY_BRANCHES_ZH[b]}自刑",
            })

    return results


def is_san_he(branches: list[int]) -> list[dict]:
    """检查一组地支中的三合关系。

    Args:
        branches: 地支索引列表。

    Returns:
        三合关系列表。
    """
    results = []
    branch_set = set(branches)

    for idx, group in enumerate(SAN_HE_GROUPS):
        if set(group).issubset(branch_set):
            results.append({
                "branches": group,
                "element": SAN_HE_ELEMENT[idx],
                "name_zh": f"{EARTHLY_BRANCHES_ZH[group[0]]}"
                           f"{EARTHLY_BRANCHES_ZH[group[1]]}"
                           f"{EARTHLY_BRANCHES_ZH[group[2]]}"
                           f"合{SAN_HE_ELEMENT[idx]}局",
            })
    return results


def all_relations(branches: list[int]) -> dict:
    """检查一组地支中所有相互作用关系。

    这是综合查询函数，同时检查六合、三合、半合、六冲、六害、三刑。

    Args:
        branches: 地支索引列表。

    Returns:
        所有关系的分类字典。
    """
    result: dict = {
        "liu_he": [],
        "san_he": is_san_he(branches),
        "ban_he": is_ban_he(branches),
        "liu_chong": [],
        "liu_hai": [],
        "san_xing": is_san_xing(branches),
    }

    # 检查所有两两组合的六合
    for i in range(len(branches)):
        for j in range(i + 1, len(branches)):
            b1, b2 = branches[i], branches[j]

            # 六合
            if is_liu_he(b1, b2):
                elem = liu_he_element(b1, b2)
                result["liu_he"].append({
                    "branches": [b1, b2],
                    "name_zh": f"{EARTHLY_BRANCHES_ZH[b1]}"
                               f"{EARTHLY_BRANCHES_ZH[b2]}合{elem}",
                })

            # 六冲
            if is_liu_chong(b1, b2):
                result["liu_chong"].append({
                    "branches": [b1, b2],
                    "name_zh": LIU_CHONG_NAMES_ZH.get(
                        frozenset([b1, b2]), ""),
                })

            # 六害
            if is_liu_hai(b1, b2):
                result["liu_hai"].append({
                    "branches": [b1, b2],
                    "name_zh": LIU_HAI_NAMES_ZH.get(
                        frozenset([b1, b2]), ""),
                })

    return result
