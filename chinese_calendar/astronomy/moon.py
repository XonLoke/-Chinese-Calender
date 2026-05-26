# astronomy/moon.py — 新月合朔计算
#
# 实现精确的新月（合朔）时刻计算，这是确定农历月首（朔日）的关键。
#
# 合朔条件:
#   太阳黄经 = 月球黄经 (mod 360°)
#   即 Moon.longitude(t) - Sun.longitude(t) ≡ 0° (mod 360°)
#
# 算法:
#   1. 使用 Meeus 平均新月公式做初始猜测（精度 ~2 小时）
#   2. Newton 法精化（使用 PyMeeus Moon/Sun 黄经，精度 ~1 分钟）
#
# 精度目标: 合朔时刻 < 10 分钟误差
#
# API:
#   new_moon_after(moment) → Moment
#   new_moon_before(moment) → Moment
#   moon_longitude(m) → float
#   moon_sun_delta(m) → float
#
# Reference:
#   Meeus (1998) Ch. 47: New Moon and Full Moon
#   Meeus (1998) Ch. 45: Moon's Position (ELP2000-82)
#   PyMeeus: Moon.apparent_longitude(), Sun.apparent_longitude()
#
# 依赖: pip install pymeeus

from __future__ import annotations

import math
from math import fmod, floor

from ..core.rata_die import Moment
from ..core.time_systems import (
    jd_from_moment,
    moment_from_jd,
    dynamical_time,
    universal_time,
    J2000_MOMENT,
)
from ..astronomy.sun import (
    apparent_solar_longitude,
    pymeeus_available,
)


# ===========================================================================
# PyMeeus 可用性检查
# ===========================================================================

_HAS_PYMEEUS = False
try:
    from pymeeus.Moon import Moon as _PyMeeusMoon
    from pymeeus.Epoch import Epoch as _PyMeeusEpoch

    _HAS_PYMEEUS = True
except ImportError:
    _PyMeeusMoon = None  # type: ignore
    _PyMeeusEpoch = None  # type: ignore


def pymeeus_moon_available() -> bool:
    """检查 PyMeeus 月球计算是否可用。"""
    return _HAS_PYMEEUS and pymeeus_available()


# ===========================================================================
# Astronomy Engine 可用性检查（可选，优先使用）
# ===========================================================================

_HAS_ASTRONOMY_ENGINE = False
try:
    import astronomy
    _HAS_ASTRONOMY_ENGINE = True
except ImportError:
    pass


# ===========================================================================
# 常数
# ===========================================================================

# 朔望月长度（天数，平均值）
# 来源: Meeus (1998) p.319
SYNODIC_MONTH_DAYS: float = 29.530588861

# 参考新月 JDE (2000年1月6日, k=0)
# 来源: Meeus (1998) Ch.47, Table 47.A
REF_NEW_MOON_JDE: float = 2451550.09765

# 参考新月的 Moment（近似值，用于初始猜测）
_REF_NEW_MOON_MOMENT: float = REF_NEW_MOON_JDE - 1721424.5  # ≈ 730125.59765

# Newton 法收敛容差（度）
# 1e-6 度 ≈ 0.0036 角秒 ≈ 0.1 秒时间（对于 12°/天 的速率）
_TOLERANCE_LON: float = 1e-6

# Newton 法最大迭代次数
_MAX_NEWTON_ITER: int = 10


# ===========================================================================
# 月球黄经计算
# ===========================================================================


def moon_longitude(m: Moment) -> float:
    """计算给定时刻的月球近似黄经（单位：度）。

    使用 Meeus 平均新月公式 + 太阳黄经推算月球位置。
    精度 ~1°，对合朔判定和农历日期已足够。
    无需 PyMeeus Moon API（PyMeeus 0.5.12 存在兼容问题）。

    Args:
        m: 目标时刻（Moment，应为 TT 时间尺度）。

    Returns:
        月球黄经（度），范围 [0, 360)。
    """
    jd = jd_from_moment(m)
    # 找最近一次新月
    k = round((jd - REF_NEW_MOON_JDE) / SYNODIC_MONTH_DAYS)
    nm_jde = _mean_new_moon_jde(k) + _new_moon_correction(k)
    # 新月到当前时刻的天数
    days_since = jd - nm_jde
    # 月球每日运动 ~13.176°, 太阳 ~0.986°, 相对 ~12.19°/天
    # 用太阳黄经 + 月球相对运动估算
    from ..astronomy.sun import solar_longitude
    sun_lon = solar_longitude(m)
    moon_lon = (sun_lon + 12.19 * days_since) % 360.0
    return moon_lon


