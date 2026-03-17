#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
居家风水分析流式接口
支持多张照片上传，SSE 流式返回结构化分析 + 大模型报告
"""

import logging
import os
import sys
import time
import json
import asyncio
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'services', 'home_fengshui'))

from server.services.llm_service_factory import LLMServiceFactory
from server.services.stream_call_logger import get_stream_call_logger
from server.config.config_loader import get_config_from_db_only
from server.api.base.stream_handler import generate_request_id
from server.utils.prompt_builders import format_home_fengshui_input_data_for_coze

logger = logging.getLogger(__name__)

router = APIRouter(tags=['居家风水-流式'])


def _safe_import_home_fengshui_analyzer():
    """安全导入 HomeFengshuiAnalyzer，避免多个同名 analyzer.py 冲突"""
    import importlib.util
    _MODULE_NAME = '_home_fengshui_analyzer'

    home_path = os.path.abspath(os.path.join(project_root, 'services', 'home_fengshui'))
    if home_path not in sys.path:
        sys.path.insert(0, home_path)

    _DEPS = ['rule_engine', 'vision_analyzer', 'mingua_calculator', 'direction_mapper']
    for dep in _DEPS:
        dep_file = os.path.join(home_path, f'{dep}.py')
        if os.path.exists(dep_file):
            cached = sys.modules.get(f'_home_{dep}')
            if cached is None:
                spec = importlib.util.spec_from_file_location(f'_home_{dep}', dep_file)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[f'_home_{dep}'] = mod
                sys.modules[dep] = mod  # 也注册无前缀名（供 analyzer.py 内部 import 使用）
                spec.loader.exec_module(mod)

    mod = sys.modules.get(_MODULE_NAME)
    if mod is not None and not hasattr(mod, 'HomeFengshuiAnalyzer'):
        del sys.modules[_MODULE_NAME]
        mod = None

    if mod is None:
        analyzer_path = os.path.join(home_path, 'analyzer.py')
        spec = importlib.util.spec_from_file_location(_MODULE_NAME, analyzer_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[_MODULE_NAME] = mod
        spec.loader.exec_module(mod)

    return mod.HomeFengshuiAnalyzer


@router.post('/analyze/stream', summary='流式生成居家风水分析报告（支持多房间）')
async def home_fengshui_stream(
    photos: List[UploadFile] = File(..., description='房间照片（1-4张）'),
    room_types: Optional[str] = Form(None, description='每张照片对应的房间类型，JSON 数组字符串，如 ["living_room","bedroom","study"]；留空或传 auto 则自动识别'),
    room_type: Optional[str] = Form(None, description='[兼容旧版] 单一房间类型；多张照片时建议用 room_types'),
    door_direction: Optional[str] = Form(None, description='大门朝向（可选）'),
    solar_date: Optional[str] = Form(None, description='出生日期（可选）'),
    solar_time: Optional[str] = Form(None, description='出生时间（可选）'),
    gender: Optional[str] = Form(None, description='性别 male/female（可选）'),
    bot_id: Optional[str] = Form(None),
):
    """
    流式居家风水分析（支持多张照片 × 多房间类型）

    room_types 传值方式：
    - JSON 数组字符串：room_types=["living_room","bedroom","study"]
    - 单个字符串（单张照片时）：room_types=bedroom
    - 不传或传 auto：自动识别

    SSE 事件流（多房间模式）：
    - request_id
    - progress_msg（进度提示）
    - room_result（每个房间的结构化数据，含 photo_index / room_type / auto_detected）
    - room_annotated_image（每个房间的标注图，可选）
    - room_progress（每个房间的 LLM 流式文字，含 room_index 区分）× N
    - room_complete（每个房间报告完成）
    - room_full_report（每个房间的完整报告文本）
    - home_score（全屋综合评分）
    - full_report（全屋综合报告，LLM 流式）× N → complete → full_report
    """
    # 解析 room_types：支持 JSON 数组字符串 或 单个字符串
    parsed_room_types: List[str] = []
    if room_types:
        stripped = room_types.strip()
        if stripped.startswith('['):
            try:
                parsed_room_types = json.loads(stripped)
            except json.JSONDecodeError:
                parsed_room_types = [stripped]
        else:
            parsed_room_types = [stripped]

    # 兼容旧版：若只传了 room_type，转为 room_types
    effective_room_types: List[str] = parsed_room_types
    if not effective_room_types and room_type:
        effective_room_types = [room_type] * len(photos)

    logger.info(f'[HomeFengshui] 收到请求: photos={len(photos)}, room_types={effective_room_types}, door={door_direction}')

    return StreamingResponse(
        home_fengshui_stream_generator(
            photos=photos,
            room_types=effective_room_types,
            door_direction=door_direction,
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            bot_id=bot_id,
        ),
        media_type='text/event-stream',
    )


async def home_fengshui_stream_generator(
    photos: List[UploadFile],
    room_types: List[str],
    door_direction: Optional[str],
    solar_date: Optional[str],
    solar_time: Optional[str],
    gender: Optional[str],
    bot_id: Optional[str] = None,
    request_id: Optional[str] = None,
):
    """居家风水 SSE 流式生成器（多房间版）"""
    api_start_time = time.time()
    request_id = request_id or generate_request_id()
    llm_first_token_time = None
    all_llm_output_chunks = []
    llm_start_time = None
    has_content = False
    PADDING = ' ' * 16384

    def _sse(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    try:
        yield _sse({'type': 'request_id', 'request_id': request_id})

        # 确定 bot_id
        used_bot_id = bot_id
        if not used_bot_id:
            used_bot_id = (
                get_config_from_db_only('BAILIAN_HOME_FENGSHUI_REPORT_APP_ID')
                or get_config_from_db_only('HOME_FENGSHUI_BOT_ID')
            )
            if not used_bot_id:
                yield _sse({'type': 'error', 'content': '数据库配置缺失：BAILIAN_HOME_FENGSHUI_REPORT_APP_ID'})
                return

        # 验证照片
        valid_photos = [p for p in photos if p.content_type and p.content_type.startswith('image/')]
        if not valid_photos:
            yield _sse({'type': 'error', 'content': '请上传图片文件（jpg/png/webp）'})
            return
        if len(valid_photos) > 4:
            valid_photos = valid_photos[:4]

        # 补齐 room_types，不足部分自动识别
        effective_room_types = list(room_types) + ['auto'] * (len(valid_photos) - len(room_types))
        effective_room_types = effective_room_types[:len(valid_photos)]

        photo_count = len(valid_photos)
        yield _sse({'type': 'progress_msg', 'content': f'正在分析 {photo_count} 张房间照片...'})

        # 读取图片数据
        image_bytes_list = [await p.read() for p in valid_photos]

        # 初始化分析器
        try:
            HomeFengshuiAnalyzer = _safe_import_home_fengshui_analyzer()
            analyzer = HomeFengshuiAnalyzer()
        except ImportError as e:
            yield _sse({'type': 'error', 'content': f'服务模块导入失败: {e}'})
            logger.error(f'HomeFengshuiAnalyzer 导入失败: {e}', exc_info=True)
            return

        # ── 逐房间分析 ──────────────────────────────────────────────
        room_results = []
        llm_service = LLMServiceFactory.get_service(scene='home_fengshui', bot_id=used_bot_id)

        async for result in analyzer.analyze_multi_async(
            image_bytes_list=image_bytes_list,
            room_types=effective_room_types,
            door_direction=door_direction,
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            use_bazi=bool(solar_date and gender),
        ):
            idx = result.get('photo_index', len(room_results))

            if not result.get('success'):
                yield _sse({'type': 'room_error', 'room_index': idx, 'content': result.get('error', '分析失败')})
                continue

            actual_room_type = result.get('room_type', 'bedroom')
            auto_detected = result.get('auto_detected', False)
            room_label = _room_label(actual_room_type)

            logger.info(f'[HomeFengshui] 房间[{idx}] {room_label} 分析完成，评分={result.get("overall_score")}')

            # 生成标注图
            annotated_b64 = None
            try:
                from image_annotator import generate_annotated_image
                from server.utils.async_executor import get_executor
                _loop = asyncio.get_event_loop()
                annotated_b64 = await _loop.run_in_executor(
                    get_executor(),
                    lambda idx=idx: generate_annotated_image(
                        image_bytes_list[idx],
                        result.get('furnitures', []),
                        result,
                        door_direction=door_direction,
                        mingua_info=result.get('mingua_info'),
                    )
                )
            except Exception as _e:
                logger.warning(f'房间[{idx}]标注图生成失败: {_e}')

            if annotated_b64:
                result['annotated_image_b64'] = annotated_b64
            result['furnitures_text'] = '、'.join(
                f.get('label', f.get('name', '')) for f in result.get('furnitures', [])
            )

            # 发送结构化数据
            yield _sse({'type': 'room_result', 'room_index': idx, 'room_type': actual_room_type,
                        'room_label': room_label, 'auto_detected': auto_detected,
                        'content': result, '_padding': PADDING})

            # 发送标注图
            if annotated_b64:
                yield _sse({'type': 'room_annotated_image', 'room_index': idx,
                            'room_type': actual_room_type, 'image_base64': annotated_b64,
                            'overall_score': result.get('overall_score', 0)})

            # 命卦
            mingua_info = result.get('mingua_info')
            if mingua_info and idx == 0:
                yield _sse({'type': 'mingua_result', 'content': mingua_info})

            # 每个房间单独调用 LLM 生成报告
            formatted_data = format_home_fengshui_input_data_for_coze(result)
            room_llm_chunks = []
            if llm_start_time is None:
                llm_start_time = time.time()

            yield _sse({'type': 'progress_msg', 'content': f'正在生成{room_label}风水报告...'})

            async for chunk in llm_service.stream_analysis(formatted_data, app_id=used_bot_id):
                chunk_type = chunk.get('type', 'unknown')
                if llm_first_token_time is None and chunk_type == 'progress':
                    llm_first_token_time = time.time()
                content = chunk.get('content', '')
                if chunk_type in ('progress', 'complete'):
                    room_llm_chunks.append(content)
                    all_llm_output_chunks.append(content)
                    has_content = True
                # 注入 room_index，方便前端区分
                tagged_chunk = dict(chunk)
                tagged_chunk['room_index'] = idx
                tagged_chunk['room_type'] = actual_room_type
                if chunk_type == 'progress':
                    tagged_chunk['type'] = 'room_progress'
                elif chunk_type == 'complete':
                    tagged_chunk['type'] = 'room_complete'
                yield _sse(tagged_chunk)
                if chunk_type in ('complete', 'error'):
                    break

            # 发送该房间完整报告
            room_report = ''.join(room_llm_chunks)
            if room_report:
                yield _sse({'type': 'room_full_report', 'room_index': idx,
                            'room_type': actual_room_type, 'room_label': room_label,
                            'content': room_report})

            result['llm_report'] = room_report
            room_results.append(result)

        # ── 全屋综合评分 ─────────────────────────────────────────────
        if room_results:
            scores = [r.get('overall_score', 0) for r in room_results if r.get('overall_score')]
            home_score = int(sum(scores) / len(scores)) if scores else 0
            yield _sse({
                'type': 'home_score',
                'overall_score': home_score,
                'room_count': len(room_results),
                'room_scores': [
                    {'room_index': r.get('photo_index', i), 'room_type': r.get('room_type'),
                     'room_label': _room_label(r.get('room_type', '')), 'score': r.get('overall_score', 0)}
                    for i, r in enumerate(room_results)
                ],
            })

        # 记录调用日志
        api_end_time = time.time()
        llm_output = ''.join(all_llm_output_chunks)
        stream_logger = get_stream_call_logger()
        stream_logger.log_async(
            function_type='home_fengshui',
            frontend_api='/api/v2/home-fengshui/analyze/stream',
            frontend_input={'room_types': effective_room_types, 'door_direction': door_direction, 'photo_count': len(valid_photos)},
            input_data='',
            llm_output=llm_output,
            api_total_ms=int((api_end_time - api_start_time) * 1000),
            llm_first_token_ms=int((llm_first_token_time - llm_start_time) * 1000) if llm_first_token_time and llm_start_time else None,
            llm_total_ms=int((api_end_time - llm_start_time) * 1000) if llm_start_time else None,
            bot_id=used_bot_id,
            llm_platform='bailian',
            status='success' if has_content else 'failed',
            request_id=request_id,
        )

    except Exception as e:
        import traceback
        logger.error(f'居家风水流式处理失败: {e}\n{traceback.format_exc()}')
        yield _sse({'type': 'error', 'content': f'处理失败: {e}'})

        api_end_time = time.time()
        stream_logger = get_stream_call_logger()
        stream_logger.log_async(
            function_type='home_fengshui',
            frontend_api='/api/v2/home-fengshui/analyze/stream',
            frontend_input={'photo_count': len(photos)},
            api_total_ms=int((api_end_time - api_start_time) * 1000),
            llm_platform='bailian',
            status='failed',
            error_message=str(e),
            request_id=request_id,
        )


def _room_label(room_type: str) -> str:
    return {
        'bedroom': '卧室', 'living_room': '客厅', 'study': '书房',
        'kitchen': '厨房', 'dining_room': '餐厅',
    }.get(room_type, '房间')
