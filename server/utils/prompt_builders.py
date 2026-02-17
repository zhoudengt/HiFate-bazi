#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompt 构建工具（兼容性代理）

实际实现已拆分到 server/utils/prompts/ 子模块：
- prompts/common.py          - 公共格式化工具
- prompts/marriage.py         - 婚姻分析
- prompts/career_wealth.py    - 事业财富
- prompts/children_study.py   - 子女学习
- prompts/health.py           - 健康分析
- prompts/general_review.py   - 总评分析
- prompts/other.py            - 智能分析/年运/面相/风水

所有导入保持向后兼容，现有代码无需修改。
"""

# 重新导出所有函数，保持向后兼容
from server.utils.prompts import *  # noqa: F401,F403
from server.utils.prompts.common import _filter_empty_deities, _simplify_dayun, _get_ganzhi, _normalize_life_stage, _collect_liunians_for_step  # noqa: F401
