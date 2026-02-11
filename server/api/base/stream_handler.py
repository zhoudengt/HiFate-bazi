#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式分析接口基类 - 封装 8 步通用流程

所有流式分析接口应继承 BaseAnalysisStreamHandler，仅实现场景特有的：
- get_modules(): 编排层模块配置
- extract_and_validate(): 从 unified_data 提取并验证数据
- get_initial_data_chunk(): 可选，先发送的 data 块（如五行占比的完整数据）
- format_for_llm(): 格式化为 LLM 输入文本
- get_llm_cache_key(): LLM 缓存 key
- get_cached_llm() / set_cached_llm(): 缓存读写（可覆盖默认实现）

详见 standards/11_流式接口开发规范.md
"""

import asyncio
import json
import logging
import time
import traceback
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger(__name__)


def _sse_yield(msg: Dict[str, Any]) -> str:
    """将消息转为 SSE 格式"""
    return f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"


class BaseAnalysisStreamHandler(ABC):
    """
    流式分析接口基类 - 封装 8 步通用流程
    
    子类必须覆盖的类属性：scene, function_type, function_name, frontend_api
    子类必须覆盖的方法：get_modules, extract_and_validate, format_for_llm, get_llm_cache_key
    """
    
    # 子类必须覆盖
    scene: str = ""
    function_type: str = ""
    function_name: str = ""
    frontend_api: str = ""
    
    @abstractmethod
    def get_modules(self, request: Any) -> Dict[str, Any]:
        """返回 BaziDataOrchestrator.fetch_data 的 modules 配置"""
        raise NotImplementedError
    
    @abstractmethod
    def extract_and_validate(
        self,
        unified_data: Dict[str, Any],
        request: Any
    ) -> Any:
        """
        从 unified_data 提取并验证数据，失败时 raise ValueError
        Returns: 提取后的主数据（用于 format_for_llm 和 get_initial_data_chunk）
        """
        raise NotImplementedError
    
    def get_initial_data_chunk(
        self,
        extracted_data: Any,
        conversion_info: Dict[str, Any],
        request: Any
    ) -> Optional[Dict[str, Any]]:
        """
        返回可选的首个 data 块（如五行占比的完整数据）
        默认 None 表示不发送初始数据块
        """
        return None
    
    @abstractmethod
    def format_for_llm(self, extracted_data: Any) -> str:
        """将提取的数据格式化为 LLM 输入文本"""
        raise NotImplementedError
    
    @abstractmethod
    def get_llm_cache_key(self, formatted_text: str, input_data_for_log: Dict) -> str:
        """生成 LLM 缓存 key"""
        raise NotImplementedError
    
    def get_input_data_for_log(
        self,
        extracted_data: Any,
        formatted_text: str
    ) -> Dict[str, Any]:
        """用于交互日志的 input_data，默认返回精简结构"""
        return {"formatted_text": formatted_text, "char_count": len(formatted_text)}
    
    def get_cache_namespace(self) -> str:
        """缓存命名空间，用于 get_cached_result 的 category。子类可覆盖以保持与旧实现兼容"""
        return f"llm-{self.scene}"

    def validate_request(self, request: Any) -> Optional[str]:
        """
        请求前置校验，返回错误消息则提前返回，None 表示通过
        子类可覆盖，如 marriage 需校验 bot_id 配置
        """
        return None
    
    def get_cached_llm(self, key: str) -> Optional[str]:
        """读取 LLM 缓存，返回 None 表示未命中。子类可覆盖以使用不同缓存实现"""
        try:
            from server.utils.api_cache_helper import get_cached_result
            result = get_cached_result(key, self.get_cache_namespace())
            if result and isinstance(result, dict):
                return result.get('content', '')
            return None
        except Exception as e:
            logger.warning(f"[{self.scene}] LLM 缓存读取失败: {e}")
            return None
    
    def set_cached_llm(self, key: str, content: str, ttl: Optional[int] = None) -> None:
        """写入 LLM 缓存。子类可覆盖以使用不同缓存实现"""
        try:
            from server.utils.api_cache_helper import set_cached_result, L2_TTL
            _ttl = ttl if ttl is not None else L2_TTL * 24
            set_cached_result(key, {'content': content}, _ttl)
        except Exception as e:
            logger.warning(f"[{self.scene}] LLM 缓存写入失败: {e}")
    
    async def stream_generator(
        self,
        request: Any,
        bot_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        通用 8 步流式生成器
        
        1. 输入处理
        2. 数据获取（BaziDataOrchestrator）
        3. 数据提取与验证
        4. 可选：发送初始 data 块
        5. LLM 缓存检查
        6. LLM 服务创建与流式生成
        7. SSE 格式化输出
        8. 交互日志
        """
        api_start_time = time.time()
        frontend_input = {
            'solar_date': getattr(request, 'solar_date', ''),
            'solar_time': getattr(request, 'solar_time', ''),
            'gender': getattr(request, 'gender', ''),
            'calendar_type': getattr(request, 'calendar_type', 'solar'),
            'location': getattr(request, 'location'),
            'latitude': getattr(request, 'latitude'),
            'longitude': getattr(request, 'longitude'),
        }
        llm_first_token_time = None
        llm_output_chunks = []
        llm_start_time = None
        actual_bot_id = bot_id
        input_data_for_log = {}
        input_data_gen_start = None
        input_data_gen_end = None
        formatted_text = ''

        try:
            # 0. 前置校验（如 bot_id 配置）
            validation_error = self.validate_request(request)
            if validation_error:
                yield _sse_yield({'type': 'error', 'content': validation_error})
                return
            # 1. 输入处理
            from server.utils.bazi_input_processor import BaziInputProcessor
            final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
                getattr(request, 'solar_date'),
                getattr(request, 'solar_time'),
                getattr(request, 'calendar_type', 'solar') or "solar",
                getattr(request, 'location'),
                getattr(request, 'latitude'),
                getattr(request, 'longitude'),
            )
            
            # 2. 数据获取（计时：input_data 生成开始）
            input_data_gen_start = time.time()
            from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
            modules = self.get_modules(request)
            unified_data = await BaziDataOrchestrator.fetch_data(
                solar_date=final_solar_date,
                solar_time=final_solar_time,
                gender=getattr(request, 'gender'),
                modules=modules,
                use_cache=True,
                parallel=True,
                calendar_type=getattr(request, 'calendar_type', 'solar') or "solar",
                location=getattr(request, 'location'),
                latitude=getattr(request, 'latitude'),
                longitude=getattr(request, 'longitude'),
                preprocessed=True,
            )
            
            # 3. 数据提取与验证
            extracted_data = self.extract_and_validate(unified_data, request)
            
            # 4. 可选：发送初始 data 块
            initial_chunk = self.get_initial_data_chunk(extracted_data, conversion_info, request)
            if initial_chunk is not None:
                yield _sse_yield({'type': 'data', 'content': initial_chunk})
            
            # 5. 格式化与缓存 key（计时：input_data 生成结束）
            formatted_text = self.format_for_llm(extracted_data)
            input_data_for_log = self.get_input_data_for_log(extracted_data, formatted_text)
            input_data_gen_end = time.time()
            llm_cache_key = self.get_llm_cache_key(formatted_text, input_data_for_log)
            
            # 6a. LLM 缓存检查
            cached_content = self.get_cached_llm(llm_cache_key)
            if cached_content:
                logger.info(f"[{self.scene}] LLM 缓存命中: {llm_cache_key[:50]}...")
                chunk_size = 50
                for i in range(0, len(cached_content), chunk_size):
                    chunk = cached_content[i:i + chunk_size]
                    yield _sse_yield({'type': 'progress', 'content': chunk})
                    await asyncio.sleep(0.01)
                yield _sse_yield({'type': 'complete', 'content': ''})
                # 缓存命中也记录
                self._log_stream_call(
                    frontend_input=frontend_input,
                    input_data=formatted_text,
                    llm_output=cached_content,
                    api_start_time=api_start_time,
                    input_data_gen_start=input_data_gen_start,
                    input_data_gen_end=input_data_gen_end,
                    llm_start_time=None,
                    llm_first_token_time=None,
                    actual_bot_id=actual_bot_id,
                    llm_platform=None,
                    status='cache_hit',
                    cache_hit=True,
                )
                return
            
            # 6b. 创建 LLM 服务
            try:
                from server.services.llm_service_factory import LLMServiceFactory
                from server.services.bailian_stream_service import BailianStreamService
                llm_service = LLMServiceFactory.get_service(scene=self.scene, bot_id=actual_bot_id)
            except ValueError:
                yield _sse_yield({'type': 'complete', 'content': ''})
                return
            except Exception:
                yield _sse_yield({'type': 'complete', 'content': ''})
                return
            
            if hasattr(llm_service, 'bot_id') and llm_service.bot_id:
                actual_bot_id = bot_id or llm_service.bot_id
            
            # 判断 LLM 平台
            llm_platform = 'bailian' if isinstance(llm_service, BailianStreamService) else 'coze'
            
            # 7. 流式生成
            llm_start_time = time.time()
            has_content = False
            stream_kwargs = {}
            if hasattr(llm_service, 'bot_id') and llm_service.bot_id:
                stream_kwargs['bot_id'] = actual_bot_id
            
            async for chunk in llm_service.stream_analysis(formatted_text, **stream_kwargs):
                chunk_type = chunk.get('type', 'progress')
                if llm_first_token_time is None and chunk_type == 'progress':
                    llm_first_token_time = time.time()
                
                if chunk_type == 'progress':
                    content = chunk.get('content', '')
                    if content:
                        llm_output_chunks.append(content)
                        has_content = True
                    yield _sse_yield({'type': 'progress', 'content': content})
                    await asyncio.sleep(0)
                elif chunk_type == 'complete':
                    complete_content = chunk.get('content', '')
                    if complete_content:
                        llm_output_chunks.append(complete_content)
                        has_content = True
                    llm_output = ''.join(llm_output_chunks)
                    if has_content and llm_output:
                        self.set_cached_llm(llm_cache_key, llm_output)
                    yield _sse_yield({'type': 'complete', 'content': complete_content})
                    break
                elif chunk_type == 'error':
                    yield _sse_yield({
                        'type': 'error',
                        'content': chunk.get('content', '分析失败')
                    })
                    return
            
            # 8. 记录流式接口调用（成功路径）
            self._log_stream_call(
                frontend_input=frontend_input,
                input_data=formatted_text,
                llm_output=''.join(llm_output_chunks),
                api_start_time=api_start_time,
                input_data_gen_start=input_data_gen_start,
                input_data_gen_end=input_data_gen_end,
                llm_start_time=llm_start_time,
                llm_first_token_time=llm_first_token_time,
                actual_bot_id=actual_bot_id,
                llm_platform=llm_platform,
                status='success' if has_content else 'failed',
            )
            
        except Exception as e:
            yield _sse_yield({
                'type': 'error',
                'content': f"流式生成{self.function_name}失败: {str(e)}\n{traceback.format_exc()}"
            })
            try:
                _bot_id = actual_bot_id
            except NameError:
                _bot_id = bot_id
            self._log_stream_call(
                frontend_input=frontend_input,
                input_data=formatted_text,
                llm_output='',
                api_start_time=api_start_time,
                input_data_gen_start=input_data_gen_start,
                input_data_gen_end=input_data_gen_end,
                llm_start_time=None,
                llm_first_token_time=None,
                actual_bot_id=_bot_id,
                llm_platform=None,
                status='failed',
                error_message=str(e),
            )
    
    def _log_stream_call(
        self,
        frontend_input: Dict,
        input_data: str,
        llm_output: str,
        api_start_time: float,
        input_data_gen_start: Optional[float],
        input_data_gen_end: Optional[float],
        llm_start_time: Optional[float],
        llm_first_token_time: Optional[float],
        actual_bot_id: Optional[str],
        llm_platform: Optional[str],
        status: str,
        error_message: Optional[str] = None,
        cache_hit: bool = False,
    ) -> None:
        """记录流式接口调用日志"""
        try:
            from server.services.stream_call_logger import get_stream_call_logger
            api_end_time = time.time()
            stream_logger = get_stream_call_logger()
            stream_logger.log_async(
                function_type=self.function_type,
                frontend_api=self.frontend_api,
                frontend_input=frontend_input,
                input_data=input_data,
                llm_output=llm_output,
                api_total_ms=int((api_end_time - api_start_time) * 1000),
                input_data_gen_ms=int((input_data_gen_end - input_data_gen_start) * 1000) if input_data_gen_start and input_data_gen_end else None,
                llm_first_token_ms=int((llm_first_token_time - llm_start_time) * 1000) if llm_first_token_time and llm_start_time else None,
                llm_total_ms=int((api_end_time - llm_start_time) * 1000) if llm_start_time else None,
                bot_id=actual_bot_id,
                llm_platform=llm_platform,
                status=status,
                error_message=error_message,
                cache_hit=cache_hit,
            )
        except Exception as log_err:
            logger.warning(f"[{self.scene}] 流式调用日志记录失败: {log_err}", exc_info=True)
