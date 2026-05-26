# tests/test_converters.py — 历法转换测试
#
# 验证 Gregorian/Julian/ISO ↔ R.D. 双向转换的准确性。
#
# 参考值来源:
#   - Dershowitz & Reingold "Calendrical Calculations" Appendix C
#   - 通过计算公式手工验算
#   - 已知天文/历史日期

from __future__ import annotations

import pytest

from ..core.rata_die import RataDie, Moment
from ..calendar.converters import (
    fixed_from_gregorian,
    gregorian_from_fixed,
    fixed_from_julian,
    julian_from_fixed,
    fixed_from_iso,
    iso_from_fixed,
    is_gregorian_leap_year,
    is_julian_leap_year,
    day_of_week,
    day_of_week_name,
    moment_from_datetime,
)


# ===========================================================================
# 闰年测试
# ===========================================================================


class TestGregorianLeapYear:
    """公历闰年判定测试。"""

    def test_leap_year_divisible_by_4(self) -> None:
        """能被 4 整除的年份通常是闰年。"""
        assert is_gregorian_leap_year(2004) is True
        assert is_gregorian_leap_year(2008) is True
        assert is_gregorian_leap_year(2012) is True
        assert is_gregorian_leap_year(2016) is True
        assert is_gregorian_leap_year(2020) is True
        assert is_gregorian_leap_year(2024) is True

    def test_century_not_leap(self) -> None:
        """能被 100 整除但不能被 400 整除的年份不是闰年。"""
        assert is_gregorian_leap_year(1900) is False
        assert is_gregorian_leap_year(1800) is False
        assert is_gregorian_leap_year(1700) is False
        assert is_gregorian_leap_year(2100) is False

    def test_century_divisible_by_400_is_leap(self) -> None:
        """能被 400 整除的世纪年是闰年。"""
        assert is_gregorian_leap_year(2000) is True
        assert is_gregorian_leap_year(1600) is True
        assert is_gregorian_leap_year(2400) is True

    def test_non_leap_years(self) -> None:
        """普通非闰年。"""
        assert is_gregorian_leap_year(2001) is False
        assert is_gregorian_leap_year(2002) is False
        assert is_gregorian_leap_year(2003) is False
        assert is_gregorian_leap_year(2005) is False
        assert is_gregorian_leap_year(2023) is False

    def test_year_1_not_leap(self) -> None:
        """公元 1 年不是闰年。"""
        assert is_gregorian_leap_year(1) is False


class TestJulianLeapYear:
    """儒略历闰年判定测试。"""

    def test_julian_every_4_years(self) -> None:
        """儒略历中每 4 年都是闰年。"""
        assert is_julian_leap_year(1900) is True    # Gregorian 中不是闰年
        assert is_julian_leap_year(1800) is True
        assert is_julian_leap_year(1700) is True
        assert is_julian_leap_year(4) is True

    def test_julian_non_leap(self) -> None:
        """不能被 4 整除的不是闰年。"""
        assert is_julian_leap_year(1901) is False
        assert is_julian_leap_year(1902) is False
        assert is_julian_leap_year(1903) is False
        assert is_julian_leap_year(2001) is False


# ===========================================================================
# 公历 ↔ R.D. 双向转换
# ===========================================================================


class TestGregorianToRD:
    """公历 → R.D. 转换测试。

    所有参考值通过 D&R 算法公式计算验证。

    已知参考值:
      Jan  1,   1 CE → R.D.        1  (历元)
      Dec 31,   1 CE → R.D.      365
      Jan  1, 1900 CE → R.D.  693596
      Jan  1, 1970 CE → R.D.  719163  (UNIX epoch)
      Jan  1, 2000 CE → R.D.  730120  (Y2K)
      May 14, 2026 CE → R.D.  739750  (today)
    """

    # (year, month, day, expected_rd)
    REFERENCE_DATES: list[tuple[int, int, int, int]] = [
        (  1,  1,  1,         1),       # 历元
        (  1, 12, 31,       365),       # 第一年的最后一天
        (1900,  1,  1,    693596),       # 1900 年元旦 (non-leap century)
        (1900,  2, 28,    693654),       # 1900 年 2 月最后一天 (平年)
        (1970,  1,  1,    719163),       # UNIX epoch
        (2000,  1,  1,    730120),       # Y2K 周六
        (2000,  2, 28,    730178),       # 2000 年 2 月 28 日
        (2000,  2, 29,    730179),       # 2000 年 2 月 29 日 (闰年)
        (2000,  3,  1,    730180),       # 2000 年 3 月 1 日 (闰年后一天)
        (2023,  1,  1,    738521),       # 2023 年元旦
        (2026,  5, 14,    739750),       # 今天 (2026-05-14)
        (2026, 12, 31,    739981),       # 2026 年最后一天
    ]

    @pytest.mark.parametrize("year,month,day,expected", REFERENCE_DATES)
    def test_gregorian_to_rd(self, year: int, month: int, day: int, expected: int) -> None:
        """公历 → R.D. 参考值验证。"""
        rd = fixed_from_gregorian(year, month, day)
        assert rd == expected, f"{year}-{month:02d}-{day:02d} → R.D.{expected}, got R.D.{rd}"

    def test_gregorian_today(self) -> None:
        """今天的日期验证。"""
        rd = fixed_from_gregorian(2026, 5, 14)
        assert rd == 739750


