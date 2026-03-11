# -*- coding: utf-8 -*-
"""
六爻占卜服务：起卦、排盘、组装卦象响应。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.liuyao import coin_method, get_hexagram_texts, number_method, plan_pan, time_method


def divinate(
    question: str,
    method: str,
    coin_results: Optional[List[int]] = None,
    number: Optional[List[int]] = None,
    divination_time: Optional[str] = None,
) -> Dict[str, Any]:
    """
    起卦并返回完整卦象数据。
    method: coin | number | time
    缺参时 raise ValueError。
    """
    if not question or not question.strip():
        raise ValueError("占卜问题不能为空")
    method = (method or "").strip().lower()
    if method not in ("coin", "number", "time"):
        raise ValueError("method 必须为 coin / number / time 之一")

    raw: Dict[str, Any]
    if method == "coin":
        if not coin_results or len(coin_results) != 6:
            raise ValueError("铜钱法需要 coin_results，且长度必须为 6")
        raw = coin_method(coin_results)
    elif method == "number":
        if not number or len(number) != 3:
            raise ValueError("数字法需要 number，且为 3 个数字")
        raw = number_method(number)
    else:
        if not divination_time or not divination_time.strip():
            raise ValueError("时间法需要 divination_time，格式 YYYY-MM-DD HH:mm")
        try:
            dt = datetime.strptime(divination_time.strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("divination_time 格式应为 YYYY-MM-DD HH:mm")
        raw = time_method(dt)

    upper, lower = raw["upper"], raw["lower"]
    lines = raw["lines"]
    moving = raw.get("moving", [])
    upper_bian = raw.get("upper_bian", upper)
    lower_bian = raw.get("lower_bian", lower)
    lines_bian = raw.get("lines_bian", lines)

    pan = plan_pan(upper, lower, lines, moving)
    lines_with_pan = pan["lines"]
    shi_yao = pan["shi_yao"]
    ying_yao = pan["ying_yao"]

    texts = get_hexagram_texts(upper, lower)
    gua_ci = (texts.get("gua_ci") or "") if texts else ""
    yao_ci_list = texts.get("lines", ["", "", "", "", "", ""]) if texts else ["", "", "", "", "", ""]

    ben_lines: List[Dict[str, Any]] = []
    for i in range(6):
        line = dict(lines_with_pan[i])
        line["position"] = i + 1  # 1=初爻, 6=上爻
        line["yao_ci"] = yao_ci_list[i] if i < len(yao_ci_list) else ""
        ben_lines.append(line)

    texts_bian = get_hexagram_texts(upper_bian, lower_bian)
    name_bian = (texts_bian.get("name") or "未知") if texts_bian else "未知"
    yao_ci_bian = texts_bian.get("lines", ["", "", "", "", "", ""]) if texts_bian else ["", "", "", "", "", ""]

    pan_bian = plan_pan(upper_bian, lower_bian, lines_bian, [])
    bian_lines: List[Dict[str, Any]] = []
    for i in range(6):
        line = dict(pan_bian["lines"][i])
        line["position"] = i + 1
        line["yao_ci"] = yao_ci_bian[i] if i < len(yao_ci_bian) else ""
        bian_lines.append(line)

    name_ben = (texts.get("name") or "未知") if texts else "未知"

    return {
        "question": question.strip(),
        "method": method,
        "ben_gua": {"name": name_ben, "lines": ben_lines},
        "bian_gua": {"name": name_bian, "lines": bian_lines},
        "gua_ci": gua_ci,
        "shi_ying": {"shi_yao": shi_yao, "ying_yao": ying_yao},
    }
