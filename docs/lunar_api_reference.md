# lunar_python API 全收录 — 按模块分类参考

> **来源：** https://github.com/6tail/lunar-python（6tail 维护，多语言支持）
> **说明：** 收录 lunar_python 所有术数相关 API，开发各模块时直接调用。
> **策略：** 先用 lunar_python 快速获得数据，将来逐步替换为自有模块实现。
> **安装：** `pip install lunar_python`
> **导入：** `from lunar_python import Lunar` / `l = Lunar.fromDate(datetime(y,m,d,12,0,0))`

---

## 一、建除十二神 / 十二黄黑道日（`D:\c_zheri`）

```python
l.get_today12DayOfficer()       # → "建" / "除" / "满" / "平" / "定" / "执"
                                #   "破" / "危" / "成" / "收" / "开" / "闭"
```

十二神顺序：建、除、满、平、定、执、破、危、成、收、开、闭
黄黑道口诀：建满平收黑，除危定执黄，成开皆可用，闭破不相当

---

## 二、玄空飞星（`D:\c_xuankong`）

```python
l.getYearNineStar()             # 年飞星 → NineStar 对象
l.getMonthNineStar()            # 月飞星
l.getDayNineStar()              # 日飞星
l.getTimeNineStar()             # 时飞星

# NineStar 对象属性：
.getName()      # 星名（一白、二黑、三碧、四绿、五黄、六白、七赤、八白、九紫）
.getColor()     # 颜色
.getWuXing()    # 五行
.getPosition()  # 宫位（1~9）
.getXiaoYun()   # 小运
```

---

## 三、二十八星宿（`D:\c_xuankong` / `D:\c_fengshui`）

```python
l.getXiu()                      # → "角木蛟"
l.getXiuLuck()                  # → "吉"/"凶"
l.getXiuSong()                  # 星宿诗诀
l.getTimeXiu()                  # 时辰星宿
```

顺序：角亢氐房心尾箕（青龙）→ 斗牛女虚危室壁（玄武）
　　　奎娄胃昴毕觜参（白虎）→ 井鬼柳星张翼轸（朱雀）

---

## 四、彭祖百忌（`D:\c_zheri` / `D:\c_bazi`）

```python
l.getPengZuGan()                # 天干百忌："甲不开仓财物耗散"
l.getPengZuZhi()                # 地支百忌："子不问卜自惹祸殃"
```

---

## 五、每日宜忌（`D:\c_zheri` 核心）

```python
l.getDayYi()                    # 宜 → ["嫁娶","纳采","出行",...]
l.getDayJi()                    # 忌 → ["动土","破土",...]
l.getDayJiShen()                # 吉神
l.getDayXiongSha()              # 凶煞

l.getTimeYi()                   # 时辰宜
l.getTimeJi()                   # 时辰忌

# 方位
l.getDayPositionXiDesc()        # 喜神："喜神在正南"
l.getDayPositionCaiDesc()       # 财神
l.getDayPositionFuDesc()        # 福神
l.getDayPositionYangGuiDesc()   # 阳贵神
l.getDayPositionYinGuiDesc()    # 阴贵神

l.getPositionXi()               # 喜神（短）
l.getPositionCai()              # 财神
l.getPositionFu()               # 福神
l.getPositionYangGui()          # 阳贵神
l.getPositionYinGui()           # 阴贵神
```

---

## 六、冲煞 / 生肖（`D:\c_zheri` / `D:\c_bazi`）

```python
l.getDayChong()                 # 冲天干："甲"
l.getDayChongDesc()             # 冲描述："冲猴(庚申)"
l.getDayChongShengXiao()        # 冲生肖："猴"
l.getDaySha()                   # 煞方向："南"
l.getDayShengXiao()             # 日生肖

l.getTimeChong()                # 时辰冲
l.getTimeChongDesc()
l.getTimeChongShengXiao()
l.getTimeShengXiao()
```

---

## 七、八字 / 四柱（`D:\c_bazi` 核心）