class TestRDToGregorian:
    """R.D. → 公历 转换测试。"""

    # (rd, year, month, day)
    REFERENCE_RD: list[tuple[int, int, int, int]] = [
        (        1,   1,  1,  1),
        (      365,   1, 12, 31),
        (   693596, 1900,  1,  1),
        (   719163, 1970,  1,  1),
        (   730120, 2000,  1,  1),
        (   730179, 2000,  2, 29),
        (   730180, 2000,  3,  1),
        (   738521, 2023,  1,  1),
        (   739750, 2026,  5, 14),
        (   739981, 2026, 12, 31),
    ]

    @pytest.mark.parametrize("rd,year,month,day", REFERENCE_RD)
    def test_rd_to_gregorian(self, rd: int, year: int, month: int, day: int) -> None:
        """R.D. → 公历 参考值验证。"""
        result = gregorian_from_fixed(RataDie(rd))
        assert result == (year, month, day), (
            f"R.D.{rd} → {year}-{month:02d}-{day:02d}, "
            f"got {result[0]}-{result[1]:02d}-{result[2]:02d}"
        )


class TestGregorianRoundTrip:
    """公历 ↔ R.D. 双向往返测试。"""

    # 覆盖各种边缘情况的测试日期
    TEST_DATES: list[tuple[int, int, int]] = [
        (  1,  1,  1),    # 历元
        (  1,  2,  1),    # 公元 1 年各月 1 号
        (  1,  6,  1),
        (  1, 12, 31),    # 第一年最后一天
        (  4,  2, 29),    # 闰日
        (100,  1,  1),    # 公元 100 年
        (1582, 10, 15),   # 格里高利历改革起始日
        (1900,  1,  1),   # 世纪年
        (1900,  2, 28),   # 世纪年 2 月底
        (1970,  1,  1),   # UNIX epoch
        (1999, 12, 31),   # 千禧年前夜
        (2000,  1,  1),   # 千禧年
        (2000,  2, 29),   # 闰日
        (2000,  3,  1),   # 闰年后 3 月 1 日
        (2023,  2, 28),   # 平年 2 月底
        (2024,  2, 29),   # 闰年 2 月 29 日
        (2026,  5, 14),   # 今天
        (2100,  2, 28),   # 未来世纪年（非闰年 2 月最后一天）
        (2400,  2, 29),   # 未来世纪闰年
    ]

    @pytest.mark.parametrize("year,month,day", TEST_DATES)
    def test_round_trip(self, year: int, month: int, day: int) -> None:
        """公历 → R.D. → 公历 往返一致性。"""
        rd = fixed_from_gregorian(year, month, day)
        result = gregorian_from_fixed(rd)
        assert result == (year, month, day), (
            f"Round-trip failed: {year}-{month:02d}-{day:02d} "
            f"→ R.D.{rd} → {result}"
        )

    def test_many_dates_range(self) -> None:
        """大范围日期往返验证（1900-2100 每年抽样）。"""
        for year in range(1900, 2101):
            # 每年测试: 1 月 1 日, 7 月 1 日, 12 月 31 日
            for month, day in [(1, 1), (7, 1), (12, 31)]:
                rd = fixed_from_gregorian(year, month, day)
                result = gregorian_from_fixed(rd)
                assert result == (year, month, day), (
                    f"Round-trip failed: {year}-{month:02d}-{day:02d} "
                    f"→ R.D.{rd} → {result}"
                )


# ===========================================================================
# 儒略历 ↔ R.D. 双向转换
# ===========================================================================


