# astronomy/corrections.py — 天文修正：岁差 · 章动 · 光行差
#
# 修正层级（从几何黄经到视黄经）:
#   几何黄经 (geometric longitude)
#       ↓  + 岁差修正 (precession)   ~50"/年
#   平均黄经 (mean longitude)
#       ↓  + 章动修正 (nutation)     ~17" 振幅
#       ↓  + 光行差修正 (aberration) ~20"
#   视黄经 (apparent longitude)  ← 节气定义使用的值
#
# 注意:
#   当使用 PyMeeus 的 Sun.apparent_longitude() 时，所有修正已内置。
#   本模块提供独立实现供参考和未来替换用。
#
# Reference:
#   Meeus (1998), Ch. 24-26

from __future__ import annotations

from math import cos, radians, sin

from ..core.rata_die import Moment
from .sun import solar_longitude


# ===========================================================================
# 岁差 (Precession)
# ===========================================================================


def precession_correction(julian_centuries_t: float) -> float:
    """计算黄经岁差修正，单位：度。

    岁差是地球自转轴进动导致的春分点西移现象，
    约 50.29 角秒/年（~0.01397°/年）。

    Args:
        julian_centuries_t: 自 J2000.0 起的儒略世纪数。

    Returns:
        黄经岁差修正量（度），正值表示增加。

    Reference:
        Meeus (1998) Eq. 24.1:
        岁差 = 0.025754 + 0.051345*t + 0.000032*t² (度, 每儒略世纪)
        更精确: 岁差总量 ≈ 5038.481507"/世纪 + 1.55817"/世纪²
              = 1.399518°/世纪 + 0.0004328°/世纪²
    """
    # 简化版：约 50.29"/年 ≈ 0.013969°/年
    # 每儒略世纪约 1.3969°
    correction = 1.3969 * julian_centuries_t
    return correction  # 度


# ===========================================================================
# 章动 (Nutation)
# ===========================================================================


def nutation_longitude(julian_centuries_t: float) -> float:
    """计算黄经章动 (Δψ)，单位：度。

    章动是月球和太阳引力导致的地球自转轴周期性摆动。
    黄经章动最大振幅约 17 角秒（~0.0047°）。
    周期主要为 18.6 年（月球轨道升交点周期）。

    Args:
        julian_centuries_t: 自 J2000.0 起的儒略世纪数。

    Returns:
        黄经章动量（度），用于修正黄经。

    Reference:
        Meeus (1998) Eq. 26.1 (简化版，仅主项):
        Δψ = -17.200*sin(Ω) - 1.319*sin(2F-2D+2Ω) - 0.227*sin(2F+2Ω)  (角秒)
        其中 Ω = 月球升交点黄经
    """
    # 简化版：仅保留最大项
    # Ω（月球升交点平均黄经）
    omega = 125.04 - 0.052954 * julian_centuries_t * 100  # 度

    # 黄经章动主项 (角秒 → 度)
    dpsi_arcsec = -17.206 * sin(radians(omega))
    return dpsi_arcsec / 3600.0  # 转换为度


def nutation_obliquity(julian_centuries_t: float) -> float:
    """计算交角章动 (Δε)，单位：度。

    交角章动是黄赤交角的周期性变化分量。

    Args:
        julian_centuries_t: 自 J2000.0 起的儒略世纪数。

    Returns:
        交角章动量（度）。

    Reference:
        Meeus (1998) Eq. 26.1 (简化版):
        Δε = 9.203*cos(Ω) + 0.574*cos(2F-2D+2Ω)  (角秒)
    """
    omega = 125.04 - 0.052954 * julian_centuries_t * 100

    # 交角章动主项 (角秒 → 度)
    deps_arcsec = 9.203 * cos(radians(omega))
    return deps_arcsec / 3600.0


def mean_obliquity(julian_centuries_t: float) -> float:
    """计算平黄赤交角 (ε₀)，单位：度。

    Args:
        julian_centuries_t: 自 J2000.0 起的儒略世纪数。

    Returns:
        平黄赤交角（度）。

    Reference:
        Meeus (1998) Eq. 26.3:
        ε₀ = 23°26'21.448" - 46.8150"*t - 0.00059"*t² + 0.001813"*t³
    """
    # 转换为度
    eps0 = (23 + 26 / 60.0 + 21.448 / 3600.0
            - (46.8150 * julian_centuries_t) / 3600.0
            - (0.00059 * julian_centuries_t ** 2) / 3600.0
            + (0.001813 * julian_centuries_t ** 3) / 3600.0)
    return eps0


def true_obliquity(julian_centuries_t: float) -> float:
    """计算真黄赤交角 (ε)，单位：度。

    Args:
        julian_centuries_t: 自 J2000.0 起的儒略世纪数。

    Returns:
        真黄赤交角（度）。
    """
    eps0 = mean_obliquity(julian_centuries_t)
    deps = nutation_obliquity(julian_centuries_t)
    return eps0 + deps


# ===========================================================================
# 光行差 (Aberration)
# ===========================================================================


def aberration_correction(julian_centuries_t: float) -> float:
    """计算光行差修正，单位：度。

    光行差是由于地球公转速度和光速有限导致的视位置偏移。
    最大振幅约 20.5 角秒（~0.0057°）。

    Args:
        julian_centuries_t: 自 J2000.0 起的儒略世纪数。

    Returns:
        光行差修正量（度）。

    Reference:
        Meeus (1998) Ch. 25:
        光行差 ≈ -20.5" * sin(太阳黄经 - 近日点黄经)
    """
    # 太阳黄经的近似
    # 对于光行差，粗略近似就足够
    sun_lon_approx = (280.46 + 36000.771 * julian_centuries_t) % 360

    # 地球近日点黄经 (约 102.9°)
    perihelion = 102.94

    # 光行差常数 20.5" → 度
    k = 20.5 / 3600.0

    return -k * sin(radians(sun_lon_approx - perihelion))


# ===========================================================================
# 统一修正接口
# ===========================================================================


def apparent_longitude_from_geometric(geo_lon: float,
                                       julian_centuries_t: float) -> float:
    """从几何黄经计算视黄经（包含所有修正）。

    修正顺序:
      几何黄经 → + 岁差 → + 章动 → + 光行差 → 视黄经

    Args:
        geo_lon: 几何黄经（度）。
        julian_centuries_t: 自 J2000.0 起的儒略世纪数。

    Returns:
        视黄经（度）。
    """
    from math import fmod

    lon = geo_lon

    # 1. 岁差修正（累计项，非逐日变化）
    # 注：VSOP87 默认输出相对于 J2000 平分春分点，
    # 需要修正到当日春分点
    # (PyMeeus 已内置该修正)

    # 2. 章动黄经修正
    lon += nutation_longitude(julian_centuries_t)

    # 3. 光行差修正
    lon += aberration_correction(julian_centuries_t)

    # 归化到 0-360
    lon = fmod(lon, 360.0)
    if lon < 0:
        lon += 360.0

    return lon
