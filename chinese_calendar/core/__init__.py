# core: 万年历引擎的基础设施层
#
# 包含:
#   rata_die.py   — RataDie / Moment 核心类型 (R.D. 系统)
#   constants.py  — 天文常数和历法常数
#   time_systems.py — JD / TT / UTC / ΔT 转换 (Sprint 2)
#
# Rata Die (R.D.) 是整个引擎的"通用桥梁"——
# 所有历法系统都通过 R.D. 互相转换，模块之间不直接依赖。
#
# 注意: time_systems 不在此处导出，以避免循环导入:
#   calendar/__init__ → converters → core/__init__ → time_systems → calendar/converters
# 请直接 from chinese_calendar.core.time_systems import ...。

from .rata_die import RataDie, Moment

__all__ = [
    "RataDie",
    "Moment",
]
