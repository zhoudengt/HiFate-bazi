#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-身体健康分析API (V2)
基于用户生辰数据，使用 Coze Bot 流式生成健康分析
按照总评分析的统一接口、一级接口、二级接口架构开发
"""

import logging
import os
import sys
from typing import Dict, Any, Optional, List, Tuple
from fastapi import APIRouter
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
import json
import asyncio
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from server.services.wangshuai_service import WangShuaiService
from server.services.bazi_detail_service import BaziDetailService
from server.services.health_analysis_service import HealthAnalysisService
from server.services.special_liunian_service import SpecialLiunianService
from server.utils.data_validator import validate_bazi_data
from server.utils.bazi_input_processor import BaziInputProcessor
from server.services.coze_stream_service import CozeStreamService
from server.services.bazi_data_orchestrator import BaziDataOrchestrator
from server.api.v1.general_review_analysis import (
    classify_special_liunians,
    organize_special_liunians_by_dayun,
    extract_xi_ji_data
)

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


class HealthAnalysisV2Request(BaseModel):
    """身体健康分析请求模型（V2）"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，默认使用环境变量配置）")


@router.post("/health-analysis-v2/stream", summary="流式生成健康分析（V2）")
async def health_analysis_v2_stream(request: HealthAnalysisV2Request):
    """
    流式生成健康分析（V2版本）
    
    按照总评分析的架构：
    - 统一接口：BaziDataOrchestrator.fetch_data()
    - 一级接口：health_analysis_v2_stream_generator()
    - 二级接口：build_health_analysis_input_data()
    
    Args:
        request: 健康分析请求参数
        
    Returns:
        StreamingResponse: SSE 流式响应
    """
    return StreamingResponse(
        health_analysis_v2_stream_generator(
            request.solar_date,
            request.solar_time,
            request.gender,
            request.bot_id
        ),
        media_type="text/event-stream"
    )


