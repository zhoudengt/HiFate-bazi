"""
十神命格匹配条件调试API
用于验证和展示匹配逻辑
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

from server.services.bazi_service import BaziService
from server.services.formula_rule_service import FormulaRuleService

router = APIRouter()


class ShishenDebugRequest(BaseModel):
    """十神命格调试请求"""
    solar_date: str  # 公历日期 YYYY-MM-DD
    solar_time: str  # 公历时间 HH:MM
    gender: str  # 性别: male/female


class ShishenDebugResponse(BaseModel):
    """十神命格调试响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/shishen/debug", response_model=ShishenDebugResponse)
async def debug_shishen_matching(request: ShishenDebugRequest):
    """
    调试十神命格匹配逻辑
    
    返回详细的匹配条件和中间状态，用于验证规则是否正确匹配
    """
    try:
        # 1. 计算八字
        bazi_result = BaziService.calculate_bazi_full(
            solar_date=request.solar_date,
            solar_time=request.solar_time,
            gender=request.gender
        )
        
        if not bazi_result.get('success'):
            raise HTTPException(status_code=400, detail="八字计算失败")
        
        bazi_data = bazi_result.get('data', {})
        
        # 2. 提取关键信息
        details = bazi_data.get('details', {})
        pillars = bazi_data.get('pillars', {})
        
        # 3. 加载十神命格规则
        rules_data = FormulaRuleService.load_rules()
        shishen_rules = rules_data.get('十神命格', {}).get('rows', [])
        
        # 4. 详细的匹配过程
        matching_details = {
            'bazi_info': {
                'year': pillars.get('year', ''),
                'month': pillars.get('month', ''),
                'day': pillars.get('day', ''),
                'hour': pillars.get('hour', '')
            },
            'shishen_info': {
                'year_stem_shishen': details.get('year_stem_shishen', ''),
                'month_stem_shishen': details.get('month_stem_shishen', ''),
                'day_stem_shishen': details.get('day_stem_shishen', ''),
                'hour_stem_shishen': details.get('hour_stem_shishen', ''),
                'year_branch_hidden': details.get('year_branch_hidden', {}),
                'month_branch_hidden': details.get('month_branch_hidden', {}),
                'day_branch_hidden': details.get('day_branch_hidden', {}),
                'hour_branch_hidden': details.get('hour_branch_hidden', {})
            },
            'matching_results': []
        }
        
        # 5. 对每条规则进行匹配测试
        for rule in shishen_rules:
            rule_id = rule.get('ID')
            rule_type = rule.get('类型')
            condition1 = rule.get('筛选条件1')
            condition2 = rule.get('筛选条件2')
            result = rule.get('结果', '')
            
            # 提取十神名称
            shishen_name = None
            for possible_shishen in ['正官', '七杀', '正印', '偏印', '正财', '偏财', '食神', '伤官']:
                if possible_shishen in condition2:
                    shishen_name = possible_shishen
                    break
            
            # 测试匹配
            is_matched = FormulaRuleService._match_shishen_rule(bazi_data, condition1, condition2)
            
            # 详细的匹配条件检查
            match_detail = {
                'rule_id': rule_id,
                'rule_type': rule_type,
                'shishen_name': shishen_name,
                'is_matched': is_matched,
                'result_preview': result[:50] + '...' if len(result) > 50 else result,
                'conditions_checked': []
            }
            
            if shishen_name:
                # 优先级1检查
                priority1_match = (
                    details.get('month_stem_shishen') == shishen_name and
                    shishen_name in details.get('month_branch_hidden', {}).values()
                )
                match_detail['conditions_checked'].append({
                    'priority': 1,
                    'description': f'月柱主星是{shishen_name}，且月柱副星有{shishen_name}',
                    'month_stem': details.get('month_stem_shishen'),
                    'month_hidden_has': shishen_name in details.get('month_branch_hidden', {}).values(),
                    'matched': priority1_match
                })
                
                # 优先级2检查
                priority2_match = (
                    shishen_name in details.get('month_branch_hidden', {}).values() and
                    (details.get('year_stem_shishen') == shishen_name or 
                     details.get('hour_stem_shishen') == shishen_name)
                )
                match_detail['conditions_checked'].append({
                    'priority': 2,
                    'description': f'月柱副星有{shishen_name}，且年柱主星有{shishen_name}或时柱主星有{shishen_name}',
                    'month_hidden_has': shishen_name in details.get('month_branch_hidden', {}).values(),
                    'year_stem': details.get('year_stem_shishen'),
                    'hour_stem': details.get('hour_stem_shishen'),
                    'matched': priority2_match
                })
                
                # 优先级3检查
                priority3_match = (
                    details.get('month_stem_shishen') == shishen_name and
                    (shishen_name in details.get('year_branch_hidden', {}).values() or
                     shishen_name in details.get('day_branch_hidden', {}).values() or
                     shishen_name in details.get('hour_branch_hidden', {}).values())
                )
                match_detail['conditions_checked'].append({
                    'priority': 3,
                    'description': f'月柱主星是{shishen_name}，且年/日/时柱副星有{shishen_name}',
                    'month_stem': details.get('month_stem_shishen'),
                    'year_hidden_has': shishen_name in details.get('year_branch_hidden', {}).values(),
                    'day_hidden_has': shishen_name in details.get('day_branch_hidden', {}).values(),
                    'hour_hidden_has': shishen_name in details.get('hour_branch_hidden', {}).values(),
                    'matched': priority3_match
                })
            
            matching_details['matching_results'].append(match_detail)
        
        return ShishenDebugResponse(
            success=True,
            data=matching_details
        )
        
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        return ShishenDebugResponse(
            success=False,
            error=error_detail
        )

