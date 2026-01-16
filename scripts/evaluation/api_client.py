# -*- coding: utf-8 -*-
"""
API客户端

封装所有API调用，支持普通请求和流式请求。
"""

import json
import asyncio
import aiohttp
import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass

from .config import EvaluationConfig, ApiEndpoints, DEFAULT_CONFIG


@dataclass
class StreamResponse:
    """流式响应结果"""
    data: Optional[Dict[str, Any]] = None  # type=data 的完整数据
    content: str = ""                       # type=complete 的完整内容
    error: Optional[str] = None            # 错误信息


class BaziApiClient:
    """八字API客户端"""
    
    def __init__(self, config: EvaluationConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.base_url = self.config.full_api_url
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self.config.stream_timeout,
                connect=30
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """关闭HTTP会话"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _post_json(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送POST JSON请求
        
        Args:
            endpoint: API端点
            data: 请求数据
            
        Returns:
            响应JSON数据
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with session.post(url, json=data) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            raise RuntimeError(f"API请求失败: {url}, {e.status}, message='{e.message}'")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"API请求失败: {url}, {e}")
    
    async def _post_grpc(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        通过 gRPC 网关发送请求
        
        用于调用可能未在 REST 路由中注册但在 gRPC 网关中动态注册的端点。
        
        Args:
            endpoint: API端点（不含 /api/v1 前缀）
            data: 请求数据
            
        Returns:
            响应JSON数据
        """
        import struct
        
        session = await self._get_session()
        grpc_url = f"{self.base_url}/grpc-web/frontend.gateway.FrontendGateway/Call"
        
        # 构建 gRPC-Web 请求 payload
        payload_json = json.dumps(data, ensure_ascii=False)
        
        # 简单的 protobuf 编码：field 1 = endpoint, field 2 = payload_json
        # field 1 (string): tag = 0x0a, length-prefixed
        # field 2 (string): tag = 0x12, length-prefixed
        endpoint_bytes = endpoint.encode('utf-8')
        payload_bytes = payload_json.encode('utf-8')
        
        def encode_varint(value):
            result = b''
            while value > 127:
                result += bytes([0x80 | (value & 0x7f)])
                value >>= 7
            result += bytes([value])
            return result
        
        message = b'\x0a' + encode_varint(len(endpoint_bytes)) + endpoint_bytes
        message += b'\x12' + encode_varint(len(payload_bytes)) + payload_bytes
        
        # gRPC-Web 帧格式：1 字节标志 + 4 字节长度 + 消息
        frame = b'\x00' + struct.pack('>I', len(message)) + message
        
        headers = {
            'Content-Type': 'application/grpc-web+proto',
            'X-Grpc-Web': '1'
        }
        
        try:
            async with session.post(grpc_url, data=frame, headers=headers) as response:
                if response.status == 404:
                    raise RuntimeError(f"gRPC端点未找到: {endpoint}")
                
                body = await response.read()
                
                # 解析 gRPC-Web 响应
                # 跳过 gRPC 帧头（5 字节）
                if len(body) > 5:
                    json_body = body[5:].decode('utf-8')
                    return json.loads(json_body)
                else:
                    raise RuntimeError(f"gRPC响应格式错误: {body}")
        except aiohttp.ClientResponseError as e:
            raise RuntimeError(f"gRPC请求失败: {grpc_url}, {e.status}, message='{e.message}'")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"gRPC请求失败: {grpc_url}, {e}")
    
    async def _post_stream(self, endpoint: str, data: Dict[str, Any], 
                           retry_count: int = 0) -> StreamResponse:
        """
        发送POST请求并处理SSE流式响应（增强版）
        
        改进：
        1. 使用更稳健的流式读取方式（iter_chunked + readline）
        2. 增强异常处理，特别是针对 TransferEncodingError
        3. 支持部分内容保存
        
        Args:
            endpoint: API端点
            data: 请求数据
            retry_count: 重试次数（内部使用）
            
        Returns:
            StreamResponse对象
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        result = StreamResponse()
        progress_chunks = []
        buffer = b''  # 字节缓冲区
        
        try:
            async with session.post(url, json=data) as response:
                response.raise_for_status()
                
                # 改进的流式读取方式：使用 iter_chunked 而不是直接迭代
                # 这样更稳健地处理 chunked transfer encoding
                try:
                    async for chunk in response.content.iter_chunked(8192):
                        if not chunk:
                            continue
                        
                        buffer += chunk
                        
                        # 处理完整的行（SSE格式）
                        while b'\n' in buffer:
                            line_bytes, buffer = buffer.split(b'\n', 1)
                            try:
                                line = line_bytes.decode('utf-8').strip()
                            except UnicodeDecodeError:
                                # 跳过无法解码的行
                                continue
                            
                            if not line or not line.startswith('data:'):
                                continue
                            
                            # 解析SSE数据
                            json_str = line[5:].strip()  # 移除 "data:" 前缀
                            if not json_str:
                                continue
                            
                            try:
                                msg = json.loads(json_str)
                                msg_type = msg.get('type', '')
                                
                                if msg_type == 'data':
                                    # 完整数据
                                    result.data = msg.get('content', {})
                                elif msg_type == 'progress':
                                    # 进度内容
                                    progress_chunks.append(msg.get('content', ''))
                                elif msg_type == 'complete':
                                    # 完成，获取完整内容
                                    result.content = msg.get('content', '')
                                    if not result.content and progress_chunks:
                                        # 如果complete没有内容，使用累积的progress
                                        result.content = ''.join(progress_chunks)
                                    return result  # 成功完成
                                elif msg_type == 'error':
                                    result.error = msg.get('content', '未知错误')
                                    return result
                            except json.JSONDecodeError:
                                continue
                    
                    # 流结束，处理剩余的 buffer
                    if buffer:
                        try:
                            line = buffer.decode('utf-8').strip()
                            if line.startswith('data:'):
                                json_str = line[5:].strip()
                                if json_str:
                                    msg = json.loads(json_str)
                                    msg_type = msg.get('type', '')
                                    if msg_type == 'complete':
                                        result.content = msg.get('content', '')
                                    elif msg_type == 'progress':
                                        progress_chunks.append(msg.get('content', ''))
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            pass
                    
                    # 如果没有收到complete，使用累积的progress
                    if not result.content and progress_chunks:
                        result.content = ''.join(progress_chunks)
                
                except (aiohttp.ClientPayloadError, aiohttp.ServerDisconnectedError) as e:
                    # 传输错误：连接中断或 payload 错误
                    # 保存已收到的部分内容
                    if progress_chunks:
                        result.content = ''.join(progress_chunks) + " [传输中断]"
                        # 如果有部分内容，不抛出异常，返回结果
                        return result
                    else:
                        # 没有收到任何内容，抛出异常以便重试
                        raise
                    
        except (aiohttp.ClientPayloadError, aiohttp.ServerDisconnectedError) as e:
            # 传输层面的错误（如 TransferEncodingError）
            # 如果已收集到部分内容，保存并标记为不完整
            if progress_chunks:
                result.content = ''.join(progress_chunks) + " [传输中断]"
                return result
            else:
                # 没有收到任何内容，记录错误以便重试
                result.error = f"传输错误: {url}, {e}"
                return result
                    
        except aiohttp.ClientError as e:
            # 客户端错误
            if progress_chunks:
                result.content = ''.join(progress_chunks) + " [连接中断]"
            else:
                result.error = f"API请求失败: {url}, {e}"
        except asyncio.TimeoutError:
            # 超时
            if progress_chunks:
                result.content = ''.join(progress_chunks) + " [超时]"
            else:
                result.error = f"请求超时: {url}"
        except Exception as e:
            # 其他异常
            error_name = type(e).__name__
            if progress_chunks:
                result.content = ''.join(progress_chunks) + f" [异常: {error_name}]"
            else:
                result.error = f"请求异常: {url}, {error_name}: {e}"
        
        # 最终空内容检测：如果结果完全为空，记录详细错误信息
        if not result.content and not result.data and not result.error:
            # 检查是否真的没有收到任何数据
            if not progress_chunks:
                result.error = f"API 返回空内容（未收到任何数据）: {url}"
            else:
                # 有 progress_chunks 但最终 content 为空，可能是解析问题
                result.error = f"API 返回空内容（收到数据但无法解析，共 {len(progress_chunks)} 个片段）: {url}"
        
        return result
    
    async def _post_stream_with_retry(
        self,
        endpoint: str,
        data: Dict[str, Any],
        max_retries: int = 3,
        min_content_length: int = 100
    ) -> StreamResponse:
        """
        带重试的流式接口调用（通用方法）
        
        所有流式接口都可以使用此方法，自动处理传输错误和空内容问题。
        参考总评接口的重试逻辑，提供统一的重试机制。
        
        Args:
            endpoint: API端点
            data: 请求数据
            max_retries: 最大重试次数（默认3次）
            min_content_length: 最小内容长度，低于此长度认为是空内容（默认100字符）
            
        Returns:
            StreamResponse对象
        """
        last_error = None
        best_result = None  # 保存最佳结果（有部分内容的）
        
        for attempt in range(max_retries):
            try:
                result = await self._post_stream(endpoint, data)
                
                # 如果成功获取完整内容，直接返回
                if result.content and len(result.content) >= min_content_length and not result.error:
                    return result
                
                # 如果收到完整数据，直接返回
                if result.data:
                    return result
                
                # 如果有部分内容（长度足够），保存为最佳结果
                if result.content and len(result.content) >= min_content_length:
                    if best_result is None or len(result.content) > len(best_result.content):
                        best_result = result
                
                # 如果有错误，记录错误信息
                if result.error:
                    last_error = result.error
                    # 如果不是传输错误或空内容，不重试（如认证错误、参数错误等）
                    should_retry = (
                        '传输错误' in result.error or 
                        '传输中断' in result.error or 
                        '连接中断' in result.error or
                        '超时' in result.error or
                        '返回空内容' in result.error
                    )
                    if not should_retry:
                        return result
                
                # 如果内容为空但长度小于最小值，可能是空内容问题，可以重试
                if not result.content or len(result.content) < min_content_length:
                    if not last_error:
                        last_error = f"API 返回空内容或内容过短（{len(result.content) if result.content else 0}字符）"
                
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)}"
                # 如果是传输相关错误，继续重试
                if 'TransferEncoding' not in last_error and 'Payload' not in last_error and 'ServerDisconnected' not in last_error:
                    # 非传输错误，不重试
                    result = StreamResponse()
                    result.error = last_error
                    return result
            
            # 准备重试
            if attempt < max_retries - 1:
                # 指数退避：1秒、2秒、4秒
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
        
        # 所有重试都失败
        if best_result and best_result.content:
            # 如果有部分内容，返回部分内容
            return best_result
        
        # 完全没有内容，返回错误
        result = StreamResponse()
        result.error = f"接口调用失败（已重试 {max_retries} 次）: {last_error or '未知错误'}"
        return result
    
    async def _get_stream(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送GET请求并处理SSE流式响应（用于smart-analyze-stream）
        
        SSE格式：
        event: <event_type>
        data: <json_data>
        
        Args:
            endpoint: API端点
            params: 查询参数
            
        Returns:
            解析后的响应数据
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        result = {
            'brief_response': '',
            'preset_questions': [],
            'llm_response': '',
            'related_questions': [],
            'error': None
        }
        
        brief_chunks = []
        llm_chunks = []
        current_event = None
        
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line:
                        continue
                    
                    # 解析SSE格式：event: xxx 或 data: xxx
                    if line.startswith('event:'):
                        current_event = line[6:].strip()
                        continue
                    
                    if line.startswith('data:'):
                        json_str = line[5:].strip()
                        if not json_str:
                            continue
                        
                        try:
                            data = json.loads(json_str)
                            
                            # 使用当前事件类型处理数据
                            event_type = current_event or ''
                            
                            if event_type == 'brief_response_chunk':
                                content = data.get('content', '') if isinstance(data, dict) else ''
                                brief_chunks.append(content)
                            elif event_type == 'preset_questions':
                                questions = data.get('questions', []) if isinstance(data, dict) else []
                                result['preset_questions'] = questions
                            elif event_type == 'llm_chunk':
                                content = data.get('content', '') if isinstance(data, dict) else ''
                                llm_chunks.append(content)
                            elif event_type == 'related_questions':
                                questions = data.get('questions', []) if isinstance(data, dict) else []
                                result['related_questions'] = questions
                            elif event_type == 'error':
                                message = data.get('message', '未知错误') if isinstance(data, dict) else str(data)
                                result['error'] = message
                            elif event_type == 'end':
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                result['brief_response'] = ''.join(brief_chunks)
                result['llm_response'] = ''.join(llm_chunks)
                
        except aiohttp.ClientError as e:
            result['error'] = f"API请求失败: {e}"
        except asyncio.TimeoutError:
            result['error'] = "请求超时"
            result['brief_response'] = ''.join(brief_chunks)
            result['llm_response'] = ''.join(llm_chunks)
        
        return result
    
    # ==================== 具体API调用方法 ====================
    
    async def call_bazi_data(self, solar_date: str, solar_time: str, 
                              gender: str) -> Dict[str, Any]:
        """
        调用统一数据接口获取基础八字数据
        
        Returns:
            包含完整八字数据的字典（bazi, wangshuai, xishen_jishen, dayun, liunian等）
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender,
            "modules": {
                "bazi": True,
                "wangshuai": True,
                "xishen_jishen": True,
                "dayun": {"mode": "count", "count": 8},  # 8步大运，每步包含完整流年
                "liunian": True,  # 包含完整流年数据
                "rules": {"types": ["shishen"]}
            },
            "use_cache": True,
            "parallel": True
        }
        return await self._post_json(ApiEndpoints.BAZI_DATA, data)
    
    async def call_rizhu_liujiazi(self, solar_date: str, solar_time: str, 
                                   gender: str) -> Dict[str, Any]:
        """
        调用日元-六十甲子接口
        
        Returns:
            包含日柱解析的字典
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_json(ApiEndpoints.RIZHU_LIUJIAZI, data)
    
    async def call_wuxing_proportion_stream(self, solar_date: str, solar_time: str,
                                            gender: str) -> StreamResponse:
        """
        调用五行占比流式分析（带重试机制）
        
        使用重试机制提高成功率，预防传输错误。
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream_with_retry(ApiEndpoints.WUXING_PROPORTION_STREAM, data, max_retries=3)
    
    async def call_xishen_jishen_stream(self, solar_date: str, solar_time: str,
                                        gender: str) -> StreamResponse:
        """
        调用喜神忌神流式分析（带重试机制）
        
        容易出现传输错误，使用重试机制提高成功率。
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream_with_retry(ApiEndpoints.XISHEN_JISHEN_STREAM, data, max_retries=3)
    
    async def call_career_wealth_stream(self, solar_date: str, solar_time: str,
                                        gender: str) -> StreamResponse:
        """
        调用事业财富流式分析（带重试机制）
        
        使用重试机制提高成功率，预防传输错误。
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream_with_retry(ApiEndpoints.CAREER_WEALTH_STREAM, data, max_retries=3)
    
    async def call_marriage_analysis_stream(self, solar_date: str, solar_time: str,
                                            gender: str) -> StreamResponse:
        """
        调用感情婚姻流式分析（带重试机制）
        
        容易出现传输错误，使用重试机制提高成功率。
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream_with_retry(ApiEndpoints.MARRIAGE_ANALYSIS_STREAM, data, max_retries=3)
    
    async def call_health_stream(self, solar_date: str, solar_time: str,
                                 gender: str) -> StreamResponse:
        """
        调用身体健康流式分析（带重试机制）
        
        使用重试机制提高成功率，预防传输错误。
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream_with_retry(ApiEndpoints.HEALTH_STREAM, data, max_retries=3)
    
    async def call_children_study_stream(self, solar_date: str, solar_time: str,
                                         gender: str) -> StreamResponse:
        """
        调用子女学习流式分析（带重试机制）
        
        容易出现传输错误，使用重试机制提高成功率。
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream_with_retry(ApiEndpoints.CHILDREN_STUDY_STREAM, data, max_retries=3)
    
    async def call_general_review_stream(self, solar_date: str, solar_time: str,
                                         gender: str) -> StreamResponse:
        """
        调用总评流式分析（带重试机制）
        
        总评接口响应时间长，容易出现传输错误（如 TransferEncodingError），
        使用通用重试机制提高成功率。
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            
        Returns:
            StreamResponse对象
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream_with_retry(ApiEndpoints.GENERAL_REVIEW_STREAM, data, max_retries=3)
    
    async def call_daily_fortune_calendar_stream(self, solar_date: str, solar_time: str,
                                                  gender: str) -> StreamResponse:
        """
        调用每日运势流式分析（带重试机制）
        
        使用重试机制提高成功率，预防传输错误。
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream_with_retry(ApiEndpoints.DAILY_FORTUNE_CALENDAR_STREAM, data, max_retries=3)
    
    async def call_smart_analyze_scenario1(self, year: int, month: int, day: int,
                                           hour: int, gender: str, category: str,
                                           user_id: str) -> Dict[str, Any]:
        """
        调用智能问答场景1（选择业务分类）
        
        Returns:
            包含 brief_response 和 preset_questions 的字典
        """
        params = {
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "gender": gender,
            "category": category,
            "user_id": user_id
        }
        return await self._get_stream(ApiEndpoints.SMART_ANALYZE_STREAM, params)
    
    async def call_smart_analyze_scenario2(self, category: str, question: str,
                                           user_id: str) -> Dict[str, Any]:
        """
        调用智能问答场景2（问答）
        
        Returns:
            包含 llm_response 和 related_questions 的字典
        """
        params = {
            "category": category,
            "question": question,
            "user_id": user_id
        }
        return await self._get_stream(ApiEndpoints.SMART_ANALYZE_STREAM, params)
    
    async def call_bazi_rules_match(self, solar_date: str, solar_time: str,
                                    gender: str, rule_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        调用八字规则匹配接口
        
        Args:
            solar_date: 公历日期 YYYY-MM-DD
            solar_time: 公历时间 HH:MM
            gender: 性别 male/female
            rule_types: 规则类型列表，如 ["wealth", "career"]
            
        Returns:
            包含匹配规则的字典
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender,
            "rule_types": rule_types,
            "include_bazi": False  # 不需要完整八字数据，只匹配规则
        }
        return await self._post_json("/bazi/rules/match", data)
    
    # ==================== 测试接口调用（获取 formatted_data）====================
    # 这些接口返回与 Coze 相同的结构化数据，用于百炼平台统一输入
    
    async def call_career_wealth_test(self, solar_date: str, solar_time: str,
                                      gender: str) -> Dict[str, Any]:
        """
        调用事业财富测试接口，获取 formatted_data
        
        Returns:
            包含 success, formatted_data 的字典
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_json(ApiEndpoints.CAREER_WEALTH_TEST, data)
    
    async def call_general_review_test(self, solar_date: str, solar_time: str,
                                       gender: str) -> Dict[str, Any]:
        """
        调用总评测试接口，获取 formatted_data
        
        Returns:
            包含 success, formatted_data 的字典
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_json(ApiEndpoints.GENERAL_REVIEW_TEST, data)
    
    async def call_marriage_analysis_test(self, solar_date: str, solar_time: str,
                                          gender: str) -> Dict[str, Any]:
        """
        调用感情婚姻测试接口，获取 formatted_data
        
        Returns:
            包含 success, formatted_data 的字典
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_json(ApiEndpoints.MARRIAGE_ANALYSIS_TEST, data)
    
    async def call_health_analysis_test(self, solar_date: str, solar_time: str,
                                        gender: str) -> Dict[str, Any]:
        """
        调用身体健康测试接口，获取 formatted_data
        
        Returns:
            包含 success, formatted_data 的字典
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_json(ApiEndpoints.HEALTH_ANALYSIS_TEST, data)
    
    async def call_children_study_test(self, solar_date: str, solar_time: str,
                                       gender: str) -> Dict[str, Any]:
        """
        调用子女学习测试接口，获取 formatted_data
        
        Returns:
            包含 success, formatted_data 的字典
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_json(ApiEndpoints.CHILDREN_STUDY_TEST, data)
    
    async def call_annual_report_test(self, solar_date: str, solar_time: str,
                                      gender: str) -> Dict[str, Any]:
        """
        调用年运报告测试接口，获取 formatted_data
        
        Returns:
            包含 success, formatted_data 的字典
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_json(ApiEndpoints.ANNUAL_REPORT_TEST, data)
    
    async def call_wuxing_proportion_test(self, solar_date: str, solar_time: str,
                                           gender: str) -> Dict[str, Any]:
        """
        调用五行占比测试接口，获取 formatted_data
        
        优先尝试 REST 接口，失败时回退到 gRPC 网关。
        
        Returns:
            包含 success, formatted_data 的字典
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        try:
            return await self._post_json(ApiEndpoints.WUXING_PROPORTION_TEST, data)
        except RuntimeError as e:
            if "404" in str(e):
                # REST 接口不可用，尝试 gRPC 网关
                return await self._post_grpc(ApiEndpoints.WUXING_PROPORTION_TEST, data)
            raise
    
    async def call_xishen_jishen_test(self, solar_date: str, solar_time: str,
                                       gender: str) -> Dict[str, Any]:
        """
        调用喜神忌神测试接口，获取 formatted_data
        
        优先尝试 REST 接口，失败时回退到 gRPC 网关。
        
        Returns:
            包含 success, formatted_data 的字典
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        try:
            return await self._post_json(ApiEndpoints.XISHEN_JISHEN_TEST, data)
        except RuntimeError as e:
            if "404" in str(e):
                # REST 接口不可用，尝试 gRPC 网关
                return await self._post_grpc(ApiEndpoints.XISHEN_JISHEN_TEST, data)
            raise
    
    async def call_daily_fortune_calendar_test(self, solar_date: str, solar_time: str,
                                                gender: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        调用每日运势测试接口，获取 formatted_data
        
        优先尝试 REST 接口，失败时回退到 gRPC 网关。
        
        Args:
            solar_date: 用户生辰阳历日期（可选）
            solar_time: 用户生辰时间（可选）
            gender: 用户性别（可选）
            date: 查询日期（可选，默认为今天）
        
        Returns:
            包含 success, formatted_data 的字典
        """
        data = {}
        if solar_date:
            data["solar_date"] = solar_date
        if solar_time:
            data["solar_time"] = solar_time
        if gender:
            data["gender"] = gender
        if date:
            data["date"] = date
        try:
            return await self._post_json(ApiEndpoints.DAILY_FORTUNE_CALENDAR_TEST, data)
        except RuntimeError as e:
            if "404" in str(e):
                # REST 接口不可用，尝试 gRPC 网关
                return await self._post_grpc(ApiEndpoints.DAILY_FORTUNE_CALENDAR_TEST, data)
            raise
    
    @staticmethod
    def generate_user_id() -> str:
        """生成唯一的用户ID（用于评测会话）"""
        return f"eval_{uuid.uuid4().hex[:12]}"

