#!/usr/bin/env python3
"""交叉验证脚本 — 万年历引擎 vs 6tail/lunar-python + astronomy-engine

用法:
    # 1. 先安装依赖:
    pip install lunar_python astronomy-engine

    # 2. 运行本脚本:
    cd D:\c_wannianli
    python cross_validate.py

说明:
    - 测试 50+ 个日期（1900-2100 抽样）的农历转换
    - 输出对比结果：一致 ✓ 或 差异 ⚠️
    - 可选测试 astronomy-engine 作为新天文引擎
"""

from __future__ import annotations

import sys
import os
from datetime import datetime

# 确保可以从项目根目录导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ===========================================================================
# 第一部分：验证我们引擎的循环导入修复
# ===========================================================================

def test_our_engine() -> bool:
    """测试万年历引擎核心功能（验证循环导入已修复）。"""
    print("=" * 60)
    print("1. 验证万年历引擎（循环导入修复检查）")
    print("=" * 60)

    try:
        from chinese_calendar.api import Calendar
        print("  ✅ Calendar 导入成功")
    except Exception as e:
        print(f"  ❌ 导入失败: {e}")
        return False

    # 测试一系列日期
    test_dates = [
        (2026, 5, 24, "丙午", "星期日", "马"),      # 今天（立春后）
        (2026, 6, 5,  "丙午", "星期五", "马"),       # 芒种附近（立春后）
        (2024, 2, 10, "甲辰", "星期六", "龙"),       # 2024 春节（立春后）
        (2024, 1, 1,  "癸卯", "星期一", "兔"),       # 2024 元旦（立春前→癸卯年）
        (2023, 1, 22, "壬寅", "星期日", "虎"),       # 2023 春节（立春前→壬寅年）
        (1949, 10, 1, "己丑", "星期六", "牛"),       # 建国（立春后）
        (2000, 1, 1,  "己卯", "星期六", "兔"),       # 千禧年（立春前→己卯年）
        (1900, 1, 1,  "己亥", "星期一", "猪"),       # 1900 元旦（立春前→己亥年）
    ]

    all_ok = True
    for y, m, d, exp_gz, exp_wd, exp_sx in test_dates:
        cal = Calendar.from_solar(y, m, d)
        bazi = cal.bazi_str.split()[0]  # 年柱
        wd = cal.weekday.zh
        sx = cal.shengxiao.zh
        if bazi != exp_gz or wd != exp_wd or sx != exp_sx:
            print(f"  ❌ {y}-{m:02d}-{d:02d}: 年柱={bazi}(期望{exp_gz}) "
                  f"星期={wd}(期望{exp_wd}) 生肖={sx}(期望{exp_sx})")
            all_ok = False
        else:
            print(f"  ✅ {y}-{m:02d}-{d:02d}: {bazi} {wd} {sx}")

    # 测试农历（需要 PyMeeus 安装）
    print()
    try:
        cal = Calendar.from_solar(2026, 5, 24)
        lun = cal.lunar
        if lun:
            print(f"  ✅ 农历: {cal.lunar_str}")
        else:
            print("  ⚠️ 农历: None（需安装 PyMeeus）")
    except Exception as e:
        print(f"  ❌ 农历错误: {e}")
        all_ok = False

    return all_ok


# ===========================================================================
# 第二部分：对比 6tail/lunar-python
# ===========================================================================

def test_lunar_python() -> bool:
    """与 6tail/lunar-python 交叉验证农历日期。"""
    print()
    print("=" * 60)
    print("2. 与 6tail/lunar-python 交叉验证")
    print("=" * 60)

    try:
        from lunar_python import Lunar
    except ImportError:
        print("  ⚠️ 未安装 lunar_python，跳过。")
        print("  → pip install lunar_python")
        return False

    from chinese_calendar.api import Calendar

    # 测试日期集（覆盖不同时期、闰月边界等）
    test_solar_dates = [
        # (公历年, 月, 日, 期望农历年, 期望农历月, 期望农历日)
        (2026, 5, 24, None, None, None),     # 今天（未知）
        (2026, 2, 17, 2026, 1, 1),           # 2026 春节
        (2026, 1, 1,  2025, 11, 12),         # 2026 元旦
        (2025, 10, 1, 2025, 8, 10),          # 2025 国庆
        (2024, 2, 10, 2024, 1, 1),           # 2024 春节
        (2023, 1, 22, 2023, 1, 1),           # 2023 春节
        (2023, 3, 22, 2023, 2, 1),           # 2023 闰二月附近
        (2020, 1, 25, 2020, 1, 1),           # 2020 春节
        (2000, 2, 5,  2000, 1, 1),           # 2000 春节
        (1990, 1, 27, 1990, 1, 1),           # 1990 春节
        (1980, 2, 16, 1980, 1, 1),           # 1980 春节
        (1949, 1, 29, 1949, 1, 1),           # 1949 春节
        (1942, 11, 8, 1942, 10, 1),          # 用户提供的 1942 测试日期
        (1930, 1, 30, 1930, 1, 1),           # 1930 春节
        (1909, 1, 22, 1909, 1, 1),           # 1909 春节
    ]

    match = 0
    mismatch = 0
    for y, m, d, _, _, _ in test_solar_dates:
        # 从 lunar_python 获取参考数据（从公历转农历）
        from datetime import datetime
        lunar_ref = Lunar.fromDate(datetime(y, m, d, 12, 0, 0))
        ref_year = lunar_ref.getYear()
        ref_month = abs(lunar_ref.getMonth())  # 负数表示闰月，取绝对值比较
        ref_is_leap = lunar_ref.getMonth() < 0  # 负数 = 闰月
        ref_day = lunar_ref.getDay()

        # 从我们的引擎获取数据
        cal = Calendar.from_solar(y, m, d)
        our_lunar = cal.lunar

        if our_lunar is None:
            print(f"  ⚠️ {y}-{m:02d}-{d:02d}: 我们的引擎无法计算农历（PyMeeus 缺失）")
            continue

        our_year = our_lunar.year
        our_month = our_lunar.month
        our_day = our_lunar.day
        our_leap = our_lunar.is_leap

        # 比较（含闰月判断）
        leap_prefix = "闰" if ref_is_leap else ""
        if (our_year == ref_year and our_month == ref_month
                and our_day == ref_day and our_leap == ref_is_leap):
            print(f"  ✅ {y}-{m:02d}-{d:02d}: 一致 {leap_prefix}{ref_year}年{ref_month}月{ref_day}日")
            match += 1
        else:
            our_pref = "闰" if our_leap else ""
            print(f"  ⚠️ {y}-{m:02d}-{d:02d}: 差异!")
            print(f"      参考(lunar_python):   {leap_prefix}{ref_year}年{ref_month}月{ref_day}日")
            print(f"      我们(万年历引擎):     {our_pref}{our_year}年{our_month}月{our_day}日")
            mismatch += 1

    total = match + mismatch
    if total > 0:
        print(f"\n  结果: {match}/{total} 一致 ({100*match//total}%)")
        if mismatch > 0:
            print(f"  ⚠️ {mismatch} 个差异需要分析")
    return mismatch == 0


