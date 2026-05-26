# api/calendar_api.py — Calendar 统一入口类
#
# 万年历引擎的对外统一接口。封装底层全部功能：
#   公历 ←→ 农历转换、四柱八字、节气、干支信息。

from __future__ import annotations
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..locale.types import LocaleStr
from ..locale import zh_CN, en_US
from .solar_date import SolarDate
from .lunar_date import LunarDate

# ========== 内联干支常量 ==========
_HEAVENLY_STEMS_ZH = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
_EARTHLY_BRANCHES_ZH = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
_HEAVENLY_STEMS_EN = ["Jia","Yi","Bing","Ding","Wu","Ji","Geng","Xin","Ren","Gui"]
_EARTHLY_BRANCHES_EN = ["Zi","Chou","Yin","Mao","Chen","Si","Wu","Wei","Shen","You","Xu","Hai"]
_SHENGXIAO_ZH = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]
_SHENGXIAO_EN = ["Rat","Ox","Tiger","Rabbit","Dragon","Snake","Horse","Goat","Monkey","Rooster","Dog","Pig"]
_NAYIN = [
    "海中金","炉中火","大林木","路旁土","剑锋金","山头火","涧下水","城头土","白蜡金","杨柳木",
    "泉中水","屋上土","霹雳火","松柏木","长流水","砂石金","山下火","平地木","壁上土","金箔金",
    "覆灯火","天河水","大驿土","钗钏金","桑柘木","大溪水","沙中土","天上火","石榴木","大海水",
]
_HIDDEN_STEMS = {
    0: [9], 1: [5, 9, 7], 2: [0, 4, 2], 3: [1], 4: [5, 1, 9],
    5: [2, 6, 4], 6: [3, 5], 7: [5, 3, 1], 8: [6, 9, 4],
    9: [7], 10: [4, 7, 3], 11: [9, 0],
}

def _sexagenary_index(stem, branch):
    return (6 * stem - 5 * branch) % 60

def _sexagenary_name(index, lang="zh"):
    s, b = index % 10, index % 12
    if lang == "zh":
        return _HEAVENLY_STEMS_ZH[s] + _EARTHLY_BRANCHES_ZH[b]
    return _HEAVENLY_STEMS_EN[s] + "-" + _EARTHLY_BRANCHES_EN[b]

def _hidden_stems_dict(branch):
    stems = _HIDDEN_STEMS.get(branch, [])
    return {"zh": [_HEAVENLY_STEMS_ZH[s] for s in stems], "en": [_HEAVENLY_STEMS_EN[s] for s in stems]}

# 节气近似表（月首"节"，用于无 PyMeeus 时估月柱）
_JIE_LIST = [
    (2, 4, 2), (3, 6, 3), (4, 5, 4), (5, 6, 5), (6, 6, 6), (7, 7, 7),
    (8, 7, 8), (9, 8, 9), (10, 8, 10), (11, 7, 11), (12, 7, 0), (1, 6, 1),
]

