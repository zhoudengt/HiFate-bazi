# -*- coding: utf-8 -*-
"""
六爻排盘：世应、六亲、六神。
卦宫五行定六亲；世应按八宫卦表；六神按日干或固定顺序。
"""

from typing import Any, Dict, List

# 八卦序号 1-8 乾兑离震巽坎艮坤 对应五行
GONG_WUXING = [None, "金", "金", "火", "木", "木", "水", "土", "土"]
# 卦宫序号 1-8 对应 乾坎艮震巽离坤兑（八宫卦序）
# 64 卦 (上卦1-8, 下卦1-8) 属于哪一宫、世爻在第几爻，查表或按规则算
# 简化：按世爻在 1-6 位的规则，八纯卦世爻在 6，初爻变世在 1... 这里用常见规则
# 卦宫 = 本卦下卦所在宫（八纯为下卦自己，一世卦为下卦对宫等）
# 最简实现：世爻位置用 (卦序或上下卦) 查表。六亲 = 卦宫五行 vs 爻五行。
# 爻五行：乾兑金、离火、震巽木、坎水、艮坤土。六爻从下往上，初爻取本卦下卦第一爻的五行...
# 本卦 6 爻的五行：下卦三爻 + 上卦三爻，每爻的五行由所在经卦定。
# 乾(金)兑(金)离(火)震(木)巽(木)坎(水)艮(土)坤(土)
TRIGRAM_WUXING = [None, "金", "金", "火", "木", "木", "水", "土", "土"]  # 1-8

LIU_SHEN = ["青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武"]


def _get_gong_and_shi(lower: int, upper: int) -> tuple:
    """
    根据本卦上下卦得卦宫(1-8)与世爻位置(0-5)。
    八宫卦规则：八纯卦世在上爻(5)；一世卦世在初爻(0)；二世在二(1)... 六世在六(5)。
    本卦 = 上卦+下卦，宫 = 下卦所在宫。世爻：看本卦是第几世（变爻在第几爻）。
    简化：用下卦为宫，世爻按「下卦几爻变」：0 变=八纯世在5，1 变=世在0，2 变=世在1...
    更简：直接按上下卦序号算。八纯 lower==upper 则世在 5；否则用动爻定世（由调用方传入 moving）。
    """
    # 若已知动爻，一世卦=动在初爻→世在0，二世=动在二→世在1 ... 六世=动在上→世在5
    # 无动爻时当静卦，世爻常取 3（三爻持世）。这里由调用方传 moving，无动取 3。
    gong = lower  # 卦宫取本卦下卦，五行用 GONG_WUXING[gong-1]
    return gong


def _yao_wuxing(trigram: int, yao_pos: int) -> str:
    """经卦 trigram(1-8) 中第 yao_pos(0,1,2) 爻的五行 = 该经卦的五行。"""
    return TRIGRAM_WUXING[trigram] or "土"


def _liu_qin(gong_wuxing: str, yao_wuxing: str) -> str:
    """卦宫五行为我，爻五行与我的生克：生我=父母，同我=兄弟，我生=子孙，我克=妻财，克我=官鬼。"""
    sheng_wo = {"金": "土", "水": "金", "木": "水", "火": "木", "土": "火"}
    ke_wo = {"金": "火", "水": "土", "木": "金", "火": "水", "土": "木"}  # 克我者
    wo_sheng = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}
    if sheng_wo.get(gong_wuxing) == yao_wuxing:
        return "父母"
    if gong_wuxing == yao_wuxing:
        return "兄弟"
    if wo_sheng.get(gong_wuxing) == yao_wuxing:
        return "子孙"
    if ke_wo.get(gong_wuxing) == yao_wuxing:
        return "妻财"
    if ke_wo.get(gong_wuxing) == yao_wuxing:
        return "官鬼"
    return "兄弟"  # fallback


def plan_pan(
    upper: int,
    lower: int,
    lines: List[Dict[str, Any]],
    moving: List[int],
) -> Dict[str, Any]:
    """
    排盘：为 lines 补充世应、六亲、六神。
    lines 从下往上 [初爻, ..., 上爻]，每项 {"yin_yang", "is_dong"}。
    返回 {"lines": [...], "shi_yao": 1-6, "ying_yao": 1-6}，lines 中每爻增加 liu_qin, liu_shen。
    """
    gong = _get_gong_and_shi(lower, upper)
    gong_wx = GONG_WUXING[gong] or "土"
    # 世爻：有动爻时，动爻最高位为世（多动取最上）；无动静卦世在 3
    if moving:
        shi_pos = max(moving)  # 0-5
    else:
        shi_pos = 3
    ying_pos = (shi_pos + 3) % 6
    # 六爻五行：下卦三爻 + 上卦三爻
    lower_wx = [_yao_wuxing(lower, i) for i in range(3)]
    upper_wx = [_yao_wuxing(upper, i) for i in range(3)]
    yaos_wx = lower_wx + upper_wx
    result_lines = []
    for i in range(6):
        line = dict(lines[i])
        line["liu_qin"] = _liu_qin(gong_wx, yaos_wx[i])
        # 六神从世爻起青龙，顺时针：世爻=青龙，世+1=朱雀，...
        j = (i - shi_pos) % 6
        line["liu_shen"] = LIU_SHEN[j]
        result_lines.append(line)
    return {
        "lines": result_lines,
        "shi_yao": shi_pos + 1,
        "ying_yao": ying_pos + 1,
    }
