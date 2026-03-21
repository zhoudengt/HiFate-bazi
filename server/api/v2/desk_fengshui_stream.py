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
from server.services.stream_call_logger import get_stream_call_logger
from server.config.config_loader import get_config_from_db_only
from server.api.base.stream_handler import generate_request_id
from server.utils.prompt_builders import format_desk_fengshui_input_data_for_coze

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由（注意：不设置prefix，因为会被包含到主路由中）
router = APIRouter(tags=["办公桌风水-流式"])


def _safe_import_desk_fengshui_analyzer():
    """
    安全导入 DeskFengshuiAnalyzer，使用唯一模块名避免 sys.modules 冲突。
    
    问题背景：项目中存在多个同名 analyzer.py（desk_fengshui / fortune_analysis / prompt_optimizer），
    使用 importlib.import_module('analyzer') 或 reload(sys.modules['analyzer']) 会导致加载错误的模块。
    """
    import importlib.util
    _MODULE_NAME = '_desk_fengshui_analyzer'
    
    # 确保 desk_fengshui 目录在 sys.path 中（analyzer.py 内部 import 需要）
    desk_fengshui_path = os.path.abspath(os.path.join(project_root, 'services', 'desk_fengshui'))
    if desk_fengshui_path not in sys.path:
        sys.path.insert(0, desk_fengshui_path)

    # 预加载 desk_fengshui 模块，覆盖 fortune_analysis 同名缓存（避免 rule_engine 等指向错误文件）
    _DESK_DEPS = ['rule_engine', 'item_detector', 'position_calculator', 'bazi_client', 'vision_analyzer',
                  'image_annotator', 'layout_generator']
    for _dep in _DESK_DEPS:
        _dep_file = os.path.join(desk_fengshui_path, f'{_dep}.py')
        if os.path.exists(_dep_file):
            _cached = sys.modules.get(_dep)
            _need_load = _cached is None or 'desk_fengshui' not in getattr(_cached, '__file__', '')
            if _need_load:
                _s = importlib.util.spec_from_file_location(_dep, _dep_file)
                _m = importlib.util.module_from_spec(_s)
                sys.modules[_dep] = _m
                _s.loader.exec_module(_m)

    # 使用已缓存的模块或从文件加载
    # 注意：热更新后缓存可能被污染（同名 analyzer.py 覆盖），需验证后再用
    mod = sys.modules.get(_MODULE_NAME)
    if mod is not None and not hasattr(mod, 'DeskFengshuiAnalyzer'):
        # 缓存的模块不包含 DeskFengshuiAnalyzer（被其他 analyzer.py 污染），强制清除重载
        del sys.modules[_MODULE_NAME]
        mod = None

    if mod is None:
        analyzer_path = os.path.join(desk_fengshui_path, 'analyzer.py')
        spec = importlib.util.spec_from_file_location(_MODULE_NAME, analyzer_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[_MODULE_NAME] = mod
        spec.loader.exec_module(mod)

    return mod.DeskFengshuiAnalyzer


def _load_desk_module(module_name: str):
    """
    按绝对路径加载 services/desk_fengshui/ 下的模块，
    避免与 home_fengshui 同名模块冲突（如 layout_generator、image_annotator）。
    """
    import importlib.util
    cache_key = f'_desk_{module_name}'
    mod = sys.modules.get(cache_key)
    if mod is not None:
        return mod
    desk_path = os.path.join(project_root, 'services', 'desk_fengshui', f'{module_name}.py')
    spec = importlib.util.spec_from_file_location(cache_key, desk_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[cache_key] = mod
    spec.loader.exec_module(mod)
    return mod


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
        
        # 安全导入分析器（避免多个 analyzer.py 模块名冲突）
        DeskFengshuiAnalyzer = _safe_import_desk_fengshui_analyzer()
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
    bot_id: Optional[str] = None,
    request_id: Optional[str] = None
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
    request_id = request_id or generate_request_id()
    llm_first_token_time = None
    llm_output_chunks = []
    llm_start_time = None
    
    try:
        yield f"data: {json.dumps({'type': 'request_id', 'request_id': request_id}, ensure_ascii=False)}\n\n"

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
            # 安全导入分析器（避免多个 analyzer.py 模块名冲突）
            DeskFengshuiAnalyzer = _safe_import_desk_fengshui_analyzer()
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
                'content': f"服务导入失败: {str(e)}。请检查服务模块是否正确安装。"
            }
            logger.error(f"DeskFengshuiAnalyzer 导入失败: {e}", exc_info=True)
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            error_msg = {
                'type': 'error',
                'content': f"分析服务异常: {str(e)}"
            }
            logger.error(f"办公桌风水分析异常: {e}", exc_info=True)
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        logger.info(f"分析成功，评分: {result.get('score', 0)}")
        
        # 6. 先返回基础数据（type: 'data'，不含图片，立即推送）
        for _item in result.get('items', []):
            if _item.get('label'):
                _item['name'] = _item['label']
        result['items_text'] = '、'.join(
            _item.get('label', _item.get('name', '')) for _item in result.get('items', [])
        )

        PADDING = ' ' * 16384
        data_msg = {
            'type': 'data',
            'content': result,
            '_padding': PADDING
        }
        yield f"data: {json.dumps(data_msg, ensure_ascii=False)}\n\n"
        logger.info(f"✅ data 事件已推送（不含图片），耗时: {time.time() - api_start_time:.2f}s")

        # 7. 并行启动：标注图 + 布局图生成（后台任务），不阻塞 LLM 文字流
        image_queue: asyncio.Queue = asyncio.Queue()

        async def _generate_annotated():
            try:
                _mod = _load_desk_module('image_annotator')
                generate_annotated_image = _mod.generate_annotated_image
                from server.utils.async_executor import get_executor
                _loop = asyncio.get_event_loop()
                b64 = await _loop.run_in_executor(
                    get_executor(),
                    lambda: generate_annotated_image(image_bytes, result.get('items', []), result)
                )
                if b64:
                    await image_queue.put(('annotated_image', b64))
                    logger.info("✅ 标注图生成成功")
            except Exception as _e:
                logger.warning(f"标注图生成失败（不影响主流程）: {_e}")

        async def _generate_layout():
            try:
                _mod = _load_desk_module('layout_generator')
                generate_layout_image = _mod.generate_layout_image
                b64 = await asyncio.wait_for(
                    generate_layout_image(result.get('items', []), result),
                    timeout=60.0
                )
                if b64:
                    await image_queue.put(('layout_image', b64))
                    logger.info("✅ AI布局图生成成功")
            except Exception as _e:
                logger.warning(f"AI布局图生成失败（不影响主流程）: {_e}")

        annotated_task = asyncio.create_task(_generate_annotated())
        layout_task = asyncio.create_task(_generate_layout())

        # 8. 格式化数据为 prompt + LLM 流式生成（与图片生成并行）
        formatted_data = format_desk_fengshui_input_data_for_coze(result)
        logger.info(f"[Desk Fengshui Stream] 格式化数据长度: {len(formatted_data)} 字符")
        
        llm_service = LLMServiceFactory.get_service(scene="desk_fengshui", bot_id=used_bot_id)
        llm_start_time = time.time()
        chunk_count = 0
        total_content_length = 0
        has_content = False
        
        async for chunk in llm_service.stream_analysis(formatted_data, bot_id=used_bot_id):
            chunk_type = chunk.get('type', 'unknown')
            
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

            # LLM 流式输出间隙，检查图片是否已就绪并推送
            while not image_queue.empty():
                img_type, img_b64 = await image_queue.get()
                img_msg = {'type': img_type, 'image_base64': img_b64, 'format': 'png'}
                yield f"data: {json.dumps(img_msg, ensure_ascii=False)}\n\n"
                logger.info(f"✅ {img_type} 事件已推送（LLM流期间）")

            if chunk_type in ['complete', 'error']:
                break

        # 9. LLM 流结束后，等待剩余图片任务完成并推送
        for task in [annotated_task, layout_task]:
            if not task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=45.0)
                except (asyncio.TimeoutError, Exception) as _e:
                    logger.warning(f"图片生成任务超时或异常: {_e}")
        while not image_queue.empty():
            img_type, img_b64 = await image_queue.get()
            img_msg = {'type': img_type, 'image_base64': img_b64, 'format': 'png'}
            yield f"data: {json.dumps(img_msg, ensure_ascii=False)}\n\n"
            logger.info(f"✅ {img_type} 事件已推送（LLM流结束后）")
        
        # 9. 记录流式接口调用（异步，不阻塞）
        api_end_time = time.time()
        llm_output = ''.join(llm_output_chunks)
        
        stream_logger = get_stream_call_logger()
        stream_logger.log_async(
            function_type='desk_fengshui',
            frontend_api='/api/v2/desk-fengshui/analyze/stream',
            frontend_input=frontend_input,
            input_data=formatted_data if 'formatted_data' in locals() and formatted_data else '',
            llm_output=llm_output,
            api_total_ms=int((api_end_time - api_start_time) * 1000),
            input_data_gen_ms=None,
            llm_first_token_ms=int((llm_first_token_time - llm_start_time) * 1000) if llm_first_token_time and llm_start_time else None,
            llm_total_ms=int((api_end_time - llm_start_time) * 1000) if llm_start_time else None,
            bot_id=used_bot_id,
            llm_platform='bailian',
            status='success' if has_content else 'failed',
            request_id=request_id,
        )
        
    except ValueError as e:
        # 配置错误
        logger.error(f"办公桌风水配置错误: {e}")
        error_msg = {
            'type': 'error',
            'content': f"配置缺失: {str(e)}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
        
        api_end_time = time.time()
        stream_logger = get_stream_call_logger()
        stream_logger.log_async(
            function_type='desk_fengshui',
            frontend_api='/api/v2/desk-fengshui/analyze/stream',
            frontend_input=frontend_input,
            api_total_ms=int((api_end_time - api_start_time) * 1000),
            llm_platform='bailian',
            status='failed',
            error_message=str(e),
            request_id=request_id,
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
        
        api_end_time = time.time()
        stream_logger = get_stream_call_logger()
        stream_logger.log_async(
            function_type='desk_fengshui',
            frontend_api='/api/v2/desk-fengshui/analyze/stream',
            frontend_input=frontend_input,
            api_total_ms=int((api_end_time - api_start_time) * 1000),
            llm_platform='bailian',
            status='failed',
            error_message=str(e),
            request_id=request_id,
        )
