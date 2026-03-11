# -*- coding: utf-8 -*-
"""
百炼平台 API 客户端

封装百炼平台（DashScope）的智能体应用调用，支持流式输出。
接口设计与 Coze 客户端保持一致，便于对比评测。
"""

import os
import sys
import json
import asyncio
import logging
import concurrent.futures
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from .config import BailianConfig, DEFAULT_BAILIAN_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class BailianStreamResponse:
    """
    百炼流式响应结果
    
    与 Coze 的 StreamResponse 保持一致的结构
    """
    data: Optional[Dict[str, Any]] = None  # 完整数据
    content: str = ""                       # 完整内容
    error: Optional[str] = None            # 错误信息


class BailianClient:
    """
    百炼平台 API 客户端
    
    使用 DashScope SDK 调用百炼智能体应用，支持流式输出。
    """
    
    def __init__(self, config: BailianConfig = None):
        """
        初始化百炼客户端
        
        Args:
            config: 百炼平台配置，如果为 None 则使用默认配置
        """
        self.config = config or DEFAULT_BAILIAN_CONFIG
        
        if not self.config.api_key:
            raise ValueError("百炼平台 API Key 未配置，请设置 DASHSCOPE_API_KEY 环境变量或在配置中提供")
        
        # 设置 DashScope API Key
        self._setup_dashscope()
    
    def _setup_dashscope(self):
        """设置 DashScope SDK"""
        try:
            import dashscope
            
            # 设置 dashscope 日志级别为 WARNING，避免其内部日志调用可能的参数问题
            # 修复: Logger._log() got an unexpected keyword argument 'flush'
            logging.getLogger("dashscope").setLevel(logging.WARNING)
            
            dashscope.api_key = self.config.api_key
            self._dashscope = dashscope
            logger.info("百炼平台 SDK 初始化成功")
        except ImportError:
            logger.error("未安装 dashscope SDK，请运行: pip install dashscope")
            raise ImportError("请安装 dashscope SDK: pip install dashscope")
    
    async def call_stream(
        self,
        app_id: str,
        prompt: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式调用百炼智能体应用（优化版：线程队列模式）
        
        使用后台线程迭代 DashScope 响应，通过 asyncio.Queue 传递到主线程，
        实现真正的异步流式响应，降低首 token 延迟。
        
        Args:
            app_id: 智能体应用 ID
            prompt: 用户输入的提示词
            session_id: 会话 ID（用于多轮对话）
            **kwargs: 其他参数
            
        Yields:
            dict: 包含 type 和 content 的字典
                - type: 'progress' 或 'complete' 或 'error'
                - content: 内容文本
        """
        from dashscope import Application
        
        logger.info(f"🚀 调用百炼智能体: app_id={app_id}, prompt长度={len(prompt)}")
        
        # 创建异步队列用于线程间通信
        queue: asyncio.Queue = asyncio.Queue()
        DONE_SENTINEL = object()  # 结束标记
        
        # 构建请求参数
        call_params = {
            "app_id": app_id,
            "prompt": prompt,
            "stream": True,
            "incremental_output": True,  # 增量输出
        }
        
        if session_id:
            call_params["session_id"] = session_id
        
        # 获取当前事件循环
        loop = asyncio.get_event_loop()
        
        def sync_iterate():
            """
            在后台线程中执行同步迭代
            
            将每个响应通过队列传递到主线程，实现真正的异步流式响应。
            """
            buffer = ""
            has_content = False
            
            try:
                # 调用 DashScope API（返回迭代器）
                responses = Application.call(**call_params)
                
                # 在后台线程中迭代响应
                for response in responses:
                    if response.status_code != 200:
                        error_msg = f"百炼 API 错误: {response.code} - {response.message}"
                        logger.error(f"❌ {error_msg}")
                        asyncio.run_coroutine_threadsafe(
                            queue.put({'type': 'error', 'content': error_msg}),
                            loop
                        ).result(timeout=5)
                        return
                    
                    # 提取输出内容
                    output = response.output
                    if output:
                        text = output.get('text', '')
                        if text:
                            # 增量内容
                            new_content = text[len(buffer):] if text.startswith(buffer) else text
                            if new_content:
                                has_content = True
                                buffer = text
                                # 将响应放入队列
                                asyncio.run_coroutine_threadsafe(
                                    queue.put({'type': 'progress', 'content': new_content}),
                                    loop
                                ).result(timeout=5)
                
                # 流结束，发送完成标记
                if has_content:
                    asyncio.run_coroutine_threadsafe(
                        queue.put({'type': 'complete', 'content': ''}),
                        loop
                    ).result(timeout=5)
                else:
                    asyncio.run_coroutine_threadsafe(
                        queue.put({'type': 'error', 'content': '百炼 API 返回空内容'}),
                        loop
                    ).result(timeout=5)
                    
            except Exception as e:
                error_msg = f"百炼 API 调用异常: {str(e)}"
                logger.error(f"❌ {error_msg}")
                try:
                    asyncio.run_coroutine_threadsafe(
                        queue.put({'type': 'error', 'content': error_msg}),
                        loop
                    ).result(timeout=5)
                except Exception:
                    pass  # 忽略队列放入失败
            finally:
                # 总是发送结束标记
                try:
                    asyncio.run_coroutine_threadsafe(
                        queue.put(DONE_SENTINEL),
                        loop
                    ).result(timeout=5)
                except Exception:
                    pass
        
        # 启动后台线程执行迭代
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(sync_iterate)
        
        try:
            # 异步从队列获取响应
            while True:
                item = await queue.get()
                
                # 检查是否结束
                if item is DONE_SENTINEL:
                    break
                
                # 直接 yield 响应
                yield item
                
                # 如果是错误或完成，退出循环
                if item.get('type') in ('error', 'complete'):
                    break
        finally:
            # 清理线程池
            executor.shutdown(wait=False)
    
    async def call_with_image(
        self,
        app_id: str,
        prompt: str,
        image_base64: str,
        image_format: str = 'jpeg',
    ) -> str:
        """
        调用百炼多模态智能体（Qwen-VL），传入 base64 图片，返回完整文本。

        Args:
            app_id: 百炼应用 ID（需配置为 Qwen-VL 系列模型）
            prompt: 文本提示词
            image_base64: 图片 base64 编码（不含 data URI 前缀）
            image_format: 图片格式，默认 jpeg

        Returns:
            模型返回的完整文本

        Raises:
            ValueError: 调用失败或返回空内容
        """
        from dashscope import Application

        loop = asyncio.get_event_loop()

        def _call():
            messages = [{
                "role": "user",
                "content": [
                    {"image": f"data:image/{image_format};base64,{image_base64}"},
                    {"text": prompt},
                ],
            }]

            response = Application.call(
                app_id=app_id,
                messages=messages,
                stream=False,
            )

            if response.status_code != 200:
                raise ValueError(
                    f"百炼视觉应用调用失败: {response.status_code} "
                    f"{getattr(response, 'code', '')} - {getattr(response, 'message', '')}"
                )

            output = response.output
            if not output:
                raise ValueError("百炼视觉应用返回空 output")

            text = output.get('text', '')
            if not text:
                raise ValueError(f"百炼视觉应用返回空文本，output={output}")

            return text

        return await loop.run_in_executor(None, _call)

    async def call_sync(
        self,
        app_id: str,
        prompt: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> BailianStreamResponse:
        """
        同步调用百炼智能体应用（一次性返回完整结果）
        
        Args:
            app_id: 智能体应用 ID
            prompt: 用户输入的提示词
            session_id: 会话 ID（用于多轮对话）
            **kwargs: 其他参数
            
        Returns:
            BailianStreamResponse 对象
        """
        result = BailianStreamResponse()
        content_parts = []
        
        async for chunk in self.call_stream(app_id, prompt, session_id, **kwargs):
            chunk_type = chunk.get('type', '')
            chunk_content = chunk.get('content', '')
            
            if chunk_type == 'error':
                result.error = chunk_content
                break
            elif chunk_type == 'progress':
                content_parts.append(chunk_content)
            elif chunk_type == 'complete':
                if chunk_content:
                    content_parts.append(chunk_content)
        
        result.content = ''.join(content_parts)
        return result
    
    # ==================== 便捷方法：各场景调用 ====================
    
    async def call_wuxing_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用五行解析"""
        app_id = self.config.get_app_id("wuxing_proportion")
        async for chunk in self.call_stream(app_id, prompt, **kwargs):
            yield chunk
    
    async def call_xishen_jishen_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用喜神忌神分析"""
        app_id = self.config.get_app_id("xishen_jishen")
        async for chunk in self.call_stream(app_id, prompt, **kwargs):
            yield chunk
    
    async def call_career_wealth_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用事业财富分析"""
        app_id = self.config.get_app_id("career_wealth")
        async for chunk in self.call_stream(app_id, prompt, **kwargs):
            yield chunk
    
    async def call_marriage_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用感情婚姻分析"""
        app_id = self.config.get_app_id("marriage")
        async for chunk in self.call_stream(app_id, prompt, **kwargs):
            yield chunk
    
    async def call_health_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用身体健康分析"""
        app_id = self.config.get_app_id("health")
        async for chunk in self.call_stream(app_id, prompt, **kwargs):
            yield chunk
    
    async def call_children_study_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用子女学习分析"""
        app_id = self.config.get_app_id("children_study")
        async for chunk in self.call_stream(app_id, prompt, **kwargs):
            yield chunk
    
    async def call_general_review_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用总评分析"""
        app_id = self.config.get_app_id("general_review")
        async for chunk in self.call_stream(app_id, prompt, **kwargs):
            yield chunk
    
    async def call_daily_fortune_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用每日运势分析"""
        app_id = self.config.get_app_id("daily_fortune")
        async for chunk in self.call_stream(app_id, prompt, **kwargs):
            yield chunk
    
    async def call_qa_question_generate_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用 QA 问题生成"""
        app_id = self.config.get_app_id("qa_question_generate")
        async for chunk in self.call_stream(app_id, prompt, **kwargs):
            yield chunk
    
    async def call_qa_analysis_stream(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用 QA 命理分析"""
        app_id = self.config.get_app_id("qa_analysis")
        async for chunk in self.call_stream(app_id, prompt, **kwargs):
            yield chunk


# ==================== 测试代码 ====================

async def _test_client():
    """测试百炼客户端"""
    print("=" * 60)
    print("百炼平台客户端测试")
    print("=" * 60)
    
    try:
        client = BailianClient()
        
        # 测试事业财富分析
        print("\n测试事业财富分析...")
        test_prompt = """
请分析以下八字的事业财富运势：

八字信息：
- 出生日期：1990年5月15日 10:00
- 性别：男
- 日主：甲木

请给出详细的事业财富分析。
"""
        
        async for chunk in client.call_career_wealth_stream(test_prompt):
            chunk_type = chunk.get('type', '')
            chunk_content = chunk.get('content', '')
            
            if chunk_type == 'progress':
                print(chunk_content, end='', flush=True)
            elif chunk_type == 'complete':
                print("\n\n[分析完成]")
            elif chunk_type == 'error':
                print(f"\n[错误] {chunk_content}")
        
        print("\n" + "=" * 60)
        print("测试完成")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(_test_client())

