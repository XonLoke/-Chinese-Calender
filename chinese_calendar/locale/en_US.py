# locale/en_US.py — 英文翻译表
#
# 提供万年历引擎需要的全部英文名称。
# 中文拼音用于天干地支（读音），英文翻译用于节气、生肖等。

from __future__ import annotations


# ===========================================================================
# Heavenly Stems
# ===========================================================================

HEAVENLY_STEMS: list[str] = [
    "Jia",    # 甲
    "Yi",     # 乙
    "Bing",   # 丙
    "Ding",   # 丁
    "Wu",     # 戊
    "Ji",     # 己
    "Geng",   # 庚
    "Xin",    # 辛
    "Ren",    # 壬
    "Gui",    # 癸
]

STEM_WUXING: list[str] = [
    "Wood", "Wood", "Fire", "Fire", "Earth",
    "Earth", "Metal", "Metal", "Water", "Water",
]

STEM_YIN_YANG_EN: list[str] = [
    "Yang", "Yin", "Yang", "Yin", "Yang",
    "Yin", "Yang", "Yin", "Yang", "Yin",
]


# ===========================================================================
# Earthly Branches
# ===========================================================================

EARTHLY_BRANCHES: list[str] = [
    "Zi",     # 子
    "Chou",   # 丑
    "Yin",    # 寅
    "Mao",    # 卯
    "Chen",   # 辰
    "Si",     # 巳
    "Wu",     # 午
    "Wei",    # 未
    "Shen",   # 申
    "You",    # 酉
    "Xu",     # 戌
    "Hai",    # 亥
]

BRANCH_WUXING: list[str] = [
    "Water", "Earth", "Wood", "Wood", "Earth", "Fire",
    "Fire", "Earth", "Metal", "Metal", "Earth", "Water",
]

BRANCH_SHENGXIAO: list[str] = [
    "Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake",
    "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig",
]


# ===========================================================================
# 24 Solar Terms
# ===========================================================================

SOLAR_TERMS: list[str] = [
    "Minor Cold",          # 小寒
    "Major Cold",          # 大寒
    "Spring Begins",       # 立春
    "Rain Water",          # 雨水
    "Waking of Insects",   # 惊蛰
    "Vernal Equinox",      # 春分
    "Pure Brightness",     # 清明
    "Grain Rain",          # 谷雨
    "Summer Begins",       # 立夏
    "Grain Buds",          # 小满
    "Grain in Ear",        # 芒种
    "Summer Solstice",     # 夏至
    "Minor Heat",          # 小暑
    "Major Heat",          # 大暑
    "Autumn Begins",       # 立秋
    "Limit of Heat",       # 处暑
    "White Dew",           # 白露
    "Autumnal Equinox",    # 秋分
    "Cold Dew",            # 寒露
    "Frost Descends",      # 霜降
    "Winter Begins",       # 立冬
    "Minor Snow",          # 小雪
    "Major Snow",          # 大雪
    "Winter Solstice",     # 冬至
]


# ===========================================================================
# Weekdays
# ===========================================================================

WEEKDAYS: list[str] = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]


# ===========================================================================
# Lunar month / day names
# ===========================================================================

LUNAR_MONTHS: list[str] = [
    "",              # 0
    "Zheng Yue",     # 1 (正月)
    "Er Yue",        # 2
    "San Yue",       # 3
    "Si Yue",        # 4
    "Wu Yue",        # 5
    "Liu Yue",       # 6
    "Qi Yue",        # 7
    "Ba Yue",        # 8
    "Jiu Yue",       # 9
    "Shi Yue",       # 10
    "Shi Yi Yue",    # 11
    "Shi Er Yue",    # 12
]

LUNAR_DAYS: list[str] = [
    "",                # 0
    "1st", "2nd", "3rd", "4th", "5th",
    "6th", "7th", "8th", "9th", "10th",
    "11th", "12th", "13th", "14th", "15th",
    "16th", "17th", "18th", "19th", "20th",
    "21st", "22nd", "23rd", "24th", "25th",
    "26th", "27th", "28th", "29th", "30th",
]

LEAP_PREFIX: str = "Leap "

# Format: "Chinese Year N"
LUNAR_YEAR_FORMAT: str = "Chinese Year"


# ===========================================================================
# Nayin (Five Elements of Sexagenary Cycle)
# ===========================================================================

NAYIN: list[str] = [
    "Sea Metal", "Furnace Fire", "Forest Wood", "Road Earth", "Sword Metal",
    "Mountain Fire", "Stream Water", "City Earth", "Wax Metal", "Willow Wood",
    "Spring Water", "Roof Earth", "Thunder Fire", "Pine Wood", "Flowing Water",
    "Sand Metal", "Hill Fire", "Flat Wood", "Wall Earth", "Gold Leaf",
    "Lamp Fire", "Sky Water", "Post Earth", "Hairpin Metal", "Mulberry Wood",
    "Ravine Water", "Sand Earth", "Sky Fire", "Pomegranate Wood", "Ocean Water",
]

WUXING: list[str] = [
    "Metal", "Wood", "Water", "Fire", "Earth",
]


# ===========================================================================
# Terminology
# ===========================================================================

PILLAR_NAMES: dict[str, str] = {
    "year": "Year Pillar",
    "month": "Month Pillar",
    "day": "Day Pillar",
    "hour": "Hour Pillar",
}

LUNAR_YEAR: str = "Chinese Year"
LUNAR_MONTH: str = "Lunar Month"
LUNAR_DAY: str = "Lunar Day"
IS_LEAP: str = "Leap Month"
SOLAR_TERM: str = "Solar Term"
NEXT_SOLAR_TERM: str = "Next Solar Term"
SHENGXIAO: str = "Zodiac"
NAYIN_NAME: str = "Nayin"
HIDDEN_STEMS: str = "Hidden Stems"
BAZI: str = "Four Pillars"
