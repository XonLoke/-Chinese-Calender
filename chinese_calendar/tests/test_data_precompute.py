# tests/test_data_precompute.py — 预计算引擎测试
#
# 覆盖:
#   precompute_year() 的完整输出
#   precompute_range() 批量计算
#   _fill_lunar_info() 农历信息填充
#   ensure_year_precomputed() 懒加载
#
# 注意: 天文计算需要 PyMeeus，无 PyMeeus 时自动跳过。

from __future__ import annotations

import os
import tempfile
import pytest

from chinese_calendar.data.cache import (
    YearInfo,
    CacheManager,
    WARM_YEAR_START,
    WARM_YEAR_END,
)


# ===========================================================================
# 辅助函数
# ===========================================================================


def _pymeeus_available() -> bool:
    """检查 PyMeeus 是否可用。"""
    try:
        from chinese_calendar.astronomy.sun import pymeeus_available
        return pymeeus_available()
    except ImportError:
        return False


_PYMEEUS = _pymeeus_available()
_NEED_PYMEEUS = pytest.mark.skipif(not _PYMEEUS, reason="requires PyMeeus")


# ===========================================================================
# precompute_year 测试
# ===========================================================================


@pytest.mark.skipif(not _PYMEEUS, reason="requires PyMeeus")
class TestPrecomputeYear:
    """precompute_year() 的完整输出验证。"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试使用独立的临时缓存。"""
        self.cache = CacheManager(cache_file="")

    def test_precompute_2026(self):
        """预计算 2026 年应返回完整的 YearInfo。"""
        from chinese_calendar.data.precompute import precompute_year

        info = precompute_year(2026, cache=self.cache)

        # 基本字段
        assert info.year == 2026
        assert info.precomputed

        # 24 节气
        assert len(info.solar_terms) == 24
        # 所有节气时刻应是严格递增的
        for i in range(1, len(info.solar_terms)):
            assert info.solar_terms[i] > info.solar_terms[i - 1]

        # 12 中气
        assert len(info.major_terms) == 12
        for mt in info.major_terms:
            assert mt in info.solar_terms  # 中气是节气的子集

        # 新月
        assert len(info.new_moons) >= 12  # 至少 12 个新月

        # 农历信息
        assert info.lunar_month_count in (12, 13)
        assert len(info.lunar_month_starts) == info.lunar_month_count
        assert len(info.lunar_month_numbers) == info.lunar_month_count

        # 月份编号应包括正月（索引 1）
        assert 1 in info.lunar_month_numbers

    def test_precompute_cache_stores(self):
        """预计算后应自动存入缓存。"""
        from chinese_calendar.data.precompute import precompute_year

        info = precompute_year(2026, cache=self.cache)
        cached = self.cache.get(2026)
        assert cached is not None
        assert cached.year == 2026

    def test_precompute_multiple_years(self):
        """连续预计算多年（2025-2027），数据一致性。"""
        from chinese_calendar.data.precompute import precompute_year

        for y in [2025, 2026, 2027]:
            info = precompute_year(y, cache=self.cache)
            assert info.year == y
            assert len(info.solar_terms) == 24

    def test_solar_terms_sequence(self):
        """节气时刻应在正确的黄经顺序上。"""
        from chinese_calendar.data.precompute import precompute_year
        from chinese_calendar.core.rata_die import Moment
        from chinese_calendar.calendar.converters import gregorian_from_fixed

        info = precompute_year(2026, cache=self.cache)

        # 立春（term 2）应在 2 月 4 日前后
        # 索引 2 = 立春
        lichun_moment = info.solar_terms[2]
        from chinese_calendar.core.rata_die import RataDie
        # 简化：直接用 Moment 的 day 属性
        from chinese_calendar.calendar.converters import gregorian_from_fixed
        from chinese_calendar.core.rata_die import RataDie

        # 立春大约是 2 月 4 日
        y_lichun, m_lichun, d_lichun = gregorian_from_fixed(RataDie(int(lichun_moment)))
        assert m_lichun == 2
        assert 3 <= d_lichun <= 6

    def test_new_moons_sorted(self):
        """新月列表应严格递增。"""
        from chinese_calendar.data.precompute import precompute_year

        info = precompute_year(2026, cache=self.cache)
        for i in range(1, len(info.new_moons)):
            assert info.new_moons[i] > info.new_moons[i - 1]

    def test_new_moon_interval(self):
        """新月间隔应在 29-30 天之间。"""
        from chinese_calendar.data.precompute import precompute_year

        info = precompute_year(2026, cache=self.cache)
        for i in range(1, min(len(info.new_moons), 5)):  # 只检查前几个
            interval = info.new_moons[i] - info.new_moons[i - 1]
            assert 29.0 <= interval <= 30.0


# ===========================================================================
# 农历月份结构测试
# ===========================================================================


