# Chinese Calendar Engine (万年历引擎)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Lunar Accuracy](https://img.shields.io/badge/Lunar_Accuracy-100%25_(1901--2100)-brightgreen)](https://github.com/XonLoke/-Chinese-Calender)

**A precise, verifiable, bilingual (Chinese/English) Chinese lunisolar calendar calculation engine.**  
**精确、可验证、中英文双语的万年历 Python 计算引擎。**

Built on Dershowitz & Reingold *Calendrical Calculations* and Meeus *Astronomical Algorithms*.  
基于 Dershowitz & Reingold《Calendrical Calculations》和 Meeus《Astronomical Algorithms》构建。

---

## Core Positioning / 核心定位

**This is a CALCULATION ENGINE, not a lookup library.**  
**这是天文计算引擎，不是查表库。**

Most Chinese calendar libraries (such as 6tail/lunar-python, cnlunar, etc.) use **precomputed lookup tables** to provide their data. This engine is fundamentally different — it **computes everything from first principles** using VSOP87 solar theory and Dershowitz & Reingold algorithms, then **validates against authoritative data**.  
市面上的农历库（如 6tail/lunar-python、cnlunar 等）大多使用**预计算查表法**。本引擎完全不同——它通过 VSOP87 太阳理论和 D&R 算法**从头计算**，再用权威数据**验证**。

### What makes this engine unique / 本引擎的独特之处

| Aspect / 对比项 | This Engine / 本引擎 | Other Libraries / 其他库 |
|--------|------------|----------------|
| **Core method / 核心方法** | Astronomical calculation (VSOP87, Newton) 天文计算 | Precomputed lookup tables 预计算查表 |
| **Lunar data / 农历数据** | D&R algorithm → verified against HKO 100% 算法计算→HKO 验证 | Direct table query 直接查表 |
| **Solar terms / 节气** | VSOP87 + Newton solver 天文求解 | Table interpolation 查表插值 |
| **Transparency / 透明度** | Every step verifiable 每一步可验证 | Black box 黑箱（表来源不明）|
| **Zero-dependency / 零依赖** | BaZi/Zodiac/Weekday with no pip install 不用安装任何库 | Require full library 需安装完整库 |
| **Accuracy / 准确率** | 100% vs HKO (1901-2100) | Depends on table source 取决于表来源 |
| **Architecture / 架构** | Modular 4-layer 模块化四层 | Monolithic 单体 |

### When to use this engine / 什么时候用本引擎

✅ You need a **transparent, verifiable** calendar foundation  
✅ 你需要**透明可验证**的历法基础  
✅ You want **astronomical-grade precision** for solar terms and lunar months  
✅ 你需要节气/农历的**天文级精度**  
✅ You need **bilingual (zh/en)** output  
✅ 你需要**中英文双语**输出  
✅ You plan to build **metaphysics modules** (BaZi, Flying Stars, Qi Men, etc.)  
✅ 你计划构建八字、飞星、奇门等**术数模块**  
✅ You want to **understand how** calendar calculations work  
✅ 你想**理解历法计算的原理**

### When other libraries may be better / 什么时候用其他库更好

❌ You need a quick, zero-setup calendar utility → use 6tail/lunar-python  
❌ 你需要快速、零配置的历法工具  
❌ You need Buddhist/Taoist calendars → 6tail/lunar-python has these  
❌ 你需要佛历、道历  
❌ You need multi-language support (Java, JS, Go, etc.)  
❌ 你需要多语言支持（Java、JS、Go 等）

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
- **100% exact match** vs Hong Kong Observatory data (1901-2100, 73,049 dates)
- **100% exact match** vs lunar_python (500 random dates)
- Spring Festival (春节) dates: all correct 1900-2100 — 春节日期全部正确
- Leap month years: all correct — 闰月年份全部正确
- 24 Solar Terms: VSOP87 precision via astronomy-engine — 24节气 VSOP87 天文精度
- Zero-dependency operation for BaZi/Weekday/Zodiac — 八字/星期/生肖零依赖

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
**Rata Die（R.D.）** 是通用桥梁——所有历法都通过 R.D. 互相转换，不直接依赖。

---

## Dependencies / 依赖

| Package / 包 | Required / 必需 | Purpose / 用途 |
|---------|----------|---------|
| Python ≥3.10 | ✅ | Core engine runs with zero deps for BaZi / 八字等核心功能零依赖 |
| PyMeeus 0.5.12 | Optional 可选 | Solar longitude / solar terms (VSOP87) 太阳黄经/节气 |
| astronomy-engine 2.1+ | Optional 可选 | New moon refinement (VSOP87) 新月精化 |
| lunar-python 1.4+ | Optional 可选 | Cultural layer (mansions, taboos, etc.) 术数文化层（星宿、宜忌等） |

---

## Validation / 验证

**Hong Kong Observatory data** (73,049 dates, 1901-2100) — **100% match** ✅  
**香港天文台数据**（73,049 条，1901-2100）— **100% 一致**
- Random dates: **100%** (500 random samples) — 随机日期抽样 500 组
- Spring Festival (春节): all 201 years correct — 201 年春节全部正确
- Leap month years: all correct — 闰月年份全部正确
- 500-edge-date test: **100%** — 500 组边界日期测试
- 15-date cross-validation vs lunar_python: **100%** — 与 lunar_python 交叉验证

---

## Project Structure / 目录结构

```
chinese_calendar/
├── core/           # RataDie, time systems, constants / 核心类型、时间系统、常数
├── astronomy/      # Sun (VSOP87), Moon, solar terms / 太阳、月亮、节气
├── calendar/       # Converters, Chinese lunar, Ganzhi / 历法转换、农历、干支
├── api/            # Calendar unified class, lunar culture / Calendar 统一接口、术数文化层
├── locale/         # Bilingual (zh/en) strings / 中英文双语字符串
├── data/           # Cache layer, precompute / 缓存层、预计算
├── inference/      # Future: Shishen, Dayun / 未来：十神、大运（占位）
└── tests/           # Pytest suite / 测试套件
web_interface/      # Test server + HTML UI / 测试服务器 + 网页界面
```

---

## License / 许可

MIT

---

## References / 参考

- Dershowitz & Reingold, *Calendrical Calculations* — 历法算法经典著作
- Meeus, *Astronomical Algorithms* — 天文算法标准参考
- VSOP87 — French Bureau des Longitudes — 行星运动理论
- [6tail/lunar-python](https://github.com/6tail/lunar-python) — cross-validation reference / 交叉验证参考
- [cosinekitty/astronomy](https://github.com/cosinekitty/astronomy) — Astronomy Engine / 天文计算引擎
- [cnlunar](https://github.com/OPN48/cnlunar) — 协纪辨方书黄历库
- [Hong Kong Observatory](https://www.weather.gov.hk/sc/gts/time/conversion.htm) — HKO calendar data / 香港天文台历法数据
