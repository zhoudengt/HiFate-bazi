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

    _DEPS = [
        'rule_engine', 'vision_analyzer', 'mingua_calculator', 'direction_mapper',
        'floor_plan_analyzer', 'position_calculator', 'sha_analyzer',
    ]
    for dep in _DEPS:
        dep_file = os.path.join(home_path, f'{dep}.py')
        if os.path.exists(dep_file):
            cached = sys.modules.get(f'_home_{dep}')
            if cached is None:
                spec = importlib.util.spec_from_file_location(f'_home_{dep}', dep_file)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[f'_home_{dep}'] = mod
                sys.modules[dep] = mod
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


@router.post('/analyze/stream', summary='流式生成居家风水分析报告（支持全屋 + 多房间）')
async def home_fengshui_stream(
    photos: List[UploadFile] = File(..., description='房间照片（1-4张）'),
    floor_plan: Optional[UploadFile] = File(None, description='户型图（可选，上传后启用全屋分析模式）'),
    room_types: Optional[str] = Form(None, description='每张照片对应的房间类型，JSON 数组字符串，如 ["living_room","bedroom","study"]；留空或传 auto 则自动识别'),
    room_type: Optional[str] = Form(None, description='[兼容旧版] 单一房间类型；多张照片时建议用 room_types'),
    door_direction: Optional[str] = Form(None, description='大门朝向（可选）'),
    birth_year: Optional[int] = Form(None, description='出生年份（可选，如 1990）'),
    solar_date: Optional[str] = Form(None, description='出生日期（可选）'),
    solar_time: Optional[str] = Form(None, description='出生时间（可选）'),
    gender: Optional[str] = Form(None, description='性别 male/female（可选）'),
    bot_id: Optional[str] = Form(None),
):
    """
    流式居家风水分析（支持全屋模式 + 多房间模式）

    全屋模式（上传 floor_plan 时启用）：
    - 额外分析户型图缺角、九宫格方位
    - 计算财位/文昌位/桃花位/天医位
    - 综合煞位分析
    - 生成全屋报告

    SSE 事件流：
    - request_id
    - progress_msg（进度提示）
    - floor_plan_result（户型图分析结果，仅全屋模式）
    - position_analysis（方位计算结果，仅全屋模式）
    - sha_analysis（煞位分析结果，仅全屋模式）
    - room_result（每个房间的结构化数据）
    - room_annotated_image（每个房间的标注图）
    - room_progress / room_complete / room_full_report（单房间 LLM 报告）
    - home_score（全屋综合评分）
    - full_report_progress / full_report_complete / full_report（全屋报告，仅全屋模式）
    """
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

    effective_room_types: List[str] = parsed_room_types
    if not effective_room_types and room_type:
        effective_room_types = [room_type] * len(photos)

    has_floor_plan = floor_plan is not None and floor_plan.content_type and floor_plan.content_type.startswith('image/')
    mode = '全屋' if has_floor_plan else '多房间'
    logger.info(f'[HomeFengshui] 收到请求({mode}): photos={len(photos)}, floor_plan={has_floor_plan}, room_types={effective_room_types}, door={door_direction}, birth_year={birth_year}')

    floor_plan_bytes = None
    if has_floor_plan:
        floor_plan_bytes = await floor_plan.read()

    return StreamingResponse(
        home_fengshui_stream_generator(
            photos=photos,
            room_types=effective_room_types,
            door_direction=door_direction,
            birth_year=birth_year,
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            bot_id=bot_id,
            floor_plan_bytes=floor_plan_bytes,
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
    birth_year: Optional[int] = None,
    floor_plan_bytes: Optional[bytes] = None,
):
    """居家风水 SSE 流式生成器（支持全屋 + 多房间）"""
    api_start_time = time.time()
    request_id = request_id or generate_request_id()
    llm_first_token_time = None
    all_llm_output_chunks = []
    llm_start_time = None
    has_content = False
    is_whole_house = floor_plan_bytes is not None
    PADDING = ' ' * 16384

    def _sse(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    try:
        yield _sse({'type': 'request_id', 'request_id': request_id})

        used_bot_id = bot_id
        if not used_bot_id:
            used_bot_id = (
                get_config_from_db_only('BAILIAN_HOME_FENGSHUI_REPORT_APP_ID')
                or get_config_from_db_only('HOME_FENGSHUI_BOT_ID')
            )
            if not used_bot_id:
                yield _sse({'type': 'error', 'content': '数据库配置缺失：BAILIAN_HOME_FENGSHUI_REPORT_APP_ID'})
                return

        valid_photos = [p for p in photos if p.content_type and p.content_type.startswith('image/')]
        if not valid_photos:
            yield _sse({'type': 'error', 'content': '请上传图片文件（jpg/png/webp）'})
            return
        if len(valid_photos) > 4:
            valid_photos = valid_photos[:4]

        effective_room_types = list(room_types) + ['auto'] * (len(valid_photos) - len(room_types))
        effective_room_types = effective_room_types[:len(valid_photos)]

        photo_count = len(valid_photos)
        mode_label = '全屋风水' if is_whole_house else f'{photo_count} 张房间照片'
        yield _sse({'type': 'progress_msg', 'content': f'正在分析{mode_label}...'})

        image_bytes_list = [await p.read() for p in valid_photos]

        try:
            HomeFengshuiAnalyzer = _safe_import_home_fengshui_analyzer()
            analyzer = HomeFengshuiAnalyzer()
        except ImportError as e:
            yield _sse({'type': 'error', 'content': f'服务模块导入失败: {e}'})
            logger.error(f'HomeFengshuiAnalyzer 导入失败: {e}', exc_info=True)
            return

        llm_service = LLMServiceFactory.get_service(scene='home_fengshui', bot_id=used_bot_id)

        # ====================================================================
        # 全屋分析模式（有户型图）
        # ====================================================================
        if is_whole_house:
            yield _sse({'type': 'progress_msg', 'content': '正在分析户型图与方位...'})

            sse_events_buffer = []

            async def _progress_cb(stage: str, data):
                sse_events_buffer.append((stage, data))

            full_result = await analyzer.analyze_full_house_async(
                image_bytes_list=image_bytes_list,
                room_types=effective_room_types,
                floor_plan_bytes=floor_plan_bytes,
                door_direction=door_direction,
                birth_year=birth_year,
                gender=gender,
                solar_date=solar_date,
                solar_time=solar_time,
                progress_callback=_progress_cb,
            )

            for stage, data in sse_events_buffer:
                if stage == 'floor_plan_result':
                    yield _sse({'type': 'floor_plan_result', 'content': data})
                elif stage == 'room_result':
                    idx = data.get('photo_index', 0)
                    rt = data.get('room_type', 'bedroom')
                    yield _sse({'type': 'room_result', 'room_index': idx,
                                'room_type': rt, 'room_label': _room_label(rt),
                                'content': data, '_padding': PADDING})
                elif stage == 'position_analysis':
                    yield _sse({'type': 'position_analysis', 'content': data})
                elif stage == 'sha_analysis':
                    yield _sse({'type': 'sha_analysis', 'content': data})

            if full_result.get('mingua_info'):
                yield _sse({'type': 'mingua_result', 'content': full_result['mingua_info']})

            yield _sse({
                'type': 'home_score',
                'overall_score': full_result.get('overall_score', 0),
                'room_count': len(full_result.get('room_results', [])),
                'is_whole_house': True,
            })

            formatted_data = format_home_fengshui_input_data_for_coze(
                full_result, is_whole_house=True
            )

            llm_start_time = time.time()
            yield _sse({'type': 'progress_msg', 'content': '正在生成全屋风水报告...'})

            full_report_chunks = []
            async for chunk in llm_service.stream_analysis(formatted_data, app_id=used_bot_id):
                chunk_type = chunk.get('type', 'unknown')
                if llm_first_token_time is None and chunk_type == 'progress':
                    llm_first_token_time = time.time()
                content = chunk.get('content', '')
                if chunk_type in ('progress', 'complete'):
                    full_report_chunks.append(content)
                    all_llm_output_chunks.append(content)
                    has_content = True
                if chunk_type == 'progress':
                    yield _sse({'type': 'full_report_progress', 'content': content})
                elif chunk_type == 'complete':
                    yield _sse({'type': 'full_report_complete', 'content': content})
                if chunk_type in ('complete', 'error'):
                    break

            full_report = ''.join(full_report_chunks)
            if full_report:
                yield _sse({'type': 'full_report', 'content': full_report})

        # ====================================================================
        # 多房间模式（无户型图，保持原有流程）
        # ====================================================================
        else:
            room_results = []

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

                yield _sse({'type': 'room_result', 'room_index': idx, 'room_type': actual_room_type,
                            'room_label': room_label, 'auto_detected': auto_detected,
                            'content': result, '_padding': PADDING})

                if annotated_b64:
                    yield _sse({'type': 'room_annotated_image', 'room_index': idx,
                                'room_type': actual_room_type, 'image_base64': annotated_b64,
                                'overall_score': result.get('overall_score', 0)})

                mingua_info = result.get('mingua_info')
                if mingua_info and idx == 0:
                    yield _sse({'type': 'mingua_result', 'content': mingua_info})

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

                room_report = ''.join(room_llm_chunks)
                if room_report:
                    yield _sse({'type': 'room_full_report', 'room_index': idx,
                                'room_type': actual_room_type, 'room_label': room_label,
                                'content': room_report})

                result['llm_report'] = room_report
                room_results.append(result)

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

        # ── 日志记录 ─────────────────────────────────────────────
        api_end_time = time.time()
        llm_output = ''.join(all_llm_output_chunks)
        stream_logger = get_stream_call_logger()
        stream_logger.log_async(
            function_type='home_fengshui',
            frontend_api='/api/v2/home-fengshui/analyze/stream',
            frontend_input={
                'room_types': effective_room_types, 'door_direction': door_direction,
                'photo_count': len(valid_photos), 'is_whole_house': is_whole_house,
                'birth_year': birth_year,
            },
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
            frontend_input={'photo_count': len(photos), 'is_whole_house': is_whole_house},
            api_total_ms=int((api_end_time - api_start_time) * 1000),
            llm_platform='bailian',
            status='failed',
            error_message=str(e),
            request_id=request_id,
        )


def _room_label(room_type: str) -> str:
    return {
        'bedroom': '卧室', 'living_room': '客厅', 'study': '书房',
        'kitchen': '厨房', 'dining_room': '餐厅', 'master_bedroom': '主卧',
        'second_bedroom': '次卧', 'bathroom': '卫生间', 'balcony': '阳台',
        'storage': '储物间', 'hallway': '走廊', 'entrance': '玄关',
    }.get(room_type, '房间')
