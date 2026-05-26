# tests/test_time_systems.py — 时间系统测试
#
# 验证 JD/TT/UTC/ΔT 转换的正确性。

from __future__ import annotations

from math import fabs

import pytest

from ..core.rata_die import Moment, RataDie
from ..core.time_systems import (
    jd_from_moment,
    moment_from_jd,
    julian_centuries,
    delta_t,
    dynamical_time,
    universal_time,
    mean_sidereal_time_greenwich,
    moment_from_utc,
    J2000_JD,
    J2000_MOMENT,
    JD_EPOCH_OFFSET,
    JULIAN_CENTURY_DAYS,
)


# ===========================================================================
# JD ↔ Moment 转换
# ===========================================================================


class TestJDtoMoment:
    """JD ↔ Moment 相互转换测试。"""

    def test_jd_offset_constant(self) -> None:
        """JD_EPOCH_OFFSET 应使 J2000.0 对齐。"""
        # J2000.0 = JD 2451545.0 = Moment(730120.5)
        # 所以 JD_EPOCH_OFFSET = 2451545.0 - 730120.5 = 1721424.5
        assert abs(JD_EPOCH_OFFSET - 1721424.5) < 1e-9

    def test_jd_from_moment_j2000(self) -> None:
        """Moment J2000.0 → JD 2451545.0"""
        m = Moment(J2000_MOMENT)  # Moment(730120.5)
        jd = jd_from_moment(m)
        assert abs(jd - J2000_JD) < 1e-9, f"Expected {J2000_JD}, got {jd}"

    def test_moment_from_jd_j2000(self) -> None:
        """JD 2451545.0 → Moment(730120.5)"""
        m = moment_from_jd(J2000_JD)
        assert abs(m.day - J2000_MOMENT) < 1e-9

    def test_jd_roundtrip(self) -> None:
        """JD → Moment → JD 往返一致性。"""
        test_values = [
            2451545.0,        # J2000.0
            2458849.5,        # ~2020-01-01
            2460500.0,        # ~2024-06-01
            1721425.5,        # Jan 1, 1 CE noon
        ]
        for jd in test_values:
            m = moment_from_jd(jd)
            jd_back = jd_from_moment(m)
            assert abs(jd_back - jd) < 1e-9, (
                f"JD round-trip failed: {jd} → Moment({m.day}) → JD {jd_back}"
            )

    def test_moment_roundtrip(self) -> None:
        """Moment → JD → Moment 往返一致性。"""
        test_moments = [
            1.0,          # Jan 1, 1 CE
            730120.5,     # J2000.0
            739750.0,     # Today
        ]
        for md in test_moments:
            m = Moment(md)
            jd = jd_from_moment(m)
            m_back = moment_from_jd(jd)
            assert abs(m_back.day - md) < 1e-9, (
                f"Moment round-trip failed: {md} → JD {jd} → Moment({m_back})"
            )


# ===========================================================================
# 儒略世纪数
# ===========================================================================


class TestJulianCenturies:
    """儒略世纪数计算测试。"""

    def test_j2000_epoch(self) -> None:
        """J2000.0 时的儒略世纪数应为 0.0。"""
        m = Moment(J2000_MOMENT)
        t = julian_centuries(m)
        assert abs(t) < 1e-12, f"J2000 t should be 0, got {t}"

    def test_one_century_later(self) -> None:
        """J2100.0 时的儒略世纪数应约为 1.0。"""
        # J2100.0 = JD 2451545.0 + 36525 = 2488070.0
        jd_2100 = J2000_JD + JULIAN_CENTURY_DAYS
        m = moment_from_jd(jd_2100)
        t = julian_centuries(m)
        assert abs(t - 1.0) < 1e-6, f"J2100 t should be ~1.0, got {t}"

    def test_today_range(self) -> None:
        """2026 年的儒略世纪数应在合理范围。"""
        m = moment_from_utc(2026, 5, 14)
        t = julian_centuries(m)
        # 2026 - 2000 = 26 years = 0.26 centuries
        assert 0.2 < t < 0.3, f"t for 2026 should be ~0.26, got {t}"


