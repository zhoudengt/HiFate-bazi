# -*- coding: utf-8 -*-
"""
六爻排盘：世应（八宫归宫表）、六亲（五行生克）、六神（按日干）。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

TRIGRAM_NAMES = ["", "乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]

TRIGRAM_WUXING = [None, "金", "金", "火", "木", "木", "水", "土", "土"]

LIU_SHEN = ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]

TIANGAN_LIU_SHEN_START = {
    "甲": 0, "乙": 0,
    "丙": 1, "丁": 1,
    "戊": 2, "己": 3,
    "庚": 4, "辛": 4,
    "壬": 5, "癸": 5,
}

WU_XING_SHENG = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}
WU_XING_KE = {"金": "木", "水": "火", "木": "土", "火": "金", "土": "水"}

# 八宫六十四卦归宫表：(上卦, 下卦) -> (宫, 世爻位置0-5)
# 宫用八卦序号 1-8（乾兑离震巽坎艮坤）
# 八宫排列：乾宫、兑宫、离宫、震宫、巽宫、坎宫、艮宫、坤宫
# 每宫8卦：本卦(世6)、一世～五世(世1～5)、游魂(世4)、归魂(世3)
_BAGONG_TABLE: Dict[Tuple[int, int], Tuple[int, int]] = {}


def _six_lines_to_upper_lower(lines6: List[bool]) -> Tuple[int, int]:
    """六爻自下而上 → (上卦序号, 下卦序号)，文王序 1-8。"""
    from core.liuyao.hexagram_calculator import _lines_to_trigram

    lower = _lines_to_trigram(lines6[0:3])
    upper = _lines_to_trigram(lines6[3:6])
    return upper, lower


def _build_bagong_table():
    """京房八宫：自下而上累变五世 → 变四爻为游魂 → 归魂还原内卦，覆盖 64 卦。"""
    if _BAGONG_TABLE:
        return

    from core.liuyao.hexagram_calculator import _trigram_to_lines

    for gong in range(1, 9):
        inner = _trigram_to_lines(gong)
        lines6 = list(inner) + list(inner)
        _BAGONG_TABLE[_six_lines_to_upper_lower(lines6)] = (gong, 5)

        for i in range(5):
            lines6[i] = not lines6[i]
            _BAGONG_TABLE[_six_lines_to_upper_lower(lines6)] = (gong, i)

        lines6[3] = not lines6[3]
        _BAGONG_TABLE[_six_lines_to_upper_lower(lines6)] = (gong, 3)

        for i in range(3):
            lines6[i] = not lines6[i]
        _BAGONG_TABLE[_six_lines_to_upper_lower(lines6)] = (gong, 2)


_build_bagong_table()


def _get_gong_and_shi(upper: int, lower: int) -> Tuple[int, int]:
    """
    查八宫归宫表，返回 (卦宫序号1-8, 世爻位置0-5)。
    """
    result = _BAGONG_TABLE.get((upper, lower))
    if result:
        return result
    return (lower, 2)


def _liu_qin(gong_wuxing: str, yao_wuxing: str) -> str:
    """
    六亲：卦宫五行为「我」，与爻五行比较。
    生我=父母，同我=兄弟，我生=子孙，我克=妻财，克我=官鬼。
    """
    if gong_wuxing == yao_wuxing:
        return "兄弟"
    if WU_XING_SHENG.get(yao_wuxing) == gong_wuxing:
        return "父母"
    if WU_XING_SHENG.get(gong_wuxing) == yao_wuxing:
        return "子孙"
    if WU_XING_KE.get(gong_wuxing) == yao_wuxing:
        return "妻财"
    if WU_XING_KE.get(yao_wuxing) == gong_wuxing:
        return "官鬼"
    return "兄弟"


def _get_day_tiangan(dt: Optional[datetime] = None) -> str:
    """获取日天干（用于六神），与 lunar_python 日柱一致。"""
    dt = dt or datetime.now()
    try:
        from lunar_python import Solar

        solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
        gan = solar.getLunar().getDayGan()
        if gan:
            return str(gan)
    except Exception:
        pass
    return "甲"


def plan_pan(
    upper: int,
    lower: int,
    lines: List[Dict[str, Any]],
    moving: List[int],
    dt: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    排盘：为 lines 补充世应、六亲、六神。
    lines 从下往上 [初爻, ..., 上爻]，每项 {"yin_yang", "is_dong"}。
    dt: 占卜时间，用于推算日干以排六神。缺省使用当前时间。
    返回 {"lines": [...], "shi_yao": 1-6, "ying_yao": 1-6, "gong": "乾", "gong_wuxing": "金"}。
    """
    gong_id, shi_pos = _get_gong_and_shi(upper, lower)
    gong_wx = TRIGRAM_WUXING[gong_id] or "土"
    ying_pos = (shi_pos + 3) % 6

    day_tg = _get_day_tiangan(dt)
    shen_start = TIANGAN_LIU_SHEN_START.get(day_tg, 0)

    lower_wx = [TRIGRAM_WUXING[lower] or "土"] * 3
    upper_wx = [TRIGRAM_WUXING[upper] or "土"] * 3
    yaos_wx = lower_wx + upper_wx

    result_lines = []
    for i in range(6):
        line = dict(lines[i])
        line["liu_qin"] = _liu_qin(gong_wx, yaos_wx[i])
        line["liu_shen"] = LIU_SHEN[(shen_start + i) % 6]
        result_lines.append(line)

    return {
        "lines": result_lines,
        "shi_yao": shi_pos + 1,
        "ying_yao": ying_pos + 1,
        "gong": TRIGRAM_NAMES[gong_id],
        "gong_wuxing": gong_wx,
    }