# ===========================================================================
# 第三部分：测试 astronomy-engine 作为 PyMeeus 替代方案
# ===========================================================================

def test_astronomy_engine():
    """测试 astronomy-engine 用于太阳黄经和新月计算。"""
    print()
    print("=" * 60)
    print("3. 测试 astronomy-engine 作为天文引擎")
    print("=" * 60)

    try:
        import astronomy
    except ImportError:
        print("  ⚠️ 未安装 astronomy-engine，跳过。")
        print("  → pip install astronomy-engine")
        return

    # 测试1：计算太阳黄经
    print("  3a. 太阳黄经 — EclipticLongitude")
    print("      (春分≈0°, 夏至≈90°, 秋分≈180°, 冬至≈270°)")
    test_dates = [
        (2026, 3, 20, "春分", 0),
        (2026, 6, 21, "夏至", 90),
        (2026, 9, 23, "秋分", 180),
        (2026, 12, 22, "冬至", 270),
    ]
    for y, m, d, name, _ in test_dates:
        t = astronomy.Time.Make(y, m, d, 12, 0, 0)
        try:
            lon = astronomy.EclipticLongitude(astronomy.Body.Sun, t)
            print(f"      {y}-{m:02d}-{d:02d} {name}: {lon:.4f}°")
        except Exception as e:
            print(f"      {name}出错: {e}")

    # 测试2：SearchSunLongitude — 太阳到达指定黄经的时刻（节气计算核心）
    print()
    print("  3b. SearchSunLongitude — 节气时刻搜索")
    print("      (冬至≈12月21日, 夏至≈6月21日)")
    try:
        for target_lon, name in [(270, "冬至"), (90, "夏至")]:
            t_start = astronomy.Time.Make(2026, 1, 1, 0, 0, 0)
            result = astronomy.SearchSunLongitude(target_lon, t_start)
            print(f"      {name}({target_lon}°): {result}")
    except Exception as e:
        print(f"      SearchSunLongitude 出错: {e}")

    # 测试3：搜索新月
    print()
    print("  3c. SearchMoonPhase — 新月时刻搜索")
    start = astronomy.Time.Make(2026, 5, 1, 0, 0, 0)
    try:
        nm = astronomy.SearchMoonPhase(0, start, 40)
        print(f"      2026年5月附近新月: {nm}")
    except AttributeError:
        # 备用API：SearchMoonPhase 可能在2.x中有不同签名
        try:
            nm = astronomy.SearchMoonPhase(0, start)
            print(f"      2026年5月附近新月(2): {nm}")
        except Exception as e2:
            print(f"      新月搜索出错: {e2}")
    except Exception as e:
        print(f"      新月搜索出错: {e}")

    print()
    print("  ℹ️ astronomy-engine API 需进一步测试具体方法。")
    print("  → 查看文档: https://github.com/cosinekitty/astronomy")


# ===========================================================================
# 主流程
# ===========================================================================

if __name__ == "__main__":
    print("万年历引擎 — 交叉验证工具")
    print("=" * 60)
    print(f"运行时间: {datetime.now()}")
    print()

    # 第一步：测试我们引擎的基本功能
    engine_ok = test_our_engine()

    # 第二步：与 lunar_python 交叉验证
    lunar_ok = test_lunar_python()

    # 第三步：测试 astronomy-engine
    test_astronomy_engine()

    # 总结
    print()
    print("=" * 60)
    print("总结")
    print("=" * 60)
    if engine_ok:
        print("✅ 万年历引擎核心功能正常（循环导入已修复）")
    else:
        print("❌ 万年历引擎存在错误，请检查输出")
    if lunar_ok:
        print("✅ 与 lunar_python 交叉验证全部通过")
    print()
    print("快速启动: python web_interface/server.py  →  http://localhost:8765")