# ===========================================================================
# ΔT (Delta T)
# ===========================================================================


class TestDeltaT:
    """ΔT 近似值测试。"""

    def test_delta_t_2000(self) -> None:
        """2000 年的 ΔT 约 63.8 秒。"""
        dt = delta_t(2000)
        assert 60 < dt < 70, f"ΔT(2000) should be ~63.8s, got {dt}"

    def test_delta_t_2020(self) -> None:
        """2020 年的 ΔT 约 69 秒。"""
        dt = delta_t(2020)
        assert 65 < dt < 75, f"ΔT(2020) should be ~69s, got {dt}"

    def test_delta_t_1900(self) -> None:
        """1900 年的 ΔT 约 8.83 + 0.0449*200 = 17.81 秒。"""
        dt = delta_t(1900)
        assert 15 < dt < 20, f"ΔT(1900) should be ~17.8s, got {dt}"

    def test_delta_t_increasing(self) -> None:
        """ΔT 随时间增加（地球自转减速）。"""
        assert delta_t(1900) < delta_t(2000) < delta_t(2020) < delta_t(2050)

    def test_delta_t_before_1620(self) -> None:
        """1620 年之前的 ΔT 返回固定近似值。"""
        dt = delta_t(1000)
        assert dt == 120.0


# ===========================================================================
# 力学时转换
# ===========================================================================


class TestDynamicalTime:
    """UTC ↔ TT 转换测试。"""

    def test_dynamical_time_positive_shift(self) -> None:
        """TT 应比 UTC 提前（正值 ΔT）。"""
        m_utc = moment_from_utc(2020, 6, 1, 12.0)
        m_tt = dynamical_time(m_utc)
        assert m_tt.day > m_utc.day, (
            f"TT({m_tt.day}) should be > UTC({m_utc.day})"
        )

    def test_dynamical_time_shift_magnitude(self) -> None:
        """TT 偏移量应约为 ΔT/86400 天。"""
        m_utc = moment_from_utc(2020, 1, 1, 0.0)
        m_tt = dynamical_time(m_utc)

        expected_dt = delta_t(2020) / 86400.0
        actual_dt = m_tt.day - m_utc.day

        assert abs(actual_dt - expected_dt) < 0.001, (
            f"TT shift: expected ~{expected_dt:.6f}d, got {actual_dt:.6f}d"
        )

    def test_tt_utc_roundtrip(self) -> None:
        """UTC → TT → UTC 往返一致性。"""
        m_utc = moment_from_utc(2025, 3, 20, 6.0)
        m_tt = dynamical_time(m_utc)
        m_utc_back = universal_time(m_tt)

        # 往返误差应 < 0.001 天 (~0.1 秒)
        diff = abs(m_utc_back.day - m_utc.day)
        assert diff < 0.001, (
            f"UTC→TT→UTC round-trip error: {diff:.6f}d"
        )


# ===========================================================================
# 恒星时
# ===========================================================================


class TestSiderealTime:
    """恒星时计算测试。"""

    def test_gmst_j2000(self) -> None:
        """J2000.0 时的 GMST 约 280.46 度。"""
        m = Moment(J2000_MOMENT)  # 2000-01-01 12:00 TT
        gmst = mean_sidereal_time_greenwich(m)
        # Meeus: J2000.0 时 GMST ≈ 280.4606°
        assert 275 < gmst < 285, f"GMST at J2000 should be ~280.5°, got {gmst}"

    def test_gmst_daily_increment(self) -> None:
        """GMST 日增量约 360.9856 度/天。"""
        m1 = moment_from_utc(2025, 1, 1, 0.0)
        m2 = moment_from_utc(2025, 1, 2, 0.0)
        gmst1 = mean_sidereal_time_greenwich(m1)
        gmst2 = mean_sidereal_time_greenwich(m2)
        diff = (gmst2 - gmst1) % 360
        # 太阳日增量：~360.9856°
        # %360 将 360.9856° 折回到 0.9856°
        assert 0.9 < diff < 1.1, f"GMST daily increment (mod 360) should be ~0.9856°, got {diff}"
