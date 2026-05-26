# api/lunar_culture.py — 术数文化层数据（lunar_python 封装）
#
# 作为 lunar_python 的轻量封装，提供星宿、彭祖百忌、宜忌、冲煞、
# 喜神财神福神方位等中国传统术数数据。
#
# 依赖: lunar_python（可选）
# 将来可以逐步替换为自有模块。

from __future__ import annotations
from typing import Optional


def lunar_culture_available() -> bool:
    """检查 lunar_python 是否可用。"""
    try:
        import lunar_python
        return True
    except ImportError:
        return False


def get_lunar_culture(year: int, month: int, day: int) -> Optional[dict]:
    """获取指定公历日期的术数文化层数据。

    返回的字典包含：
      - xiu:       二十八星宿
      - peng_zu:   彭祖百忌（天干 + 地支）
      - yi:        宜事项列表
      - ji:        忌事项列表
      - chong:     冲煞描述
      - chong_shengxiao: 冲生肖
      - sha:       煞方向
      - xi_shen:   喜神方位
      - cai_shen:  财神方位
      - fu_shen:   福神方位
      - yang_gui:  阳贵神方位
      - yin_gui:   阴贵神方位
      - wu_hou:    五侯（七十二候）
      - hou:       候
      - jie_qi:    当前节气名
      - ji_qi:     当前中气名
      - full_str:  完整中文字符串（toFullString）
    """
    try:
        from lunar_python import Lunar
        from datetime import datetime
        l = Lunar.fromDate(datetime(year, month, day, 12, 0, 0))

        def _safe(val):
            """确保返回值可 JSON 序列化。"""
            if val is None:
                return None
            if isinstance(val, (str, int, float, bool, list, dict)):
                return val
            return str(val)

        return {
            "xiu": _safe(l.getXiu()),
            "xiu_luck": _safe(l.getXiuLuck()),
            "xiu_song": _safe(l.getXiuSong()),
            "peng_zu_gan": _safe(l.getPengZuGan()),
            "peng_zu_zhi": _safe(l.getPengZuZhi()),
            "yi": _safe(l.getDayYi()),
            "ji": _safe(l.getDayJi()),
            "chong": _safe(l.getDayChongDesc()),
            "chong_shengxiao": _safe(l.getDayChongShengXiao()),
            "sha": _safe(l.getDaySha()),
            "xi_shen": _safe(l.getDayPositionXiDesc()),
            "cai_shen": _safe(l.getDayPositionCaiDesc()),
            "fu_shen": _safe(l.getDayPositionFuDesc()),
            "yang_gui": _safe(l.getDayPositionYangGuiDesc()),
            "yin_gui": _safe(l.getDayPositionYinGuiDesc()),
            "wu_hou": _safe(l.getWuHou()),
            "hou": _safe(l.getHou()),
            "jie_qi": _safe(l.getCurrentJieQi()),
            "full_str": _safe(l.toFullString()),
        }
    except Exception:
        return None