```python
# 年柱
l.getYearInGanZhi()              # 正月初一换年
l.getYearInGanZhiByLiChun()      # 立春换年（与我们一致）
l.getYearGan()                   # 年干
l.getYearZhi()                   # 年支
l.getYearShengXiao()             # 年生肖
l.getYearShengXiaoByLiChun()     # 年生肖（立春换年）

# 月柱
l.getMonthInGanZhi()             # 月柱
l.getMonthInGanZhiExact()        # 月柱（精确节气）
l.getMonthGan()
l.getMonthZhi()

# 日柱
l.getDayInGanZhi()               # 日柱
l.getDayInGanZhiExact()
l.getDayGan()
l.getDayZhi()

# 时柱
l.getTimeInGanZhi()              # 时柱
l.getTimeGan()
l.getTimeZhi()

# 组合
l.getBaZi()                      # "甲辰 丙寅 甲辰 庚午"
l.getBaZiWuXing()                # 八字五行
l.getBaZiNaYin()                 # 八字纳音
l.getBaZiShiShenGan()            # 十神（天干）
l.getBaZiShiShenZhi()            # 十神（地支）
```

---

## 八、纳音（`D:\c_bazi`）

```python
l.getYearNaYin()                 # 年柱纳音
l.getMonthNaYin()                # 月柱纳音
l.getDayNaYin()                  # 日柱纳音
l.getTimeNaYin()                 # 时柱纳音
```

---

## 九、神煞 / 旬空（`D:\c_bazi`）

```python
l.getDayLu()                     # 日禄
l.getDayXun()                    # 日旬
l.getDayXunKong()                # 日空亡："戌亥"
l.getMonthXun()                  # 月旬
l.getMonthXunKong()              # 月空亡
l.getYearXun()                   # 年旬
l.getYearXunKong()               # 年空亡

l.getDayTianShen()               # 天神
l.getDayTianShenType()
l.getDayTianShenLuck()
```

---

## 十、时辰吉凶（`D:\c_zheri`）

```python
l.getTimes()                     # 时辰列表
l.getTimeYi()                    # 时辰宜
l.getTimeJi()                    # 时辰忌
l.getTimeNaYin()                 # 时辰纳音
l.getTimeShengXiao()             # 时辰生肖
l.getTimeChong()                 # 时辰冲
l.getTimeXun()                   # 时辰旬
l.getTimeXunKong()               # 时辰空亡
l.getTimePositionXi()            # 时辰喜神
l.getTimePositionCai()           # 时辰财神
l.getTimePositionFu()            # 时辰福神
```

---

## 十一、年神 / 月神 / 胎神（`D:\c_fengshui` / `D:\c_zheri`）

```python
l.getYearPositionTaiSui()        # 太岁方位
l.getYearPositionTaiSuiDesc()
l.getMonthPositionTai()
l.getMonthPositionTaiSui()
l.getMonthPositionTaiSuiDesc()
```

---

## 十二、月相 / 候 / 节气

```python
l.getYueXiang()                  # 月相
l.getHou()                       # 七十二候
l.getWuHou()                     # 五候
l.getSeason()                    # 季节
l.getCurrentJieQi()              # 当前节气
```

---

## 十三、常用构造方式

```python
from lunar_python import Lunar
from datetime import datetime

# 从公历 datetime 构造（最常用）
l = Lunar.fromDate(datetime(2026, 6, 10, 12, 0, 0))

# 从农历构造
l = Lunar.fromYmd(2026, 4, 25)   # 农历 2026 年四月廿五

# 获取公历
solar = l.getSolar()
solar.getYear()
solar.getMonth()
solar.getDay()

# 农历属性
l.getYear()                      # 农历年
l.getMonth()                     # 农历月（负数=闰月）
l.getDay()                       # 农历日
# 闰月判断：l.getMonth() < 0

# 完整输出
l.toFullString()                 # "二〇二六年四月初八 丙午(马)年..."
l.toString()                     # 简短版
```

---

## 十四、按模块速查

| 模块 | 主要 API |
|------|---------|
| `c_zheri` | `get_today12DayOfficer()`, `getDayYi()`, `getDayJi()`, `getDayChongDesc()`, `getDaySha()`, `getDayPositionXxxDesc()`, `getTimeYi/Ji()` |
| `c_xuankong` | `getYear/Month/Day/TimeNineStar()`, `getXiu()`, `getXiuLuck()` |
| `c_bazi` | `getYear/Month/Day/TimeInGanZhi()`, `getBaZi*()`, `getNaYin()`, `getXunKong()`, `getBaZiShiShen*()` |
| `c_fengshui` | `getYear/MonthNineStar()`, `getPositionTaiSui()`, `getXiu()` |
| `c_qimen` | 无直接 API，需自实现 |
| `c_zhanbu` | 无直接 API，需自实现 |

> **备注：** 将来各模块完成后，可逐步替换 lunar_python 为自有实现。
> 接口设计可参考此文档保持兼容。
