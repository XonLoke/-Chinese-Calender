# data/cache.py — YearInfo 缓存系统
#
# 提供 YearInfo 数据结构和三层缓存策略：
#   Hot  (热) — 当前年 ±5 年，内存 LRU
#   Warm (温) — 1900-2100，JSON 文件持久化
#   Cold (冷) — 范围外年份，回退到实时天文计算
#
# YearInfo 存储一年的全部预计算数据，避免重复的天文计算。
# 典型场景：查询 2026-05-21 的农历日期 → 加载 2026 年缓存 →
# 直接读取月份结构，无需 5+ 次 Newton 求解。
#
# Reference:
#   Sprint 7: 缓存层 + 数据优化 (development_schedule.md)

from __future__ import annotations

import json
import os
import functools
from dataclasses import dataclass, field, asdict
from typing import Optional


# ===========================================================================
# 常数
# ===========================================================================

# 温缓存文件的默认路径（相对于 chinese_calendar 包根目录）
DEFAULT_CACHE_DIR: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "tables",
)
DEFAULT_CACHE_FILE: str = os.path.join(DEFAULT_CACHE_DIR, "year_cache.json")

# 热缓存的热度范围（当前年 ± 偏移年数）
HOT_RANGE: int = 5

# 温缓存覆盖的年份范围
WARM_YEAR_START: int = 1900
WARM_YEAR_END: int = 2100


# ===========================================================================
# YearInfo — 单年预计算数据
# ===========================================================================


@dataclass
class YearInfo:
    """某一年全部预计算数据的结构体。

    包含天文数据（节气时刻、朔日）和历法数据（农历月份结构）。
    所有时刻以 R.D. 浮点值（Moment.day）存储，避免 Moment 对象序列化问题。

    Fields:
        year:             公历年份。
        solar_terms:      24 节气时刻的 R.D. 浮点值列表 [24]。
        major_terms:      12 中气时刻的 R.D. 浮点值列表 [12]。
        new_moons:        该年所有新月的 R.D. 浮点值列表（约 12-13 个）。
        precomputed:      是否已完成预计算（True=来自缓存/预计算，
                          False=来自实时计算）。
    """
    year: int
    solar_terms: list[float] = field(default_factory=list)
    major_terms: list[float] = field(default_factory=list)
    new_moons: list[float] = field(default_factory=list)
    precomputed: bool = False

    # 以下字段在首次需要时延迟填充（由下游模块调用）
    # lunar_year_info 由 precompute 填充，包含该农历年的月份结构
    lunar_month_starts: list[float] = field(default_factory=list)
    lunar_month_numbers: list[int] = field(default_factory=list)
    lunar_leap_month: int = -1
    lunar_month_count: int = 0

    def has_lunar_info(self) -> bool:
        """是否已有农历月份结构数据。"""
        return len(self.lunar_month_starts) > 0

    def to_dict(self) -> dict:
        """序列化为字典（用于 JSON 存储）。"""
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> YearInfo:
        """从字典反序列化。"""
        return YearInfo(
            year=d["year"],
            solar_terms=d.get("solar_terms", []),
            major_terms=d.get("major_terms", []),
            new_moons=d.get("new_moons", []),
            precomputed=d.get("precomputed", False),
            lunar_month_starts=d.get("lunar_month_starts", []),
            lunar_month_numbers=d.get("lunar_month_numbers", []),
            lunar_leap_month=d.get("lunar_leap_month", -1),
            lunar_month_count=d.get("lunar_month_count", 0),
        )


# ===========================================================================
# CacheManager — 三层缓存管理器
# ===========================================================================


