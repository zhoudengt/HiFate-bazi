#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字命理-喜神与忌神API
获取喜神五行、忌神五行和十神命格，并映射ID
"""

import logging
import os
import sys
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field, validator
from fastapi.responses import StreamingResponse
import json
import asyncio
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.wangshuai_service import WangShuaiService
from server.services.bazi_service import BaziService
from server.services.rule_service import RuleService
from server.services.config_service import ConfigService
from server.utils.data_validator import validate_bazi_data
from server.api.v1.models.bazi_base_models import BaziBaseRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.config.config_loader import get_config_from_db_only
from server.utils.api_cache_helper import (
    generate_cache_key, get_cached_result, set_cached_result, L2_TTL
)

logger = logging.getLogger(__name__)

router = APIRouter()


class XishenJishenRequest(BaziBaseRequest):
    """喜神忌神请求模型"""
    pass


class XishenJishenResponse(BaseModel):
    """喜神忌神响应模型"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/bazi/xishen-jishen", response_model=XishenJishenResponse, summary="获取喜神忌神和十神命格")
async def get_xishen_jishen(request: XishenJishenRequest):
    """
    获取喜神五行、忌神五行和十神命格
    
    根据用户的生辰（与基础八字排盘生辰同）：
    1. 从旺衰分析中获取喜神五行和忌神五行
    2. 从公式分析中获取十神命格
    3. 查询配置表获取对应的ID
    
    Returns:
        - xi_shen_elements: 喜神五行列表（包含名称和ID）
        - ji_shen_elements: 忌神五行列表（包含名称和ID）
        - shishen_mingge: 十神命格列表（包含名称和ID）
    """
    logger.info(f"📥 收到喜神忌神请求: {request.solar_date} {request.solar_time} {request.gender}")
    
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
        
        # >>> 缓存检查（喜神忌神固定，不随时间变化）<<<
        cache_key = generate_cache_key("xishen", final_solar_date, final_solar_time, request.gender)
        cached = get_cached_result(cache_key, "xishen-jishen")
        if cached:
            logger.info(f"✅ 喜神忌神缓存命中")
            return XishenJishenResponse(success=True, data=cached)
        # >>> 缓存检查结束 <<<
        
        # 1. 获取旺衰分析结果（包含喜神五行和忌神五行）
        # ✅ 修复：改为异步执行，避免阻塞事件循环
        import time
        start_time = time.time()
        loop = asyncio.get_event_loop()
        from concurrent.futures import ThreadPoolExecutor
        executor = ThreadPoolExecutor(max_workers=min(os.cpu_count() or 4 * 2, 100))
        
        try:
            # 使用线程池执行，添加30秒超时保护
            wangshuai_result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    WangShuaiService.calculate_wangshuai,
                    final_solar_date,
                    final_solar_time,
                    request.gender
                ),
                timeout=30.0
            )
            elapsed_time = time.time() - start_time
            logger.info(f"⏱️ 旺衰计算耗时: {elapsed_time:.2f}秒")
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ 旺衰计算超时（>{30.0}秒），耗时: {elapsed_time:.2f}秒")
            raise HTTPException(status_code=500, detail="旺衰计算超时，请稍后重试")
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ 旺衰计算异常（耗时: {elapsed_time:.2f}秒）: {e}", exc_info=True)
            raise
        
        if not wangshuai_result.get('success'):
            error_msg = wangshuai_result.get('error', '旺衰计算失败')
            logger.error(f"❌ 旺衰计算失败: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        wangshuai_data = wangshuai_result.get('data', {})
        
        # 调试：打印完整的数据结构
        logger.info(f"   wangshuai_data keys: {list(wangshuai_data.keys())}")
        logger.info(f"   wangshuai_data.xi_shen_elements: {wangshuai_data.get('xi_shen_elements', 'NOT_FOUND')}")
        logger.info(f"   wangshuai_data.ji_shen_elements: {wangshuai_data.get('ji_shen_elements', 'NOT_FOUND')}")
        
        # 提取喜神五行和忌神五行（优先使用final_xi_ji中的综合结果，如果没有则使用原始结果）
        final_xi_ji = wangshuai_data.get('final_xi_ji', {})
        logger.info(f"   final_xi_ji存在: {bool(final_xi_ji)}, keys: {list(final_xi_ji.keys()) if final_xi_ji else []}")
        if final_xi_ji:
            logger.info(f"   final_xi_ji.xi_shen_elements: {final_xi_ji.get('xi_shen_elements', 'NOT_FOUND')}")
            logger.info(f"   final_xi_ji.ji_shen_elements: {final_xi_ji.get('ji_shen_elements', 'NOT_FOUND')}")
        
        if final_xi_ji and final_xi_ji.get('xi_shen_elements'):
            # 使用综合调候后的最终结果
            xi_shen_elements_raw = final_xi_ji.get('xi_shen_elements', [])
            ji_shen_elements_raw = final_xi_ji.get('ji_shen_elements', [])
            logger.info(f"   ✅ 使用final_xi_ji中的数据: 喜神={xi_shen_elements_raw}, 忌神={ji_shen_elements_raw}")
        else:
            # 使用原始旺衰结果
            xi_shen_elements_raw = wangshuai_data.get('xi_shen_elements', [])  # 如 ['金', '土']
            ji_shen_elements_raw = wangshuai_data.get('ji_shen_elements', [])  # 如 ['水', '木', '火']
            logger.info(f"   ⚠️  使用原始数据: 喜神={xi_shen_elements_raw}, 忌神={ji_shen_elements_raw}")
        
        logger.info(f"   最终提取 - 喜神五行: {xi_shen_elements_raw}, 忌神五行: {ji_shen_elements_raw}")
        
        # 2. 获取十神命格
        # ✅ 直接调用算法公式规则分析接口的逻辑，确保数据一致性
        from server.api.v1.formula_analysis import analyze_formula_rules, FormulaAnalysisRequest
        
        # 调用算法公式规则分析接口（只查询十神命格类型）
        formula_request = FormulaAnalysisRequest(
            solar_date=final_solar_date,
            solar_time=final_solar_time,
            gender=request.gender,
            calendar_type=request.calendar_type or "solar",
            location=request.location,
            latitude=request.latitude,
            longitude=request.longitude,
            rule_types=['shishen']  # 只查询十神命格
        )
        formula_result = await analyze_formula_rules(formula_request)
        
        if not formula_result.success:
            logger.warning(f"算法公式规则分析接口调用失败: {formula_result.error}")
            shishen_mingge_names = []
        else:
            # 从算法公式规则分析接口返回的数据中提取十神命格名称
            formula_data = formula_result.data
            matched_rules = formula_data.get('matched_rules', {})
            rule_details = formula_data.get('rule_details', {})
            
            # 获取十神命格规则的ID列表
            shishen_rule_ids = matched_rules.get('shishen', [])
            
            logger.info(f"   开始提取命格名称，规则ID列表: {shishen_rule_ids}")
            logger.info(f"   rule_details 的键: {list(rule_details.keys())}")
            
            # ✅ 使用统一的命格提取器
            from server.services.mingge_extractor import extract_mingge_names_from_rules
            
            # 构建规则列表（从 rule_details 中提取）
            shishen_rules = []
            for rule_id in shishen_rule_ids:
                rule_detail = rule_details.get(str(rule_id), rule_details.get(rule_id, {}))
                logger.info(f"   规则 {rule_id}: rule_detail 存在 = {bool(rule_detail)}")
                if rule_detail:
                    logger.info(f"   规则 {rule_id}: 键 = {list(rule_detail.keys())}")
                    logger.info(f"   规则 {rule_id}: 结果字段 = {rule_detail.get('结果', rule_detail.get('result', '无'))[:80]}")
                    shishen_rules.append(rule_detail)
            
            logger.info(f"   ✅ 提取到 {len(shishen_rules)} 条规则详情")
            
            # 使用统一的提取器提取命格名称
            logger.info(f"   🔄 调用 extract_mingge_names_from_rules，输入规则数量: {len(shishen_rules)}")
            shishen_mingge_names = extract_mingge_names_from_rules(shishen_rules)
            
            logger.info(f"   🔚 extract_mingge_names_from_rules 返回: {shishen_mingge_names}")
        
        logger.info(f"   十神命格: {shishen_mingge_names}")
        
        # 3. 映射ID
        xi_shen_elements = ConfigService.map_elements_to_ids(xi_shen_elements_raw)
        ji_shen_elements = ConfigService.map_elements_to_ids(ji_shen_elements_raw)
        shishen_mingge = ConfigService.map_mingge_to_ids(shishen_mingge_names)
        
        # 4. 构建响应数据
        response_data = {
            'solar_date': request.solar_date,
            'solar_time': request.solar_time,
            'gender': request.gender,
            'xi_shen_elements': xi_shen_elements,  # [{'name': '金', 'id': 4}, {'name': '土', 'id': 3}]
            'ji_shen_elements': ji_shen_elements,  # [{'name': '水', 'id': 5}, {'name': '木', 'id': 1}, {'name': '火', 'id': 2}]
            'shishen_mingge': shishen_mingge,  # [{'name': '正官格', 'id': 2001}, ...]
            'wangshuai': wangshuai_data.get('wangshuai'),  # 旺衰状态
            'total_score': wangshuai_data.get('total_score'),  # 总分
        }
        
        # >>> 缓存写入 <<<
        set_cached_result(cache_key, response_data, L2_TTL)
        # >>> 缓存写入结束 <<<
        
        logger.info(f"✅ 喜神忌神获取成功")
        return XishenJishenResponse(success=True, data=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 喜神忌神API异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


async def xishen_jishen_stream_generator(
    request: XishenJishenRequest,
    bot_id: Optional[str] = None
):
    """
    流式生成喜神忌神大模型分析
    
    先返回完整的喜神忌神数据，然后流式返回大模型分析
    
    Args:
        request: 喜神忌神请求（与普通接口相同）
        bot_id: Coze Bot ID（可选）
    """
    import traceback
    
    try:
        # 1. 获取完整的喜神忌神数据（调用普通接口逻辑）
        base_result = await get_xishen_jishen(request)
        
        if not base_result.success or not base_result.data:
            error_msg = {
                'type': 'error',
                'content': f"获取喜神忌神数据失败: {base_result.error or '未知错误'}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        data = base_result.data
        
        # 2. 构建响应数据（与普通接口一致）
        response_data = {
            'success': True,
            'data': data
        }
        
        # 填充数据：16KB 空格，强制刷新网络缓冲区（需要超过网络设备的缓冲阈值）
        PADDING = ' ' * 16384
        
        # 3. 先发送完整的喜神忌神数据（type: "data"，带填充）
        data_msg = {
            'type': 'data',
            'content': response_data,
            '_padding': PADDING  # 填充数据强制刷新缓冲区
        }
        yield f"data: {json.dumps(data_msg, ensure_ascii=False)}\n\n"
        
        # 4. 构建提示词
        xi_elements_text = '、'.join([e['name'] for e in data.get('xi_shen_elements', [])]) or '无'
        ji_elements_text = '、'.join([e['name'] for e in data.get('ji_shen_elements', [])]) or '无'
        mingge_text = '、'.join([m['name'] for m in data.get('shishen_mingge', [])]) or '无'
        
        prompt = f"""请根据以下八字命理信息，生成详细的喜神忌神分析：

十神命格：{mingge_text}
喜神五行：{xi_elements_text}
忌神五行：{ji_elements_text}
旺衰状态：{data.get('wangshuai', '未知')}
总分：{data.get('total_score', 0)}分

请基于这些信息，生成详细的命理分析内容。"""
        
        # 5. 确定使用的 bot_id
        actual_bot_id = bot_id
        if not actual_bot_id:
            actual_bot_id = get_config_from_db_only("XISHEN_JISHEN_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
            if not actual_bot_id:
                # 没有配置bot_id，跳过大模型分析
                complete_msg = {
                    'type': 'complete',
                    'content': ''
                }
                yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
                return
        
        # 6. 创建 LLM 流式服务（支持 Coze 和百炼平台）
        try:
            from server.services.llm_service_factory import LLMServiceFactory
            llm_service = LLMServiceFactory.get_service(scene="xishen_jishen", bot_id=actual_bot_id)
        except ValueError as e:
            # 配置缺失，跳过大模型分析
            complete_msg = {
                'type': 'complete',
                'content': ''
            }
            yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            complete_msg = {
                'type': 'complete',
                'content': ''
            }
            yield f"data: {json.dumps(complete_msg, ensure_ascii=False)}\n\n"
            return
        
        # 7. 流式生成大模型分析（带心跳包保持连接）
        # 使用异步队列来实现心跳与数据的交错发送
        import asyncio
        from asyncio import Queue
        
        HEARTBEAT_INTERVAL = 10  # 心跳间隔（秒）
        # 填充数据：16KB 空格，强制刷新网络缓冲区（解决跨域网络缓冲问题）
        PADDING = ' ' * 16384
        data_queue = Queue()
        stop_heartbeat = asyncio.Event()
        
        # 心跳任务：定期发送心跳包
        async def heartbeat_task():
            heartbeat_count = 0
            while not stop_heartbeat.is_set():
                try:
                    await asyncio.wait_for(stop_heartbeat.wait(), timeout=HEARTBEAT_INTERVAL)
                    break  # 如果收到停止信号，退出
                except asyncio.TimeoutError:
                    # 超时，发送心跳（带填充数据）
                    heartbeat_count += 1
                    heartbeat_msg = {
                        'type': 'heartbeat',
                        'content': f'正在生成AI分析... ({heartbeat_count * HEARTBEAT_INTERVAL}秒)',
                        '_padding': PADDING  # 填充数据强制刷新缓冲区
                    }
                    await data_queue.put(heartbeat_msg)
                    logger.info(f"[喜神忌神流式] 发送心跳包 #{heartbeat_count} (带16KB填充)")
        
        # 数据任务：从 LLM API 读取数据
        async def data_task():
            try:
                async for result in llm_service.stream_analysis(prompt, bot_id=actual_bot_id):
                    await data_queue.put(result)
                # 发送完成标记
                await data_queue.put({'type': '_done'})
            except Exception as e:
                logger.error(f"[喜神忌神流式] Coze API 错误: {e}")
                await data_queue.put({'type': 'error', 'content': str(e)})
                await data_queue.put({'type': '_done'})
            finally:
                stop_heartbeat.set()
        
        # 发送初始心跳（带填充数据）
        heartbeat_msg = {
            'type': 'heartbeat',
            'content': '正在生成AI分析，请稍候...',
            '_padding': PADDING  # 填充数据强制刷新缓冲区
        }
        yield f"data: {json.dumps(heartbeat_msg, ensure_ascii=False)}\n\n"
        logger.info("[喜神忌神流式] 发送初始心跳 (带2KB填充)")
        
        # 启动心跳和数据任务
        heartbeat_coro = asyncio.create_task(heartbeat_task())
        data_coro = asyncio.create_task(data_task())
        
        try:
            # 从队列中读取数据并发送
            while True:
                result = await data_queue.get()
                
                if result.get('type') == '_done':
                    # 发送完成消息
                    msg = {
                        'type': 'complete',
                        'content': '分析完成'
                    }
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    break
                elif result.get('type') == 'heartbeat':
                    yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
                elif result.get('type') == 'progress':
                    msg = {
                        'type': 'progress',
                        'content': result.get('content', '')
                    }
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)
                elif result.get('type') == 'complete':
                    msg = {
                        'type': 'complete',
                        'content': result.get('content', '')
                    }
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    break
                elif result.get('type') == 'error':
                    msg = {
                        'type': 'error',
                        'content': result.get('content', '生成失败')
                    }
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    break
        finally:
            # 清理任务
            stop_heartbeat.set()
            heartbeat_coro.cancel()
            try:
                await heartbeat_coro
            except asyncio.CancelledError:
                pass
                
    except Exception as e:
        error_msg = {
            'type': 'error',
            'content': f"流式生成喜神忌神分析失败: {str(e)}\n{traceback.format_exc()}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


async def _xishen_jishen_stream_handler(request: Request):
    """内部处理函数，供 GET 和 POST 路由共享"""
    """
    流式生成喜神忌神大模型分析
    
    支持 GET 和 POST 两种方式：
    - GET: 通过 URL 参数传递（用于 EventSource API）
    - POST: 通过请求体传递（向后兼容）
    
    与 /bazi/xishen-jishen 接口相同的输入，但以SSE流式方式返回数据：
    1. 首先返回完整的喜神忌神数据（type: "data"）
    2. 然后流式返回大模型分析（type: "progress"）
    3. 最后返回完成标记（type: "complete"）
    
    **参数说明**：
    - **solar_date**: 阳历日期，格式：YYYY-MM-DD（当calendar_type=lunar时，可为农历日期）
    - **solar_time**: 出生时间，格式：HH:MM
    - **gender**: 性别，male(男) 或 female(女)
    - **calendar_type**: 历法类型：solar(阳历) 或 lunar(农历)，默认solar
    - **location**: 出生地点（用于时区转换，优先级1）
    - **latitude**: 纬度（用于时区转换，优先级2）
    - **longitude**: 经度（用于时区转换和真太阳时计算，优先级2）
    
    **返回格式**：
    SSE流式响应，每行格式：`data: {"type": "data|progress|complete|error", "content": ...}`
    
    **示例**：
    ```
    data: {"type": "data", "content": {"success": true, "data": {...}}}
    data: {"type": "progress", "content": "喜神忌神分析："}
    data: {"type": "progress", "content": "您的命局..."}
    data: {"type": "complete", "content": "完整的大模型分析内容"}
    ```
    """
    try:
        # 根据请求方法处理参数
        if request.method == "POST":
            # POST 请求：从请求体读取 JSON
            try:
                body_data = await request.json()
                params = XishenJishenRequest(**body_data)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"POST 请求体解析失败: {str(e)}"
                )
        else:
            # GET 请求：从 URL 参数手动读取（避免 FastAPI Query 依赖注入问题）
            query_params = request.query_params
            solar_date = query_params.get("solar_date")
            solar_time = query_params.get("solar_time")
            gender = query_params.get("gender")
            calendar_type = query_params.get("calendar_type")
            location = query_params.get("location")
            latitude_str = query_params.get("latitude")
            longitude_str = query_params.get("longitude")
            
            if not solar_date or not solar_time or not gender:
                raise HTTPException(
                    status_code=400,
                    detail="缺少必需参数：solar_date, solar_time, gender"
                )
            
            # 转换可选参数
            latitude = float(latitude_str) if latitude_str else None
            longitude = float(longitude_str) if longitude_str else None
            
            params = XishenJishenRequest(
                solar_date=solar_date,
                solar_time=solar_time,
                gender=gender,
                calendar_type=calendar_type,
                location=location,
                latitude=latitude,
                longitude=longitude
            )
        
        return StreamingResponse(
            xishen_jishen_stream_generator(params),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Encoding": "identity"  # ⚠️ 关键：禁止 GZip 压缩 SSE 流
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 流式生成异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"流式查询喜神忌神异常: {str(e)}"
        )


# 注册 GET 和 POST 路由（都指向同一个处理函数）
@router.get("/bazi/xishen-jishen/stream", summary="流式生成喜神忌神分析（GET）")
async def xishen_jishen_stream_get(request: Request):
    """GET 方式流式生成喜神忌神分析（用于 EventSource API）"""
    return await _xishen_jishen_stream_handler(request)


@router.post("/bazi/xishen-jishen/stream", summary="流式生成喜神忌神分析（POST）")
async def xishen_jishen_stream_post(request: Request):
    """POST 方式流式生成喜神忌神分析（向后兼容）"""
    return await _xishen_jishen_stream_handler(request)

