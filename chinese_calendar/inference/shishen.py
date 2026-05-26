# inference/shishen.py — 十神系统
#
# 十神是八字推演的基础：以日干为"我"，其他天干与我的关系。
# 完全确定性算法，基于五行生克 + 阴阳异同。
#
# 规则:
#   同我者为比劫（比肩/劫财）
#   我生者为食伤（食神/伤官）
#   我克者为财（正财/偏财）
#   克我者为官杀（正官/七杀）
#   生我者为印（正印/偏印）
#
# 参考:
#   《渊海子平》十神章
#   五行生克: 木→火→土→金→水→木

from __future__ import annotations

from ..calendar.ganzhi import (
    HEAVENLY_STEMS_ZH,
    HEAVENLY_STEMS_EN,
    HEAVENLY_STEMS_WUXING,
    HIDDEN_STEMS,
)


# ===========================================================================
# 常量
# ===========================================================================

# 天干五行索引: 甲乙=木(0), 丙丁=火(1), 戊己=土(2), 庚辛=金(3), 壬癸=水(4)
STEM_ELEMENT: list[int] = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]

# 天干阴阳: 0=阳(甲丙戊庚壬), 1=阴(乙丁己辛癸)
STEM_YIN_YANG: list[int] = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]

# 十神名称（中文）
SHI_SHEN_ZH: dict[str, dict[str, str]] = {
    "同我": {"same": "比肩", "opposite": "劫财"},
    "我生": {"same": "食神", "opposite": "伤官"},
    "我克": {"same": "偏财", "opposite": "正财"},
    "克我": {"same": "七杀", "opposite": "正官"},
    "生我": {"same": "偏印", "opposite": "正印"},
}

# 十神名称（英文）
SHI_SHEN_EN: dict[str, dict[str, str]] = {
    "同我": {"same": "Bi Jian (Peer)", "opposite": "Jie Cai (Rob Wealth)"},
    "我生": {"same": "Shi Shen (Food God)", "opposite": "Shang Guan (Hurting Officer)"},
    "我克": {"same": "Pian Cai (Partial Wealth)", "opposite": "Zheng Cai (Direct Wealth)"},
    "克我": {"same": "Qi Sha (Seven Kill)", "opposite": "Zheng Guan (Direct Officer)"},
    "生我": {"same": "Pian Yin (Partial Seal)", "opposite": "Zheng Yin (Direct Seal)"},
}

# 十神五行属性（十神本身也有五行，由同柱地支藏干决定）
# 但十神的"五行"实际上是它对应的天干五行


# ===========================================================================
# 核心函数
# ===========================================================================


def _stem_relation(day_stem: int, other_stem: int) -> str:
    """计算日干与其他天干的五行关系类型。

    Args:
        day_stem:   日干索引 (0-9)。
        other_stem: 其他天干索引 (0-9)。

    Returns:
        关系类型: "同我" / "我生" / "我克" / "克我" / "生我"。
    """
    self_elem = STEM_ELEMENT[day_stem]
    other_elem = STEM_ELEMENT[other_stem]

    offset = (other_elem - self_elem) % 5

    relation_map = {
        0: "同我",
        1: "我生",
        2: "我克",
        3: "克我",
        4: "生我",
    }
    return relation_map[offset]


def _yin_yang_same(day_stem: int, other_stem: int) -> bool:
    """判断日干与其他天干的阴阳是否相同。

    Args:
        day_stem:   日干索引。
        other_stem: 其他天干索引。

    Returns:
        True 同阴阳, False 异阴阳。
    """
    return STEM_YIN_YANG[day_stem] == STEM_YIN_YANG[other_stem]


def shishen(day_stem: int, other_stem: int, lang: str = "zh") -> str:
    """计算日干对其他天干的十神关系。

    Args:
        day_stem:   日干索引 (0-9)。
        other_stem: 其他天干索引 (0-9)。
        lang:       "zh" 中文, "en" 英文。

    Returns:
        十神名称，如 "正官" 或 "Zheng Guan"。

    Examples:
        >>> shishen(4, 0)  # 戊日见甲 → 七杀（木克土，同阳）
        '七杀'
        >>> shishen(4, 1)  # 戊日见乙 → 正官（木克土，阴阳异）
        '正官'
        >>> shishen(0, 4)  # 甲日见戊 → 偏财（木克土，同阳）
        '偏财'
    """
    rel = _stem_relation(day_stem, other_stem)
    same = _yin_yang_same(day_stem, other_stem)

    key = "same" if same else "opposite"

    if lang == "zh":
        return SHI_SHEN_ZH[rel][key]
    return SHI_SHEN_EN[rel][key]


