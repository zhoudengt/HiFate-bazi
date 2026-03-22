# -*- coding: utf-8 -*-
"""
API客户端

封装所有API调用，支持普通请求和流式请求。
"""

import json
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
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
    
    # ==================== 具体API调用方法 ====================
    
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
    
    async def call_bazi_rules_match(self, solar_date: str, solar_time: str,
                                    gender: str, rule_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        调用八字规则匹配接口
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender,
            "rule_types": rule_types,
            "include_bazi": False
        }
        return await self._post_json("/bazi/rules/match", data)
    
    async def call_annual_report_stream(self, solar_date: str, solar_time: str,
                                        gender: str, year: Optional[int] = None) -> StreamResponse:
        """
        调用年运报告流式分析（带重试机制）
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            year: 目标年份（可选，默认使用服务端数据库配置）
            
        Returns:
            StreamResponse对象
        """
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        if year is not None:
            data["year"] = year
        return await self._post_stream_with_retry(ApiEndpoints.ANNUAL_REPORT_STREAM, data, max_retries=3)

