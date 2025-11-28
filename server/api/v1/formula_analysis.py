"""
算法公式规则分析API

⚠️ 已迁移：内部使用RuleService（数据库规则），保持API兼容性
原基于 docs/2025.11.20算法公式.json 的规则已迁移到数据库
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import warnings
import json

from server.services.bazi_service import BaziService
from server.services.rule_service import RuleService
# 保留导入以支持废弃的FormulaRuleService（向后兼容）
try:
    from server.services.formula_rule_service import FormulaRuleService
    FORMULA_SERVICE_AVAILABLE = True
except ImportError:
    FORMULA_SERVICE_AVAILABLE = False
    FormulaRuleService = None

router = APIRouter()


class FormulaAnalysisRequest(BaseModel):
    """算法公式分析请求"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD")
    solar_time: str = Field(..., description="阳历时间，格式：HH:MM")
    gender: str = Field(..., description="性别：male/female")
    rule_types: Optional[List[str]] = Field(None, description="规则类型列表，可选值：wealth/marriage/career/children/character/summary/health/peach_blossom/shishen")


class FormulaAnalysisResponse(BaseModel):
    """算法公式分析响应"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/bazi/formula-analysis", response_model=FormulaAnalysisResponse)
async def analyze_formula_rules(request: FormulaAnalysisRequest):
    """
    算法公式规则分析
    
    根据八字信息匹配相应的规则，返回匹配的规则详情
    
    规则类型:
    - wealth: 财富规则
    - marriage: 婚配规则
    - career: 事业规则
    - children: 子女规则
    - character: 性格规则
    - summary: 总评规则
    - health: 身体规则
    - peach_blossom: 桃花规则
    - shishen: 十神命格规则
    """
    try:
        # 1. 计算八字
        bazi_result = BaziService.calculate_bazi_full(
            solar_date=request.solar_date,
            solar_time=request.solar_time,
            gender=request.gender
        )
        
        # calculate_bazi_full返回的数据结构: {'bazi': {...}, 'rizhu': {...}, 'matched_rules': {...}}
        if not bazi_result or not isinstance(bazi_result, dict):
            raise HTTPException(status_code=400, detail='八字计算失败')
        
        # 提取实际的八字数据（在bazi键下）
        bazi_data = bazi_result.get('bazi', {})
        if not bazi_data:
            raise HTTPException(status_code=400, detail='八字数据为空')
        
        # 2. 匹配规则（使用RuleService，已迁移到数据库）
        # 构建规则匹配数据
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': bazi_data.get('element_counts', {}),
            'relationships': bazi_data.get('relationships', {})
        }
        
        # 转换规则类型（前端传入的是英文，RuleService也使用英文）
        rule_types = request.rule_types if request.rule_types else ['wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen']
        
        # ⚠️ 十神命格特殊处理：使用FormulaRuleService的优先级匹配逻辑
        # RuleService不支持十神命格的复杂优先级逻辑，所以对于十神命格使用FormulaRuleService
        migrated_rules = []
        
        if 'shishen' in rule_types and FORMULA_SERVICE_AVAILABLE:
            # 使用FormulaRuleService匹配十神命格（支持优先级逻辑）
            try:
                formula_result = FormulaRuleService.match_rules(rule_data, ['十神命格'])
                # 转换为RuleService格式
                for shishen_id in formula_result['matched_rules'].get('shishen', []):
                    shishen_detail = formula_result['rule_details'].get(shishen_id)
                    if shishen_detail:
                        migrated_rules.append({
                            'rule_id': f'FORMULA_{shishen_id}',
                            'rule_type': 'shishen',
                            'content': {'text': shishen_detail.get('result', '')},
                            'conditions': {},  # FormulaRuleService已经完成匹配
                            'priority': 100
                        })
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"十神命格匹配失败: {e}")
            
            # 从rule_types中移除shishen，避免重复匹配
            rule_types_without_shishen = [rt for rt in rule_types if rt != 'shishen']
        else:
            rule_types_without_shishen = rule_types
        
        # 使用RuleService匹配其他规则（只匹配迁移的FORMULA_规则）
        if rule_types_without_shishen:
            rule_matched = RuleService.match_rules(rule_data, rule_types=rule_types_without_shishen, use_cache=True)
        # 筛选迁移的规则（FORMULA_前缀）
            migrated_rules.extend([r for r in rule_matched if r.get('rule_id', '').startswith('FORMULA_')])
        
        # 3. 转换为FormulaRuleService的响应格式（保持API兼容性）
        matched_result = _convert_rule_service_to_formula_format(migrated_rules, rule_types)
        
        # 4. 格式化响应
        response_data = {
            'bazi_info': {
                'solar_date': request.solar_date,
                'solar_time': request.solar_time,
                'gender': request.gender,
                'bazi_pillars': bazi_data.get('bazi_pillars', {}),
                'day_stem': bazi_data.get('bazi_pillars', {}).get('day', {}).get('stem', ''),
                'day_branch': bazi_data.get('bazi_pillars', {}).get('day', {}).get('branch', '')
            },
            'bazi_data': bazi_data,  # 添加完整的八字数据（包含details）
            'matched_rules': matched_result['matched_rules'],
            'rule_details': matched_result['rule_details'],
            'statistics': {
                'total_matched': matched_result['total_matched'],
                'wealth_count': len(matched_result['matched_rules'].get('wealth', [])),
                'marriage_count': len(matched_result['matched_rules'].get('marriage', [])),
                'career_count': len(matched_result['matched_rules'].get('career', [])),
                'children_count': len(matched_result['matched_rules'].get('children', [])),
                'character_count': len(matched_result['matched_rules'].get('character', [])),
                'summary_count': len(matched_result['matched_rules'].get('summary', [])),
                'health_count': len(matched_result['matched_rules'].get('health', [])),
                'peach_blossom_count': len(matched_result['matched_rules'].get('peach_blossom', [])),
                'shishen_count': len(matched_result['matched_rules'].get('shishen', []))
            }
        }
        
        return FormulaAnalysisResponse(success=True, data=response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        return FormulaAnalysisResponse(success=False, error=str(e))


def _convert_rule_service_to_formula_format(migrated_rules: list, rule_types: Optional[List[str]] = None) -> dict:
    """
    将RuleService的返回格式转换为FormulaRuleService的格式（保持API兼容性）
    
    Args:
        migrated_rules: RuleService返回的规则列表
        rule_types: 规则类型列表
        
    Returns:
        FormulaRuleService格式的匹配结果
    """
    # 初始化匹配结果结构
    matched_rules = {
        'wealth': [],
        'marriage': [],
        'career': [],
        'children': [],
        'character': [],
        'summary': [],
        'health': [],
        'peach_blossom': [],
        'shishen': []
    }
    rule_details = {}
    
    # 规则类型中文映射
    type_cn_mapping = {
        'wealth': '财富',
        'marriage': '婚姻',
        'career': '事业',
        'children': '子女',
        'character': '性格',
        'summary': '总评',
        'health': '身体',
        'peach_blossom': '桃花',
        'shishen': '十神命格'
    }
    
    # ✅ 从数据库查询规则详情（包括条件信息）
    try:
        from server.db.mysql_connector import get_db_connection
        db = get_db_connection()
    except Exception:
        db = None
    
    for rule in migrated_rules:
        rule_id = rule.get('rule_id', '')
        rule_type = rule.get('rule_type', '')
        
        # 提取原始规则ID（去掉FORMULA_前缀）
        if rule_id.startswith('FORMULA_'):
            original_id = rule_id.replace('FORMULA_', '')
        else:
            continue
        
        # 尝试从规则ID中提取数字部分（兼容 FORMULA_80001 和 FORMULA_事业_80001 两种格式）
        try:
            # 尝试直接转换为整数
            numeric_id = int(original_id)
        except ValueError:
            # 如果失败，尝试从末尾提取数字（格式如: 事业_80001）
            parts = original_id.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                numeric_id = int(parts[1])
            else:
                # 使用规则ID的哈希值作为ID
                numeric_id = hash(original_id) % 1000000
        
        # 根据规则类型添加到对应列表
        if rule_type in matched_rules:
            matched_rules[rule_type].append(numeric_id)
        
        # 构建规则详情（保持FormulaRuleService格式）
        content = rule.get('content', {})
        if isinstance(content, dict):
            rule_text = content.get('text', '')
        else:
            rule_text = str(content)
        
        # ✅ 从数据库查询条件信息（从description字段读取）
        condition1 = ''
        condition2 = ''
        gender = '无论男女'
        
        if db:
            try:
                # 查询规则详情（从description字段读取条件信息）
                db_rule = db.execute_query(
                    "SELECT description, conditions FROM bazi_rules WHERE rule_code = %s LIMIT 1",
                    (rule_id,)
                )
                if db_rule and len(db_rule) > 0:
                    rule_data = db_rule[0]
                    description = rule_data.get('description', '') or ''
                    conditions = rule_data.get('conditions', {})
                    
                    # 处理 description 可能是 JSON 字符串的情况
                    if description:
                        desc_data = None
                        # 如果description是字典类型（MySQL JSON字段可能已经解析）
                        if isinstance(description, dict):
                            desc_data = description
                        # 如果description是字符串类型，尝试解析为JSON
                        elif isinstance(description, str):
                            try:
                                desc_data = json.loads(str(description))
                            except (json.JSONDecodeError, TypeError, ValueError):
                                desc_data = None
                        
                        # 从JSON格式的description中提取条件信息
                        if desc_data and isinstance(desc_data, dict):
                            condition1 = desc_data.get('筛选条件1', '') or ''
                            condition2 = desc_data.get('筛选条件2', '') or ''
                            gender = desc_data.get('性别', '无论男女') or '无论男女'
                        elif description and isinstance(description, str):
                            # 如果不是JSON格式，尝试从文本中提取（兼容旧格式）
                            import re
                            cond1_match = re.search(r'筛选条件1[：:]\s*([^，,\n]+)', description)
                            cond2_match = re.search(r'筛选条件2[：:]\s*([^，,\n]+)', description)
                            if cond1_match:
                                condition1 = cond1_match.group(1).strip()
                            if cond2_match:
                                condition2 = cond2_match.group(1).strip()
                    
                    # 如果没有从description中提取到，尝试从 conditions JSON 转换
                    if not condition1 and not condition2 and conditions:
                        if isinstance(conditions, str):
                            try:
                                conditions = json.loads(conditions)
                            except:
                                conditions = {}
                        
                        if isinstance(conditions, dict) and conditions:
                            condition_text = _convert_conditions_to_text(conditions)
                            if condition_text:
                                parts = condition_text.split('，', 1)
                                condition1 = parts[0] if len(parts) > 0 else ''
                                condition2 = parts[1] if len(parts) > 1 else ''
                    
                    # 从 conditions 中提取性别信息（如果description中没有）
                    if gender == '无论男女' and conditions:
                        if isinstance(conditions, str):
                            try:
                                conditions = json.loads(conditions)
                            except:
                                conditions = {}
                        
                        if isinstance(conditions, dict) and conditions.get('gender'):
                            gender_map = {'male': '男', 'female': '女'}
                            gender = gender_map.get(conditions['gender'], '无论男女')
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"查询规则详情失败 (rule_id={rule_id}): {e}")
        
        # 如果数据库查询失败，从 rule 对象的 conditions 字段转换（兜底方案）
        if not condition1 and not condition2:
            conditions = rule.get('conditions', {})
            if isinstance(conditions, str):
                try:
                    conditions = json.loads(conditions)
                except:
                    conditions = {}
            
            if isinstance(conditions, dict) and conditions:
                condition_text = _convert_conditions_to_text(conditions)
                if condition_text:
                    parts = condition_text.split('，', 1)
                    condition1 = parts[0] if len(parts) > 0 else ''
                    condition2 = parts[1] if len(parts) > 1 else ''
        
        # 从 rule 对象的 conditions 中提取性别信息（兜底方案）
        if gender == '无论男女':
            conditions = rule.get('conditions', {})
            if isinstance(conditions, dict) and conditions.get('gender'):
                gender_map = {'male': '男', 'female': '女'}
                gender = gender_map.get(conditions['gender'], '无论男女')
        
        # 构建规则详情（同时提供中英文字段名，兼容前端）
        rule_details[numeric_id] = {
            'ID': numeric_id,
            'id': numeric_id,  # 添加英文字段
            '类型': type_cn_mapping.get(rule_type, rule_type),
            'type': type_cn_mapping.get(rule_type, rule_type),  # 添加英文字段
            '性别': gender,
            'gender': gender,  # 添加英文字段
            '筛选条件1': condition1,
            'condition1': condition1,  # 添加英文字段
            '筛选条件2': condition2,
            'condition2': condition2,  # 添加英文字段
            '数量': None,
            '结果': rule_text,
            'result': rule_text  # 添加英文字段
        }
    
    # 计算总数
    total_matched = sum(len(rules) for rules in matched_rules.values())
    
    return {
        'matched_rules': matched_rules,
        'rule_details': rule_details,
        'total_matched': total_matched
    }


def _convert_conditions_to_text(conditions: dict) -> str:
    """
    将 conditions JSON 转换为人类可读的文本格式
    
    Args:
        conditions: 条件字典
        
    Returns:
        str: 可读的条件文本
    """
    if not conditions or not isinstance(conditions, dict):
        return ''
    
    parts = []
    
    # 处理简单条件
    if conditions.get('year_pillar'):
        value = conditions['year_pillar']
        if value != '*':
            parts.append(f"年柱: {value}")
    
    if conditions.get('month_pillar'):
        value = conditions['month_pillar']
        if value != '*':
            parts.append(f"月柱: {value}")
    
    if conditions.get('day_pillar'):
        value = conditions['day_pillar']
        if value != '*':
            parts.append(f"日柱: {value}")
    
    if conditions.get('hour_pillar'):
        value = conditions['hour_pillar']
        if value != '*':
            parts.append(f"时柱: {value}")
    
    if conditions.get('gender'):
        gender_map = {'male': '男', 'female': '女'}
        parts.append(f"性别: {gender_map.get(conditions['gender'], conditions['gender'])}")
    
    # 处理神煞条件
    if conditions.get('deities_in_any_pillar'):
        deities = conditions['deities_in_any_pillar']
        if isinstance(deities, list):
            parts.append(f"神煞: {', '.join(deities)}")
    
    # 处理元素条件
    if conditions.get('elements_count'):
        elem_count = conditions['elements_count']
        if isinstance(elem_count, dict):
            for elem, count in elem_count.items():
                if count:
                    parts.append(f"五行{elem}: {count}个")
    
    # 处理组合条件
    if conditions.get('all'):
        all_parts = []
        for cond in conditions['all']:
            text = _convert_conditions_to_text(cond)
            if text:
                all_parts.append(text)
        if all_parts:
            parts.append(' 且 '.join(all_parts))
    
    if conditions.get('any'):
        any_parts = []
        for cond in conditions['any']:
            text = _convert_conditions_to_text(cond)
            if text:
                any_parts.append(text)
        if any_parts:
            parts.append(' 或 '.join(any_parts))
    
    return '，'.join(parts) if parts else ''


@router.get("/bazi/formula-rules/info")
async def get_formula_rules_info():
    """
    获取规则信息
    
    返回所有规则的统计信息（从数据库获取）
    """
    try:
        from server.db.mysql_connector import get_db_connection
        
        db = get_db_connection()
        
        # 从数据库获取规则统计
        stats = db.execute_query("""
            SELECT rule_type, COUNT(*) as count
            FROM bazi_rules
            WHERE rule_code LIKE 'FORMULA_%'
            GROUP BY rule_type
        """)
        
        info = {
            'total_rules': 0,
            'rule_types': {}
        }
        
        type_mapping = {
            'wealth': {'name': '财富', 'name_en': 'wealth'},
            'marriage': {'name': '婚姻', 'name_en': 'marriage'},
            'career': {'name': '事业', 'name_en': 'career'},
            'children': {'name': '子女', 'name_en': 'children'},
            'character': {'name': '性格', 'name_en': 'character'},
            'summary': {'name': '总评', 'name_en': 'summary'},
            'health': {'name': '身体', 'name_en': 'health'},
            'peach_blossom': {'name': '桃花', 'name_en': 'peach_blossom'},
            'shishen': {'name': '十神命格', 'name_en': 'shishen'}
        }
        
        for stat in stats:
            rule_type = stat['rule_type']
            count = stat['count']
            
            info['total_rules'] += count
            type_info = type_mapping.get(rule_type, {'name': rule_type, 'name_en': rule_type})
            info['rule_types'][rule_type] = {
                'name': type_info['name'],
                'name_en': type_info['name_en'],
                'count': count,
                'has_result': True  # 所有规则都有结果
            }
        
        return {
            'success': True,
            'data': info
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
