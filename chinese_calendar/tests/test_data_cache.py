# tests/test_data_cache.py — 缓存层测试
#
# 覆盖:
#   YearInfo 序列化/反序列化
#   CacheManager 三层缓存策略
#   温缓存 JSON 持久化
#   冷数据回退

from __future__ import annotations

import os
import tempfile
import json
import pytest

from chinese_calendar.data.cache import (
    YearInfo,
    CacheManager,
    get_cache,
    set_cache,
    WARM_YEAR_START,
    WARM_YEAR_END,
)


# ===========================================================================
# YearInfo 测试
# ===========================================================================


class TestYearInfo:
    """YearInfo 数据结构的创建、序列化、反序列化。"""

    def test_create_empty(self):
        """创建空 YearInfo。"""
        info = YearInfo(year=2026)
        assert info.year == 2026
        assert info.solar_terms == []
        assert not info.precomputed
        assert not info.has_lunar_info()

    def test_create_full(self):
        """创建完整 YearInfo。"""
        info = YearInfo(
            year=2026,
            solar_terms=[739750.0 + i * 15.0 for i in range(24)],
            major_terms=[739750.0 + i * 30.0 for i in range(12)],
            new_moons=[739750.0, 739779.5, 739809.0],
            precomputed=True,
            lunar_month_starts=[739800.0, 739830.0, 739860.0],
            lunar_month_numbers=[11, 12, 1],
            lunar_leap_month=-1,
            lunar_month_count=12,
        )
        assert info.precomputed
        assert info.has_lunar_info()
        assert info.lunar_month_count == 12

    def test_to_dict_and_from_dict(self):
        """字典序列化往返。"""
        info = YearInfo(
            year=2026,
            solar_terms=[1.0, 2.0],
            major_terms=[3.0],
            new_moons=[4.0, 5.0, 6.0],
            precomputed=True,
            lunar_month_starts=[10.0, 20.0],
            lunar_month_numbers=[11, 12],
            lunar_leap_month=-1,
            lunar_month_count=2,
        )
        d = info.to_dict()
        restored = YearInfo.from_dict(d)
        assert restored.year == 2026
        assert restored.solar_terms == [1.0, 2.0]
        assert restored.major_terms == [3.0]
        assert restored.new_moons == [4.0, 5.0, 6.0]
        assert restored.precomputed
        assert restored.lunar_month_numbers == [11, 12]
        assert restored.has_lunar_info()  # lunar_month_starts was preserved

    def test_from_dict_minimal(self):
        """从最小字典反序列化（只含 year）。"""
        d = {"year": 2025}
        info = YearInfo.from_dict(d)
        assert info.year == 2025
        assert info.solar_terms == []
        assert not info.precomputed

    def test_json_roundtrip(self):
        """JSON 序列化往返。"""
        info = YearInfo(
            year=2026,
            solar_terms=[1.0, 2.0, 3.0],
            precomputed=True,
        )
        json_str = json.dumps(info.to_dict())
        restored = YearInfo.from_dict(json.loads(json_str))
        assert restored.year == 2026
        assert restored.solar_terms == [1.0, 2.0, 3.0]


# ===========================================================================
# CacheManager 测试
# ===========================================================================


class TestCacheManager:
    """CacheManager 三层缓存策略测试。"""

    @pytest.fixture
    def cache(self):
        """创建一个没有持久化文件的缓存管理器。"""
        return CacheManager(cache_file="")  # 空路径 = 不加载温缓存

    @pytest.fixture
    def sample_info(self):
        """创建一个示例 YearInfo。"""
        return YearInfo(
            year=2026,
            solar_terms=[739750.0 + i for i in range(24)],
            precomputed=True,
        )

    def test_hot_cache_put_and_get(self, cache, sample_info):
        """热缓存：存入后能取出。"""
        cache.put(sample_info)
        result = cache.get(2026)
        assert result is not None
        assert result.year == 2026
        assert result.precomputed

    def test_hot_cache_miss_returns_none(self, cache):
        """热缓存：未命中返回 None。"""
        result = cache.get(1999)
        assert result is None

    def test_warm_cache_not_loaded_empty(self, cache):
        """温缓存：文件不存在时不加载。"""
        result = cache.get(2000)
        assert result is None  # 应走冷数据路径
        assert cache.warm_size == 0

    def test_warm_cache_save_and_load(self, cache, sample_info):
        """温缓存：保存到 JSON 后能重新加载。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            tmp_path = f.name
        try:
            # 保存温缓存
            cache.put_warm_batch([sample_info])
            cache.save_warm_cache(tmp_path)

            # 新建缓存管理器重新加载
            cache2 = CacheManager(cache_file=tmp_path)
            loaded = cache2.load_warm_cache()
            assert loaded >= 1

            result = cache2.get(2026)
            assert result is not None
            assert result.year == 2026
            assert result.solar_terms[0] == 739750.0
        finally:
            os.unlink(tmp_path)

    def test_warm_cache_promotes_to_hot(self, cache, sample_info):
        """温缓存数据在 get 后应提升到热缓存。"""
        # 先通过 put_warm_batch 模拟温缓存加载
        cache.put_warm_batch([sample_info])

        # get 应返回数据（温缓存命中）
        result = cache.get(2026)
        assert result is not None

        # 热缓存应有该条目
        assert cache.hot_size >= 1
        assert 2026 in cache._hot_cache

    def test_clear_hot(self, cache, sample_info):
        """清空热缓存不影响温缓存。"""
        cache.put(sample_info)
        assert cache.hot_size == 1

        cache.clear_hot()
        assert cache.hot_size == 0

    def test_clear_all(self, cache, sample_info):
        """清空全部缓存。"""
        cache.put_warm_batch([sample_info])
        cache.clear_all()
        assert cache.hot_size == 0
        assert cache.warm_size == 0

    def test_get_multi(self, cache):
        """批量获取多年份。"""
        infos = [
            YearInfo(year=2025, precomputed=True),
            YearInfo(year=2026, precomputed=True),
        ]
        cache.put_warm_batch(infos)

        results = cache.get_multi([2025, 2026, 2027])
        assert results[2025] is not None
        assert results[2026] is not None
        assert results[2027] is None  # 冷数据

    def test_hot_range_warm_years(self, cache):
        """温数据范围外的冷数据返回 None。"""
        # 1900-2100 是温数据范围
        # 1800 年应返回冷数据（None）
        result = cache.get(1800)
        assert result is None


# ===========================================================================
# 全局默认缓存测试
# ===========================================================================


class TestDefaultCache:
    """全局默认缓存实例测试。"""

    def teardown_method(self):
        """每个测试后重置全局缓存。"""
        set_cache(CacheManager(cache_file=""))

    def test_get_cache_returns_singleton(self):
        """get_cache 返回单例。"""
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2

    def test_set_cache_overrides(self):
        """set_cache 可以替换全局实例（用于测试注入）。"""
        cm = CacheManager(cache_file="test.json", hot_range=2)
        set_cache(cm)
        assert get_cache() is cm

    def test_cache_put_then_get(self):
        """全局缓存存取值。"""
        cache = get_cache()
        cache.put(YearInfo(year=2026, solar_terms=[1.0], precomputed=True))
        result = cache.get(2026)
        assert result is not None
        assert result.year == 2026
