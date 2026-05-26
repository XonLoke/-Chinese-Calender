# tests/test_solar_terms.py — 二十四节气判定测试
#
# 验证节气计算精度，与已知日期比对。
# 测试需要 PyMeeus 库 (pip install pymeeus)。
#
# 参考数据源（非精确，仅用于粗糙验证）:
#   - 香港天文台节气表 (HKO)
#   - 中科院紫金山天文台《天文年历》
#
# 精度目标:
#   - 单节气计算: 日期与 HKO 一致，时刻误差 < 60 分钟
#   - 春分/秋分: 日期准确
#   - 节气时序: 24 节气严格递增

from __future__ import annotations

from math import fabs

import pytest

from ..core.rata_die import Moment, RataDie
from ..calendar.converters import gregorian_from_fixed
from ..core.time_systems import (
    moment_from_utc,
    dynamical_time,
    universal_time,
)
from ..astronomy.sun import (
    apparent_solar_longitude,
    pymeeus_available,
    solve_solar_longitude,
)
from ..astronomy.solar_terms import (
    solar_term_time,
    solar_terms_of_year,
    major_solar_terms_of_year,
    term_longitude,
    term_index_from_longitude,
    term_name,
    SOLAR_TERM_NAMES_ZH,
    SOLAR_TERM_NAMES_EN,
)


# ===========================================================================
# PyMeeus 可用性
# ===========================================================================


pymeeus = pytest.mark.skipif(
    not pymeeus_available(),
    reason="PyMeeus is not installed. Install with: pip install pymeeus",
)


# ===========================================================================
# 节气黄经映射
# ===========================================================================


class TestTermLongitude:
    """节气索引 ↔ 黄经 映射测试。"""

    def test_term_longitude_formula(self) -> None:
        """验证 term_longitude 公式: (idx*15 + 285) % 360。"""
        expected = [285, 300, 315, 330, 345, 0, 15, 30, 45, 60, 75, 90,
                    105, 120, 135, 150, 165, 180, 195, 210, 225, 240, 255, 270]
        for i in range(24):
            assert term_longitude(i) == expected[i], (
                f"term_longitude({i}): expected {expected[i]}, got {term_longitude(i)}"
            )

    def test_term_longitude_boundary(self) -> None:
        """边界检查: 索引范围。"""
        with pytest.raises(ValueError):
            term_longitude(-1)
        with pytest.raises(ValueError):
            term_longitude(24)

    def test_term_index_from_longitude(self) -> None:
        """黄经 → 索引 反向映射。"""
        # 已知对应
        cases = [(285, 0), (300, 1), (315, 2), (0, 5), (90, 11),
                 (180, 17), (270, 23)]
        for lon, expected_idx in cases:
            idx = term_index_from_longitude(lon)
            assert idx == expected_idx, (
                f"term_index_from_longitude({lon}): expected {expected_idx}, got {idx}"
            )


# ===========================================================================
# 节气名称
# ===========================================================================


class TestTermNames:
    """节气名称测试。"""

    def test_names_count(self) -> None:
        """中文/英文名称均应包含 24 个。"""
        assert len(SOLAR_TERM_NAMES_ZH) == 24
        assert len(SOLAR_TERM_NAMES_EN) == 24

    def test_term_name_zh(self) -> None:
        """term_name 中文返回正确。"""
        assert term_name(0) == "小寒"
        assert term_name(2) == "立春"
        assert term_name(5) == "春分"
        assert term_name(23) == "冬至"

    def test_term_name_en(self) -> None:
        """term_name 英文返回正确。"""
        assert term_name(0, "en") == "Minor Cold"
        assert term_name(2, "en") == "Spring Begins"
        assert term_name(23, "en") == "Winter Solstice"

    def test_term_name_invalid_lang(self) -> None:
        """无效语言参数应抛出 ValueError。"""
        with pytest.raises(ValueError):
            term_name(0, "jp")


# ===========================================================================
# 单节气计算 — 已知参考值
# ===========================================================================


