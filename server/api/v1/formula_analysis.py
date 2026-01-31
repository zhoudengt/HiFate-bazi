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
import os
import time
import logging

from server.services.bazi_service import BaziService
from server.services.rule_service import RuleService
from server.utils.data_validator import validate_bazi_data
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.services.wangshuai_service import WangShuaiService
from server.services.bazi_detail_service import BaziDetailService
from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
from server.services.health_analysis_service import HealthAnalysisService
from server.services.bazi_display_service import BaziDisplayService
from core.analyzers.fortune_relation_analyzer import FortuneRelationAnalyzer
from server.utils.api_cache_helper import (
    generate_cache_key, get_cached_result, set_cached_result, L2_TTL
)
import asyncio
# ⚠️ FormulaRuleService 已完全废弃，所有规则匹配统一使用 RuleService

router = APIRouter()

# 双轨并行：编排层开关，默认关闭
USE_ORCHESTRATOR_FORMULA = os.environ.get("USE_ORCHESTRATOR_FORMULA", "false").lower() == "true"


class FormulaAnalysisRequest(BaziBaseRequest):
    """算法公式分析请求"""
    rule_types: Optional[List[str]] = Field(None, description="规则类型列表，可选值：wealth/marriage/career/children/character/summary/health/peach_blossom/shishen/parents")


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
    - parents: 父母规则
    """
    try:
        # 处理农历输入和时区转换
        final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
            request.solar_date,
            request.solar_time,
            request.calendar_type or "solar",
            request.location,
            request.latitude,
            request.longitude
        )
        
        logger = logging.getLogger(__name__)
        
        # >>> 缓存检查（公式分析固定，按规则类型缓存）<<<
        rule_types_str = "_".join(sorted(request.rule_types)) if request.rule_types else "all"
        cache_key = generate_cache_key("formula", final_solar_date, final_solar_time, request.gender, rule_types_str)
        cached = get_cached_result(cache_key, "formula-analysis")
        if cached:
            logger.info(f"✅ 公式分析缓存命中")
            return FormulaAnalysisResponse(success=True, data=cached)
        # >>> 缓存检查结束 <<<
        
        # 双轨并行：优先走编排层（USE_ORCHESTRATOR_FORMULA=true 时）
        if USE_ORCHESTRATOR_FORMULA:
            orchestrator_data = await BaziDataOrchestrator.fetch_data(
                final_solar_date,
                final_solar_time,
                request.gender,
                modules={
                    "bazi": True,
                    "wangshuai": True,
                    "detail": True,
                    "health": True,
                },
                preprocessed=True,
                calendar_type=request.calendar_type or "solar",
                location=request.location,
                latitude=request.latitude,
                longitude=request.longitude,
            )
            bazi_result = orchestrator_data.get("bazi") or {}
            bazi_data = bazi_result.get("bazi", bazi_result) if isinstance(bazi_result, dict) else {}
            bazi_data = validate_bazi_data(bazi_data) if bazi_data else {}
            wangshuai_result = orchestrator_data.get("wangshuai") or {}
            detail_result = orchestrator_data.get("detail") or {}
            health_result = orchestrator_data.get("health") or {}
            if not bazi_data:
                raise HTTPException(status_code=400, detail="八字数据为空")
        else:
            # 1. 计算八字
            # ✅ 修复：改为异步执行，避免阻塞事件循环
            start_time = time.time()
            loop = asyncio.get_event_loop()
            from server.utils.async_executor import get_executor
            try:
                # 使用统一线程池执行，添加30秒超时保护
                bazi_result = await asyncio.wait_for(
                    loop.run_in_executor(
                        get_executor(),
                        BaziService.calculate_bazi_full,
                        final_solar_date,
                        final_solar_time,
                        request.gender
                    ),
                    timeout=30.0
                )
                elapsed_time = time.time() - start_time
                logger.info(f"⏱️ 八字计算耗时: {elapsed_time:.2f}秒")
            except asyncio.TimeoutError:
                elapsed_time = time.time() - start_time
                logger.error(f"❌ 八字计算超时（>{30.0}秒），耗时: {elapsed_time:.2f}秒")
                raise HTTPException(status_code=500, detail="八字计算超时，请稍后重试")
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"❌ 八字计算异常（耗时: {elapsed_time:.2f}秒）: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"八字计算失败: {str(e)}")
            
            # calculate_bazi_full返回的数据结构: {'bazi': {...}, 'rizhu': {...}, 'matched_rules': {...}}
            if not bazi_result or not isinstance(bazi_result, dict):
                raise HTTPException(status_code=400, detail='八字计算失败')
            
            # 提取实际的八字数据（在bazi键下）
            bazi_data = bazi_result.get('bazi', {})
            if not bazi_data:
                raise HTTPException(status_code=400, detail='八字数据为空')
            
            # ✅ 统一类型验证：确保所有字段类型正确（防止gRPC序列化问题）
            bazi_data = validate_bazi_data(bazi_data)
            
            # 1.1. 并行获取额外数据（喜忌、大运流年、健康分析），使用统一线程池
            loop = asyncio.get_event_loop()
            from server.utils.async_executor import get_executor
            _exec = get_executor()
            try:
                wangshuai_result, detail_result, health_result = await asyncio.gather(
                    loop.run_in_executor(
                        _exec,
                        WangShuaiService.calculate_wangshuai,
                        final_solar_date,
                        final_solar_time,
                        request.gender
                    ),
                    loop.run_in_executor(
                        _exec,
                        BaziDetailService.calculate_detail_full,
                        final_solar_date,
                        final_solar_time,
                        request.gender
                    ),
                    loop.run_in_executor(
                        _exec,
                        HealthAnalysisService.analyze,
                        bazi_data
                    ),
                    return_exceptions=True
                )
                
                # 记录数据获取结果（用于调试）
                if isinstance(wangshuai_result, Exception):
                    logger.warning(f"获取喜忌数据失败: {wangshuai_result}")
                if isinstance(detail_result, Exception):
                    logger.warning(f"获取大运流年数据失败: {detail_result}")
                if isinstance(health_result, Exception):
                    logger.warning(f"获取健康分析数据失败: {health_result}")
            except Exception as e:
                # 如果并行调用失败，使用默认值，不影响主流程
                logger.warning(f"并行数据获取异常: {e}")
                wangshuai_result = {}
                detail_result = {}
                health_result = {}
        
        # 提取喜忌数据
        xi_ji_data = {}
        if isinstance(wangshuai_result, dict) and not isinstance(wangshuai_result, Exception):
            xi_ji_data = {
                'xi_shen': wangshuai_result.get('xi_shen', []),
                'ji_shen': wangshuai_result.get('ji_shen', []),
                'xi_shen_elements': wangshuai_result.get('xi_shen_elements', []),
                'ji_shen_elements': wangshuai_result.get('ji_shen_elements', [])
            }
        
        # 提取大运流年序列
        dayun_sequence = []
        liunian_sequence = []
        if isinstance(detail_result, dict) and not isinstance(detail_result, Exception):
            dayun_sequence = detail_result.get('dayun_sequence', [])[:8]  # 限制为前8个大运
            liunian_sequence = detail_result.get('liunian_sequence', [])
        
        # 提取健康分析数据
        health_analysis = {}
        if isinstance(health_result, dict) and not isinstance(health_result, Exception):
            health_analysis = {
                'wuxing_balance': health_result.get('wuxing_balance', {}),
                'zangfu_duiying': health_result.get('body_algorithm', {}),  # 注意字段名映射
                'jiankang_ruodian': health_result.get('pathology_tendency', {})
            }
        
        # 筛选特殊流年（四柱冲合刑害、岁运并临）
        special_liunians = _filter_special_liunians(
            liunian_sequence,
            dayun_sequence,
            bazi_data.get('bazi_pillars', {})
        )
        
        # 调试日志：检查数据获取情况（在所有变量定义之后）
        logger.info(f"[FormulaAnalysis] xi_ji_data: {bool(xi_ji_data)}, dayun_sequence: {len(dayun_sequence) if dayun_sequence else 0}, special_liunians: {len(special_liunians) if special_liunians else 0}, health_analysis: {bool(health_analysis)}")
        
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
        # ✅ 统一类型验证：确保规则匹配数据也经过验证
        rule_data = validate_bazi_data(rule_data)
        
        # 转换规则类型（前端传入的是英文，RuleService也使用英文）
        rule_types = request.rule_types if request.rule_types else ['wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents']
        
        # ✅ 统一使用RuleService匹配所有规则（包括十神命格）
        # 十神命格规则已迁移到数据库，使用JSON条件格式，RuleService已支持
        # ✅ 优化：规则类型已统一为标准格式（wealth, marriage等），无需兼容formula_*格式
        migrated_rules = []
        
        # 使用RuleService匹配所有规则（只匹配迁移的FORMULA_规则）
        # ✅ 优化：启用缓存，提升性能（规则更新时会自动刷新缓存）
        if rule_types:
            rule_matched = RuleService.match_rules(rule_data, rule_types=rule_types, use_cache=True)
            # 筛选迁移的规则（FORMULA_前缀）
            migrated_rules.extend([r for r in rule_matched if r.get('rule_id', '').startswith('FORMULA_')])
        
        # 3. 转换为前端期望的响应格式（保持API兼容性）
        # 注意：使用原始的 rule_types（不带 formula_ 前缀），因为前端期望的是 wealth, parents 等格式
        matched_result = _convert_rule_service_to_formula_format(migrated_rules, rule_types)
        
        # 4. 格式化响应
        # 确保新增字段始终存在（即使数据为空）
        formatted_dayun = _format_dayun_sequence(dayun_sequence) if dayun_sequence else []
        
        # 调试日志：检查变量值
        logger.info(f"[FormulaAnalysis DEBUG] Before building response_data: xi_ji_data={bool(xi_ji_data)}, formatted_dayun={len(formatted_dayun) if formatted_dayun else 0}, special_liunians={len(special_liunians) if special_liunians else 0}, health_analysis={bool(health_analysis)}")
        
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
                'shishen_count': len(matched_result['matched_rules'].get('shishen', [])),
                'parents_count': len(matched_result['matched_rules'].get('parents', []))
            },
            # 新增数据（确保始终存在，即使为空）
            'xi_ji': xi_ji_data if xi_ji_data else {'xi_shen': [], 'ji_shen': [], 'xi_shen_elements': [], 'ji_shen_elements': []},
            'dayun_sequence': formatted_dayun if formatted_dayun else [],
            'special_liunians': special_liunians if special_liunians else [],
            'health_analysis': health_analysis if health_analysis else {}
        }
        
        # 添加转换信息到结果
        if conversion_info.get('converted') or conversion_info.get('timezone_info'):
            response_data['conversion_info'] = conversion_info
        
        # 调试日志：检查最终响应数据
        logger.info(f"[FormulaAnalysis DEBUG] Final response_data keys: {list(response_data.keys())}")
        logger.info(f"[FormulaAnalysis DEBUG] Has xi_ji in response_data: {'xi_ji' in response_data}")
        logger.info(f"[FormulaAnalysis DEBUG] Has dayun_sequence in response_data: {'dayun_sequence' in response_data}")
        logger.info(f"[FormulaAnalysis DEBUG] Has special_liunians in response_data: {'special_liunians' in response_data}")
        logger.info(f"[FormulaAnalysis DEBUG] Has health_analysis in response_data: {'health_analysis' in response_data}")
        
        # >>> 缓存写入 <<<
        set_cached_result(cache_key, response_data, L2_TTL)
        # >>> 缓存写入结束 <<<
        
        return FormulaAnalysisResponse(success=True, data=response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        return FormulaAnalysisResponse(success=False, error=str(e))


def _convert_rule_service_to_formula_format(migrated_rules: list, rule_types: Optional[List[str]] = None) -> dict:
    """
    将RuleService的返回格式转换为前端期望的格式（保持API兼容性）
    
    Args:
        migrated_rules: RuleService返回的规则列表
        rule_types: 规则类型列表
        
    Returns:
        前端期望格式的匹配结果
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
        'shishen': [],
        'parents': []  # 新增
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
        'shishen': '十神命格',
        'parents': '父母'  # 新增
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
        
        # ✅ 优化：规则类型已统一为标准格式，无需处理formula_前缀
        # rule_type 现在统一为标准格式（wealth, marriage等）
        
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
        
        # 构建规则详情（保持前端期望格式）
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
    
    # ✅ 如果十神命格规则为空，添加默认的"常格"规则
    if not matched_rules['shishen']:
        changge_id = 99009
        matched_rules['shishen'].append(changge_id)
        # 使用字符串键（与其他规则保持一致，JSON序列化后键为字符串）
        rule_details[str(changge_id)] = {
            'ID': changge_id,
            'id': changge_id,
            '类型': '十神命格',
            'type': '十神命格',
            '性别': '无论男女',
            'gender': '无论男女',
            '筛选条件1': '无',
            'condition1': '无',
            '筛选条件2': '',
            'condition2': '',
            '数量': None,
            '结果': '常格\n解读：是八字命理中最基础、最常见的格局类型。它遵循 "五行平衡、力量中和" 的基本原则，通过日主与月令的关系确定核心特质和发展方向。',
            'result': '常格\n解读：是八字命理中最基础、最常见的格局类型。它遵循 "五行平衡、力量中和" 的基本原则，通过日主与月令的关系确定核心特质和发展方向。'
        }
        # 重新计算总数（因为添加了默认规则）
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


