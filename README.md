# Chinese Calendar Engine (万年历引擎)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**A precise, verifiable, bilingual (Chinese/English) Chinese lunisolar calendar calculation engine.**  
**精确、可验证、中英文双语的万年历 Python 计算引擎。**

Built on Dershowitz & Reingold *Calendrical Calculations* and Meeus *Astronomical Algorithms*.  
基于 Dershowitz & Reingold《Calendrical Calculations》和 Meeus《Astronomical Algorithms》构建。

---

## Features / 功能

### Core / 核心
- ✅ **Gregorian ↔ Lunar** — bidirectional conversion (公历↔农历双向转换)
- ✅ **24 Solar Terms** (二十四节气) — precise to < 60 seconds
- ✅ **Four Pillars (BaZi / 四柱八字)** — with Li Chun year boundary (立春换年)
- ✅ **Sexagenary Cycle / Heavenly Stems & Earthly Branches** (天干地支)
- ✅ **Shengxiao / Zodiac Animals** (生肖)
- ✅ **Nayin / Na Yin** (纳音五行)
- ✅ **Hidden Stems / 藏干**

### Cultural Layer / 术数文化层(via lunar_python)
- ✅ **28 Lunar Mansions** (二十八星宿)
- ✅ **Peng Zu Hundred Taboos** (彭祖百忌)
- ✅ **Daily Yi/Ji** (每日宜忌)
- ✅ **Chong/Sha** (冲煞)
- ✅ **Xi Shen/Cai Shen/Fu Shen** (喜神/财神/福神方位)

### Accuracy / 精度
- **15/15 dates** exact match vs lunar_python (1900-2026 sample)
- Lunar month boundaries: **±0 days** (after astronomy-engine refinement)
- Solar terms: VSOP87 precision
- Zero-dependency operation for BaZi/Weekday/Zodiac

---

## Quick Start / 快速开始

```bash
# Install / 安装
pip install pymeeus astronomy-engine lunar_python

# Or minimal (no astronomy) / 或最小安装
pip install pymeeus

# Test / 测试
cd chinese_calendar
python -c "
from chinese_calendar.api import Calendar
cal = Calendar.from_solar(2026, 5, 24)
print(cal.bazi_str)   # 丙午 癸巳 戊戌 戊午
print(cal.lunar_str)  # 农历2026年四月初八
print(cal.shengxiao.zh)  # 马
"
```

### Web Interface / 网页界面

```bash
python web_interface/server.py
# Open http://localhost:8765
```

---

## Architecture / 架构

```
┌──────────────────────────────────┐
│  Web UI (test interface)         │
├──────────────────────────────────┤
│  API + Locale (Calendar class)   │
├──────────────────────────────────┤
│  Calendar Layer                  │
│  (Gregorian/Lunar/Ganzhi ↔ R.D.) │
├──────────────────────────────────┤
│  Astronomy Layer                 │
│  (Sun/Moon/Solar Terms)          │
├──────────────────────────────────┤
│  Core Layer                      │
│  (RataDie/Time Systems/Constants) │
└──────────────────────────────────┘
```

**Rata Die (R.D.)** is the universal bridge — every calendar converts to/from R.D., never directly.

---

## Dependencies / 依赖

| Package | Required | Purpose |
|---------|----------|---------|
| Python ≥3.10 | ✅ | Core engine runs with zero deps for BaZi |
| PyMeeus 0.5.12 | Optional | Solar longitude / solar terms (VSOP87) |
| astronomy-engine 2.1+ | Optional | New moon refinement (VSOP87) |
| lunar-python 1.4+ | Optional | Cultural layer (mansions, taboos, etc.) |

---

## Validation / 验证

15-date cross-validation against 6tail/lunar-python — **100% match**:
- Spring Festival dates (春节): 2026, 2000, 1980, 1949, 1990, 1930 ✅
- Leap month (闰月): 2023 ✅
- Historical dates: 1942 ✅
- All month boundaries: ±0 days ✅

---

## Project Structure / 目录结构

```
chinese_calendar/
├── core/           # RataDie, time systems, constants
├── astronomy/      # Sun (VSOP87), Moon, solar terms
├── calendar/       # Converters, Chinese lunar, Ganzhi
├── api/            # Calendar unified class, lunar culture
├── locale/         # Bilingual (zh/en) strings
├── data/           # Cache layer, precompute
├── inference/      # Future: Shishen, Dayun (placeholder)
└── tests/           # Pytest suite
web_interface/      # Test server + HTML UI
```

---

## License / 许可

MIT

---

## References / 参考

- Dershowitz & Reingold, *Calendrical Calculations*
- Meeus, *Astronomical Algorithms*
- VSOP87 — French Bureau des Longitudes
- [6tail/lunar-python](https://github.com/6tail/lunar-python) — cross-validation reference
- [cosinekitty/astronomy](https://github.com/cosinekitty/astronomy) — Astronomy Engine