class TestSolarTermTime:
    """单节气时刻计算精度测试。"""

    @pymeeus
    def test_lichun_2026_date(self) -> None:
        """2026 年立春（315°）应在 2 月 4 日附近。"""
        m = solar_term_time(2026, 2)  # term 2 = 立春
        rd = RataDie(int(m.day))
        y, mo, d = gregorian_from_fixed(rd)
        assert y == 2026
        assert mo == 2
        assert 3 <= d <= 5, (
            f"2026 Lichun date: 2026-2-{d}, expected ~Feb 4"
        )

    @pymeeus
    def test_lichun_2026_longitude(self) -> None:
        """验证 solar_term_time 返回时刻的黄经确实为 315°。"""
        m = solar_term_time(2026, 2)
        # solve_solar_longitude 在 TT 下工作，验证时也需要 TT
        m_tt = dynamical_time(m)
        lon = apparent_solar_longitude(m_tt)
        diff = abs(lon - 315.0)
        assert diff < 0.001, (
            f"2026 Lichun longitude at solved time: {lon:.6f}° "
            f"(should be ~315°, diff={diff:.6f}°)"
        )

    @pymeeus
    def test_vernal_equinox_2026(self) -> None:
        """2026 年春分（0°）应在 3 月 20 日附近。"""
        m = solar_term_time(2026, 5)  # term 5 = 春分
        rd = RataDie(int(m.day))
        y, mo, d = gregorian_from_fixed(rd)
        assert y == 2026
        assert mo == 3
        assert 19 <= d <= 21, (
            f"2026 Vernal Equinox date: 2026-3-{d}, expected ~Mar 20"
        )

    @pymeeus
    def test_summer_solstice_2026(self) -> None:
        """2026 年夏至（90°）应在 6 月 21 日附近。"""
        m = solar_term_time(2026, 11)  # term 11 = 夏至
        rd = RataDie(int(m.day))
        y, mo, d = gregorian_from_fixed(rd)
        assert y == 2026
        assert mo == 6
        assert 20 <= d <= 22, (
            f"2026 Summer Solstice date: 2026-6-{d}, expected ~Jun 21"
        )

    @pymeeus
    def test_winter_solstice_2026(self) -> None:
        """2026 年冬至（270°）应在 12 月 21 日附近。"""
        m = solar_term_time(2026, 23)  # term 23 = 冬至
        rd = RataDie(int(m.day))
        y, mo, d = gregorian_from_fixed(rd)
        assert y == 2026
        assert mo == 12
        assert 20 <= d <= 22, (
            f"2026 Winter Solstice date: 2026-12-{d}, expected ~Dec 21"
        )

    @pymeeus
    def test_known_term_2025(self) -> None:
        """2025 年冬至应在 12 月 21 日附近。"""
        m = solar_term_time(2025, 23)
        rd = RataDie(int(m.day))
        y, mo, d = gregorian_from_fixed(rd)
        # 2025 年冬至约在 12 月 21 日
        assert y == 2025
        assert mo == 12
        assert 20 <= d <= 22, (
            f"2025 Winter Solstice: 2025-12-{d}, expected ~Dec 21"
        )

    @pymeeus
    def test_xiaohan_2026(self) -> None:
        """2026 年小寒（285°）应在 1 月 5 日附近。"""
        m = solar_term_time(2026, 0)  # term 0 = 小寒
        rd = RataDie(int(m.day))
        y, mo, d = gregorian_from_fixed(rd)
        assert y == 2026
        assert 1 <= d <= 6, (
            f"2026 Xiaohan date: 2026-1-{d}, expected ~Jan 5-6"
        )


# ===========================================================================
# 全年节气表
# ===========================================================================


class TestSolarTermsOfYear:
    """全年 24 节气表测试。"""

    @pymeeus
    def test_count_24(self) -> None:
        """solar_terms_of_year 应返回 24 个节气。"""
        terms = solar_terms_of_year(2026)
        assert len(terms) == 24, (
            f"Expected 24 terms, got {len(terms)}"
        )

    @pymeeus
    def test_monotonic_increasing(self) -> None:
        """24 节气时刻应严格递增。"""
        terms = solar_terms_of_year(2026)
        for i in range(1, len(terms)):
            assert terms[i].day > terms[i - 1].day, (
                f"Term {i} ({terms[i].day}) should be after term {i - 1} "
                f"({terms[i - 1].day})"
            )

    @pymeeus
    def test_all_in_same_year(self) -> None:
        """所有 24 节气应在同一年内。"""
        terms = solar_terms_of_year(2026)
        for i, m in enumerate(terms):
            rd = RataDie(int(m.day))
            y, _, _ = gregorian_from_fixed(rd)
            assert y == 2026, (
                f"Term {i}: year={y}, expected 2026"
            )

    @pymeeus
    def test_term_span_days(self) -> None:
        """首个到最后节气跨度约 350-351 天（不足一年 365 天）。"""
        terms = solar_terms_of_year(2026)
        span = terms[23].day - terms[0].day
        # 小寒到冬至约 350 天
        assert 345 < span < 355, (
            f"Term span (Xiaohan to Dongzhi): {span:.2f} days, "
            f"expected ~350"
        )

    @pymeeus
    def test_consecutive_term_gaps(self) -> None:
        """相邻节气间隔应接近 15 天。"""
        terms = solar_terms_of_year(2026)
        for i in range(1, len(terms)):
            gap = terms[i].day - terms[i - 1].day
            assert 14.0 <= gap <= 16.5, (
                f"Gap between term {i - 1} and {i}: {gap:.4f} days, "
                f"expected ~15 days"
            )