def _is_special_liunian(liunian: dict, dayun_info: dict, bazi_pillars: dict) -> bool:
    """
    判断流年是否有特殊关系（岁运并临、四柱冲合刑害）
    
    Args:
        liunian: 流年信息（包含 relations 字段）
        dayun_info: 对应的大运信息
        bazi_pillars: 八字四柱
    
    Returns:
        bool: 是否为特殊流年
    """
    # 方法1：检查原有的 relations 字段（快速判断）
    relations = liunian.get('relations', [])
    if relations and len(relations) > 0:
        return True  # 有特殊关系
    
    # 方法2：检查岁运并临（流年天干地支与大运天干地支完全相同）
    if dayun_info:
        liunian_stem = liunian.get('stem', '')
        liunian_branch = liunian.get('branch', '')
        dayun_stem = dayun_info.get('stem', '')
        dayun_branch = dayun_info.get('branch', '')
        
        if liunian_stem == dayun_stem and liunian_branch == dayun_branch:
            return True  # 岁运并临
    
    return False


def _find_dayun_for_liunian(liunian: dict, dayun_sequence: list) -> dict:
    """
    查找流年对应的大运信息
    
    Args:
        liunian: 流年信息
        dayun_sequence: 大运序列
    
    Returns:
        dict: 对应的大运信息，如果找不到则返回空字典
    """
    liunian_year = liunian.get('year')
    if not liunian_year:
        return {}
    
    # 查找包含该流年的大运
    for dayun in dayun_sequence:
        start_year = dayun.get('start_year')
        end_year = dayun.get('end_year')
        
        if start_year and end_year:
            if start_year <= liunian_year <= end_year:
                return dayun
    
    return {}