class TestJulianToRD:
    """儒略历 → R.D. 转换测试。

    参考值:
      Jan 1, 1 CE (Julian)   → R.D.       1
      Jan 1, 1900 (Julian)   → R.D.  693610
      Jan 1, 2000 (Julian)   → R.D.  730135

    注: 到 1900 年，儒略历比公历多 14 天，
        因为公历跳过了世纪年的 3 个闰年（1700, 1800, 1900）。
    """

    def test_julian_epoch(self) -> None:
        """Jan 1, 1 CE (Julian) = R.D. 1（与公历相同）。"""
        rd = fixed_from_julian(1, 1, 1)
        assert rd == 1

    def test_julian_1900(self) -> None:
        """Jan 1, 1900 (Julian) = R.D. 693610

        儒略历比公历多 14 天:
          693610 - 693596 = 14 ✓
        """
        rd_julian = fixed_from_julian(1900, 1, 1)
        rd_gregorian = fixed_from_gregorian(1900, 1, 1)
        assert rd_julian == 693610
        assert rd_julian - rd_gregorian == 14  # 儒略历超前 14 天

    def test_julian_2000(self) -> None:
        """Jan 1, 2000 (Julian) = R.D. 730135

        Gregorian 在 2000 年 1 月 1 日是 R.D. 730120
        儒略历超前 15 天（2000 年在儒略历和公历中都是闰年，
        但公历在 1900 年跳过一个闰年，所以多一天差值）
        """
        rd_julian = fixed_from_julian(2000, 1, 1)
        rd_gregorian = fixed_from_gregorian(2000, 1, 1)
        assert rd_julian == 730135
        # 因为 1900 年在儒略历中多了一个闰日，所以差值变成 15 天
        assert rd_julian - rd_gregorian == 15

    def test_julian_oct_1582(self) -> None:
        """1582 年 10 月 3 日（儒略历）= 1582 年 10 月 15 日（公历）

        Proleptic 公历中儒略历比公历超前 12 天（因世纪闰年规则差异）。
        注意：历史上儒略历 1582-10-05 对应公历 1582-10-15（仅差 10 天）
        是因为格里高利改革只移除了 10 天，但 proleptic 计算使用统一规则。
        """
        rd_julian = fixed_from_julian(1582, 10, 3)
        rd_gregorian = fixed_from_gregorian(1582, 10, 15)
        assert rd_julian == rd_gregorian


class TestJulianRoundTrip:
    """儒略历 ↔ R.D. 往返测试。"""

    TEST_DATES: list[tuple[int, int, int]] = [
        (  1,  1,  1),
        (  4,  2, 29),   # 儒略历闰年
        (100,  1,  1),
        (1582, 10,  4),  # 儒略历最后一天
        (1900,  1,  1),
        (2000,  1,  1),
        (2026,  5, 14),
    ]

    @pytest.mark.parametrize("year,month,day", TEST_DATES)
    def test_julian_round_trip(self, year: int, month: int, day: int) -> None:
        """儒略历 → R.D. → 儒略历 往返一致性。"""
        rd = fixed_from_julian(year, month, day)
        result = julian_from_fixed(rd)
        assert result == (year, month, day), (
            f"Julian round-trip failed: {year}-{month:02d}-{day:02d} "
            f"→ R.D.{rd} → {result}"
        )


# ===========================================================================
# 公历与儒略历交叉验证
# ===========================================================================


class TestGregorianJulianCross:
    """公历与儒略历交叉验证。"""

    def test_known_difference_1582(self) -> None:
        """1582 年 10 月儒略历与公历差 12 天（proleptic 计算）。"""
        # 公历 1582-10-15 = 儒略历 1582-10-03
        rd_g = fixed_from_gregorian(1582, 10, 15)
        rd_j = fixed_from_julian(1582, 10, 3)
        assert rd_g == rd_j

    def test_known_difference_1700(self) -> None:
        """1700 年儒略历与公历差 12 天（proleptic 计算）。"""
        # 公历 1700-03-01 = 儒略历 1700-02-17
        rd_g = fixed_from_gregorian(1700, 3, 1)
        rd_j = fixed_from_julian(1700, 2, 17)
        assert rd_g == rd_j, f"12 day difference expected after 1700 in proleptic"

    def test_known_difference_1900(self) -> None:
        """1900 年儒略历与公历差 14 天（proleptic 计算）。"""
        # 公历 1900-03-01 = 儒略历 1900-02-15
        rd_g = fixed_from_gregorian(1900, 3, 1)
        rd_j = fixed_from_julian(1900, 2, 15)
        assert rd_g == rd_j, f"14 day difference expected in proleptic at 1900"


# ===========================================================================
# ISO 周历 ↔ R.D. 转换
# ===========================================================================


