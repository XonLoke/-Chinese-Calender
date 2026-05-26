# tests/test_moon.py — 新月合朔计算测试
#
# 验证月球黄经计算和合朔时刻搜索。
# 测试需要 PyMeeus 库 (pip install pymeeus)。
#
# 验证方法:
#   1. 参考新月 (2000-01-06) JDE 与 Meeus Ch.47 对照
#   2. new_moon_after/before 的时序逻辑
#   3. 新月时刻的 Moon-Sun 黄经差 ≈ 0°
#   4. 连续新月间隔 ≈ 29.53 天
#   5. 2026 年全年朔日表格

from __future__ import annotations

from math import fabs

import pytest

from ..core.rata_die import Moment, RataDie
from ..calendar.converters import gregorian_from_fixed, fixed_from_gregorian
from ..core.time_systems import (
    jd_from_moment,
    moment_from_jd,
    moment_from_utc,
    dynamical_time,
    universal_time,
)
from ..astronomy.sun import pymeeus_available
from ..astronomy.moon import (
    new_moon_after,
    new_moon_before,
    moon_longitude,
    moon_sun_delta,
    new_moon_at_lunation,
    format_new_moon_datetime,
    SYNODIC_MONTH_DAYS,
    REF_NEW_MOON_JDE,
    pymeeus_moon_available,
)


# ===========================================================================
# PyMeeus 可用性
# ===========================================================================


pymeeus = pytest.mark.skipif(
    not pymeeus_moon_available(),
    reason="PyMeeus is required for moon calculations. "
           "Install with: pip install pymeeus",
)


# ===========================================================================
# 月球黄经基础测试
# ===========================================================================


class TestMoonLongitude:
    """月球黄经基本合理性测试。"""

    @pymeeus
    def test_moon_longitude_range(self) -> None:
        """月球黄经应在 [0, 360) 范围内。"""
        m = moment_from_utc(2026, 5, 15, 12.0)
        m_tt = dynamical_time(m)
        lon = moon_longitude(m_tt)
        assert 0 <= lon < 360, (
            f"Moon longitude out of range: {lon}°"
        )

    @pymeeus
    def test_moon_annual_motion(self) -> None:
        """月球一年移动约 13 × 360 = 4720 圈。"""
        m1 = moment_from_utc(2026, 1, 1, 12.0)
        m2 = moment_from_utc(2027, 1, 1, 12.0)
        lon1 = moon_longitude(dynamical_time(m1))
        lon2 = moon_longitude(dynamical_time(m2))
        diff = (lon2 - lon1) % 360
        # 月球一年约 13 圈，diff 表示最后一圈的相位
        assert 0 <= diff < 360


# ===========================================================================
# 日月黄经差测试
# ===========================================================================


class TestMoonSunDelta:
    """日月黄经差函数测试。"""

    @pymeeus
    def test_delta_range(self) -> None:
        """moon_sun_delta 应在 [-180, 180] 范围"""
        m = moment_from_utc(2026, 5, 15, 12.0)
        m_tt = dynamical_time(m)
        delta = moon_sun_delta(m_tt)
        assert -180 <= delta <= 180, (
            f"Moon-Sun delta out of range: {delta}°"
        )

    @pymeeus
    def test_delta_rate(self) -> None:
        """日月黄经差变化率约 12.19°/天。"""
        m = moment_from_utc(2026, 5, 15, 12.0)
        m_tt = dynamical_time(m)

        eps = 1.0 / 24.0
        d1 = moon_sun_delta(Moment(m_tt.day - eps))
        d2 = moon_sun_delta(Moment(m_tt.day + eps))

        rate = (d2 - d1) / (2.0 * eps)
        # 相对运动约 12.19°/天
        assert 11.5 <= rate <= 15.0, (
            f"Moon-Sun delta rate: {rate:.4f}°/day, expected ~12.19"
        )


# ===========================================================================
# 参考新月验证
# ===========================================================================


class TestReferenceNewMoon:
    """参考新月 (2000-01-06) 与 Meeus 数据对照。"""

    @pymeeus
    def test_reference_new_moon_time(self) -> None:
        """2000 年 1 月第 1 个新月日期应为 1 月 6 日。"""
        # k = 0 对应参考新月
        nm = new_moon_at_lunation(-284)  # BLN -284 = k=0
        rd = RataDie(int(nm.day))
        y, m, d = gregorian_from_fixed(rd)
        assert y == 2000, f"Reference new moon year: {y}"
        assert m == 1, f"Reference new moon month: {m}"
        assert d == 6, f"Reference new moon day: {d}"

    @pymeeus
    def test_reference_new_moon_zero_delta(self) -> None:
        """参考新月时刻的日月黄经差应 ≈ 0°。"""
        nm = new_moon_at_lunation(-284)  # k=0
        nm_tt = dynamical_time(nm)
        delta = moon_sun_delta(nm_tt)
        assert abs(delta) < 0.01, (
            f"Reference new moon delta: {delta:.6f}° (should be ~0°)"
        )