def _filter_special_liunians(
    liunian_sequence: list,
    dayun_sequence: list,
    bazi_pillars: dict
) -> list:
    """
    筛选特殊流年（只返回有特殊关系的流年）
    
    Args:
        liunian_sequence: 流年序列
        dayun_sequence: 大运序列
        bazi_pillars: 八字四柱
    
    Returns:
        list: 特殊流年列表（包含详细关系分析）
    """
    special_liunians = []
    
    for liunian in liunian_sequence:
        # 查找对应的大运信息
        dayun_info = _find_dayun_for_liunian(liunian, dayun_sequence)
        
        # 判断是否为特殊流年
        if _is_special_liunian(liunian, dayun_info, bazi_pillars):
            # 获取详细关系分析
            try:
                # 准备流年和大运的格式（FortuneRelationAnalyzer 需要的格式）
                liunian_dict = {
                    'stem': liunian.get('stem', ''),
                    'branch': liunian.get('branch', '')
                }
                dayun_dict = {
                    'stem': dayun_info.get('stem', ''),
                    'branch': dayun_info.get('branch', '')
                } if dayun_info else None
                
                # 调用 FortuneRelationAnalyzer 获取详细关系分析
                relation_analysis = FortuneRelationAnalyzer.analyze(
                    bazi_pillars,
                    liunian_dict,
                    dayun_dict
                )
            except Exception as e:
                # 如果关系分析失败，使用空字典
                relation_analysis = {}
            
            # 添加到特殊流年列表
            special_liunians.append({
                **liunian,  # 保留原有字段（包括 relations）
                'relation_analysis': relation_analysis,  # 添加详细关系分析
                'dayun_info': dayun_info  # 添加对应的大运信息
            })
    
    return special_liunians


def _format_dayun_sequence(dayun_sequence: list) -> list:
    """
    格式化大运序列（使用 BaziDisplayService._format_dayun_item 确保格式一致）
    
    Args:
        dayun_sequence: 原始大运序列
    
    Returns:
        list: 格式化后的大运序列
    """
    formatted_sequence = []
    
    for dayun in dayun_sequence:
        try:
            # 使用 BaziDisplayService._format_dayun_item 格式化（静态方法）
            formatted_dayun = BaziDisplayService._format_dayun_item(dayun)
            formatted_sequence.append(formatted_dayun)
        except Exception as e:
            # 如果格式化失败，使用原始数据（保持向后兼容）
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"格式化大运项失败: {e}, 使用原始数据")
            formatted_sequence.append(dayun)
    
    return formatted_sequence


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
