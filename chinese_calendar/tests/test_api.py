# tests/test_api.py — Calendar API 测试
#
# 覆盖 Calendar 类的全部公共接口。
# 注意: 部分测试需要 PyMeeus（节气计算依赖天文引擎），
#       无需 PyMeeus 的纯逻辑测试优先覆盖。

from __future__ import annotations

import pytest
import json

from chinese_calendar.api.solar_date import SolarDate
from chinese_calendar.api.lunar_date import LunarDate


class TestSolarDate:
    """SolarDate 测试。"""

    def test_create(self):
        sd = SolarDate(2026, 5, 21, 12.0)
        assert sd.year == 2026
        assert sd.month == 5
        assert sd.day == 21
        assert sd.hours == 12.0

    def test_default_hours(self):
        sd = SolarDate(2026, 5, 21)
        assert sd.hours == 12.0

    def test_invalid_month(self):
        with pytest.raises(ValueError):
            SolarDate(2026, 0, 1)

    def test_invalid_day(self):
        with pytest.raises(ValueError):
            SolarDate(2026, 1, 0)

    def test_frozen(self):
        sd = SolarDate(2026, 5, 21)
        with pytest.raises(AttributeError):
            sd.year = 2025

    def test_repr(self):
        sd = SolarDate(2026, 5, 21)
        r = repr(sd)
        assert "SolarDate" in r


class TestLunarDate:
    """LunarDate 测试。"""

    def test_create(self):
        ld = LunarDate(2026, 4, 5, False)
        assert ld.year == 2026
        assert ld.month == 4
        assert ld.day == 5
        assert not ld.is_leap

    def test_default_is_leap(self):
        ld = LunarDate(2026, 1, 1)
        assert not ld.is_leap

    def test_leap_month(self):
        ld = LunarDate(2026, 4, 5, True)
        assert ld.is_leap


# ===========================================================================
# Calendar 测试 — 纯逻辑（无需 PyMeeus）
# ===========================================================================


class TestCalendarBasic:
    """Calendar 基本功能测试（无需 PyMeeus）。"""

    def test_from_solar_creates_calendar(self):
        """from_solar 应正确创建 Calendar 实例。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        assert cal.solar_date.year == 2026
        assert cal.solar_date.month == 5
        assert cal.solar_date.day == 21

    def test_rd_property(self):
        """rd 属性应返回正确的 R.D. 值。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(1900, 1, 1)
        assert cal.rd == 693596

    def test_weekday_property(self):
        """weekday 属性应返回正确星期。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        # 2026-05-21 = Thursday
        assert "星期四" in cal.weekday.zh
        # English check
        cal_en = Calendar.from_solar(2026, 5, 21, locale="en")
        assert "Thursday" in cal_en.weekday.en

    def test_rd_2026_may_21(self):
        """2026-05-21 的 R.D. 验证。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        assert cal.rd == 739757

    def test_year_ganzhi(self):
        """年柱干支。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        assert "丙午" in cal.year_ganzhi.zh
        assert "Bing" in cal.year_ganzhi.en

    def test_day_ganzhi(self):
        """日柱干支。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        # May 21, 2026 = 乙未
        assert "乙" in cal.day_ganzhi.zh
        assert "Yi" in cal.day_ganzhi.en

    def test_shengxiao(self):
        """生肖。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        assert "马" in cal.shengxiao.zh
        assert "Horse" in cal.shengxiao.en

    def test_bazi_str(self):
        """bazi_str 应返回四柱字符串。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        b_str = cal.bazi_str
        # 确认包含各柱
        assert len(b_str) > 0
        assert " " in b_str

    def test_to_dict_has_gregorian(self):
        """to_dict 应包含公历信息。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        d = cal.to_dict()
        assert "gregorian" in d
        assert d["gregorian"]["year"] == 2026
        assert d["gregorian"]["month"] == 5
        assert d["gregorian"]["day"] == 21

    def test_to_dict_has_bazi(self):
        """to_dict 应包含八字信息。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        d = cal.to_dict()
        assert "bazi" in d
        assert "year" in d["bazi"]
        assert "month" in d["bazi"]
        assert "day" in d["bazi"]

    def test_to_dict_has_shengxiao(self):
        """to_dict 应包含生肖信息。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        d = cal.to_dict()
        assert "shengxiao" in d

    def test_to_json(self):
        """to_json 应返回有效 JSON。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        js = cal.to_json()
        parsed = json.loads(js)
        assert parsed["gregorian"]["year"] == 2026

    def test_locale_default_zh(self):
        """默认 locale 应为中文。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        assert cal.locale == "zh"

    def test_locale_en(self):
        """可指定英文 locale。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21, locale="en")
        assert cal.locale == "en"

    def test_str_zh(self):
        """__str__ 中文格式。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        s = str(cal)
        assert "2026" in s
        assert "八字" in s

    def test_str_en(self):
        """__str__ 英文格式。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21, locale="en")
        s = str(cal)
        assert "2026" in s
        assert "Bazi" in s

    def test_now(self):
        """now() 应返回当前日期。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.now()
        assert cal.solar_date.year >= 2026

    def test_hour_ganzhi_available(self):
        """有小时数时 hour_ganzhi 应返回内容。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21, hours=14.5)
        # Calendar 的内置回退算法始终能计算时柱
        assert cal.hour_ganzhi is not None
        assert len(cal.hour_ganzhi.zh) >= 2


# ===========================================================================
# Calendar 测试 — 需 PyMeeus
# ===========================================================================


def _pymeeus_available() -> bool:
    try:
        from chinese_calendar.astronomy.sun import pymeeus_available
        return pymeeus_available()
    except ImportError:
        return False


_PYMEEUS = _pymeeus_available()
_NEED_PYMEEUS = pytest.mark.skipif(not _PYMEEUS, reason="requires PyMeeus")


@_NEED_PYMEEUS
class TestCalendarAstronomy:
    """需要 PyMeeus 的 Calendar 测试。"""

    def test_lunar_date(self):
        """农历日期转换。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        lun = cal.lunar
        assert lun.year >= 2025
        assert 1 <= lun.month <= 12
        assert 1 <= lun.day <= 30

    def test_lunar_str(self):
        """农历字符串格式化。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        s = cal.lunar_str
        assert "农历" in s or "Chinese" in s

    def test_solar_terms_list(self):
        """节气列表。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 6, 21)
        terms = cal.solar_terms
        assert len(terms) == 24

    def test_next_solar_term(self):
        """下一个节气。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 6, 1)
        nst = cal.next_solar_term
        assert nst is not None
        assert "芒种" == nst["name_zh"]

    def test_to_dict_lunar(self):
        """to_dict 应包含农历信息。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21)
        d = cal.to_dict()
        assert "lunar" in d
        assert d["lunar"]["year"] >= 2025

    def test_hour_ganzhi_available(self):
        """提供小时数时应有时柱。"""
        from chinese_calendar.api import Calendar

        cal = Calendar.from_solar(2026, 5, 21, hours=14.5)  # 未时
        hg = cal.hour_ganzhi
        assert hg is not None