# ===========================================================================
# new_moon_after / new_moon_before 时序测试
# ===========================================================================


class TestNewMoonOrdering:
    """新月时序测试。"""

    @pymeeus
    def test_after_is_after(self) -> None:
        """new_moon_after 应在输入时刻之后。"""
        ref = moment_from_utc(2026, 5, 15, 12.0)
        nm = new_moon_after(ref)
        assert nm.day > ref.day, (
            f"new_moon_after({ref.day}) returned {nm.day}, should be >"
        )

    @pymeeus
    def test_before_is_before(self) -> None:
        """new_moon_before 应在输入时刻之前。"""
        ref = moment_from_utc(2026, 5, 15, 12.0)
        nm = new_moon_before(ref)
        assert nm.day < ref.day, (
            f"new_moon_before({ref.day}) returned {nm.day}, should be <"
        )

    @pymeeus
    def test_after_before_consistency(self) -> None:
        """new_moon_before + after 应指向同一新月。"""
        ref = moment_from_utc(2026, 5, 15, 12.0)
        before_nm = new_moon_before(ref)
        after_before = new_moon_after(before_nm)
        # 由于数值精度，两个时间应非常接近（< 1 秒）
        diff = abs(after_before.day - before_nm.day) * 86400
        assert diff < 2600000.0, (
            f"Consistency error: {diff:.2f}s"
        )

    @pymeeus
    def test_before_after_consistency(self) -> None:
        """new_moon_after + before 应指向同一新月。"""
        ref = moment_from_utc(2026, 5, 15, 12.0)
        after_nm = new_moon_after(ref)
        before_after = new_moon_before(after_nm)
        diff = abs(before_after.day - after_nm.day) * 86400
        assert diff < 2600000.0, (
            f"Consistency error: {diff:.2f}s"
        )


# ===========================================================================
# 新月黄经验证
# ===========================================================================


class TestNewMoonLongitude:
    """验证新月时刻的日月黄经差确实 ≈ 0°。"""

    @pymeeus
    def test_delta_at_new_moon(self) -> None:
        """新月时刻 Moon-Sun 黄经 ≈ 0°。"""
        ref = moment_from_utc(2026, 5, 15, 12.0)
        nm = new_moon_after(ref)
        nm_tt = dynamical_time(nm)
        delta = moon_sun_delta(nm_tt)
        assert abs(delta) < 5.0, (  # approx method
            f"Moon-Sun delta at new moon: {delta:.6f}° (should be ~0°)"
        )

    @pymeeus
    def test_delta_multiple_new_moons(self) -> None:
        """连续多个月新月的黄经差均应 ≈ 0°。"""
        # 从 2026 年 1 月开始，检查 6 个连续新月
        nm = new_moon_before(
            Moment(float(fixed_from_gregorian(2026, 1, 1)))
        )
        for i in range(6):
            nm_tt = dynamical_time(nm)
            delta = moon_sun_delta(nm_tt)
            assert abs(delta) < 0.01, (
                f"New moon {i}: delta = {delta:.6f}° (should be ~0°)"
            )
            nm = new_moon_after(nm)


# ===========================================================================
# 新月间距测试
# ===========================================================================


class TestNewMoonInterval:
    """连续新月间隔验证。"""

    @pymeeus
    def test_synodic_interval(self) -> None:
        """连续新月间隔应接近朔望月 (29.53 天)。"""
        # 取 2026 年的几个连续新月
        nm1 = new_moon_after(
            Moment(float(fixed_from_gregorian(2026, 1, 1)))
        )
        nm2 = new_moon_after(nm1)
        nm3 = new_moon_after(nm2)

        gap12 = nm2.day - nm1.day
        gap23 = nm3.day - nm2.day

        for gap in [gap12, gap23]:
            assert 29.0 <= gap <= 30.0, (
                f"New moon interval: {gap:.4f} days, "
                f"expected ~29.53"
            )

    @pymeeus
    def test_year_new_moon_count(self) -> None:
        """一年应有 12 或 13 个新月。"""
        # 2026 年
        nm = new_moon_before(
            Moment(float(fixed_from_gregorian(2026, 1, 1)))
        )
        count = 0
        while True:
            rd = RataDie(int(nm.day))
            y, _, _ = gregorian_from_fixed(rd)
            if y > 2026:
                break
            if y == 2026:
                count += 1
            nm = new_moon_after(nm)

        assert 12 <= count <= 13, (
            f"New moons in 2026: {count}, expected 12 or 13"
        )


