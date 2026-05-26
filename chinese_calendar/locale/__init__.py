# locale: 双语本地化系统 (Sprint 8)
#
# 提供万年历引擎的完整中英文支持。
#
# 用法:
#   from locale.types import LocaleStr, set_default_lang
#   from locale import zh_CN, en_US
#
#   名称 = LocaleStr(zh="立春", en="Spring Begins")
#   名称.get("zh")  # "立春"
#   名称.get("en")  # "Spring Begins"

from __future__ import annotations

from .types import LocaleStr, set_default_lang, get_default_lang
from . import zh_CN
from . import en_US

__all__ = [
    "LocaleStr",
    "set_default_lang",
    "get_default_lang",
    "zh_CN",
    "en_US",
]
