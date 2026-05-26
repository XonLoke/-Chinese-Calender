# data/precompute.py — 批量预计算引擎
#
# 提供 precompute_year() 和 precompute_range()，一次性计算
# 某年（或某区间）的全部天文和历法数据。
#
# 预计算的数据流向：
#   astronomy 层          calendar 层              data 层
#   solar_terms_of_year ──→ major_terms (提取) ──→ YearInfo
#   new_moon_after     ──→ 全年朔日序列     ──→ YearInfo
#   winter_solstice    ──→ 农历月份结构     ──→ YearInfo.lunar_*
#
# 被预计算的函数原本各自独立做 Newton 求解。
# 预计算将它们合并为一次性的全年计算，结果存入 YearInfo 以供缓存。
#
# 参考:
#   Sprint 7: 缓存层 + 数据优化

from __future__ import annotations

import os
import logging
from typing import Optional

from ..core.rata_die import Moment
from ..astronomy.solar_terms import solar_terms_of_year
from ..astronomy.moon import new_moon_after, new_moon_before
from ..calendar.chinese import (
    winter_solstice_on_or_before,
    _new_moon_on_or_before,
    _has_major_solar_term,
    _assign_month_numbers,
)
from .cache import (
    YearInfo,
    CacheManager,
    get_cache,
    WARM_YEAR_START,
    WARM_YEAR_END,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# 预计算函数
# ===========================================================================


def precompute_year(year: int, cache: Optional[CacheManager] = None) -> YearInfo:
    """预计算指定公历年份的全部数据。

    一次调用会触发：
      - 24 节气计算（24 次 Newton 求解 → 合并）
      - 全年新月序列（约 13 次 Newton 求解）
      - 农历月份结构（依赖冬至定位）

    计算完成后自动存入缓存（如果提供）。

    Args:
        year:  公历年份。
        cache: 可选的缓存实例（存入缓存避免重复计算）。

    Returns:
        包含全年数据的 YearInfo 实例。

    Raises:
        ImportError: 如果 PyMeeus 未安装。
    """
    # ---------------------------------------------------------------
    # 1. 节气数据
    # ---------------------------------------------------------------

    # 一次性计算全年 24 节气（内部做 24 次 Newton 求解）
    term_moments = solar_terms_of_year(year)

    # 提取 12 个中气（春分/谷雨/小满/夏至/大暑/处暑/秋分/霜降/小雪/冬至/大寒/雨水）
    # 中气索引: 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 1, 3
    major_term_indices = [5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 1, 3]
    major_terms = [term_moments[i].day for i in major_term_indices]

    info = YearInfo(
        year=year,
        solar_terms=[m.day for m in term_moments],
        major_terms=major_terms,
        precomputed=True,
    )

    # ---------------------------------------------------------------
    # 2. 新月数据
    # ---------------------------------------------------------------

    # 找该年的新月序列：
    #   从该年第一个节气前一个新月开始，到该年最后一个节气后一个新月
    first_term_rd = term_moments[0].day
    last_term_rd = term_moments[-1].day

    # 从第一个节气前推一个新月
    nm = new_moon_before(Moment(first_term_rd + 0.1))
    new_moons: list[float] = [nm.day]

    # 连续收集新月，直到该年最后一个节气之后
    while nm.day < last_term_rd + 35.0:
        nm = new_moon_after(nm)
        new_moons.append(nm.day)

    info.new_moons = new_moons

    # ---------------------------------------------------------------
    # 3. 农历月份结构
    # ---------------------------------------------------------------

    _fill_lunar_info(info)

    # ---------------------------------------------------------------
    # 4. 存入缓存
    # ---------------------------------------------------------------

    if cache is not None:
        cache.put(info)

    return info


def precompute_range(
    from_year: int,
    to_year: int,
    cache: Optional[CacheManager] = None,
    progress: bool = True,
) -> list[YearInfo]:
    """预计算一个年份范围的全年数据。

    用于批量生成 1900-2100 温缓存。

    Args:
        from_year: 起始年份（含）。
        to_year:   结束年份（含）。
        cache:     可选的缓存实例。
        progress:  是否打印进度信息。

    Returns:
        YearInfo 列表。

    Raises:
        ImportError: 如果 PyMeeus 未安装。
    """
    results: list[YearInfo] = []
    total = to_year - from_year + 1

    for i, year in enumerate(range(from_year, to_year + 1)):
        info = precompute_year(year, cache=cache)
        results.append(info)

        if progress and (i + 1) % 50 == 0:
            print(f"  precompute_range: {i + 1}/{total} years done...")

    if progress:
        print(f"  precompute_range: {total}/{total} years done.")

    return results


# ===========================================================================
# 农历月份结构填充
# ===========================================================================


def _fill_lunar_info(info: YearInfo) -> None:
    """填充 YearInfo 中的农历月份结构数据。

    从公历年份的冬至定位开始，找到农历年的月份结构
    （朔日序列、月份编号、闰月信息）。

    本函数修改 info 对象，不返回值。

    Args:
        info: 待填充的 YearInfo（year 必须有效）。
    """
    year = info.year

    # 农历年 N 的月份结构由公历 N-1 年的冬至决定
    # 冬至约在 12 月 21-23 日

    # 找到公历 year-1 年冬至之后的十一月朔日
    from ..calendar.converters import fixed_from_gregorian
    approx_rd = fixed_from_gregorian(year - 1, 12, 22)
    s1 = winter_solstice_on_or_before(approx_rd)
    s2 = winter_solstice_on_or_before(Moment(s1.day + 370.0))

    m11 = _new_moon_on_or_before(s1)
    m11_next = _new_moon_on_or_before(s2)

    if m11_next.day <= m11.day:
        s2 = winter_solstice_on_or_before(Moment(s2.day + 370.0))
        m11_next = _new_moon_on_or_before(s2)

    # 收集从十一月到十月（或闰十月）的所有朔日
    from ..astronomy.moon import new_moon_after as _nma

    month_starts: list[Moment] = [m11]
    while True:
        next_nm = _nma(month_starts[-1])
        if next_nm.day >= m11_next.day - 1e-6:
            break
        month_starts.append(next_nm)

    n_months = len(month_starts)

    # 闰月判定
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

    # 写入 YearInfo
    info.lunar_month_starts = [ms.day for ms in month_starts]
    info.lunar_month_numbers = month_numbers
    info.lunar_leap_month = leap_month
    info.lunar_month_count = n_months


# ===========================================================================
# 便捷函数
# ===========================================================================


def ensure_year_precomputed(
    year: int,
    cache: Optional[CacheManager] = None,
) -> YearInfo:
    """确保某年已被预计算（缓存命中则跳过，否则实时计算）。

    Args:
        year:  公历年份。
        cache: 缓存实例（默认使用全局缓存）。

    Returns:
        YearInfo 实例。
    """
    cm = cache or get_cache()

    # 查缓存
    cached = cm.get(year)
    if cached is not None and cached.precomputed:
        return cached

    # 未命中 → 实时预计算并放入缓存
    info = precompute_year(year, cache=cm)
    if cm.get(year) is None:
        cm.put(info)
    return info


def generate_warm_cache(
    from_year: int = WARM_YEAR_START,
    to_year: int = WARM_YEAR_END,
    cache_file: Optional[str] = None,
) -> str:
    """生成温缓存 JSON 文件（1900-2100 全量预计算）。

    Args:
        from_year:  起始年份（默认 1900）。
        to_year:    结束年份（默认 2100）。
        cache_file: 输出 JSON 路径（默认 data/tables/year_cache.json）。

    Returns:
        JSON 文件路径。

    Raises:
        ImportError: 如果 PyMeeus 未安装。
    """
    from ..data.cache import DEFAULT_CACHE_FILE

    cache = CacheManager()
    out_path = cache_file or DEFAULT_CACHE_FILE

    print(f"Precomputing {from_year}-{to_year}...")
    results = precompute_range(from_year, to_year, cache=cache)

    # 保存到温缓存
    cache.put_warm_batch(results)
    cache.save_warm_cache(out_path)

    print(f"Warm cache saved: {out_path}")
    print(f"  {len(results)} years, "
          f"{sum(1 for r in results if r.lunar_month_count > 0)} with lunar data.")

    return out_path


def warm_cache_exists(cache_file: Optional[str] = None) -> bool:
    """检查温缓存文件是否存在。

    Args:
        cache_file: 路径（默认 DEFAULT_CACHE_FILE）。

    Returns:
        True 如果文件存在。
    """
    from ..data.cache import DEFAULT_CACHE_FILE
    return os.path.exists(cache_file or DEFAULT_CACHE_FILE)