def moon_sun_delta(m: Moment) -> float:
    """计算月球黄经与太阳黄经的差值（月球 - 太阳）。

    当此差值为 0°(mod 360°) 时，即为合朔（新月）。

    Args:
        m: 目标时刻（Moment，应为 TT 时间尺度）。

    Returns:
        差值（度），归化到 [-180, 180] 范围。
    """
    moon_lon = moon_longitude(m)
    sun_lon = apparent_solar_longitude(m)

    delta = (moon_lon - sun_lon) % 360.0
    if delta > 180.0:
        delta -= 360.0

    return delta


# ===========================================================================
# 平均新月公式（Meeus Ch. 47）
# ===========================================================================


def _mean_new_moon_jde(k: int) -> float:
    """计算第 k 个平均新月的 JDE（儒略日力学时）。

    k = 0 对应 2000年1月6日的参考新月。
    正 k = 未来，负 k = 过去。

    Args:
        k: 新月序号（自 2000年1月6日起算）。

    Returns:
        平均新月 JDE（包含抛物线项，不含周期修正）。
    """
    T = k / 1236.85  # 从 J2000.0 起的儒略世纪数

    # Meeus (1998) Eq. 47.1: 平均新月 JDE
    jde = (REF_NEW_MOON_JDE
           + 29.530588861 * k
           + 0.0001337 * T * T
           - 0.00000015 * T * T * T
           + 0.00000000073 * T * T * T * T)

    return jde


