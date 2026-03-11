# -*- coding: utf-8 -*-
"""六爻卦辞爻辞加载。"""

import json
import os
from typing import Any, Dict, Optional

_HEXAGRAM_CACHE: Optional[Dict[str, Any]] = None


def _load_hexagrams() -> Dict[str, Any]:
    global _HEXAGRAM_CACHE
    if _HEXAGRAM_CACHE is not None:
        return _HEXAGRAM_CACHE
    path = os.path.join(os.path.dirname(__file__), "data", "hexagram_texts.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _HEXAGRAM_CACHE = data.get("hexagrams", {})
    return _HEXAGRAM_CACHE


def get_hexagram_texts(upper: int, lower: int) -> Optional[Dict[str, Any]]:
    """根据上下卦序号(1-8)获取卦名、卦辞、爻辞。"""
    hexagrams = _load_hexagrams()
    key = f"{upper}_{lower}"
    return hexagrams.get(key)