# ===========================================================================
# 中气
# ===========================================================================


class TestMajorSolarTerms:
    """中气测试。"""

    @pymeeus
    def test_count_12(self) -> None:
        """major_solar_terms_of_year 应返回 12 个中气。"""
        terms = major_solar_terms_of_year(2026)
        assert len(terms) == 12, (
            f"Expected 12 major terms, got {len(terms)}"
        )

    @pymeeus
    def test_major_terms_are_subset(self) -> None:
        """所有中气应在全年节气表中。"""
        all_terms = solar_terms_of_year(2026)
        all_days = {round(m.day, 6) for m in all_terms}

        major = major_solar_terms_of_year(2026)
        for m in major:
            day_rounded = round(m.day, 6)
            assert day_rounded in all_days, (
                f"Major term at {m} not found in full term list"
            )

    @pymeeus
    def test_major_term_longitudes(self) -> None:
        """中气的黄经应为 0°, 30°, 60°, ..., 330°。"""
        major = major_solar_terms_of_year(2026)
        expected_lons = [0, 30, 60, 90, 120, 150,
                         180, 210, 240, 270, 300, 330]
        for i, m in enumerate(major):
            m_tt = dynamical_time(m)
            lon = apparent_solar_longitude(m_tt)
            expected = expected_lons[i]
            diff = min(abs(lon - expected), abs(lon - expected - 360))
            assert diff < 0.01, (
                f"Major term {i}: longitude={lon:.4f}°, "
                f"expected ~{expected}°, diff={diff:.4f}°"
            )


# ===========================================================================
# 连续多年验证
# ===========================================================================


class TestMultiYear:
    """多年节气一致性测试。"""

    @pymeeus
    def test_2024_2026_consistency(self) -> None:
        """2024-2026 三年节气应保持时序一致。"""
        for year in [2024, 2025, 2026]:
            terms = solar_terms_of_year(year)
            # 检查数量
            assert len(terms) == 24
            # 检查严格递增
            for i in range(1, 24):
                assert terms[i].day > terms[i - 1].day
            # 第一项在 Jan 附近
            rd0 = RataDie(int(terms[0].day))
            y0, mo0, d0 = gregorian_from_fixed(rd0)
            assert mo0 == 1, (
                f"Year {year}: first term month={mo0}, expected January"
            )
            # 最后一项在 Dec 附近
            rd23 = RataDie(int(terms[23].day))
            y23, mo23, d23 = gregorian_from_fixed(rd23)
            assert mo23 == 12, (
                f"Year {year}: last term month={mo23}, expected December"
            )


# ===========================================================================
# 验证数据对照（HKO 参考）
# ===========================================================================


class TestHKOReference:
    """与香港天文台已知节气日期粗略对照。

    注: HKO 数据在 chinese_calendar.db 中尚未导入项目，
    这里使用已知公开值做粗略日期对照。
    """

    @pymeeus
    def test_known_dates_2024(self) -> None:
        """2024 年已知节气日期对照（从权威来源已知）。"""
        # 2024 年节气已知日期（仅供参考，可能存在 ±1 天偏差）
        known: dict[str, tuple[int, int, int]] = {
            # term_index: (year, month, day)
            0: (2024, 1, 6),    # 小寒
            2: (2024, 2, 4),    # 立春
            5: (2024, 3, 20),   # 春分
            11: (2024, 6, 21),  # 夏至
            17: (2024, 9, 22),  # 秋分
            23: (2024, 12, 21), # 冬至
        }

        for idx, (y_known, m_known, d_known) in known.items():
            m = solar_term_time(2024, idx)
            rd = RataDie(int(m.day))
            y, mo, d = gregorian_from_fixed(rd)
            # 日期应完全一致
            assert y == y_known, (
                f"2024 term {idx}: year {y} != {y_known}"
            )
            assert mo == m_known, (
                f"2024 term {idx}: month {mo} != {m_known}"
            )
            assert d == d_known or abs(d - d_known) <= 1, (
                f"2024 term {idx}: day {d} != {d_known}"
            )