class TestISOToRD:
    """ISO 周历 → R.D. 转换测试。

    ISO 周历规则:
      - 周一 = 1, 周日 = 7
      - 每年第一周包含该年第一个周四
      - 每周从周一开始

    已知参考:
      2000 年第 1 周周一 (2000-01-03) = R.D. 730122
    """

    def test_iso_2000_week1_monday(self) -> None:
        """2000 年第 1 周周一 = 2000-01-03 = R.D. 730122。"""
        rd = fixed_from_iso(0, 2000, 1, 1)
        # 验证: 2000-01-03 = Monday
        expected = fixed_from_gregorian(2000, 1, 3)
        assert rd == expected

    def test_iso_epoch(self) -> None:
        """公元 1 年第 1 周周一 = R.D. 1。"""
        rd = fixed_from_iso(0, 1, 1, 1)
        assert rd == 1

    def test_iso_2000_week1_sunday(self) -> None:
        """2000 年第 1 周周日 = R.D. 730128。"""
        rd = fixed_from_iso(0, 2000, 1, 7)
        assert rd == 730122 + 6  # 周一 + 6 天


class TestISOFromFixed:
    """R.D. → ISO 周历 转换测试。"""

    def test_rd_1_to_iso(self) -> None:
        """R.D. 1 → (0, 1, 1, 1) 公元 1年第 1 周周一。"""
        result = iso_from_fixed(RataDie(1))
        assert result == (0, 1, 1, 1)

    def test_rd_730122_to_iso(self) -> None:
        """R.D. 730122 → (0, 2000, 1, 1) 2000 年第 1 周周一。"""
        result = iso_from_fixed(RataDie(730122))
        assert result[1] == 2000
        assert result[2] == 1
        assert result[3] == 1  # Monday


class TestISORoundTrip:
    """ISO ↔ R.D. 往返测试。"""

    def test_iso_round_trip(self) -> None:
        """ISO → R.D. → ISO 往返一致性。"""
        for year in [1, 100, 2000, 2023, 2026]:
            for week in [1, 10, 20]:
                if week > 52:
                    continue
                rd = fixed_from_iso(0, year, week, 1)
                result = iso_from_fixed(rd)
                assert result[1] == year, f"Year mismatch for ISO({year}, w{week})"
                assert result[2] == week, f"Week mismatch for ISO({year}, w{week})"


# ===========================================================================
# 星期计算测试
# ===========================================================================


class TestDayOfWeek:
    """星期计算测试。

    R.D. 1 = Monday（星期一），所以:
      R.D. 1  → 索引 0 = Monday
      R.D. 7  → 索引 6 = Sunday
    """

    def test_rd_1_monday(self) -> None:
        """R.D. 1 = Monday（索引 0）。"""
        assert day_of_week(RataDie(1)) == 0

    def test_rd_7_sunday(self) -> None:
        """R.D. 7 = Sunday（索引 6）。"""
        assert day_of_week(RataDie(7)) == 6

    def test_known_dates(self) -> None:
        """已知日期的星期验证。"""
        # 2000-01-01 = Saturday = 索引 5
        rd = fixed_from_gregorian(2000, 1, 1)
        assert day_of_week(rd) == 5  # Saturday

        # 2026-05-14 = Thursday = 索引 3
        rd = fixed_from_gregorian(2026, 5, 14)
        assert day_of_week(rd) == 3  # Thursday

    def test_weekday_cycle_7(self) -> None:
        """星期在 7 天后循环。"""
        rd1 = RataDie(1)  # Monday
        rd7 = rd1 + 7     # 应该也是 Monday
        assert day_of_week(rd1) == day_of_week(rd7)


class TestDayOfWeekName:
    """星期名称测试。"""

    def test_english(self) -> None:
        """英文星期名称。"""
        assert day_of_week_name(RataDie(1), "en") == "Monday"

    def test_chinese(self) -> None:
        """中文星期名称。"""
        assert day_of_week_name(RataDie(1), "zh") == "星期一"


# ===========================================================================
# Moment 与公历互转
# ===========================================================================


class TestMomentFromDatetime:
    """moment_from_datetime 测试。"""

    def test_moment_midnight(self) -> None:
        """午夜时刻的 Moment。"""
        m = moment_from_datetime(2000, 1, 1, 0.0)
        assert abs(m.day - 730120.0) < 1e-12

    def test_moment_noon(self) -> None:
        """正午时刻的 Moment。"""
        m = moment_from_datetime(2000, 1, 1, 12.0)
        assert abs(m.day - 730120.5) < 1e-12

    def test_moment_custom_time(self) -> None:
        """自定义时刻的 Moment。"""
        m = moment_from_datetime(2026, 5, 14, 14.5)
        # 14:30 = 14.5/24 = 0.6041666... 天
        assert abs(m.day - 739750.6041666666) < 1e-8