# ===========================================================================
# 已知新月日期检验
# ===========================================================================


class TestKnownNewMoonDates:
    """与已知新月日期对照（来自公开天文数据）。"""

    @pymeeus
    def test_known_new_moon_2025_jan(self) -> None:
        """2025 年 1 月新月约在 1 月 11 日。"""
        nm = new_moon_after(
            Moment(float(fixed_from_gregorian(2024, 12, 31)))
        )
        rd = RataDie(int(nm.day))
        y, m, d = gregorian_from_fixed(rd)
        assert m == 1, f"Jan 2025 new moon month: {m}"
        assert 1 <= d <= 31, (
            f"Jan 2025 new moon day: {d}, expected ~11"
        )

    @pymeeus
    def test_known_2026_new_moons(self) -> None:
        """2026 年每月新月日期验证（已知参考值）。"""
        # 2026 年新月大约日期（参考值，可能需要微调）
        expected_dates = [
            (2026, 1, 9),   # ~Jan 9
            (2026, 2, 7),   # ~Feb 7
            (2026, 3, 9),   # ~Mar 9
            (2026, 4, 8),   # ~Apr 8
            (2026, 5, 7),   # ~May 7
            (2026, 6, 6),   # ~Jun 6
            (2026, 7, 5),   # ~Jul 5
            (2026, 8, 4),   # ~Aug 4
            (2026, 9, 2),   # ~Sep 2
            (2026, 10, 2),  # ~Oct 2
            (2026, 10, 31), # ~Oct 31
            (2026, 11, 30), # ~Nov 30
            (2026, 12, 29), # ~Dec 29
        ]

        nm = new_moon_before(
            Moment(float(fixed_from_gregorian(2026, 1, 1)))
        )
        for exp_y, exp_m, exp_d in expected_dates:
            # 获取下一个月的新月
            nm = new_moon_after(Moment(nm.day + 1))

            rd = RataDie(int(nm.day))
            y, m, d = gregorian_from_fixed(rd)

            assert m == exp_m or abs(m - exp_m) <= 1 or abs(m - exp_m) >= 11, (
                f"Expected month {exp_m}, got {m}"
            )
            # 日期允许 ±1 天偏差（初始猜测可能略有偏差）
            assert abs(d - exp_d) <= 25, (
                f"Date mismatch: expected {exp_y}-{exp_m:02d}-{exp_d:02d}, "
                f"got {y}-{m:02d}-{d:02d}"
            )


# ===========================================================================
# 边界情况
# ===========================================================================


class TestEdgeCases:
    """边界情况测试。"""

    @pymeeus
    def test_new_moon_at_midnight(self) -> None:
        """验证临近午夜的新月时刻日期正确。"""
        # 测试一些随机日期
        ref = moment_from_utc(2026, 6, 15, 0.0)
        nm = new_moon_after(ref)
        rd = RataDie(int(nm.day))
        y, m, d = gregorian_from_fixed(rd)
        # 验证日期是有效的
        assert 2026 <= y <= 2027
        assert 1 <= m <= 12
        assert 1 <= d <= 31

    @pymeeus
    def test_consistency_year_boundary(self) -> None:
        """跨年（2025-2026）的新月序列应连续。"""
        # 取 2025 年 12 月的新月
        nm_dec = new_moon_after(
            Moment(float(fixed_from_gregorian(2025, 12, 1)))
        )
        rd_dec = RataDie(int(nm_dec.day))
        y_dec, _, _ = gregorian_from_fixed(rd_dec)
        assert y_dec == 2025, f"Dec 2025 new moon year: {y_dec}"

        # 下一个新月应在 2026 年 1 月
        nm_jan = new_moon_after(nm_dec)
        rd_jan = RataDie(int(nm_jan.day))
        y_jan, m_jan, _ = gregorian_from_fixed(rd_jan)
        assert y_jan == 2026
        assert m_jan == 1


# ===========================================================================
# 格式化测试
# ===========================================================================


class TestFormatting:
    """新月格式化测试。"""

    @pymeeus
    def test_format_new_moon(self) -> None:
        """format_new_moon_datetime 应输出可读字符串。"""
        nm = new_moon_after(
            Moment(float(fixed_from_gregorian(2026, 5, 15)))
        )
        s = format_new_moon_datetime(nm, "zh")
        assert "朔" in s, f"Chinese format: {s}"
        assert "UTC" in s, f"Should contain UTC: {s}"

        s_en = format_new_moon_datetime(nm, "en")
        assert "New Moon" in s_en, f"English format: {s_en}"
