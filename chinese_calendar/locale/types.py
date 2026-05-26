# locale/types.py — 双语字符串类型
#
# 提供 LocaleStr 类，根据当前语言环境自动切换中英文。
#
# 用法:
#   name = LocaleStr(zh="立春", en="Spring Begins")
#   name.get("zh") → "立春"
#   name.get("en") → "Spring Begins"
#   str(name)      → 默认语言的字符串

from __future__ import annotations

from typing import Optional


# 全局语言环境设置
# 默认为中文，可通过 set_default_lang() 修改
_DEFAULT_LANG: str = "zh"


def set_default_lang(lang: str) -> None:
    """设置全局默认语言。

    Args:
        lang: "zh" 或 "en"。
    """
    global _DEFAULT_LANG
    if lang not in ("zh", "en"):
        raise ValueError(f"lang must be 'zh' or 'en', got {lang!r}")
    _DEFAULT_LANG = lang


def get_default_lang() -> str:
    """获取当前全局默认语言。"""
    return _DEFAULT_LANG


class LocaleStr:
    """双语字符串，根据语言环境自动选择中英文。

    Attributes:
        zh: 中文文本。
        en: 英文文本。
    """

    __slots__ = ("zh", "en")

    def __init__(self, zh: str, en: str):
        self.zh: str = zh
        self.en: str = en

    def get(self, lang: Optional[str] = None) -> str:
        """获取指定语言的文本。

        Args:
            lang: "zh" 或 "en"。为 None 时使用全局默认。

        Returns:
            对应语言的字符串。
        """
        if lang is None:
            lang = _DEFAULT_LANG
        if lang == "zh":
            return self.zh
        elif lang == "en":
            return self.en
        else:
            raise ValueError(f"lang must be 'zh' or 'en', got {lang!r}")

    def __str__(self) -> str:
        return self.get()

    def __repr__(self) -> str:
        return f"LocaleStr(zh={self.zh!r}, en={self.en!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LocaleStr):
            return self.zh == other.zh and self.en == other.en
        return NotImplemented
