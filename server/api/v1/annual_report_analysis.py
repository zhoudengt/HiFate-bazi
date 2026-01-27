#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-年运报告API
基于用户生辰数据，使用 Coze Bot 流式生成年运报告
按照层次化开发规范：一级接口（路由层）
"""

import logging
import os
import sys
from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
import json
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from server.services.wangshuai_service import WangShuaiService
from server.services.bazi_detail_service import BaziDetailService
from server.utils.data_validator import validate_bazi_data
from server.utils.bazi_input_processor import BaziInputProcessor
from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
from server.services.annual_report_service import AnnualReportService

# 导入配置加载器（从数据库读取配置）
try:
    from server.config.config_loader import get_config_from_db_only
except ImportError:
    def get_config_from_db_only(key: str) -> Optional[str]:
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter()


class AnnualReportRequest(BaseModel):
    """年运报告请求模型"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，默认使用数据库配置）")


@router.post("/annual-report/test", summary="测试接口：返回格式化后的数据（用于 Coze Bot）")
async def annual_report_test(request: AnnualReportRequest):
    """
    测试接口：返回格式化后的数据（用于 Coze Bot 的 {{input}} 占位符）
    
    方案2：使用占位符模板，数据不重复，节省 Token
    提示词模板已配置在 Coze Bot 的 System Prompt 中，代码只发送数据
    
    Args:
        request: 年运报告请求参数
        
    Returns:
        dict: 包含格式化后的数据
    """
    try:
        # 1. 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            request.solar_date, request.solar_time, "solar", None, None, None
        )
        
        # 2. 从数据库读取年份配置
        target_year_str = get_config_from_db_only("ANNUAL_REPORT_YEAR")
        if target_year_str:
            try:
                target_year = int(target_year_str)
            except ValueError:
                logger.warning(f"年份配置无效: {target_year_str}，使用默认值2026")
                target_year = 2026
        else:
            logger.warning("年份配置不存在，使用默认值2026")
            target_year = 2026
        
        logger.info(f"年运报告目标年份: {target_year}")
        
        # 3. 使用统一接口获取数据（增加 special_liunians 获取）
        modules = {
            'bazi': True,
            'wangshuai': True,
            'detail': True,
            'dayun': {
                'mode': 'count',
                'count': 13  # 获取所有大运
            },
            'special_liunians': {
                'dayun_config': {
                    'mode': 'count',
                    'count': 13  # 获取所有大运
                },
                'count': 200  # 获取足够多的特殊流年
            }
        }
        
        unified_data = await BaziDataOrchestrator.fetch_data(
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            gender=request.gender,
            modules=modules,
            use_cache=True,
            parallel=True,
            calendar_type="solar",
            location=None,
            latitude=None,
            longitude=None,
            preprocessed=True
        )
        
        # 4. 从统一接口结果中提取数据
        bazi_data = unified_data.get('bazi', {})
        wangshuai_result = unified_data.get('wangshuai', {})
        detail_result = unified_data.get('detail', {})
        
        # 提取和验证数据
        if isinstance(bazi_data, dict) and 'bazi' in bazi_data:
            bazi_data = bazi_data['bazi']
        bazi_data = validate_bazi_data(bazi_data)
        
        # 获取大运序列（从detail_result）
        dayun_sequence = detail_result.get('dayun_sequence', [])
        
        # 提取特殊流年（岁运并临、天克地冲、天合地合）
        special_liunians_data = unified_data.get('special_liunians', {})
        if isinstance(special_liunians_data, dict):
            special_liunians = special_liunians_data.get('list', [])
        elif isinstance(special_liunians_data, list):
            special_liunians = special_liunians_data
        else:
            special_liunians = []
        logger.info(f"年运报告获取到特殊流年数量: {len(special_liunians)}")
        
        # 5. 调用二级接口构建input_data（增加 special_liunians 参数）
        input_data = AnnualReportService.build_annual_report_input_data(
            bazi_data=bazi_data,
            wangshuai_result=wangshuai_result,
            detail_result=detail_result,
            dayun_sequence=dayun_sequence,
            special_liunians=special_liunians,  # ⚠️ 新增：特殊流年（岁运并临、天克地冲、天合地合）
            gender=request.gender,
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            target_year=target_year
        )
        
        # 6. 验证数据完整性
        is_valid, validation_error = AnnualReportService.validate_annual_report_input_data(input_data)
        if not is_valid:
            return {
                "success": False,
                "error": f"数据完整性验证失败: {validation_error}",
                "input_data": input_data
            }
        
        # 7. 格式化数据
        formatted_data = AnnualReportService.format_input_data_for_coze(input_data)
        
        return {
            "success": True,
            "target_year": target_year,
            "formatted_data": formatted_data,
            "formatted_data_length": len(formatted_data),
            "data_summary": {
                "mingpan_analysis": {
                    "bazi_pillars": input_data.get('mingpan_analysis', {}).get('bazi_pillars', {}),
                    "element_counts": input_data.get('mingpan_analysis', {}).get('element_counts', {}),
                    "wangshuai": input_data.get('mingpan_analysis', {}).get('wangshuai', '')
                },
                "monthly_analysis": {
                    "year": input_data.get('monthly_analysis', {}).get('year', ''),
                    "months_count": len(input_data.get('monthly_analysis', {}).get('months', []))
                },
                "taisui_info": {
                    "year": input_data.get('taisui_info', {}).get('year', ''),
                    "taisui_name": input_data.get('taisui_info', {}).get('taisui_name', '')
                },
                "fengshui_info": {
                    "year": input_data.get('fengshui_info', {}).get('year', ''),
                    "wuhuang": input_data.get('fengshui_info', {}).get('wuhuang', {})
                }
            },
            "usage": {
                "description": "此接口返回的数据可以直接用于 Coze Bot 的 {{input}} 占位符",
                "coze_bot_setup": "1. 登录 Coze 平台\n2. 找到'年运报告分析' Bot\n3. 进入 Bot 设置 → System Prompt\n4. 复制 docs/需求/Coze_Bot_System_Prompt_年运报告.md 中的提示词\n5. 粘贴到 System Prompt 中\n6. 保存设置",
                "test_command": f'curl -X POST "http://localhost:8001/api/v1/annual-report/test" -H "Content-Type: application/json" -d \'{{"solar_date": "{request.solar_date}", "solar_time": "{request.solar_time}", "gender": "{request.gender}"}}\''
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"测试接口异常: {e}\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.post("/annual-report/stream", summary="流式生成年运报告")
async def annual_report_stream(request: AnnualReportRequest):
    """
    流式生成年运报告
    
    按照层次化开发规范：
    - 一级接口（路由层）：annual_report_stream() - 本函数
    - 二级接口（业务逻辑层）：AnnualReportService - 业务逻辑处理
    - 三级服务（数据服务层）：太岁服务、风水服务、流月服务
    
    Args:
        request: 年运报告请求参数
        
    Returns:
        StreamingResponse: SSE 流式响应
    """
    return StreamingResponse(
        annual_report_stream_generator(
            request.solar_date,
            request.solar_time,
            request.gender,
            request.bot_id
        ),
        media_type="text/event-stream"
    )


async def annual_report_stream_generator(
    solar_date: str,
    solar_time: str,
    gender: str,
    bot_id: Optional[str] = None
):
    """流式生成年运报告的生成器（一级接口）"""
    try:
        # 1. 确定使用的 bot_id（优先级：参数 > 数据库配置）
        used_bot_id = bot_id
        if not used_bot_id:
            # 只从数据库读取，不降级到环境变量
            used_bot_id = get_config_from_db_only("ANNUAL_REPORT_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            if not used_bot_id:
                error_msg = {
                    'type': 'error',
                    'content': "数据库配置缺失: ANNUAL_REPORT_BOT_ID 或 COZE_BOT_ID，请在 service_configs 表中配置。"
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                return
        
        logger.info(f"年运报告请求: solar_date={solar_date}, solar_time={solar_time}, gender={gender}, bot_id={used_bot_id}")
        
        # 2. 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, "solar", None, None, None
        )
        
        # 3. 从数据库读取年份配置
        target_year_str = get_config_from_db_only("ANNUAL_REPORT_YEAR")
        if target_year_str:
            try:
                target_year = int(target_year_str)
            except ValueError:
                logger.warning(f"年份配置无效: {target_year_str}，使用默认值2026")
                target_year = 2026
        else:
            logger.warning("年份配置不存在，使用默认值2026")
            target_year = 2026
        
        logger.info(f"年运报告目标年份: {target_year}")
        
        # 4. 使用统一接口获取数据（增加 special_liunians 获取）
        try:
            modules = {
                'bazi': True,
                'wangshuai': True,
                'detail': True,
                'dayun': {
                    'mode': 'count',
                    'count': 13  # 获取所有大运
                },
                'special_liunians': {
                    'dayun_config': {
                        'mode': 'count',
                        'count': 13  # 获取所有大运
                    },
                    'count': 200  # 获取足够多的特殊流年
                }
            }
            
            logger.info(f"[Annual Report Stream] 开始调用统一接口获取数据")
            unified_data = await BaziDataOrchestrator.fetch_data(
                solar_date=final_solar_date,
                solar_time=final_solar_time,
                gender=gender,
                modules=modules,
                use_cache=True,
                parallel=True,
                calendar_type="solar",
                location=None,
                latitude=None,
                longitude=None,
                preprocessed=True
            )
            logger.info(f"[Annual Report Stream] ✅ 统一接口数据获取完成")
            
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            logger.error(f"[Annual Report Stream] ❌ 统一接口调用失败: {e}\n{error_msg}")
            error_response = {
                'type': 'error',
                'content': f"数据获取失败: {str(e)}。请稍后重试。"
            }
            yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            return
        
        # 5. 从统一接口返回的数据中提取所需字段
        bazi_module_data = unified_data.get('bazi', {})
        if isinstance(bazi_module_data, dict) and 'bazi' in bazi_module_data:
            bazi_data = bazi_module_data.get('bazi', {})
        else:
            bazi_data = bazi_module_data
        
        wangshuai_result = unified_data.get('wangshuai', {})
        detail_data = unified_data.get('detail', {})
        
        # 验证八字数据
        bazi_data = validate_bazi_data(bazi_data)
        
        # 提取大运序列
        if detail_data:
            details = detail_data.get('details', detail_data)
            dayun_sequence = details.get('dayun_sequence', [])
        else:
            dayun_sequence = unified_data.get('dayun', [])
        
        logger.info(f"[Annual Report Stream] 获取到 dayun_sequence 数量: {len(dayun_sequence)}")
        
        # 提取特殊流年（岁运并临、天克地冲、天合地合）
        special_liunians_data = unified_data.get('special_liunians', {})
        if isinstance(special_liunians_data, dict):
            special_liunians = special_liunians_data.get('list', [])
        elif isinstance(special_liunians_data, list):
            special_liunians = special_liunians_data
        else:
            special_liunians = []
        logger.info(f"[Annual Report Stream] 获取到特殊流年数量: {len(special_liunians)}")
        
        # 构建 detail_result（用于二级接口）
        detail_result = detail_data if detail_data else {
            'details': {
                'dayun_sequence': dayun_sequence
            }
        }
        
        # 6. 调用二级接口构建输入数据（增加 special_liunians 参数）
        input_data = AnnualReportService.build_annual_report_input_data(
            bazi_data=bazi_data,
            wangshuai_result=wangshuai_result,
            detail_result=detail_result,
            dayun_sequence=dayun_sequence,
            special_liunians=special_liunians,  # ⚠️ 新增：特殊流年（岁运并临、天克地冲、天合地合）
            gender=gender,
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            target_year=target_year
        )
        
        # 7. 验证数据完整性
        is_valid, validation_error = AnnualReportService.validate_annual_report_input_data(input_data)
        if not is_valid:
            error_msg = {
                'type': 'error',
                'content': f"数据完整性验证失败: {validation_error}。请检查生辰数据是否正确。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 8. 格式化数据为 Coze Bot 输入格式
        formatted_data = AnnualReportService.format_input_data_for_coze(input_data)
        logger.info(f"[Annual Report Stream] 格式化数据长度: {len(formatted_data)} 字符")
        logger.debug(f"[Annual Report Stream] 格式化数据前500字符: {formatted_data[:500]}")
        
        # 9. 调用 LLM API（支持 Coze 和百炼平台）
        try:
            from server.services.llm_service_factory import LLMServiceFactory
            llm_service = LLMServiceFactory.get_service(scene="general_review", bot_id=used_bot_id)
            async for chunk in llm_service.stream_analysis(formatted_data, bot_id=used_bot_id):
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
            logger.error(f"[Annual Report Stream] Coze API 调用失败: {e}\n{traceback.format_exc()}")
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"年运报告流式生成失败: {e}\n{error_trace}")
        error_msg = {
            'type': 'error',
            'content': f"处理失败: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