def shishen_for_stems(day_stem: int, other_stems: list[int],
                       lang: str = "zh") -> list[dict]:
    """批量计算多个天干的十神关系。

    Args:
        day_stem:     日干索引。
        other_stems:  其他天干索引列表。
        lang:         "zh" 或 "en"。

    Returns:
        十神信息字典列表，每项包含 stem, name_zh, name_en, relation, same_yinyang。
    """
    results = []
    for stem in other_stems:
        rel = _stem_relation(day_stem, stem)
        same = _yin_yang_same(day_stem, stem)
        results.append({
            "stem": stem,
            "name_zh": HEAVENLY_STEMS_ZH[stem],
            "name_en": HEAVENLY_STEMS_EN[stem],
            "shishen_zh": shishen(day_stem, stem, "zh"),
            "shishen_en": shishen(day_stem, stem, "en"),
            "relation": rel,
            "same_yinyang": same,
            "element": HEAVENLY_STEMS_WUXING[stem],
        })
    return results


def shishen_for_hidden_stems(day_stem: int, branch: int,
                              lang: str = "zh") -> list[dict]:
    """计算指定地支中藏干的十神关系。

    Args:
        day_stem: 日干索引。
        branch:   地支索引 (0-11)。
        lang:     "zh" 或 "en"。

    Returns:
        藏干的十神信息列表。
    """
    hidden = HIDDEN_STEMS.get(branch, [])
    return shishen_for_stems(day_stem, hidden, lang)


def shishen_for_bazi(bazi: dict, lang: str = "zh") -> dict:
    """计算完整四柱八字的十神分布。

    对年柱、月柱、日柱（日干自身）、时柱的天干，
    以及四柱地支的藏干，全部计算十神关系。

    Args:
        bazi: full_bazi() 返回的字典。
        lang: "zh" 或 "en"。

    Returns:
        十神分布字典:
            {
                "day_master": {日干信息},
                "pillars": {年/月/时天干的十神},
                "hidden": {各柱地支藏干的十神},
                "summary": {各十神出现次数统计},
            }
    """
    day_stem = bazi["day"]["stem"]

    result: dict = {
        "day_master": {
            "stem": day_stem,
            "name_zh": bazi["day"]["name_zh"],
            "name_en": bazi["day"]["name_en"],
            "nayin": bazi["day"]["nayin"],
        },
        "pillars": {},
        "hidden": {},
        "summary": {},
    }

    # 四柱天干的十神
    pillar_stems = {
        "year": bazi["year"]["stem"],
        "month": bazi["month"]["stem"],
    }
    # 日柱自身不算十神，时柱如果有则计算
    if bazi["hour"] is not None:
        pillar_stems["hour"] = bazi["hour"]["stem"]

    for pillar, stem in pillar_stems.items():
        info = {
            "stem": stem,
            "name_zh": HEAVENLY_STEMS_ZH[stem],
            "shishen_zh": shishen(day_stem, stem, "zh"),
            "shishen_en": shishen(day_stem, stem, "en"),
        }
        result["pillars"][pillar] = info

    # 地支藏干的十神
    pillar_branches = {
        "year": bazi["year"]["branch"],
        "month": bazi["month"]["branch"],
        "day": bazi["day"]["branch"],
    }
    if bazi["hour"] is not None:
        pillar_branches["hour"] = bazi["hour"]["branch"]

    for pillar, branch in pillar_branches.items():
        hidden = shishen_for_hidden_stems(day_stem, branch, lang)
        result["hidden"][pillar] = {
            "branch": branch,
            "branch_zh": "" if lang == "en" else (
                "子丑寅卯辰巳午未申酉戌亥"[branch]
            ),
            "hidden_stems": hidden,
        }

    # 统计各十神出现次数
    counter: dict[str, int] = {}
    for pillar in result["pillars"]:
        name = result["pillars"][pillar]["shishen_zh"]
        counter[name] = counter.get(name, 0) + 1
    for pillar in result["hidden"]:
        for hs in result["hidden"][pillar]["hidden_stems"]:
            name = hs["shishen_zh"]
            counter[name] = counter.get(name, 0) + 1
    # 排序：按出现次数降序
    sorted_summary = dict(sorted(counter.items(), key=lambda x: -x[1]))
    result["summary"] = sorted_summary

    return result
