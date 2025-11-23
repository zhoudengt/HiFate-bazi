#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理神煞华盖+六合三合数量条件
"""

from typing import Any, Dict, List, Optional, Tuple


def handle_deities_huagai_liuhe_sanhe(cond2: str, qty: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """处理：带有"华盖"这个神煞，并且命局中"六合"与"三合"数量之和至少3个以上（包含3个）"""
    if "华盖" in cond2 and ("六合" in cond2 or "三合" in cond2):
        # 提取数量要求
        min_count = 3
        if "至少3个" in cond2 or "3个以上" in cond2:
            min_count = 3
        
        return [
            {
                "deities_in_any_pillar": ["华盖"]
            },
            {
                "branch_liuhe_sanhe_count": {
                    "min": min_count
                }
            }
        ], None
    
    return None, f"未实现的神煞华盖六合三合条件: {cond2}"

