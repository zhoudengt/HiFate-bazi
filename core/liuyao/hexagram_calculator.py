# -*- coding: utf-8 -*-
"""
六爻起卦计算：铜钱法、数字法、时间法。
2=少阴(阴静) 3=少阳(阳静) 6=老阴(阴动) 9=老阳(阳动)
八卦数：乾1 兑2 离3 震4 巽5 坎6 艮7 坤8，0 视为 8。
"""

from datetime import datetime
from typing import Dict, List, Tuple

# 八卦序号 1-8：乾兑离震巽坎艮坤（与 hexagram_texts.json 键 upper_lower 一致）
TRIGRAM_NAMES = ["", "乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]

# 每卦三爻自下而上：True=阳 False=阴
_KING_WEN_LINES: Dict[int, Tuple[bool, bool, bool]] = {
    1: (True, True, True),
    2: (True, True, False),
    3: (True, False, True),
    4: (True, False, False),
    5: (False, True, True),
    6: (False, True, False),
    7: (False, False, True),
    8: (False, False, False),
}
_LINES_TO_TRIGRAM = {v: k for k, v in _KING_WEN_LINES.items()}


def _trigram_to_lines(trigram: int) -> List[bool]:
    """八卦序号(1-8)转三爻，True=阳 False=阴，从下往上。"""
    if trigram not in _KING_WEN_LINES:
        raise ValueError(f"八卦序号须在 1-8 之间，收到 {trigram}")
    return list(_KING_WEN_LINES[trigram])


def _lines_to_trigram(lines: List[bool]) -> int:
    """下三爻转八卦序号 1-8（文王序）。"""
    key = (bool(lines[0]), bool(lines[1]), bool(lines[2]))
    t = _LINES_TO_TRIGRAM.get(key)
    if t is None:
        raise ValueError(f"无法识别的三爻组合: {key}")
    return t


def flip_trigram_line(trigram: int, line_idx: int) -> int:
    """翻转经卦中某一爻（0=初爻…2=三爻），返回新卦序号。"""
    bits = list(_trigram_to_lines(trigram))
    bits[line_idx] = not bits[line_idx]
    return _lines_to_trigram(bits)


def coin_method(coin_results: List[int]) -> dict:
    """
    铜钱法：6 个 2/3/6/9 → 本卦 + 变卦。
    返回 {"upper": 1-8, "lower": 1-8, "lines": [{"yin_yang": "yang"|"yin", "is_dong": bool}, ...], "moving": [0-5]}
    """
    if len(coin_results) != 6:
        raise ValueError("铜钱法需要 6 个结果")
    for v in coin_results:
        if v not in (2, 3, 6, 9):
            raise ValueError("铜钱结果只能为 2/3/6/9")
    lines = []  # 从下往上，索引 0 为初爻
    moving = []
    for i, v in enumerate(coin_results):
        is_yang = v in (3, 9)
        is_dong = v in (6, 9)
        lines.append({"yin_yang": "yang" if is_yang else "yin", "is_dong": is_dong})
        if is_dong:
            moving.append(i)
    lower = _lines_to_trigram([lines[0]["yin_yang"] == "yang", lines[1]["yin_yang"] == "yang", lines[2]["yin_yang"] == "yang"])
    upper = _lines_to_trigram([lines[3]["yin_yang"] == "yang", lines[4]["yin_yang"] == "yang", lines[5]["yin_yang"] == "yang"])
    # 变卦：老阴→阳，老阳→阴
    new_lines = []
    for i, line in enumerate(lines):
        if line["is_dong"]:
            new_lines.append({"yin_yang": "yin" if line["yin_yang"] == "yang" else "yang", "is_dong": False})
        else:
            new_lines.append({**line})
    lower_bian = _lines_to_trigram([new_lines[0]["yin_yang"] == "yang", new_lines[1]["yin_yang"] == "yang", new_lines[2]["yin_yang"] == "yang"])
    upper_bian = _lines_to_trigram([new_lines[3]["yin_yang"] == "yang", new_lines[4]["yin_yang"] == "yang", new_lines[5]["yin_yang"] == "yang"])
    return {
        "upper": upper,
        "lower": lower,
        "lines": lines,
        "moving": moving,
        "upper_bian": upper_bian,
        "lower_bian": lower_bian,
        "lines_bian": new_lines,
    }


def number_method(numbers: List[int]) -> dict:
    """
    数字法：3 数 a,b,c → 上卦=a%8, 下卦=b%8, 动爻=c%6，0 视为 8/6。
    返回结构同 coin_method。
    """
    if len(numbers) != 3:
        raise ValueError("数字法需要 3 个数字")
    a, b, c = numbers
    upper = (a % 8) or 8
    lower = (b % 8) or 8
    dong_idx = (c % 6) or 6  # 1-6 动爻位，转为 0-5
    dong_idx = dong_idx - 1
    lines = []
    lower_lines = _trigram_to_lines(lower)
    upper_lines = _trigram_to_lines(upper)
    for i in range(6):
        is_yang = (lower_lines if i < 3 else upper_lines)[i % 3]
        is_dong = i == dong_idx
        lines.append({"yin_yang": "yang" if is_yang else "yin", "is_dong": is_dong})
    new_lines = [*lines]
    if 0 <= dong_idx < 6:
        flip = new_lines[dong_idx]
        new_lines[dong_idx] = {"yin_yang": "yin" if flip["yin_yang"] == "yang" else "yang", "is_dong": False}
    lower_bian = _lines_to_trigram([new_lines[0]["yin_yang"] == "yang", new_lines[1]["yin_yang"] == "yang", new_lines[2]["yin_yang"] == "yang"])
    upper_bian = _lines_to_trigram([new_lines[3]["yin_yang"] == "yang", new_lines[4]["yin_yang"] == "yang", new_lines[5]["yin_yang"] == "yang"])
    return {
        "upper": upper,
        "lower": lower,
        "lines": lines,
        "moving": [dong_idx] if 0 <= dong_idx < 6 else [],
        "upper_bian": upper_bian,
        "lower_bian": lower_bian,
        "lines_bian": new_lines,
    }


def time_method(dt: datetime) -> dict:
    """
    时间法：年+月+日 取余 8 得上卦，年+月+日+时 取余 8 得下卦，总和取余 6 得动爻（0 视为 6）。
    """
    y, m, d = dt.year, dt.month, dt.day
    h = dt.hour
    # 时按地支序 0-11 或 1-12
    if h == 23:
        shi = 1
    else:
        shi = (h // 2) + 1
    s1 = (y + m + d) % 8 or 8
    s2 = (y + m + d + shi) % 8 or 8
    dong = (y + m + d + shi) % 6 or 6
    dong_idx = dong - 1
    return number_method([s1, s2, dong])
