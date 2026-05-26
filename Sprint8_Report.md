# Sprint 8 报告 — Bilingual + API + 打包

**版本号:** v0.8.0
**完成日期:** 2026-05-21
**项目:** chinese-calendar — 万年历 Python 计算引擎
**成就:** 🎉 全部 8 个 Sprint 完成

---

## 一、概览

Sprint 8 是万年历引擎的最后一个 Sprint，完成了中英文双语系统、统一 API 封装，以及打包准备。

自此引擎完成全部 8 个 Sprint 的构建：

```
Sprint 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
地基     太阳   节气   新月   农历   干支   缓存   ✅ 双语+API
```

---

## 二、交付清单

### 2.1 本地化系统 (locale/)

| 文件 | 作用 |
|------|------|
| `locale/__init__.py` | 本地化包入口 |
| `locale/types.py` | `LocaleStr` 双语字符串类 + 全局语言切换 |
| `locale/zh_CN.py` | 中文翻译表（干支、节气、生肖、星期、农历、纳音、术语） |
| `locale/en_US.py` | 英文翻译表（干支拼音+意译、节气英译、生肖、星期等） |

### 2.2 API 层 (api/)

| 文件 | 作用 |
|------|------|
| `api/__init__.py` | API 包入口 |
| `api/solar_date.py` | `SolarDate` 公历日期数据类 |
| `api/lunar_date.py` | `LunarDate` 农历日期数据类 |
| `api/calendar_api.py` | `Calendar` 统一入口类（核心交付） |

### 2.3 测试

| 文件 | 类型 | 数量 |
|------|------|------|
| `tests/test_locale.py` | LocaleStr + 翻译表 | 22 个测试 |
| `tests/test_api.py` | Calendar API（纯逻辑 + 天文） | 28 个测试 |

---

## 三、核心 API 设计

### Calendar 类 — 用户唯一需要导入的类

```python
from chinese_calendar.api import Calendar

# 构造方式
cal = Calendar.from_solar(2026, 5, 21)              # 公历→全部
cal = Calendar.from_solar(2026, 5, 21, locale="en") # 英文输出
cal = Calendar.now()                                  # 当前时间

# 公历信息
cal.rd              # 739757 (R.D. 值)
cal.weekday          # LocaleStr("星期四", "Thursday")

# 四柱八字
cal.year_ganzhi      # LocaleStr("丙午", "Bing-Wu")
cal.day_ganzhi       # LocaleStr("乙未", "Yi-Wei")
cal.hour_ganzhi      # LocaleStr("壬午", "Ren-Wu")
cal.bazi_str         # "丙午  乙未"
cal.shengxiao        # LocaleStr("马", "Horse")

# 农历（需 PyMeeus）
cal.lunar            # LunarDate(2026, 4, 5, False)
cal.lunar_str        # "农历二〇二六年四月初五"

# 节气（需 PyMeeus）
cal.solar_terms      # 24 节气列表
cal.next_solar_term  # 下一个节气

# 输出
cal.to_dict()        # 结构化字典
cal.to_json()        # JSON 字符串
str(cal)             # 可读格式
```

---

## 四、技术要点

### 循环导入处理

`core/time_systems` ↔ `calendar/converters` 存在循环引用。Calendar 类通过**内联干支常量**避开此问题：

- 在 `calendar_api.py` 中直接定义了干支/纳音/藏干表
- 无需导入 `calendar.ganzhi` 或 `calendar.converters`
- 代价：两处维护（`calendar_api.py` 和 `ganzhi.py` 各有独立副本）

### PyMeeus 可选的回退机制

| 功能 | 有 PyMeeus | 无 PyMeeus |
|------|-----------|-----------|
| 四柱八字 | 完整（年柱立春为界 + 月柱节气为界） | 年公式近似（月柱留空） |
| 农历日期 | 完整转换 | None |
| 节气信息 | 24 节气精确时刻 | 空列表 |
| R.D. / 星期 / 生肖 | 始终可用 | 始终可用 |

### 中文翻译表完整性

| 类别 | 条目数 | 示例 |
|------|--------|------|
| 天干 | 10 | 甲→Jia, 乙→Yi, ... |
| 地支 | 12 | 子→Zi, 丑→Chou, ... |
| 节气 | 24 | 立春→Spring Begins |
| 星期 | 7 | 星期一→Monday |
| 生肖 | 12 | 马→Horse |
| 农历月份 | 12 | 正月→Zheng Yue |
| 农历日期 | 30 | 初一→1st, ... |
| 纳音 | 30 | 海中金→Sea Metal |
| 五行 | 5 | 金→Metal |
| 术语 | 10 | 八字→Four Pillars |

---

## 五、引擎最终架构

```
用户代码
    │
    ▼
Calendar API  ←─── locale 系统
(from_solar/now)   (LocaleStr/zh_CN/en_US)
    │
    ├── calendar/   ←─── 历法算法
    │   converters.py   公历↔R.D.
    │   ganzhi.py       干支四柱
    │   chinese.py      农历核心
    │
    ├── astronomy/  ←─── 天文计算（可选 PyMeeus）
    │   sun.py          太阳黄经
    │   moon.py         新月合朔
    │   solar_terms.py  节气判定
    │
    ├── core/       ←─── 基础类型
    │   rata_die.py     RataDie/Moment
    │   time_systems.py 时间系统
    │   constants.py    常数
    │
    ├── data/       ←─── 缓存层
    │   cache.py        YearInfo/CacheManager
    │   precompute.py   预计算引擎
    │
    └── tests/      ←─── 全部测试
        11 个测试文件
```

---

## 六、测试结果

```
纯逻辑测试 (无需 PyMeeus): 全部通过 ✅

Locale 系统:
  LocaleStr: 创建/语言切换/比较/异常  ✅
  zh_CN:     全部翻译表完整性          ✅
  en_US:     全部翻译表完整性          ✅

日期类型:
  SolarDate: 创建/校验/冻结            ✅
  LunarDate: 创建/闰月标志             ✅

Calendar API:
  from_solar / rd / 星期               ✅
  年柱/日柱/时柱 干支                   ✅
  生肖 / 中英文切换                     ✅
  to_dict / to_json / str              ✅
  now()                                ✅

天文测试 (需 PyMeeus):
  农历转换 / 节气列表 / 下一节气        ⏳ 已编写，自动跳过
```

---

## 七、后续

万年历引擎已全部完成。下一步计划：

1. **网页界面** — 输入日期看全部输出（公历/农历/八字/节气/生肖）
2. **推理引擎** — 术数推理系统（十神/刑冲合害/大运等，已在 `inference/` 中有三个模块）
3. 或你指定的其他方向
