#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
办公桌风水分析流式接口
基于用户上传的办公桌照片，使用百炼大模型流式生成整合分析
"""

import logging
import os
import sys
import time
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'services', 'desk_fengshui'))

from server.services.llm_service_factory import LLMServiceFactory
from server.services.user_interaction_logger import get_user_interaction_logger
from server.config.config_loader import get_config_from_db_only
from server.utils.prompt_builders import format_desk_fengshui_input_data_for_coze

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由（注意：不设置prefix，因为会被包含到主路由中）
router = APIRouter(tags=["办公桌风水-流式"])


class DeskFengshuiStreamRequest(BaseModel):
    """办公桌风水流式请求模型（用于gRPC-Web）"""
    image_base64: str = Field(..., description="base64编码的图片数据")
    filename: Optional[str] = Field(None, description="文件名")
    content_type: Optional[str] = Field(None, description="内容类型")
    bot_id: Optional[str] = Field(None, description="Bot ID（可选）")


@router.post("/analyze/test", summary="测试接口：返回格式化后的数据")
async def desk_fengshui_test(
    image: UploadFile = File(..., description="办公桌照片")
):
    """
    测试接口：返回格式化后的数据（用于百炼应用测试）
    
    不调用LLM，只返回格式化后的prompt文本
    """
    try:
        # 验证图片
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")
        
        # 读取图片数据
        image_bytes = await image.read()
        
        # 调用分析服务
        # 确保从正确的路径导入
        import sys
        desk_fengshui_path = os.path.join(project_root, 'services', 'desk_fengshui')
        # 确保desk_fengshui路径在最前面，这样相对导入才能工作
        if desk_fengshui_path in sys.path:
            sys.path.remove(desk_fengshui_path)
        sys.path.insert(0, desk_fengshui_path)
        # 切换到desk_fengshui目录以确保相对导入工作
        old_cwd = os.getcwd()
        try:
            os.chdir(desk_fengshui_path)
            from analyzer import DeskFengshuiAnalyzer
        finally:
            os.chdir(old_cwd)
        analyzer = DeskFengshuiAnalyzer()
        
        result = await asyncio.wait_for(
            analyzer.analyze_async(
                image_bytes=image_bytes,
                use_bazi=False
            ),
            timeout=90.0
        )
        
        if not result or not result.get('success'):
            return {
                "success": False,
                "error": result.get('error', '分析失败') if result else '分析服务返回空结果'
            }
        
        # 格式化数据为prompt
        formatted_data = format_desk_fengshui_input_data_for_coze(result)
        
        return {
            "success": True,
            "formatted_data": formatted_data,
            "formatted_data_length": len(formatted_data),
            "usage": {
                "description": "此接口返回的数据可以直接用于百炼智能体的输入",
                "test_command": f'curl -X POST "http://localhost:8001/api/v2/desk-fengshui/analyze/test" -F "image=@test_desk.jpg"'
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"办公桌风水测试接口异常: {e}\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.post("/analyze/stream", summary="流式生成办公桌风水整合分析")
async def desk_fengshui_stream(
    image: UploadFile = File(..., description="办公桌照片"),
    bot_id: Optional[str] = Form(None)
):
    """
    流式生成办公桌风水整合分析
    
    先返回基础风水分析数据，然后流式返回大模型整合分析
    """
    logger.info(f"[Desk Fengshui Stream] 收到请求: filename={image.filename}")
    
    return StreamingResponse(
        desk_fengshui_stream_generator(
            image=image,
            bot_id=bot_id
        ),
        media_type="text/event-stream"
    )


async def desk_fengshui_stream_generator(
    image: UploadFile,
    bot_id: Optional[str] = None
):
    """
    流式生成办公桌风水分析的生成器
    
    Args:
        image: 上传的图片文件
        bot_id: Bot ID（可选）
    """
    api_start_time = time.time()
    frontend_input = {
        'filename': image.filename
    }
    llm_first_token_time = None
    llm_output_chunks = []
    llm_start_time = None
    
    try:
        # 1. 确定使用的 bot_id（优先级：参数 > 数据库配置）
        used_bot_id = bot_id
        if not used_bot_id:
            used_bot_id = get_config_from_db_only("DESK_FENGSHUI_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            if not used_bot_id:
                error_msg = {
                    'type': 'error',
                    'content': "数据库配置缺失: DESK_FENGSHUI_BOT_ID 或 COZE_BOT_ID，请在 service_configs 表中配置。"
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                return
        
        logger.info(f"办公桌风水流式请求: filename={image.filename}, bot_id={used_bot_id}")
        
        # 2. 发送进度提示
        progress_msg = {
            'type': 'progress',
            'content': '正在分析办公桌风水...'
        }
        yield f"data: {json.dumps(progress_msg, ensure_ascii=False)}\n\n"
        
        # 3. 验证图片
        if not image.content_type.startswith('image/'):
            error_msg = {
                'type': 'error',
                'content': "请上传图片文件"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 4. 读取图片数据
        image_bytes = await image.read()
        
        # 5. 调用基础分析服务（异步，带超时）
        try:
            # 确保从正确的路径导入
            import sys
            desk_fengshui_path = os.path.join(project_root, 'services', 'desk_fengshui')
            # 确保desk_fengshui路径在最前面，这样相对导入才能工作
            if desk_fengshui_path in sys.path:
                sys.path.remove(desk_fengshui_path)
            sys.path.insert(0, desk_fengshui_path)
            # 切换到desk_fengshui目录以确保相对导入工作
            old_cwd = os.getcwd()
            try:
                os.chdir(desk_fengshui_path)
                from analyzer import DeskFengshuiAnalyzer
            finally:
                os.chdir(old_cwd)
            analyzer = DeskFengshuiAnalyzer()
            
            result = await asyncio.wait_for(
                analyzer.analyze_async(
                    image_bytes=image_bytes,
                    use_bazi=False
                ),
                timeout=90.0
            )
            
            if result is None:
                error_msg = {
                    'type': 'error',
                    'content': "分析服务返回空结果，请稍后重试"
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                return
            
            if not isinstance(result, dict):
                error_msg = {
                    'type': 'error',
                    'content': f"分析服务返回了无效的数据类型: {type(result).__name__}"
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                return
            
            if not result.get('success'):
                error_msg = {
                    'type': 'error',
                    'content': result.get('error', '分析失败')
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                return
            
        except asyncio.TimeoutError:
            error_msg = {
                'type': 'error',
                'content': "分析超时（>90秒），请稍后重试。建议：上传更小的图片"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except ImportError as e:
            error_msg = {
                'type': 'error',
                'content': "服务未就绪，请稍后重试"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        logger.info(f"分析成功，评分: {result.get('score', 0)}")
        
        # 6. 先返回基础数据（type: 'data'，带填充）
        PADDING = ' ' * 16384
        data_msg = {
            'type': 'data',
            'content': result,
            '_padding': PADDING
        }
        yield f"data: {json.dumps(data_msg, ensure_ascii=False)}\n\n"
        
        # 7. 格式化数据为 prompt
        formatted_data = format_desk_fengshui_input_data_for_coze(result)
        logger.info(f"[Desk Fengshui Stream] 格式化数据长度: {len(formatted_data)} 字符")
        
        # 8. 调用 LLM 服务流式生成
        llm_service = LLMServiceFactory.get_service(scene="desk_fengshui", bot_id=used_bot_id)
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
                    logger.info(f"✅ [Desk Fengshui Stream] 收到第一个响应块")
            elif chunk_type == 'complete':
                complete_content = chunk.get('content', '')
                llm_output_chunks.append(complete_content)
                logger.info(f"✅ [Desk Fengshui Stream] 收到完成响应，总块数: {chunk_count}, 总内容长度: {total_content_length}")
                has_content = True
            elif chunk_type == 'error':
                logger.error(f"❌ [Desk Fengshui Stream] 收到错误响应: {chunk.get('content', '')}")
            
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            if chunk_type in ['complete', 'error']:
                break
        
        # 9. 记录交互数据（异步，不阻塞）
        api_end_time = time.time()
        api_response_time_ms = int((api_end_time - api_start_time) * 1000)
        llm_total_time_ms = int((api_end_time - llm_start_time) * 1000) if llm_start_time else None
        llm_output = ''.join(llm_output_chunks)
        
        logger_instance = get_user_interaction_logger()
        logger_instance.log_function_usage_async(
            function_type='desk_fengshui',
            function_name='办公桌风水分析',
            frontend_api='/api/v2/desk-fengshui/analyze/stream',
            frontend_input=frontend_input,
            input_data=result,
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
        logger.error(f"办公桌风水配置错误: {e}")
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
            function_type='desk_fengshui',
            function_name='办公桌风水分析',
            frontend_api='/api/v2/desk-fengshui/analyze/stream',
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
        logger.error(f"办公桌风水流式处理失败: {e}\n{traceback.format_exc()}")
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
            function_type='desk_fengshui',
            function_name='办公桌风水分析',
            frontend_api='/api/v2/desk-fengshui/analyze/stream',
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