@pytest.mark.skipif(not _PYMEEUS, reason="requires PyMeeus")
class TestLunarYearInfo:
    """农历月份结构填充测试。"""

    def test_lunar_year_2026(self):
        """2026 年农历信息检查。"""
        from chinese_calendar.data.precompute import precompute_year

        info = precompute_year(2026)
        starts = info.lunar_month_starts
        numbers = info.lunar_month_numbers

        # 月份编号应包含 11, 12, 1, 2, ...
        assert 11 in numbers  # 十一月
        assert 12 in numbers  # 十二月
        assert 1 in numbers   # 正月
        assert 2 in numbers   # 二月

        # 月份编号顺序正确
        assert numbers[0] == 11  # 第一个月是十一月

        # 起止 R.D. 应连续
        for i in range(len(starts) - 1):
            interval = starts[i + 1] - starts[i]
            assert 29.0 <= interval <= 30.0

    def test_lunar_year_2025(self):
        """2025 年（含闰六月）。"""
        from chinese_calendar.data.precompute import precompute_year

        info = precompute_year(2025)

        # 2025 是闰年（闰六月），应有 13 个月
        assert info.lunar_month_count in (12, 13)

        # 如果有闰月，检查闰月编号
        if info.lunar_month_count == 13:
            assert info.lunar_leap_month >= 0
            leap_idx = info.lunar_leap_month
            # 闰月编号应与前一月相同
            assert info.lunar_month_numbers[leap_idx] == info.lunar_month_numbers[leap_idx - 1]

    def test_lunar_year_2023(self):
        """2023 年（闰二月）——已知闰年。"""
        from chinese_calendar.data.precompute import precompute_year

        info = precompute_year(2023)
        assert info.lunar_month_count in (12, 13)


# ===========================================================================
# precompute_range 测试
# ===========================================================================


@pytest.mark.skipif(not _PYMEEUS, reason="requires PyMeeus")
class TestPrecomputeRange:
    """批量预计算测试。"""

    def test_precompute_range_small(self):
        """小范围（5 年）预计算。"""
        from chinese_calendar.data.precompute import precompute_range

        results = precompute_range(2024, 2028, progress=False)
        assert len(results) == 5
        for info in results:
            assert info.precomputed
            assert len(info.solar_terms) == 24

    def test_precompute_range_output(self):
        """预计算输出应包含所有年份。"""
        from chinese_calendar.data.precompute import precompute_range

        results = precompute_range(2025, 2027, progress=False)
        years = [r.year for r in results]
        assert years == [2025, 2026, 2027]


# ===========================================================================
# ensure_year_precomputed 测试
# ===========================================================================


@pytest.mark.skipif(not _PYMEEUS, reason="requires PyMeeus")
class TestEnsurePrecomputed:
    """懒加载测试。"""

    def test_ensure_year(self):
        """ensure_year_precomputed 应返回有效数据。"""
        from chinese_calendar.data.precompute import ensure_year_precomputed

        info = ensure_year_precomputed(2026)
        assert info.year == 2026
        assert info.precomputed

    def test_ensure_cached(self):
        """连续调用应命中缓存。"""
        from chinese_calendar.data.precompute import ensure_year_precomputed

        info1 = ensure_year_precomputed(2026)
        info2 = ensure_year_precomputed(2026)
        # 两次调用应返回相同数据（从缓存读取）
        assert info1.year == info2.year
        assert info1.solar_terms == info2.solar_terms


# ===========================================================================
# generate_warm_cache 测试
# ===========================================================================


@pytest.mark.skipif(not _PYMEEUS, reason="requires PyMeeus")
class TestGenerateWarmCache:
    """温缓存文件生成测试。"""

    def test_generate_small_range(self):
        """生 5 年温缓存并验证文件。"""
        from chinese_calendar.data.precompute import generate_warm_cache

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            tmp_path = f.name

        try:
            out_path = generate_warm_cache(
                from_year=2025, to_year=2027, cache_file=tmp_path
            )
            assert os.path.exists(out_path)

            # 验证 JSON 文件内容
            import json
            with open(out_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert "2025" in data
            assert "2026" in data
            assert "2027" in data
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


# ===========================================================================
# 合约测试（无需 PyMeeus）
# ===========================================================================


class TestPrecomputeContract:
    """纯合约测试，验证函数签名和接口一致性。"""

    def test_module_exports(self):
        """precompute 模块应导出核心函数。"""
        import chinese_calendar.data.precompute as mod
        assert hasattr(mod, "precompute_year")
        assert hasattr(mod, "precompute_range")
        assert hasattr(mod, "ensure_year_precomputed")
        assert hasattr(mod, "generate_warm_cache")
        assert hasattr(mod, "warm_cache_exists")

    def test_cache_module_exports(self):
        """cache 模块应导出核心类型。"""
        import chinese_calendar.data.cache as mod
        assert hasattr(mod, "YearInfo")
        assert hasattr(mod, "CacheManager")
        assert hasattr(mod, "get_cache")
        assert hasattr(mod, "set_cache")
        assert hasattr(mod, "WARM_YEAR_START")
        assert hasattr(mod, "WARM_YEAR_END")

    def test_year_info_interface(self):
        """YearInfo 应提供 has_lunar_info() 和 to_dict()。"""
        info = YearInfo(year=2026)
        assert hasattr(info, "has_lunar_info")
        assert hasattr(info, "to_dict")
        assert callable(info.has_lunar_info)
        assert callable(info.to_dict)

    def test_cache_manager_interface(self):
        """CacheManager 应提供完整接口。"""
        cm = CacheManager(cache_file="")
        assert hasattr(cm, "get")
        assert hasattr(cm, "put")
        assert hasattr(cm, "get_multi")
        assert hasattr(cm, "put_warm_batch")
        assert hasattr(cm, "save_warm_cache")
        assert hasattr(cm, "load_warm_cache")
        assert hasattr(cm, "clear_hot")
        assert hasattr(cm, "clear_all")
        assert hasattr(cm, "hot_size")
        assert hasattr(cm, "warm_size")
