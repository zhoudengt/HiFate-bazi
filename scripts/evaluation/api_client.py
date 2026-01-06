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
        except aiohttp.ClientError as e:
            raise RuntimeError(f"API请求失败: {url}, {e}")
    
    async def _post_stream(self, endpoint: str, data: Dict[str, Any]) -> StreamResponse:
        """
        发送POST请求并处理SSE流式响应
        
        Args:
            endpoint: API端点
            data: 请求数据
            
        Returns:
            StreamResponse对象
        """
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        result = StreamResponse()
        progress_chunks = []
        
        try:
            async with session.post(url, json=data) as response:
                response.raise_for_status()
                
                # 读取SSE流
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
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
                            break
                        elif msg_type == 'error':
                            result.error = msg.get('content', '未知错误')
                            break
                    except json.JSONDecodeError:
                        continue
                
                # 如果没有收到complete，使用累积的progress
                if not result.content and progress_chunks:
                    result.content = ''.join(progress_chunks)
                    
        except aiohttp.ClientError as e:
            # 如果已收集到部分内容，保存并标记为不完整
            if progress_chunks:
                result.content = ''.join(progress_chunks) + " [连接中断]"
            else:
                result.error = f"API请求失败: {url}, {e}"
        except asyncio.TimeoutError:
            # 超时时保存已收集的内容
            if progress_chunks:
                result.content = ''.join(progress_chunks) + " [超时]"
            else:
                result.error = f"请求超时: {url}"
        except Exception as e:
            # 其他异常（如TransferEncodingError）
            if progress_chunks:
                result.content = ''.join(progress_chunks) + " [传输中断]"
            else:
                result.error = f"请求异常: {url}, {e}"
        
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
        """调用五行占比流式分析"""
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream(ApiEndpoints.WUXING_PROPORTION_STREAM, data)
    
    async def call_xishen_jishen_stream(self, solar_date: str, solar_time: str,
                                        gender: str) -> StreamResponse:
        """调用喜神忌神流式分析"""
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream(ApiEndpoints.XISHEN_JISHEN_STREAM, data)
    
    async def call_career_wealth_stream(self, solar_date: str, solar_time: str,
                                        gender: str) -> StreamResponse:
        """调用事业财富流式分析"""
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream(ApiEndpoints.CAREER_WEALTH_STREAM, data)
    
    async def call_marriage_analysis_stream(self, solar_date: str, solar_time: str,
                                            gender: str) -> StreamResponse:
        """调用感情婚姻流式分析"""
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream(ApiEndpoints.MARRIAGE_ANALYSIS_STREAM, data)
    
    async def call_health_stream(self, solar_date: str, solar_time: str,
                                 gender: str) -> StreamResponse:
        """调用身体健康流式分析"""
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream(ApiEndpoints.HEALTH_STREAM, data)
    
    async def call_children_study_stream(self, solar_date: str, solar_time: str,
                                         gender: str) -> StreamResponse:
        """调用子女学习流式分析"""
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream(ApiEndpoints.CHILDREN_STUDY_STREAM, data)
    
    async def call_general_review_stream(self, solar_date: str, solar_time: str,
                                         gender: str) -> StreamResponse:
        """调用总评流式分析"""
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream(ApiEndpoints.GENERAL_REVIEW_STREAM, data)
    
    async def call_daily_fortune_calendar_stream(self, solar_date: str, solar_time: str,
                                                  gender: str) -> StreamResponse:
        """调用每日运势流式分析"""
        data = {
            "solar_date": solar_date,
            "solar_time": solar_time,
            "gender": gender
        }
        return await self._post_stream(ApiEndpoints.DAILY_FORTUNE_CALENDAR_STREAM, data)
    
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
    
    @staticmethod
    def generate_user_id() -> str:
        """生成唯一的用户ID（用于评测会话）"""
        return f"eval_{uuid.uuid4().hex[:12]}"