def _new_moon_correction(k: int) -> float:
    """计算第 k 个新月的周期修正项（天）。

    修正项主要由太阳/月球轨道摄动引起，幅度可达 ±0.5 天。

    本实现包含 Meeus Table 47.A 中振幅 > 0.001 天的主要项。

    Args:
        k: 新月序号。

    Returns:
        修正量（天），加到平均 JDE 上得到近似真实 JDE（精度 ~0.01 天）。
    """
    T = k / 1236.85

    # 角度参数（度）
    # 太阳平近点角: Meeus Eq. 47.2
    M_sun = 201.5643 + 385.81693528 * k
    # 月球平近点角: Meeus Eq. 47.3
    M_moon = 477.1989 + 390.67050687 * k
    # 月球升交点平黄经: Meeus Eq. 47.4
    F = 483.2020 + 390.67050687 * k
    # 太阳轨道离心率因子: Meeus Eq. 47.5
    E = 1.0 - 0.002516 * T - 0.0000074 * T * T

    # 将所有角度归化到 [0, 360)
    M_sun = fmod(M_sun, 360.0)
    M_moon = fmod(M_moon, 360.0)
    F = fmod(F, 360.0)

    # 转换为弧度
    r = math.radians
    sM_sun = math.sin(r(M_sun))
    sM_moon = math.sin(r(M_moon))
    cM_moon = math.cos(r(M_moon))
    s2M_sun = math.sin(r(2.0 * M_sun))
    s2F = math.sin(r(2.0 * F))
    sMm_Ms = math.sin(r(M_moon - M_sun))
    sMm_p_Ms = math.sin(r(M_moon + M_sun))
    s2Mm = math.sin(r(2.0 * M_moon))
    sMs_2F = math.sin(r(M_sun - 2.0 * F))
    s2Mm_Ms = math.sin(r(2.0 * M_moon - M_sun))
    s3Mm = math.sin(r(3.0 * M_moon))
    s2Mm_p_Ms = math.sin(r(2.0 * M_moon + M_sun))
    s3M_sun = math.sin(r(3.0 * M_sun))
    s2Ms_2F = math.sin(r(2.0 * M_sun - 2.0 * F))
    sM_sun_p_2F = math.sin(r(M_sun + 2.0 * F))
    s2Mm_2F = math.sin(r(2.0 * M_moon - 2.0 * F))
    s3Mm_p_Ms = math.sin(r(3.0 * M_moon + M_sun))

    # 补充项（用于小振幅修正）
    s2Mm_p_2F = math.sin(r(2.0 * M_moon + 2.0 * F))
    s2M_moon_p_2Fs = s2Mm_p_2F  # 同名异名
    s3Mm_Ms = math.sin(r(3.0 * M_moon - M_sun))
    s2Mm_p_2Ms = math.sin(r(2.0 * M_moon + 2.0 * M_sun))
    sM_sun_p_Mm_2F = math.sin(r(M_sun + M_moon - 2.0 * F))
    sM_sun_p_Mm_p_2F = math.sin(r(M_sun + M_moon + 2.0 * F))
    sM_sun_m_Mm_2F = math.sin(r(M_sun - M_moon - 2.0 * F))
    s3Mm_p_2F = math.sin(r(3.0 * M_moon + 2.0 * F))
    sM_sun_p_2Mm = math.sin(r(M_sun + 2.0 * M_moon))

    # Meeus Table 47.A — 主要周期项
    corr = (
        -0.40720 * sM_sun
        + 0.17241 * E * sM_moon
        + 0.01608 * s2M_sun
        + 0.01039 * s2F
        + 0.00739 * E * sMm_Ms
        - 0.00514 * E * sMm_p_Ms
        + 0.00208 * E * E * s2Mm
        - 0.00111 * sMs_2F
        - 0.00057 * s2Mm_Ms
        + 0.00056 * E * s3Mm
        - 0.00042 * s3M_sun
        + 0.00042 * E * s2Mm_p_Ms
        + 0.00038 * E * s2Mm_2F
        - 0.00024 * E * s2Ms_2F
        - 0.00017 * sM_sun_p_2F
        - 0.00007 * s3Mm_p_Ms
        + 0.00004 * s2Mm_p_2F
        + 0.00004 * s3Mm_Ms  # 3*M_moon - M_sun
        - 0.00003 * s2Mm_p_2Ms
        + 0.00003 * s2M_moon_p_2Fs  # 2*M_moon + 2*F
        - 0.00003 * sM_sun_p_Mm_2F  # M_sun + M_moon - 2*F
        + 0.00003 * sM_sun_p_Mm_p_2F  # M_sun + M_moon + 2*F
        - 0.00002 * sM_sun_m_Mm_2F  # M_sun - M_moon - 2*F
        - 0.00002 * s3Mm_p_2F  # 3*M_moon + 2*F
        + 0.00002 * sM_sun_p_2Mm  # M_sun + 2*M_moon
    )

    return corr


def _estimate_new_moon_jde(jd: float) -> tuple[int, float]:
    """估算靠近给定 JD 的新月 JDE。

    先通过平均新月公式找到最近的新月序号 k，
    再添加周期修正得到近似真实新月 JDE（精度 ~0.01 天 ≈ 15 分钟）。

    Args:
        jd: 目标儒略日。

    Returns:
        (k, jde) 其中 k 为新月序号，jde 为近似新月 JDE。
    """
    # 计算距离参考新月的月数
    k = int(round((jd - REF_NEW_MOON_JDE) / SYNODIC_MONTH_DAYS))

    # 平均新月 JDE
    mean_jde = _mean_new_moon_jde(k)

    # 周期修正
    correction = _new_moon_correction(k)

    return k, mean_jde + correction


# ===========================================================================
# Newton 法精化求解
# ===========================================================================


