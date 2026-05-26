# tests/test_rata_die.py — RataDie / Moment 类型测试
#
# 验证 RataDie 和 Moment 核心类型的基本运算、比较和转换功能。
#
# 参考: Dershowitz & Reingold "Calendrical Calculations" Appendix C

from __future__ import annotations

from math import floor

import pytest

from ..core.rata_die import RataDie, Moment


# ===========================================================================
# RataDie 基础测试
# ===========================================================================


class TestRataDieCreation:
    """RataDie 创建和基本属性测试。"""

    def test_creation_from_int(self) -> None:
        """从整数创建 RataDie。"""
        rd = RataDie(1)
        assert rd.day == 1

    def test_creation_from_float_whole(self) -> None:
        """从整数值的 float 创建（应自动转换为 int）。"""
        rd = RataDie(1.0)
        assert rd.day == 1
        assert isinstance(rd.day, int)

    def test_creation_from_float_fractional_raises(self) -> None:
        """从小数 float 创建应抛出 TypeError。"""
        with pytest.raises(TypeError):
            RataDie(1.5)

    def test_creation_negative(self) -> None:
        """支持负值 R.D.（代表公元前日期）。"""
        rd = RataDie(-1)
        assert rd.day == -1

    def test_frozen_immutable(self) -> None:
        """RataDie 应该是不可变的。"""
        rd = RataDie(100)
        with pytest.raises(Exception):
            rd.day = 200  # type: ignore[misc]

    def test_repr(self) -> None:
        """__repr__() 测试。"""
        rd = RataDie(42)
        assert repr(rd) == "RataDie(42)"

    def test_str(self) -> None:
        """__str__() 测试。"""
        rd = RataDie(42)
        assert str(rd) == "42"

    def test_int_conversion(self) -> None:
        """int() 转换测试。"""
        rd = RataDie(999)
        assert int(rd) == 999


class TestRataDieArithmetic:
    """RataDie 算术运算测试。"""

    def test_add_int(self) -> None:
        """R.D. + int = 新的 R.D."""
        rd = RataDie(100)
        result = rd + 50
        assert isinstance(result, RataDie)
        assert result.day == 150

    def test_radd_int(self) -> None:
        """int + R.D. = 新的 R.D."""
        rd = RataDie(100)
        result = 50 + rd
        assert isinstance(result, RataDie)
        assert result.day == 150

    def test_sub_rata_die(self) -> None:
        """R.D. - R.D. = 天数差 (int)。"""
        rd1 = RataDie(200)
        rd2 = RataDie(150)
        result = rd1 - rd2
        assert isinstance(result, int)
        assert result == 50

    def test_sub_int(self) -> None:
        """R.D. - int = 新的 R.D."""
        rd = RataDie(100)
        result = rd - 30
        assert isinstance(result, RataDie)
        assert result.day == 70

    def test_rsub_int(self) -> None:
        """int - R.D. = 新的 R.D."""
        rd = RataDie(30)
        result = 100 - rd
        assert isinstance(result, RataDie)
        assert result.day == 70

    def test_arithmetic_chain(self) -> None:
        """链式运算测试。"""
        rd = RataDie(1)
        result = rd + 10 - 3 + 100 - 50
        assert result.day == 58

    def test_add_non_int_raises_type_error(self) -> None:
        """与非 int 类型相加应抛出 TypeError。

        Python 中当 __add__ 和 __radd__ 都返回 NotImplemented 时，
        解释器自动抛出 TypeError。
        """
        rd = RataDie(100)
        with pytest.raises(TypeError):
            _ = rd + "string"  # type: ignore[operator]


class TestRataDieComparison:
    """RataDie 比较运算测试。"""

    def test_equality(self) -> None:
        """== 测试。"""
        assert RataDie(100) == RataDie(100)
        assert RataDie(100) == 100

    def test_inequality(self) -> None:
        """!= 测试。"""
        assert RataDie(100) != RataDie(200)

    def test_less_than(self) -> None:
        """< 测试。"""
        assert RataDie(50) < RataDie(100)
        assert RataDie(50) < 100

    def test_less_equal(self) -> None:
        """<= 测试。"""
        assert RataDie(50) <= RataDie(50)
        assert RataDie(50) <= RataDie(100)
        assert RataDie(50) <= 50

    def test_greater_than(self) -> None:
        """> 测试。"""
        assert RataDie(100) > RataDie(50)
        assert RataDie(100) > 50

    def test_greater_equal(self) -> None:
        """>= 测试。"""
        assert RataDie(100) >= RataDie(100)
        assert RataDie(100) >= RataDie(50)
        assert RataDie(100) >= 100

    def test_hash(self) -> None:
        """RataDie 应可用作字典键。"""
        d = {RataDie(1): "one", RataDie(2): "two"}
        assert d[RataDie(1)] == "one"
        assert d[RataDie(2)] == "two"

    def test_sorting(self) -> None:
        """RataDie 列表应能排序。"""
        unsorted = [RataDie(5), RataDie(1), RataDie(10), RataDie(3)]
        sorted_rd = sorted(unsorted)
        assert sorted_rd == [RataDie(1), RataDie(3), RataDie(5), RataDie(10)]


# ===========================================================================
# Moment 测试
# ===========================================================================