async def health_analysis_v2_stream_generator(
    solar_date: str,
    solar_time: str,
    gender: str,
    bot_id: Optional[str] = None
):
    """流式生成健康分析的生成器（一级接口）"""
    try:
        # 1. 确定使用的 bot_id（优先级：参数 > HEALTH_ANALYSIS_BOT_ID > COZE_BOT_ID）
        used_bot_id = bot_id
        if not used_bot_id:
            used_bot_id = os.getenv("HEALTH_ANALYSIS_BOT_ID")
            if not used_bot_id:
                used_bot_id = os.getenv("COZE_BOT_ID")
                if not used_bot_id:
                    error_msg = {
                        'type': 'error',
                        'content': "Coze Bot ID 配置缺失: 请设置环境变量 HEALTH_ANALYSIS_BOT_ID 或 COZE_BOT_ID。"
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
        
        logger.info(f"健康分析请求: solar_date={solar_date}, solar_time={solar_time}, gender={gender}, bot_id={used_bot_id}")
        
        # 2. 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, "solar", None, None, None
        )
        
        # 3. 使用统一接口获取数据（阶段2：数据获取与并行优化）
        try:
            # 构建统一接口的 modules 配置
            modules = {
                'bazi': True,
                'wangshuai': True,
                'xishen_jishen': True,
                'detail': True,
                'dayun': {
                    'mode': 'indices',
                    'indices': [1, 2, 3]  # 第2-4步大运
                },
                'special_liunians': {
                    'dayun_config': {
                        'mode': 'indices',
                        'indices': [1, 2, 3]  # 与dayun一致
                    },
                    'count': 100
                },
                'health': True
            }
            
            logger.info(f"[Health Analysis V2 Stream] 开始调用统一接口获取数据")
            unified_data = await BaziDataOrchestrator.fetch_data(
                solar_date=final_solar_date,
                solar_time=final_solar_time,
                gender=gender,
                modules=modules,
                use_cache=True,
                parallel=True
            )
            logger.info(f"[Health Analysis V2 Stream] ✅ 统一接口数据获取完成")
            
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            logger.error(f"[Health Analysis V2 Stream] ❌ 统一接口调用失败: {e}\n{error_msg}")
            error_response = {
                'type': 'error',
                'content': f"数据获取失败: {str(e)}。请稍后重试。"
            }
            yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            return
        
        # 4. 从统一接口返回的数据中提取所需字段
        bazi_module_data = unified_data.get('bazi', {})
        if isinstance(bazi_module_data, dict) and 'bazi' in bazi_module_data:
            bazi_data = bazi_module_data.get('bazi', {})
        else:
            bazi_data = bazi_module_data
        
        wangshuai_result = unified_data.get('wangshuai', {})
        xishen_jishen_result = unified_data.get('xishen_jishen', {})
        detail_data = unified_data.get('detail', {})
        health_result = unified_data.get('health', {})
        
        # 处理 xishen_jishen_result（可能是 Pydantic 模型，需要转换为字典）
        if xishen_jishen_result and hasattr(xishen_jishen_result, 'model_dump'):
            xishen_jishen_result = xishen_jishen_result.model_dump()
        elif xishen_jishen_result and hasattr(xishen_jishen_result, 'dict'):
            xishen_jishen_result = xishen_jishen_result.dict()
        
        # 验证八字数据
        bazi_data = validate_bazi_data(bazi_data)
        
        # 提取大运序列和流年序列
        if detail_data:
            details = detail_data.get('details', detail_data)
            dayun_sequence = details.get('dayun_sequence', [])
            liunian_sequence = details.get('liunian_sequence', [])
        else:
            dayun_sequence = unified_data.get('dayun', [])
            liunian_sequence = unified_data.get('liunian', [])
        
        logger.info(f"[Health Analysis V2 Stream] 获取到 dayun_sequence 数量: {len(dayun_sequence)}")
        
        # 提取特殊流年（统一接口返回的是字典格式，包含 'list', 'by_dayun', 'formatted'）
        special_liunians_data = unified_data.get('special_liunians', {})
        if isinstance(special_liunians_data, dict):
            special_liunians = special_liunians_data.get('list', [])
        elif isinstance(special_liunians_data, list):
            special_liunians = special_liunians_data
        else:
            special_liunians = []
        
        logger.info(f"[Health Analysis V2 Stream] 获取到特殊流年数量: {len(special_liunians)}")
        
        # 构建 detail_result（用于 build_health_analysis_input_data）
        detail_result = detail_data if detail_data else {
            'details': {
                'dayun_sequence': dayun_sequence,
                'liunian_sequence': liunian_sequence
            }
        }
        
        # 5. 调用二级接口构建输入数据（阶段3：数据验证与完整性检查）
        input_data = build_health_analysis_input_data(
            bazi_data=bazi_data,
            wangshuai_result=wangshuai_result,
            detail_result=detail_result,
            dayun_sequence=dayun_sequence,
            gender=gender,
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            health_result=health_result,
            special_liunians=special_liunians,
            xishen_jishen_result=xishen_jishen_result
        )
        
        # 6. 验证数据完整性（阶段3：数据验证与完整性检查）
        is_valid, validation_error = validate_health_analysis_input_data(input_data)
        if not is_valid:
            error_msg = {
                'type': 'error',
                'content': f"数据完整性验证失败: {validation_error}。请检查生辰数据是否正确。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 7. 构建自然语言 Prompt（阶段4：Prompt构建）
        prompt = build_health_analysis_prompt(input_data)
        
        # 记录 Prompt 前500字符到日志（便于调试）
        prompt_preview = prompt[:500] if len(prompt) > 500 else prompt
        logger.info(f"[Health Analysis V2 Stream] Prompt 预览（前500字符）: {prompt_preview}...")
        
        # 8. 调用 Coze API（阶段5：Coze API调用）
        try:
            coze_service = CozeStreamService(bot_id=used_bot_id)
            async for chunk in coze_service.stream_custom_analysis(prompt, bot_id=used_bot_id):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                if chunk.get('type') in ['complete', 'error']:
                    break
                    
        except ValueError as e:
            # 配置错误
            error_msg = {
                'type': 'error',
                'content': f"Coze API 配置缺失: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            # 其他错误
            import traceback
            error_msg = {
                'type': 'error',
                'content': f"Coze API 调用失败: {str(e)}"
            }
            logger.error(f"[Health Analysis V2 Stream] Coze API 调用失败: {e}\n{traceback.format_exc()}")
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"健康分析流式生成失败: {e}\n{error_trace}")
        error_msg = {
            'type': 'error',
            'content': f"处理失败: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


def build_health_analysis_input_data(
    bazi_data: Dict[str, Any],
    wangshuai_result: Dict[str, Any],
    detail_result: Dict[str, Any],
    dayun_sequence: List[Dict[str, Any]],
    gender: str,
    solar_date: str = None,
    solar_time: str = None,
    health_result: Dict[str, Any] = None,
    special_liunians: List[Dict[str, Any]] = None,
    xishen_jishen_result: Any = None
) -> Dict[str, Any]:
    """
    构建健康分析的输入数据（二级接口）
    
    Args:
        bazi_data: 八字基础数据
        wangshuai_result: 旺衰分析结果
        detail_result: 详细计算结果
        dayun_sequence: 大运序列
        gender: 性别（male/female）
        solar_date: 原始阳历日期
        solar_time: 原始阳历时间
        health_result: 健康分析结果
        special_liunians: 特殊流年列表（已筛选）
        xishen_jishen_result: 喜忌数据结果（XishenJishenResponse）
        
    Returns:
        dict: 健康分析的input_data
    """
    # 提取基础数据
    bazi_pillars = bazi_data.get('bazi_pillars', {})
    day_pillar = bazi_pillars.get('day', {})
    element_counts = bazi_data.get('element_counts', {})
    ten_gods_data = bazi_data.get('ten_gods_stats', {})
    ten_gods_full = bazi_data.get('ten_gods', {})
    
    # 提取月令
    month_pillar = bazi_pillars.get('month', {})
    month_branch = month_pillar.get('branch', '')
    yue_ling = f"{month_branch}月" if month_branch else ''
    
    # 提取旺衰数据
    wangshuai_data = wangshuai_result.get('wangshuai', '')
    
    # 提取健康相关数据
    wuxing_balance = health_result.get('wuxing_balance', '') if health_result else ''
    body_algorithm = health_result.get('body_algorithm', {}) if health_result else {}
    pathology_tendency = health_result.get('pathology_tendency', {}) if health_result else {}
    wuxing_tuning = health_result.get('wuxing_tuning', {}) if health_result else {}
    zangfu_care = health_result.get('zangfu_care', {}) if health_result else {}
    
    # 提取五行生克关系
    wuxing_relations = pathology_tendency.get('wuxing_relations', {}) if pathology_tendency else {}
    
    # 提取喜忌数据
    xi_ji_data = extract_xi_ji_data(xishen_jishen_result, wangshuai_result)
    
    # 提取当前大运
    current_dayun = None
    if dayun_sequence:
        from datetime import datetime
        birth_date = bazi_data.get('basic_info', {}).get('solar_date', '')
        if birth_date:
            try:
                birth = datetime.strptime(birth_date, '%Y-%m-%d')
                today = datetime.now()
                age = today.year - birth.year - (1 if (today.month, today.day) < (birth.month, birth.day) else 0)
                
                for dayun in dayun_sequence:
                    age_range = dayun.get('age_display', '')
                    if age_range:
                        try:
                            parts = age_range.replace('岁', '').split('-')
                            if len(parts) == 2:
                                start_age = int(parts[0])
                                end_age = int(parts[1])
                                if start_age <= age <= end_age:
                                    current_dayun = dayun
                                    break
                        except:
                            pass
                
                if not current_dayun and dayun_sequence:
                    current_dayun = dayun_sequence[1] if len(dayun_sequence) > 1 else dayun_sequence[0]
            except:
                pass
    
    # 获取关键大运（第2-4步，索引1、2、3）
    dayun_list = []
    for idx in [1, 2, 3]:
        if idx < len(dayun_sequence):
            dayun = dayun_sequence[idx]
            dayun_list.append({
                'step': dayun.get('step', idx),
                'stem': dayun.get('stem', ''),
                'branch': dayun.get('branch', ''),
                'main_star': dayun.get('main_star', ''),
                'year_start': dayun.get('year_start', 0),
                'year_end': dayun.get('year_end', 0),
                'age_display': dayun.get('age_display', '')
            })
    
    # ⚠️ 关键：按大运分组特殊流年，每个大运最多2条（按优先级）
    if special_liunians is None:
        special_liunians = []
    
    # 按大运分组特殊流年
    dayun_liunians = organize_special_liunians_by_dayun(special_liunians, dayun_sequence)
    
    # 每个大运筛选最多2条流年（按优先级：天克地冲 > 天合地合 > 岁运并临 > 其他）
    for dayun_step, dayun_data in dayun_liunians.items():
        key_liunians = []
        
        # 按优先级顺序取流年，最多2条
        # 优先级1：天克地冲
        if dayun_data.get('tiankedi_chong'):
            remaining = 2 - len(key_liunians)
            if remaining > 0:
                key_liunians.extend(dayun_data['tiankedi_chong'][:remaining])
        
        # 优先级2：天合地合
        if len(key_liunians) < 2 and dayun_data.get('tianhedi_he'):
            remaining = 2 - len(key_liunians)
            if remaining > 0:
                key_liunians.extend(dayun_data['tianhedi_he'][:remaining])
        
        # 优先级3：岁运并临
        if len(key_liunians) < 2 and dayun_data.get('suiyun_binglin'):
            remaining = 2 - len(key_liunians)
            if remaining > 0:
                key_liunians.extend(dayun_data['suiyun_binglin'][:remaining])
        
        # 优先级4：其他
        if len(key_liunians) < 2 and dayun_data.get('other'):
            remaining = 2 - len(key_liunians)
            if remaining > 0:
                key_liunians.extend(dayun_data['other'][:remaining])
        
        # 确保最多2条
        dayun_data['key_liunian'] = key_liunians[:2]
    
    # 构建完整的input_data
    input_data = {
        # 1. 命盘体质总论
        'mingpan_tizhi_zonglun': {
            'day_master': day_pillar,
            'bazi_pillars': bazi_pillars,
            'elements': element_counts,
            'wangshuai': wangshuai_data,
            'yue_ling': yue_ling,
            'wuxing_balance': wuxing_balance
        },
        
        # 2. 五行病理推演
        'wuxing_bingli': {
            'wuxing_shengke': wuxing_relations,
            'body_algorithm': body_algorithm,
            'pathology_tendency': pathology_tendency
        },
        
        # 3. 大运流年健康警示
        'dayun_jiankang': {
            'current_dayun': current_dayun,
            'dayun_list': dayun_list,  # 第2-4步大运
            'dayun_liunians': dayun_liunians,  # 按大运分组，每个大运最多2条流年
            'ten_gods': ten_gods_data
        },
        
        # 4. 体质调理建议
        'tizhi_tiaoli': {
            'xi_ji': xi_ji_data,
            'wuxing_tiaohe': wuxing_tuning,
            'zangfu_yanghu': zangfu_care
        }
    }
    
    return input_data


def validate_health_analysis_input_data(data: dict) -> tuple[bool, str]:
    """
    验证健康分析输入数据的完整性
    
    Args:
        data: 输入数据字典
        
    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = {
        'mingpan_tizhi_zonglun': {
            'day_master': '日主信息',
            'bazi_pillars': '四柱排盘',
            'elements': '五行分布',
            'wangshuai': '旺衰分析',
            'wuxing_balance': '五行平衡情况'
        },
        'wuxing_bingli': {
            'body_algorithm': '五行五脏对应',
            'pathology_tendency': '病理倾向'
        },
        'dayun_jiankang': {
            'current_dayun': '当前大运',
            'dayun_list': '大运流年列表',
            'dayun_liunians': '按大运分组的流年'
        },
        'tizhi_tiaoli': {
            'xi_ji': '喜忌数据',
            'wuxing_tiaohe': '五行调和方案',
            'zangfu_yanghu': '脏腑养护建议'
        }
    }
    
    missing_fields = []
    
    for section, fields in required_fields.items():
        if section not in data:
            missing_fields.append(f"{section}（整个部分缺失）")
            continue
            
        section_data = data[section]
        if not isinstance(section_data, dict):
            missing_fields.append(f"{section}（格式错误，应为字典）")
            continue
            
        for field, field_name in fields.items():
            if field not in section_data:
                missing_fields.append(f"{section}.{field}（{field_name}）")
            elif section_data[field] is None:
                missing_fields.append(f"{section}.{field}（{field_name}为None）")
            elif isinstance(section_data[field], (list, dict)) and len(section_data[field]) == 0:
                # 空列表/字典可能是正常的（如无匹配规则），不报错
                pass
    
    if missing_fields:
        error_msg = f"数据不完整，缺失字段：{', '.join(missing_fields)}"
        return False, error_msg
    
    return True, ""


def build_health_analysis_prompt(data: dict) -> str:
    """
    构建自然语言格式的提示词（阶段4：Prompt构建）
    将JSON数据转换为自然语言格式，确保 Coze Bot 能正确理解
    """
    prompt_lines = []
    # ⚠️ 注意：代码中只提供数据，不包含任何提示词或指令
    # 提示词必须在 Coze Bot 中配置
    
    # 1. 命盘体质总论
    prompt_lines.append("【命盘体质总论】")
    mingpan = data.get('mingpan_tizhi_zonglun', {})
    
    day_master = mingpan.get('day_master', {})
    if day_master:
        stem = day_master.get('stem', '')
        branch = day_master.get('branch', '')
        element = day_master.get('element', '')
        if stem and branch:
            prompt_lines.append(f"日主：{stem}{branch}（{element}）")
    
    bazi_pillars = mingpan.get('bazi_pillars', {})
    if bazi_pillars:
        prompt_lines.append("四柱排盘：")
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar = bazi_pillars.get(pillar_type, {})
            stem = pillar.get('stem', '')
            branch = pillar.get('branch', '')
            if stem and branch:
                pillar_name = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}.get(pillar_type, pillar_type)
                prompt_lines.append(f"  {pillar_name}：{stem}{branch}")
    
    elements = mingpan.get('elements', {})
    if elements:
        prompt_lines.append("五行分布：")
        for element, count in elements.items():
            if count > 0:
                prompt_lines.append(f"  {element}：{count}个")
    
    wangshuai = mingpan.get('wangshuai', '')
    if wangshuai:
        prompt_lines.append(f"旺衰：{wangshuai}")
    
    yue_ling = mingpan.get('yue_ling', '')
    if yue_ling:
        prompt_lines.append(f"月令：{yue_ling}")
    
    wuxing_balance = mingpan.get('wuxing_balance', '')
    if wuxing_balance:
        prompt_lines.append(f"全局五行平衡：{wuxing_balance}")
    
    prompt_lines.append("")
    
    # 2. 五行病理推演
    prompt_lines.append("【五行病理推演】")
    wuxing_bingli = data.get('wuxing_bingli', {})
    
    wuxing_shengke = wuxing_bingli.get('wuxing_shengke', {})
    if wuxing_shengke:
        relations = wuxing_shengke.get('relations', [])
        if relations:
            prompt_lines.append("五行生克关系：")
            for relation in relations:
                organ = relation.get('organ', '')
                issue = relation.get('issue', '')
                risk = relation.get('risk', '')
                if organ and issue:
                    prompt_lines.append(f"  {organ}：{issue}，{risk}")
    
    body_algorithm = wuxing_bingli.get('body_algorithm', {})
    if body_algorithm:
        organ_analysis = body_algorithm.get('organ_analysis', {})
        if organ_analysis:
            prompt_lines.append("五脏对应：")
            for organ, analysis in organ_analysis.items():
                element = analysis.get('element', '')
                strength = analysis.get('strength', '')
                health_status = analysis.get('health_status', '')
                if element and strength:
                    prompt_lines.append(f"  {organ}（{element}）：{strength}，{health_status}")
    
    pathology_tendency = wuxing_bingli.get('pathology_tendency', {})
    if pathology_tendency:
        pathology_list = pathology_tendency.get('pathology_list', [])
        if pathology_list:
            prompt_lines.append("病理倾向：")
            for pathology in pathology_list:
                organ = pathology.get('organ', '')
                tendency = pathology.get('tendency', '')
                risk = pathology.get('risk', '')
                if organ and tendency:
                    prompt_lines.append(f"  {organ}：{tendency}，{risk}")
    
    prompt_lines.append("")
    
    # 3. 大运流年健康警示
    prompt_lines.append("【大运流年健康警示】")
    dayun_jiankang = data.get('dayun_jiankang', {})
    
    # 当前大运
    current_dayun = dayun_jiankang.get('current_dayun', {})
    if current_dayun:
        stem = current_dayun.get('stem', '')
        branch = current_dayun.get('branch', '')
        age_display = current_dayun.get('age_display', '')
        if stem and branch:
            prompt_lines.append(f"当前大运：{stem}{branch}（{age_display}）")
    
    # 关键大运列表（第2-4步）
    dayun_list = dayun_jiankang.get('dayun_list', [])
    if dayun_list:
        prompt_lines.append("关键大运（第2-4步）：")
        for dayun in dayun_list:
            step = dayun.get('step', '')
            stem = dayun.get('stem', '')
            branch = dayun.get('branch', '')
            age_display = dayun.get('age_display', '')
            if stem and branch:
                prompt_lines.append(f"  第{step}步大运：{stem}{branch}（{age_display}）")
    
    # 每个大运下的关键流年（最多2条，按优先级）
    dayun_liunians = dayun_jiankang.get('dayun_liunians', {})
    if dayun_liunians:
        prompt_lines.append("关键流年健康风险：")
        
        # 获取完整的大运序列（用于格式化）
        dayun_sequence_for_format = dayun_list if dayun_list else []
        
        # 按大运步骤排序
        sorted_dayun_steps = sorted([int(k) for k in dayun_liunians.keys() if isinstance(k, (int, str)) and str(k).isdigit()])
        
        for dayun_step in sorted_dayun_steps:
            dayun_data = dayun_liunians.get(dayun_step, {})
            if not dayun_data:
                continue
            
            dayun_info = dayun_data.get('dayun_info', {})
            key_liunians = dayun_data.get('key_liunian', [])
            
            if key_liunians:
                step = dayun_info.get('step', dayun_step)
                stem = dayun_info.get('stem', '')
                branch = dayun_info.get('branch', '')
                age_display = dayun_info.get('age_display', '')
                
                prompt_lines.append(f"第{step}步大运{stem}{branch}（{age_display}）关键流年：")
                
                # 使用 SpecialLiunianService.format_special_liunians_for_prompt 格式化
                formatted = SpecialLiunianService.format_special_liunians_for_prompt(
                    key_liunians, dayun_sequence_for_format
                )
                if formatted:
                    prompt_lines.append(formatted)
                else:
                    # 如果格式化失败，至少列出年份和干支
                    for liunian in key_liunians:
                        year = liunian.get('year', '')
                        ganzhi = liunian.get('ganzhi', '')
                        relations = liunian.get('relations', [])
                        if year and ganzhi:
                            relation_str = ''
                            if relations:
                                if isinstance(relations[0], dict):
                                    relation_str = '、'.join([r.get('type', '') for r in relations])
                                else:
                                    relation_str = '、'.join([str(r) for r in relations])
                            if relation_str:
                                prompt_lines.append(f"  - {year}年{ganzhi}（{relation_str}）")
                            else:
                                prompt_lines.append(f"  - {year}年{ganzhi}")
    
    # 十神配置
    ten_gods = dayun_jiankang.get('ten_gods', {})
    if ten_gods:
        prompt_lines.append("十神配置：")
        for shishen, count in ten_gods.items():
            if count > 0:
                prompt_lines.append(f"  {shishen}：{count}个")
    
    prompt_lines.append("")
    
    # 4. 体质调理建议
    prompt_lines.append("【体质调理建议】")
    tizhi_tiaoli = data.get('tizhi_tiaoli', {})
    
    xi_ji = tizhi_tiaoli.get('xi_ji', {})
    if xi_ji:
        xishen_wuxing = xi_ji.get('xishen_wuxing', [])
        jishen_wuxing = xi_ji.get('jishen_wuxing', [])
        
        if xishen_wuxing:
            prompt_lines.append(f"喜神五行：{'、'.join(xishen_wuxing)}")
        else:
            prompt_lines.append("喜神五行：无")
        
        if jishen_wuxing:
            prompt_lines.append(f"忌神五行：{'、'.join(jishen_wuxing)}")
        else:
            prompt_lines.append("忌神五行：无")
    
    wuxing_tiaohe = tizhi_tiaoli.get('wuxing_tiaohe', {})
    if wuxing_tiaohe:
        tuning_suggestions = wuxing_tiaohe.get('tuning_suggestions', [])
        if tuning_suggestions:
            prompt_lines.append("五行调和方案：")
            for tuning in tuning_suggestions:
                element = tuning.get('element', '')
                organ = tuning.get('organ', '')
                direction = tuning.get('direction', '')
                reason = tuning.get('reason', '')
                if element and organ:
                    prompt_lines.append(f"  {element}（{organ}）：{direction}，{reason}")
    
    zangfu_yanghu = tizhi_tiaoli.get('zangfu_yanghu', {})
    if zangfu_yanghu:
        care_suggestions = zangfu_yanghu.get('care_suggestions', [])
        if care_suggestions:
            prompt_lines.append("脏腑养护建议：")
            for care in care_suggestions:
                organ = care.get('organ', '')
                priority = care.get('priority', '')
                care_focus = care.get('care_focus', '')
                suggestions = care.get('suggestions', [])
                if organ:
                    prompt_lines.append(f"  {organ}（优先级：{priority}，重点：{care_focus}）：")
                    for suggestion in suggestions[:3]:  # 最多显示3条建议
                        prompt_lines.append(f"    - {suggestion}")
    
    return '\n'.join(prompt_lines)

