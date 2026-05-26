# tests/test_locale.py — 本地化系统测试

from __future__ import annotations

import pytest

from chinese_calendar.locale.types import LocaleStr, set_default_lang, get_default_lang
from chinese_calendar.locale import zh_CN, en_US


class TestLocaleStr:
    """LocaleStr 类型测试。"""

    def test_create(self):
        s = LocaleStr(zh="立春", en="Spring Begins")
        assert s.zh == "立春"
        assert s.en == "Spring Begins"

    def test_get_zh(self):
        s = LocaleStr(zh="立春", en="Spring Begins")
        assert s.get("zh") == "立春"

    def test_get_en(self):
        s = LocaleStr(zh="立春", en="Spring Begins")
        assert s.get("en") == "Spring Begins"

    def test_get_default(self):
        s = LocaleStr(zh="甲", en="Jia")
        # 默认是 zh
        assert s.get() == "甲"

    def test_str(self):
        s = LocaleStr(zh="甲", en="Jia")
        assert str(s) == "甲"

    def test_repr(self):
        s = LocaleStr(zh="甲", en="Jia")
        r = repr(s)
        assert "LocaleStr" in r
        assert "甲" in r
        assert "Jia" in r

    def test_eq(self):
        a = LocaleStr(zh="甲", en="Jia")
        b = LocaleStr(zh="甲", en="Jia")
        assert a == b

    def test_not_eq(self):
        a = LocaleStr(zh="甲", en="Jia")
        b = LocaleStr(zh="乙", en="Yi")
        assert a != b

    def test_default_lang_switch(self):
        set_default_lang("en")
        s = LocaleStr(zh="甲", en="Jia")
        assert s.get() == "Jia"
        set_default_lang("zh")
        # 验证改回来了
        assert s.get() == "甲"

    def test_get_default_lang(self):
        set_default_lang("zh")
        assert get_default_lang() == "zh"
        set_default_lang("en")
        assert get_default_lang() == "en"
        set_default_lang("zh")

    def test_invalid_lang(self):
        s = LocaleStr(zh="甲", en="Jia")
        with pytest.raises(ValueError):
            s.get("fr")

    def test_invalid_default(self):
        with pytest.raises(ValueError):
            set_default_lang("fr")


class TestZhCN:
    """中文翻译表完整性测试。"""

    def test_stems(self):
        assert len(zh_CN.HEAVENLY_STEMS) == 10
        assert zh_CN.HEAVENLY_STEMS[0] == "甲"
        assert zh_CN.HEAVENLY_STEMS[9] == "癸"

    def test_branches(self):
        assert len(zh_CN.EARTHLY_BRANCHES) == 12
        assert zh_CN.EARTHLY_BRANCHES[0] == "子"
        assert zh_CN.EARTHLY_BRANCHES[11] == "亥"

    def test_solar_terms(self):
        assert len(zh_CN.SOLAR_TERMS) == 24
        assert zh_CN.SOLAR_TERMS[2] == "立春"
        assert zh_CN.SOLAR_TERMS[23] == "冬至"

    def test_weekdays(self):
        assert len(zh_CN.WEEKDAYS) == 7
        assert zh_CN.WEEKDAYS[0] == "星期一"

    def test_shengxiao(self):
        assert len(zh_CN.BRANCH_SHENGXIAO) == 12
        assert zh_CN.BRANCH_SHENGXIAO[0] == "鼠"

    def test_lunar_months(self):
        assert len(zh_CN.LUNAR_MONTHS) == 13  # 索引 0-12
        assert zh_CN.LUNAR_MONTHS[1] == "正月"
        assert zh_CN.LUNAR_MONTHS[11] == "十一月"

    def test_lunar_days(self):
        assert len(zh_CN.LUNAR_DAYS) == 31  # 索引 0-30
        assert zh_CN.LUNAR_DAYS[1] == "初一"
        assert zh_CN.LUNAR_DAYS[30] == "三十"

    def test_nayin(self):
        assert len(zh_CN.NAYIN) == 30
        assert zh_CN.NAYIN[0] == "海中金"
        assert zh_CN.NAYIN[29] == "大海水"


class TestEnUS:
    """英文翻译表完整性测试。"""

    def test_stems(self):
        assert len(en_US.HEAVENLY_STEMS) == 10
        assert en_US.HEAVENLY_STEMS[0] == "Jia"
        assert en_US.HEAVENLY_STEMS[9] == "Gui"

    def test_branches(self):
        assert len(en_US.EARTHLY_BRANCHES) == 12
        assert en_US.EARTHLY_BRANCHES[0] == "Zi"
        assert en_US.EARTHLY_BRANCHES[11] == "Hai"

    def test_solar_terms(self):
        assert len(en_US.SOLAR_TERMS) == 24
        assert en_US.SOLAR_TERMS[2] == "Spring Begins"
        assert en_US.SOLAR_TERMS[23] == "Winter Solstice"

    def test_weekdays(self):
        assert len(en_US.WEEKDAYS) == 7
        assert en_US.WEEKDAYS[0] == "Monday"

    def test_shengxiao(self):
        assert len(en_US.BRANCH_SHENGXIAO) == 12
        assert en_US.BRANCH_SHENGXIAO[0] == "Rat"

    def test_lunar_months(self):
        assert len(en_US.LUNAR_MONTHS) == 13
        assert "Yue" in en_US.LUNAR_MONTHS[1]

    def test_lunar_days(self):
        assert len(en_US.LUNAR_DAYS) == 31
        assert en_US.LUNAR_DAYS[1] == "1st"

    def test_nayin(self):
        assert len(en_US.NAYIN) == 30
        assert "Metal" in en_US.NAYIN[0]
        assert "Water" in en_US.NAYIN[29]

    def test_wuxing(self):
        assert len(en_US.WUXING) == 5
        assert en_US.WUXING[0] == "Metal"