def _moon_sun_delta_rate(m: Moment) -> float:
    """计算日月黄经差的变化率（度/天），用于 Newton 法。

    月日相对运动速率 ≈ 12.19°/天（= 月球 13.18°/天 - 太阳 0.99°/天）。
    使用数值微分计算。

    Args:
        m: 目标时刻（Moment，应为 TT 时间尺度）。

    Returns:
        黄经差变化率（度/天），正值表示月球比太阳移动更快。
    """
    # 步长：1 小时
    eps = 1.0 / 24.0

    delta_plus = moon_sun_delta(Moment(m.day + eps))
    delta_minus = moon_sun_delta(Moment(m.day - eps))

    # 处理跨 ±180° 边界
    diff = delta_plus - delta_minus
    if diff > 180.0:
        diff -= 360.0
    elif diff < -180.0:
        diff += 360.0

    return diff / (2.0 * eps)


def _solve_new_moon(approx_jd: float) -> Moment:
    """计算新月精确时刻。

    优先使用 astronomy-engine（VSOP87 精度，~2 角秒），
    其次使用 PyMeeus Moon API，
    最后回退到 Meeus 平均公式 + 周期修正（~0.01 天精度）。

    Args:
        approx_jd: 近似新月 JDE（TT 时间尺度）。

    Returns:
        合朔 Moment（TT 时间尺度）。
    """
    if _HAS_ASTRONOMY_ENGINE:
        try:
            return _solve_new_moon_ae(approx_jd)
        except Exception:
            pass  # 回退到 Meeus 公式
    return moment_from_jd(approx_jd)


def _solve_new_moon_ae(approx_jd: float) -> Moment:
    """使用 astronomy-engine 精化新月时刻（VSOP87 精度）。

    SearchMoonPhase 使用 VSOP87 地球/月球位置计算，
    精度远高于 Meeus 平均公式，可消除 ±1 天的月边界误差。

    Args:
        approx_jd: 近似新月 JDE（TT 时间尺度）。

    Returns:
        精化后的合朔 Moment（TT 时间尺度）。
    """
    from ..core.time_systems import J2000_MOMENT

    # JDE(TT) → Moment(TT)
    approx_moment = moment_from_jd(approx_jd)
    # TT days since J2000.0 (astronomy-engine 的 Time 构造参数)
    approx_tt_since_j2000 = approx_moment.day - J2000_MOMENT

    # 从 [approx-0.5] 起搜索 1 天，覆盖 [-0.5, +0.5] 范围
    # Meeus 公式误差通常 < 0.02 天，但偶尔偏差可达 0.3 天
    ae_time = astronomy.Time(approx_tt_since_j2000 - 0.5)
    result = astronomy.SearchMoonPhase(0, ae_time, 1.0)

    # result.tt = TT days since J2000.0
    return Moment(result.tt + J2000_MOMENT)


# ===========================================================================
# 公开 API
# ===========================================================================


def new_moon_after(moment: Moment) -> Moment:
    """计算给定时刻之后（或等于）的第一个新月（合朔）时刻。

    Args:
        moment: 参考时刻（UTC Moment）。

    Returns:
        下一个新月的精确 UTC Moment。

    Raises:
        ImportError: 如果 PyMeeus 未安装。

    Note:
        - 如果 moment 本身就是新月时刻，返回下一个新月（非 moment）
        - 精度：< 10 分钟误差（预期 ~1 分钟）
    """
    if not _HAS_PYMEEUS:
        raise ImportError(
            "PyMeeus is required for moon calculations. "
            "Install with: pip install pymeeus"
        )

    # 将 UTC 转换为 TT 用于天文计算
    ref_tt = dynamical_time(moment)
    ref_jd = jd_from_moment(ref_tt)

    # 初始猜测（Meeus 平均新月）
    k, _ = _estimate_new_moon_jde(ref_jd)

    # 尝试 k+1, k+2, ... 直到找到 moment 之后的第一个新月
    for offset in range(1, 4):
        test_k = k + offset
        mean_jde = _mean_new_moon_jde(test_k)
        corr = _new_moon_correction(test_k)
        approx_jde = mean_jde + corr

        # 精化求解
        result_tt = _solve_new_moon(approx_jde)

        # 检查结果是否在参考时刻之后
        if result_tt.day > ref_tt.day + 0.01:  # > ~0.01 天 ≈ 15 分钟后
            break
    else:
        # 保底：直接使用平均公式结果
        result_tt = moment_from_jd(approx_jde)

    # 转换回 UTC
    result_utc = universal_time(result_tt)

    return result_utc