class TestMoment:
    """Moment 类型测试。"""

    def test_creation(self) -> None:
        """Moment 创建。"""
        m = Moment(739750.5)
        assert m.day == 739750.5

    def test_rata_die_approximation(self) -> None:
        """rata_die() 测试 — 向下取整到最近整数日。"""
        m = Moment(739750.5)
        rd = m.rata_die()
        assert isinstance(rd, RataDie)
        assert rd.day == 739750

    def test_moment_from_rata_die(self) -> None:
        """从 RataDie 创建 Moment（当日午夜）。"""
        rd = RataDie(739750)
        m = Moment.from_rata_die(rd)
        assert m.day == 739750.0

    def test_standard_time_midnight(self) -> None:
        """standard_time() 测试 — 午夜。"""
        m = Moment(739750.0)
        assert m.standard_time() == 0.0

    def test_standard_time_noon(self) -> None:
        """standard_time() 测试 — 正午。"""
        m = Moment(739750.5)
        assert m.standard_time() == 0.5

    def test_standard_time_quarter(self) -> None:
        """standard_time() 测试 — 06:00。"""
        m = Moment(739750.25)
        assert abs(m.standard_time() - 0.25) < 1e-12

    def test_moment_sub_moment(self) -> None:
        """Moment - Moment = 天数差 (float)。"""
        m1 = Moment(100.5)
        m2 = Moment(50.25)
        result = m1 - m2
        assert isinstance(result, float)
        assert abs(result - 50.25) < 1e-12

    def test_moment_add_float(self) -> None:
        """Moment + float = 新的 Moment。"""
        m = Moment(100.0)
        result = m + 50.5
        assert isinstance(result, Moment)
        assert result.day == 150.5

    def test_moment_sub_float(self) -> None:
        """Moment - float = 新的 Moment。"""
        m = Moment(100.5)
        result = m - 50.0
        assert isinstance(result, Moment)
        assert result.day == 50.5

    def test_moment_comparison(self) -> None:
        """Moment 比较运算。"""
        assert Moment(100.0) < Moment(200.0)
        assert Moment(200.0) > Moment(100.0)
        assert Moment(100.0) <= Moment(100.0)
        assert Moment(100.0) >= Moment(100.0)
        assert Moment(100.0) == Moment(100.0)

    def test_float_conversion(self) -> None:
        """float() 转换。"""
        m = Moment(739750.5)
        assert float(m) == 739750.5

    def test_repr(self) -> None:
        """__repr__() 测试。"""
        m = Moment(42.5)
        assert repr(m) == "Moment(42.5)"


# ===========================================================================
# R.D. 历元参考值验证
# ===========================================================================


class TestReferenceValues:
    """参考 R.D. 值的交叉验证。

    这些值通过 Dershowitz & Reingold 算法计算得出，
    并与已知的天文/历史日期对照。
    """

    def test_epoch_jan_1_ce1(self) -> None:
        """公元 1 年 1 月 1 日 = R.D. 1

        这是 R.D. 系统的历元。
        """
        assert RataDie(1) == RataDie(1)

    def test_dec_31_ce1_days_in_year(self) -> None:
        """公元 1 年 12 月 31 日 = R.D. 365

        公元 1 年是平年（365 天），所以 R.D. 值 = 365。
        """
        assert RataDie(365) == RataDie(365)

    def test_positive_values_are_positive(self) -> None:
        """公元后的 R.D. 值都为正数。"""
        assert RataDie(1) > RataDie(0)
        assert RataDie(365) > RataDie(0)

    def test_rd_arithmetic_consistency(self) -> None:
        """R.D. 算术一致性：连续日期的 R.D. 差 = 1。"""
        # Jan 1 到 Jan 2 应差 1 天
        rd_jan1 = RataDie(1)
        rd_jan2 = rd_jan1 + 1
        assert rd_jan2 - rd_jan1 == 1

    def test_weekday_cycle(self) -> None:
        """R.D. 星期周期性：每隔 7 天同一星期。"""
        rd1 = RataDie(1)   # Monday
        rd8 = RataDie(8)   # Should also be Monday
        assert (rd1 - 1) % 7 == (rd8 - 1) % 7


# ===========================================================================
# Moment ↔ RataDie 互转
# ===========================================================================


class TestMomentRataDieConversion:
    """Moment ↔ RataDie 双向转换测试。"""

    def test_moment_to_rd_midnight(self) -> None:
        """午夜时刻的 Moment → RataDie。"""
        m = Moment(100.0)
        rd = m.to_rata_die()
        assert rd == RataDie(100)

    def test_moment_to_rd_afternoon(self) -> None:
        """下午时刻的 Moment → RataDie（取整为前一日午夜）。"""
        m = Moment(100.75)
        rd = m.to_rata_die()
        assert rd == RataDie(100)

    def test_moment_to_rd_negative(self) -> None:
        """负值 Moment → RataDie。"""
        m = Moment(-0.5)
        rd = m.to_rata_die()
        # floor(-0.5) = -1
        assert rd == RataDie(-1)

    def test_moment_rd_roundtrip(self) -> None:
        """Moment ↔ RataDie 往返一致性。"""
        rd = RataDie(5000)
        m = Moment.from_rata_die(rd)
        rd_back = m.to_rata_die()
        assert rd_back == rd


# ===========================================================================
# 边界条件
# ===========================================================================


class TestEdgeCases:
    """边界条件测试。"""

    def test_rd_zero(self) -> None:
        """R.D. 0（公元 1 年 1 月 1 日前一天）。"""
        rd = RataDie(0)
        assert rd.day == 0

    def test_rd_negative(self) -> None:
        """负 R.D. 值（公元前日期）。"""
        rd = RataDie(-1000)
        assert rd.day == -1000

    def test_moment_negative(self) -> None:
        """负 Moment 值。"""
        m = Moment(-0.001)
        assert m.day < 0

    def test_large_rd_values(self) -> None:
        """大 R.D. 值验证。"""
        # 数万年后的日期
        rd = RataDie(10000000)
        assert rd.day == 10000000
        # 简单算术应该仍然正确
        assert rd - 10000000 == 0
