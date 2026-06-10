# data/hko_cache.py — 香港天文台农历缓存查询
#
# 从 HKO 数据库导出的 JSON 缓存，覆盖 1901-2100 全部农历日期。
# 当 HKO 缓存存在时优先使用，保证 100% 准确率。
# 回退到 D&R 算法（用于 HKO 范围外的日期）。

from __future__ import annotations
import json
import os
from typing import Optional

_cache: Optional[dict] = None


def _load_cache() -> Optional[dict]:
    """加载 HKO 缓存到内存。"""
    global _cache
    if _cache is not None:
        return _cache
    cache_path = os.path.join(os.path.dirname(__file__), "hko_cache.json")
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            _cache = json.load(f)
        return _cache
    except Exception:
        return None


def hko_lookup(rd: str) -> Optional[tuple[int, int, int, bool]]:
    """查询指定 RD 的农历日期。

    Args:
        rd: R.D. 整数的字符串形式。

    Returns:
        (year, month, day, is_leap) 元组，如果不在缓存中则返回 None。
    """
    cache = _load_cache()
    if cache is None:
        return None
    entry = cache.get(rd)
    if entry is None:
        return None
    return (entry[0], entry[1], entry[2], entry[3])
