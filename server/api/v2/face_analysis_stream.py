#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
面相分析V2流式接口
基于用户上传的面相照片，使用百炼大模型流式生成整合分析
"""

import logging
import os
import sys
import time
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from services.face_analysis_v2.service import FaceAnalysisService
from server.services.llm_service_factory import LLMServiceFactory
from server.services.user_interaction_logger import get_user_interaction_logger
from server.config.config_loader import get_config_from_db_only
from server.utils.prompt_builders import format_face_analysis_input_data_for_coze

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由（注意：不设置prefix，因为会被包含到主路由中）
router = APIRouter(tags=["面相分析V2-流式"])


class FaceAnalysisStreamRequest(BaseModel):
    """面相分析流式请求模型（用于gRPC-Web）"""
    image_base64: str = Field(..., description="base64编码的图片数据")
    filename: Optional[str] = Field(None, description="文件名")
    content_type: Optional[str] = Field(None, description="内容类型")
    analysis_types: Optional[str] = Field("gongwei,liuqin,shishen", description="分析类型")
    birth_year: Optional[int] = Field(None, description="出生年份")
    birth_month: Optional[int] = Field(None, description="出生月份")
    birth_day: Optional[int] = Field(None, description="出生日期")
    birth_hour: Optional[int] = Field(None, description="出生时辰")
    gender: Optional[str] = Field(None, description="性别")
    bot_id: Optional[str] = Field(None, description="Bot ID（可选）")


@router.post("/analyze/test", summary="测试接口：返回格式化后的数据")
async def face_analysis_test(
    image: UploadFile = File(..., description="面相照片"),
    analysis_types: Optional[str] = Form("gongwei,liuqin,shishen"),
    birth_year: Optional[int] = Form(None),
    birth_month: Optional[int] = Form(None),
    birth_day: Optional[int] = Form(None),
    birth_hour: Optional[int] = Form(None),
    gender: Optional[str] = Form(None)
):
    """
    测试接口：返回格式化后的数据（用于百炼应用测试）
    
    不调用LLM，只返回格式化后的prompt文本
    """
    try:
        # 读取图片数据
        image_data = await image.read()
        
        # 准备生辰信息
        birth_info = None
        if birth_year and birth_month and birth_day:
            birth_info = {
                'year': birth_year,
                'month': birth_month,
                'day': birth_day,
                'hour': birth_hour or 12,
                'gender': gender or 'unknown'
            }
        
        # 调用分析服务
        service = FaceAnalysisService()
        result = service.analyze_face_features(
            image_data,
            image_format='jpg',
            birth_info=birth_info
        )
        
        if not result['success']:
            return {
                "success": False,
                "error": result.get('message', '分析失败')
            }
        
        # 构建响应数据（与流式接口一致）
        gongwei_result = result.get('gongwei', {})
        response_data = {
            'success': True,
            'data': {
                'face_detected': True,
                'landmarks': result.get('landmarks', {}),
                'santing_analysis': result.get('santing', {}),
                'wuyan_analysis': result.get('wuyan', {}),
                'gongwei_analysis': gongwei_result.get('gongwei_list', []),
                'liuqin_analysis': gongwei_result.get('liuqin_list', []),
                'shishen_analysis': gongwei_result.get('shishen_list', []),
                'overall_summary': result.get('overall_summary', ''),
                'birth_info': birth_info
            }
        }
        
        # 格式化数据为prompt
        formatted_data = format_face_analysis_input_data_for_coze(response_data)
        
        return {
            "success": True,
            "formatted_data": formatted_data,
            "formatted_data_length": len(formatted_data),
            "usage": {
                "description": "此接口返回的数据可以直接用于百炼智能体的输入",
                "test_command": f'curl -X POST "http://localhost:8001/api/v2/face/analyze/test" -F "image=@test_face.jpg"'
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"面相分析测试接口异常: {e}\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.post("/analyze/stream", summary="流式生成面相整合分析")
async def face_analysis_stream(
    image: UploadFile = File(..., description="面相照片"),
    analysis_types: Optional[str] = Form("gongwei,liuqin,shishen"),
    birth_year: Optional[int] = Form(None),
    birth_month: Optional[int] = Form(None),
    birth_day: Optional[int] = Form(None),
    birth_hour: Optional[int] = Form(None),
    gender: Optional[str] = Form(None),
    bot_id: Optional[str] = Form(None)
):
    """
    流式生成面相整合分析
    
    先返回基础面相分析数据，然后流式返回大模型整合分析
    """
    logger.info(f"[Face Analysis Stream] 收到请求: filename={image.filename}")
    
    return StreamingResponse(
        face_analysis_stream_generator(
            image=image,
            analysis_types=analysis_types,
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day,
            birth_hour=birth_hour,
            gender=gender,
            bot_id=bot_id
        ),
        media_type="text/event-stream"
    )


async def face_analysis_stream_generator(
    image: UploadFile,
    analysis_types: Optional[str] = "gongwei,liuqin,shishen",
    birth_year: Optional[int] = None,
    birth_month: Optional[int] = None,
    birth_day: Optional[int] = None,
    birth_hour: Optional[int] = None,
    gender: Optional[str] = None,
    bot_id: Optional[str] = None
):
    """
    流式生成面相分析的生成器
    
    Args:
        image: 上传的图片文件
        analysis_types: 分析类型
        birth_year: 出生年份（可选）
        birth_month: 出生月份（可选）
        birth_day: 出生日期（可选）
        birth_hour: 出生时辰（可选）
        gender: 性别（可选）
        bot_id: Bot ID（可选）
    """
    api_start_time = time.time()
    frontend_input = {
        'filename': image.filename,
        'analysis_types': analysis_types,
        'birth_year': birth_year,
        'birth_month': birth_month,
        'birth_day': birth_day,
        'birth_hour': birth_hour,
        'gender': gender
    }
    llm_first_token_time = None
    llm_output_chunks = []
    llm_start_time = None
    
    try:
        # 1. 确定使用的 bot_id（优先级：参数 > 数据库配置）
        used_bot_id = bot_id
        if not used_bot_id:
            used_bot_id = get_config_from_db_only("FACE_ANALYSIS_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            if not used_bot_id:
                error_msg = {
                    'type': 'error',
                    'content': "数据库配置缺失: FACE_ANALYSIS_BOT_ID 或 COZE_BOT_ID，请在 service_configs 表中配置。"
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                return
        
        logger.info(f"面相分析流式请求: filename={image.filename}, bot_id={used_bot_id}")
        
        # 3. 读取图片数据
        image_data = await image.read()
        
        # 4. 准备生辰信息
        birth_info = None
        if birth_year and birth_month and birth_day:
            birth_info = {
                'year': birth_year,
                'month': birth_month,
                'day': birth_day,
                'hour': birth_hour or 12,
                'gender': gender or 'unknown'
            }
        
        # 5. 调用基础分析服务
        try:
            service = FaceAnalysisService()
        except ImportError as e:
            error_msg = {
                'type': 'error',
                'content': f"服务初始化失败: 缺少依赖模块。请安装依赖: pip install -r services/face_analysis_v2/requirements.txt。错误详情: {str(e)}"
            }
            logger.error(f"FaceAnalysisService 初始化失败（依赖缺失）: {e}", exc_info=True)
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            error_msg = {
                'type': 'error',
                'content': f"服务初始化失败: {str(e)}"
            }
            logger.error(f"FaceAnalysisService 初始化失败: {e}", exc_info=True)
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        try:
            result = service.analyze_face_features(
                image_data,
                image_format='jpg',
                birth_info=birth_info
            )
        except BrokenPipeError as e:
            error_msg = {
                'type': 'error',
                'content': "面相分析失败: 连接中断。请重试。"
            }
            logger.error(f"面相分析 Broken pipe 错误: {e}", exc_info=True)
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            error_msg = {
                'type': 'error',
                'content': f"面相分析失败: {str(e)}"
            }
            logger.error(f"面相分析异常: {e}", exc_info=True)
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        if not result['success']:
            error_msg = {
                'type': 'error',
                'content': f"面相分析失败: {result.get('message', '未知错误')}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 6. 构建响应数据（与普通接口一致）
        gongwei_result = result.get('gongwei', {})
        response_data = {
            'success': True,
            'data': {
                'face_detected': True,
                'landmarks': result.get('landmarks', {}),
                'santing_analysis': result.get('santing', {}),
                'wuyan_analysis': result.get('wuyan', {}),
                'gongwei_analysis': gongwei_result.get('gongwei_list', []),
                'liuqin_analysis': gongwei_result.get('liuqin_list', []),
                'shishen_analysis': gongwei_result.get('shishen_list', []),
                'overall_summary': result.get('overall_summary', ''),
                'birth_info': birth_info
            }
        }
        
        # 7. 先返回基础数据（type: 'data'，带填充）
        PADDING = ' ' * 16384
        data_msg = {
            'type': 'data',
            'content': response_data,
            '_padding': PADDING
        }
        yield f"data: {json.dumps(data_msg, ensure_ascii=False)}\n\n"
        
        # 8. 格式化数据为 prompt
        formatted_data = format_face_analysis_input_data_for_coze(response_data)
        logger.info(f"[Face Analysis Stream] 格式化数据长度: {len(formatted_data)} 字符")
        
        # 9. 调用 LLM 服务流式生成
        llm_service = LLMServiceFactory.get_service(scene="face_analysis", bot_id=used_bot_id)
        llm_start_time = time.time()
        chunk_count = 0
        total_content_length = 0
        has_content = False
        
        async for chunk in llm_service.stream_analysis(formatted_data, bot_id=used_bot_id):
            chunk_type = chunk.get('type', 'unknown')
            
            # 记录第一个token时间
            if llm_first_token_time is None and chunk_type == 'progress':
                llm_first_token_time = time.time()
            
            if chunk_type == 'progress':
                chunk_count += 1
                content = chunk.get('content', '')
                llm_output_chunks.append(content)
                total_content_length += len(content)
                has_content = True
                if chunk_count == 1:
                    logger.info(f"✅ [Face Analysis Stream] 收到第一个响应块")
            elif chunk_type == 'complete':
                complete_content = chunk.get('content', '')
                llm_output_chunks.append(complete_content)
                logger.info(f"✅ [Face Analysis Stream] 收到完成响应，总块数: {chunk_count}, 总内容长度: {total_content_length}")
                has_content = True
            elif chunk_type == 'error':
                logger.error(f"❌ [Face Analysis Stream] 收到错误响应: {chunk.get('content', '')}")
            
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            if chunk_type in ['complete', 'error']:
                break
        
        # 10. 记录交互数据（异步，不阻塞）
        api_end_time = time.time()
        api_response_time_ms = int((api_end_time - api_start_time) * 1000)
        llm_total_time_ms = int((api_end_time - llm_start_time) * 1000) if llm_start_time else None
        llm_output = ''.join(llm_output_chunks)
        
        logger_instance = get_user_interaction_logger()
        logger_instance.log_function_usage_async(
            function_type='face_analysis',
            function_name='AI智能面相分析V2',
            frontend_api='/api/v2/face/analyze/stream',
            frontend_input=frontend_input,
            input_data=response_data,
            llm_output=llm_output,
            llm_api='bailian_api',
            api_response_time_ms=api_response_time_ms,
            llm_first_token_time_ms=int((llm_first_token_time - llm_start_time) * 1000) if llm_first_token_time and llm_start_time else None,
            llm_total_time_ms=llm_total_time_ms,
            round_number=1,
            bot_id=used_bot_id,
            status='success' if has_content else 'failed',
            streaming=True
        )
        
    except ValueError as e:
        # 配置错误
        logger.error(f"面相分析配置错误: {e}")
        error_msg = {
            'type': 'error',
            'content': f"配置缺失: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        
        # 记录错误
        api_end_time = time.time()
        api_response_time_ms = int((api_end_time - api_start_time) * 1000)
        logger_instance = get_user_interaction_logger()
        logger_instance.log_function_usage_async(
            function_type='face_analysis',
            function_name='AI智能面相分析V2',
            frontend_api='/api/v2/face/analyze/stream',
            frontend_input=frontend_input,
            input_data={},
            llm_output='',
            llm_api='bailian_api',
            api_response_time_ms=api_response_time_ms,
            llm_first_token_time_ms=None,
            llm_total_time_ms=None,
            round_number=1,
            status='failed',
            error_message=str(e),
            streaming=True
        )
    except Exception as e:
        # 其他错误
        import traceback
        logger.error(f"面相分析流式处理失败: {e}\n{traceback.format_exc()}")
        error_msg = {
            'type': 'error',
            'content': f"分析处理失败: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        
        # 记录错误
        api_end_time = time.time()
        api_response_time_ms = int((api_end_time - api_start_time) * 1000)
        logger_instance = get_user_interaction_logger()
        logger_instance.log_function_usage_async(
            function_type='face_analysis',
            function_name='AI智能面相分析V2',
            frontend_api='/api/v2/face/analyze/stream',
            frontend_input=frontend_input,
            input_data={},
            llm_output='',
            llm_api='bailian_api',
            api_response_time_ms=api_response_time_ms,
            llm_first_token_time_ms=None,
            llm_total_time_ms=None,
            round_number=1,
            status='failed',
            error_message=str(e),
            streaming=True
        )