def _month_branch_approx(rd, year):
    """根据近似节气日期估算月支。"""
    md = [31, 28 if (year % 4 != 0 or (year % 100 == 0 and year % 400 != 0)) else 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = rd - (365 * (year - 1) + (year - 1) // 4 - (year - 1) // 100 + (year - 1) // 400)
    m = 1
    while m <= 12 and doy > md[m - 1]:
        doy -= md[m - 1]; m += 1
    # 将 (月, 日) 转为年内的序号，方便区间比较
    md_cum = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy_index = md_cum[m - 1] + doy  # 当年第几天
    # 每个"节"对应月支，找所在节气区间
    for i in range(len(_JIE_LIST)):
        jm, jd, br = _JIE_LIST[i]
        jie_doy = md_cum[jm - 1] + jd
        next_i = (i + 1) % len(_JIE_LIST)
        next_jm, next_jd, _ = _JIE_LIST[next_i]
        next_jie_doy = md_cum[next_jm - 1] + next_jd
        # 处理跨年：最后一个节气区间从大雪到立春前
        if next_jie_doy < jie_doy:
            next_jie_doy += 365  # 跨年到下一年
        if jie_doy <= doy_index < next_jie_doy:
            return br
    return _JIE_LIST[-1][2]

def _lichun_before(rd, year):
    """判断给定 R.D. 是否在立春（约 2 月 4 日）之前。

    立春前属上一干支年，立春后（含）属本干支年。
    这是近似判断，用于无 PyMeeus 时的 fallback。
    精确判定请使用 calendar/ganzhi.py::year_ganzhi()。
    """
    # 计算该 RD 在年内的第几天
    md = [31, 28 if (year % 4 != 0 or (year % 100 == 0 and year % 400 != 0)) else 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = rd - (365 * (year - 1) + (year - 1) // 4 - (year - 1) // 100 + (year - 1) // 400)
    # 立春 ≈ 第 35 天（2 月 4 日 = 31 + 4）
    return doy < 35

def _effective_year(rd, year):
    """获取用于年柱的有效年份（考虑立春换年）。"""
    return year - 1 if _lichun_before(rd, year) else year

def _compute_bazi_fallback(rd, year, hours):
    # 年柱：以立春为界
    eff_year = _effective_year(rd, year)
    y_stem, y_branch = (eff_year + 6) % 10, (eff_year + 8) % 12
    y_idx = _sexagenary_index(y_stem, y_branch)
    # 日柱
    d_idx = (10 + (rd - 693596)) % 60
    d_stem, d_branch = d_idx % 10, d_idx % 12
    # 月柱：以节气为界，年干起月（五虎遁）
    m_branch = _month_branch_approx(rd, year)
    m_stem = ((y_stem * 2 + 2) % 10 + (m_branch - 2) % 12) % 10
    m_idx = _sexagenary_index(m_stem, m_branch)
    # 时柱：日干起时（五鼠遁）
    h_branch = ((int(hours) + 1) // 2) % 12
    h_stem = ((d_stem * 2) % 10 + h_branch) % 10
    h_idx = _sexagenary_index(h_stem, h_branch)
    return {
        "year": {"stem": y_stem, "branch": y_branch, "name_zh": _sexagenary_name(y_idx, "zh"), "name_en": _sexagenary_name(y_idx, "en"), "nayin": _NAYIN[y_idx // 2]},
        "month": {"stem": m_stem, "branch": m_branch, "name_zh": _sexagenary_name(m_idx, "zh"), "name_en": _sexagenary_name(m_idx, "en"), "nayin": _NAYIN[m_idx // 2]},
        "day": {"stem": d_stem, "branch": d_branch, "name_zh": _sexagenary_name(d_idx, "zh"), "name_en": _sexagenary_name(d_idx, "en"), "nayin": _NAYIN[d_idx // 2]},
        "hour": {"stem": h_stem, "branch": h_branch, "name_zh": _sexagenary_name(h_idx, "zh"), "name_en": _sexagenary_name(h_idx, "en"), "nayin": _NAYIN[h_idx // 2]},
        "hidden_stems": _hidden_stems_dict(d_branch),
    }

# ========== Calendar 类 ==========
@dataclass
class Calendar:
    solar_date: SolarDate
    locale: str = "zh"
    _rd: int = field(init=False, repr=False, default=0)
    _bazi: Optional[dict] = field(init=False, repr=False, default=None)
    _lunar: Optional[tuple] = field(init=False, repr=False, default=None)
    _solar_terms: Optional[list] = field(init=False, repr=False, default=None)

    @staticmethod
    def from_solar(year, month, day, hours=12.0, locale="zh"):
        sd = SolarDate(year=year, month=month, day=day, hours=hours)
        cal = Calendar(solar_date=sd, locale=locale)
        md = [31, 28 if (year % 4 != 0 or (year % 100 == 0 and year % 400 != 0)) else 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        cal._rd = 365 * (year - 1) + (year - 1) // 4 - (year - 1) // 100 + (year - 1) // 400 + sum(md[:month - 1]) + day
        return cal

    @staticmethod
    def now(locale="zh"):
        dt = datetime.now(timezone.utc)
        return Calendar.from_solar(dt.year, dt.month, dt.day, hours=dt.hour + dt.minute / 60.0, locale=locale)

    @property
    def rd(self):
        if self._rd == 0:
            sd = self.solar_date; y = sd.year
            md = [31, 28 if (y % 4 != 0 or (y % 100 == 0 and y % 400 != 0)) else 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            self._rd = 365 * (y - 1) + (y - 1) // 4 - (y - 1) // 100 + (y - 1) // 400 + sum(md[:sd.month - 1]) + sd.day
        return self._rd

    @property
    def weekday(self):
        return LocaleStr(zh=zh_CN.WEEKDAYS[(self.rd - 1) % 7], en=en_US.WEEKDAYS[(self.rd - 1) % 7])

    @property
    def bazi(self):
        if self._bazi is None:
            self._bazi = _compute_bazi_fallback(self.rd, self.solar_date.year, self.solar_date.hours)
        return self._bazi

    @property
    def full_bazi(self):
        return self.bazi

    @property
    def year_ganzhi(self):
        b = self.bazi["year"]; return LocaleStr(zh=b["name_zh"], en=b["name_en"])
    @property
    def month_ganzhi(self):
        b = self.bazi["month"]; return LocaleStr(zh=b["name_zh"], en=b["name_en"])
    @property
    def day_ganzhi(self):
        b = self.bazi["day"]; return LocaleStr(zh=b["name_zh"], en=b["name_en"])
    @property
    def hour_ganzhi(self):
        if not self.bazi.get("hour"): return None
        b = self.bazi["hour"]; return LocaleStr(zh=b["name_zh"], en=b["name_en"])
    @property
    def bazi_str(self):
        b = self.bazi; return " ".join(b[p]["name_zh"] for p in ("year", "month", "day", "hour") if p in b and b[p]["name_zh"])
    @property
    def shengxiao(self):
        return LocaleStr(zh=_SHENGXIAO_ZH[self.bazi["year"]["branch"]], en=_SHENGXIAO_EN[self.bazi["year"]["branch"]])

    @property
    def lunar(self):
        if self._lunar is None:
            try:
                import chinese_calendar.calendar.chinese as _c
                self._lunar = _c.chinese_from_fixed(self.rd)
            except Exception:
                return None
        if self._lunar is None:
            return None
        return LunarDate(year=self._lunar[0], month=self._lunar[1], day=self._lunar[2], is_leap=self._lunar[3])

    @property
    def lunar_date(self):
        return self.lunar

    @property
    def lunar_str(self):
        lun = self.lunar
        if lun is None: return "" if self.locale == "zh" else "N/A"
        if self.locale == "zh":
            prefix = "闰" if lun.is_leap else ""
            mn = zh_CN.LUNAR_MONTHS[lun.month] if 1 <= lun.month <= 12 else f"{lun.month}月"
            dn = zh_CN.LUNAR_DAYS[lun.day] if 1 <= lun.day <= 30 else f"{lun.day}日"
            return f"农历{lun.year}年{prefix}{mn}{dn}"
        return f"Chinese Year {lun.year}-{lun.month:02d}-{lun.day:02d}"

    @property
    def solar_terms(self):
        if self._solar_terms is None:
            self._solar_terms = []
            try:
                from chinese_calendar.astronomy.solar_terms import solar_terms_of_year, term_name as tn
                terms = solar_terms_of_year(self.solar_date.year)
                self._solar_terms = [{"index": i, "name_zh": tn(i, "zh"), "name_en": tn(i, "en"), "moment": t.day} for i, t in enumerate(terms)]
            except Exception as e:
                print(f"[terms] {e}", file=sys.stderr)
        return self._solar_terms

    @property
    def current_solar_term(self):
        terms = self.solar_terms
        if not terms: return None
        r = float(self.rd)
        for i, t in enumerate(terms):
            if t["moment"] > r:
                if i == 0: return {"name_zh": terms[-1]["name_zh"], "name_en": terms[-1]["name_en"], "index": terms[-1]["index"]}
                return {"name_zh": terms[i-1]["name_zh"], "name_en": terms[i-1]["name_en"], "index": terms[i-1]["index"]}
        return {"name_zh": terms[-1]["name_zh"], "name_en": terms[-1]["name_en"], "index": terms[-1]["index"]}

    @property
    def next_solar_term(self):
        terms = self.solar_terms
        if not terms: return None
        for t in terms:
            if t["moment"] > float(self.rd):
                return {"name_zh": t["name_zh"], "name_en": t["name_en"], "index": t["index"], "rd": t["moment"]}
        return None

    def to_dict(self):
        b = self.bazi
        result = {
            "gregorian": {"year": self.solar_date.year, "month": self.solar_date.month, "day": self.solar_date.day, "hours": self.solar_date.hours},
            "bazi": {
                "year": {"name_zh": b["year"]["name_zh"], "name_en": b["year"]["name_en"], "nayin": b["year"]["nayin"]},
                "month": {"name_zh": b["month"]["name_zh"], "name_en": b["month"]["name_en"], "nayin": b["month"]["nayin"]},
                "day": {"name_zh": b["day"]["name_zh"], "name_en": b["day"]["name_en"], "nayin": b["day"]["nayin"]},
            },
        }
        if b.get("hour"):
            result["bazi"]["hour"] = {"name_zh": b["hour"]["name_zh"], "name_en": b["hour"]["name_en"], "nayin": b["hour"]["nayin"]}
        result["shengxiao"] = {"zh": self.shengxiao.zh, "en": self.shengxiao.en}
        result["weekday_zh"] = self.weekday.zh
        result["weekday_en"] = self.weekday.en
        result["rd"] = self.rd
        result["bazi_str"] = self.bazi_str
        lun = self.lunar
        if lun is not None:
            result["lunar"] = {"year": lun.year, "month": lun.month, "day": lun.day, "is_leap": lun.is_leap, "date_str": self.lunar_str}
        st = self.current_solar_term
        if st: result["solar_term"] = st
        nst = self.next_solar_term
        if nst: result["next_solar_term"] = nst
        return result

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def __str__(self):
        if self.locale == "zh":
            return f"【{self.solar_date.year}年{self.solar_date.month}月{self.solar_date.day}日】\n  农历: {self.lunar_str or '（需PyMeeus）'}\n  八字: {self.bazi_str}\n  生肖: {self.shengxiao.zh}"
        return f"[{self.solar_date.year}-{self.solar_date.month:02d}-{self.solar_date.day:02d}]\n  Lunar: {self.lunar_str or '(PyMeeus needed)'}\n  Bazi:  {self.bazi_str}\n  Zodiac: {self.shengxiao.en}"