class CacheManager:
    """三层缓存管理器。

    用法:
        cm = CacheManager()
        info = cm.get(2026)  # 自动从热→温→冷逐层查找

    分层策略:
        Hot  — 字典缓存，最近访问的年份常驻内存
        Warm — JSON 文件，第一次读取时加载全部 1900-2100 数据到内存
        Cold — 返回 None，由调用方触发实时计算
    """

    def __init__(
        self,
        cache_file: str = DEFAULT_CACHE_FILE,
        hot_range: int = HOT_RANGE,
    ):
        self.cache_file: str = cache_file
        self.hot_range: int = hot_range

        # 热缓存：{year: YearInfo}
        self._hot_cache: dict[int, YearInfo] = {}

        # 温缓存：加载后驻留内存
        self._warm_cache: dict[int, YearInfo] = {}
        self._warm_loaded: bool = False

    # ------------------------------------------------------------------
    # 核心获取方法
    # ------------------------------------------------------------------

    def get(self, year: int) -> Optional[YearInfo]:
        """按年份获取缓存数据（热→温→冷）。

        Args:
            year: 公历年份。

        Returns:
            YearInfo 实例，如果冷数据则返回 None。
        """
        # 1. 热缓存
        if year in self._hot_cache:
            return self._hot_cache[year]

        # 2. 温缓存（按需加载）
        if WARM_YEAR_START <= year <= WARM_YEAR_END:
            self._ensure_warm_loaded()
            if year in self._warm_cache:
                info = self._warm_cache[year]
                # 提升到热缓存（最近访问）
                self._hot_cache[year] = info
                return info

        # 3. 冷数据 — 返回 None，由调用方实时计算
        return None

    def get_multi(self, years: list[int]) -> dict[int, Optional[YearInfo]]:
        """批量获取多年份缓存。

        Args:
            years: 公历年份列表。

        Returns:
            {year: YearInfo or None} 字典。
        """
        return {y: self.get(y) for y in years}

    # ------------------------------------------------------------------
    # 缓存填充
    # ------------------------------------------------------------------

    def put(self, info: YearInfo) -> None:
        """将 YearInfo 存入热缓存。

        Args:
            info: 预计算数据。
        """
        self._hot_cache[info.year] = info

    def put_warm_batch(self, infos: list[YearInfo]) -> None:
        """批量存入温缓存（用于预计算后的加载）。

        Args:
            infos: YearInfo 列表。
        """
        for info in infos:
            self._warm_cache[info.year] = info
        self._warm_loaded = True

    # ------------------------------------------------------------------
    # 温缓存持久化
    # ------------------------------------------------------------------

    def save_warm_cache(self, filepath: Optional[str] = None) -> None:
        """将温缓存保存到 JSON 文件。

        Args:
            filepath: JSON 文件路径（默认使用 self.cache_file）。
        """
        path = filepath or self.cache_file
        os.makedirs(os.path.dirname(path), exist_ok=True)

        data = {
            str(year): info.to_dict()
            for year, info in self._warm_cache.items()
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)

        # 同时更新热缓存
        for info in self._warm_cache.values():
            self._hot_cache[info.year] = info

    def load_warm_cache(self, filepath: Optional[str] = None) -> int:
        """从 JSON 文件加载温缓存。

        Args:
            filepath: JSON 文件路径（默认使用 self.cache_file）。

        Returns:
            加载的年份数量。
        """
        path = filepath or self.cache_file
        if not os.path.exists(path):
            return 0

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for year_str, info_dict in data.items():
            year = int(year_str)
            info = YearInfo.from_dict(info_dict)
            self._warm_cache[year] = info
            count += 1

        self._warm_loaded = True
        return count

    # ------------------------------------------------------------------
    # 缓存维护
    # ------------------------------------------------------------------

    def clear_hot(self) -> None:
        """清空热缓存（保留温缓存）。"""
        self._hot_cache.clear()

    def clear_all(self) -> None:
        """清空所有缓存。"""
        self._hot_cache.clear()
        self._warm_cache.clear()
        self._warm_loaded = False

    @property
    def hot_size(self) -> int:
        """热缓存条目数。"""
        return len(self._hot_cache)

    @property
    def warm_size(self) -> int:
        """温缓存条目数。"""
        return len(self._warm_cache)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _ensure_warm_loaded(self) -> None:
        """确保温缓存已从 JSON 加载。"""
        if not self._warm_loaded and os.path.exists(self.cache_file):
            self.load_warm_cache()

    def _prune_hot(self, current_year: int) -> None:
        """裁剪热缓存，仅保留 current_year ± hot_range 内的年份。

        Args:
            current_year: 当前参考年份。
        """
        keep_low = current_year - self.hot_range
        keep_high = current_year + self.hot_range
        self._hot_cache = {
            y: info for y, info in self._hot_cache.items()
            if keep_low <= y <= keep_high
        }


# ===========================================================================
# 全局默认缓存实例
# ===========================================================================

# 模块级单例，供全包共用
_default_cache: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """获取全局默认缓存实例。

    第一次调用时创建，后续复用。
    温缓存 JSON 文件在首次使用时按需加载。

    Returns:
        CacheManager 实例。
    """
    global _default_cache
    if _default_cache is None:
        _default_cache = CacheManager()
    return _default_cache


def set_cache(cache: CacheManager) -> None:
    """设置全局默认缓存实例（用于测试注入）。"""
    global _default_cache
    _default_cache = cache