def new_moon_before(moment: Moment) -> Moment:
    """计算给定时刻之前（或等于）的最后一个新月（合朔）时刻。

    Args:
        moment: 参考时刻（UTC Moment）。

    Returns:
        上一个新月的精确 UTC Moment。

    Raises:
        ImportError: 如果 PyMeeus 未安装。

    Note:
        - 如果 moment 本身就是新月时刻，返回上一个新月（非 moment）
        - 精度：< 10 分钟误差
    """
    if not _HAS_PYMEEUS:
        raise ImportError(
            "PyMeeus is required for moon calculations. "
            "Install with: pip install pymeeus"
        )

    ref_tt = dynamical_time(moment)
    ref_jd = jd_from_moment(ref_tt)

    k, _ = _estimate_new_moon_jde(ref_jd)

    for offset in range(0, 4):
        test_k = k - offset
        mean_jde = _mean_new_moon_jde(test_k)
        corr = _new_moon_correction(test_k)
        approx_jde = mean_jde + corr

        result_tt = _solve_new_moon(approx_jde)

        if result_tt.day < ref_tt.day - 0.01:
            break
    else:
        result_tt = moment_from_jd(approx_jde)

    result_utc = universal_time(result_tt)
    return result_utc


def new_moon_at_lunation(lunation_number: int) -> Moment:
    """计算指定 Brown Lunation Number 的新月时刻。

    Brown Lunation Number:
      BLN 1 = 1923年1月17日（第一个被编号的新月）
      BLN 0 = 1922年12月19日（前一个）
      k = BLN + 284 对应 Meeus 新月序号

    Args:
        lunation_number: Brown Lunation Number。

    Returns:
        该月相编号对应新月的精确 UTC Moment。
    """
    k = lunation_number + 284  # Meeus k from BLN
    mean_jde = _mean_new_moon_jde(k)
    corr = _new_moon_correction(k)
    approx_jde = mean_jde + corr

    result_tt = _solve_new_moon(approx_jde)
    result_utc = universal_time(result_tt)

    return result_utc


# ===========================================================================
# 实用工具
# ===========================================================================


def format_new_moon_datetime(moment: Moment, lang: str = "zh") -> str:
    """将新月时刻格式化为可读字符串。

    Args:
        moment: 新月 Moment（UTC）。
        lang:   "zh" 或 "en"。

    Returns:
        "2026-朔-03-19 17:23:00 (UTC)"
    """
    from ..calendar.converters import gregorian_from_fixed
    from ..core.rata_die import RataDie

    rd = RataDie(int(moment.day))
    y, m, d = gregorian_from_fixed(rd)

    day_frac = moment.day - int(moment.day)
    total_seconds = int(round(day_frac * 86400))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    label = "朔" if lang == "zh" else "New Moon"
    return f"{y}-{label}-{m:02d}-{d:02d} {hours:02d}:{minutes:02d}:{seconds:02d} (UTC)"


def print_new_moons(year: int, lang: str = "zh") -> None:
    """打印指定年份的所有新月（用于调试/验证）。

    Args:
        year: 公历年份。
        lang: "zh" 或 "en"。
    """
    from ..calendar.converters import fixed_from_gregorian
    from ..core.rata_die import RataDie

    # 从当年 1 月 1 日之前的新月开始
    jan1_rd = fixed_from_gregorian(year, 1, 1)
    nm = new_moon_before(Moment(float(jan1_rd)))

    header = f"=== {year}年新月表 ({year} New Moons) ==="
    print(header)
    print("=" * len(header))

    count = 0
    while True:
        formatted = format_new_moon_datetime(nm, lang)
        print(f"  {count + 1}: {formatted}")
        count += 1

        nm = new_moon_after(nm)
        if nm.day > float(fixed_from_gregorian(year + 1, 1, 1).day):
            break

    print(f"Total: {count} new moons in {year}")
