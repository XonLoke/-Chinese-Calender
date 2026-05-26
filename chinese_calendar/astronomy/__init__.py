# astronomy: 天文计算引擎
#
# 包含:
#   sun.py          — 太阳黄经计算 (VSOP87 或 PyMeeus 封装)
#   moon.py         — 新月合朔计算 (Sprint 4)
#   solar_terms.py  — 24 节气判定 (Sprint 3)
#   corrections.py  — 岁差/章动/光行差修正
#
# 精度目标:
#   太阳黄经: < 1 角秒
#   节气时刻: < 60 秒
#   合朔时刻: < 10 分钟

from .sun import (
    solar_longitude,
    apparent_solar_longitude,
    solar_longitude_rate,
    solve_solar_longitude,
    pymeeus_available,
)
from .corrections import (
    nutation_longitude,
    mean_obliquity,
    true_obliquity,
)
from .solar_terms import (
    solar_term_time,
    solar_terms_of_year,
    major_solar_terms_of_year,
    term_longitude,
    term_index_from_longitude,
    term_name,
    format_term_datetime,
    print_year_terms,
    SOLAR_TERM_NAMES_ZH,
    SOLAR_TERM_NAMES_EN,
)
from .moon import (
    moon_longitude,
    moon_sun_delta,
    new_moon_after,
    new_moon_before,
    new_moon_at_lunation,
    format_new_moon_datetime,
    print_new_moons,
    SYNODIC_MONTH_DAYS,
    REF_NEW_MOON_JDE,
    pymeeus_moon_available,
)

__all__ = [
    "solar_longitude",
    "apparent_solar_longitude",
    "solar_longitude_rate",
    "solve_solar_longitude",
    "pymeeus_available",
    "nutation_longitude",
    "mean_obliquity",
    "true_obliquity",
    "solar_term_time",
    "solar_terms_of_year",
    "major_solar_terms_of_year",
    "term_longitude",
    "term_index_from_longitude",
    "term_name",
    "format_term_datetime",
    "print_year_terms",
    "SOLAR_TERM_NAMES_ZH",
    "SOLAR_TERM_NAMES_EN",
    "moon_longitude",
    "moon_sun_delta",
    "new_moon_after",
    "new_moon_before",
    "new_moon_at_lunation",
    "format_new_moon_datetime",
    "print_new_moons",
    "SYNODIC_MONTH_DAYS",
    "REF_NEW_MOON_JDE",
    "pymeeus_moon_available",
]
