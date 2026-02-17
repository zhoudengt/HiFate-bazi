# -*- coding: utf-8 -*-
"""
SSE 流式响应收集器

将流式生成器的输出收集为统一的响应格式。
"""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def collect_sse_stream(generator) -> Dict[str, Any]:
    """
    收集 SSE 流式响应的所有数据

    将流式生成器的输出收集为统一的响应格式：
    - 收集所有 brief_response_chunk 内容到 stream_content
    - 收集 preset_questions 到 data
    - 收集 performance 到 data
    - 捕获 error 消息

    Args:
        generator: 流式生成器

    Returns:
        Dict: 包含 success, data, stream_content, error 的响应字典
    """
    data_content = {}
    stream_contents = []
    error_content = None
    current_event_type = None

    try:
        chunk_count = 0
        async for chunk in generator:
            chunk_count += 1
            if not chunk:
                continue

            chunk_str = chunk if isinstance(chunk, str) else chunk.decode('utf-8')
            lines = chunk_str.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith('event:'):
                    current_event_type = line[6:].strip()
                    logger.debug(f"[collect_sse_stream] 收到事件: {current_event_type}")
                    continue

                if line.startswith('data:'):
                    json_str = line[5:].strip()
                    if not json_str:
                        continue

                    try:
                        msg = json.loads(json_str)
                        msg_type = msg.get('type')
                        if msg_type:
                            event_type_to_use = msg_type
                            logger.debug(f"[collect_sse_stream] 从消息中提取类型: {event_type_to_use}")
                        else:
                            event_type_to_use = current_event_type
                            logger.debug(f"[collect_sse_stream] 使用 event 行类型: {event_type_to_use}")

                        if event_type_to_use == 'data':
                            content = msg.get('content', {})
                            if content:
                                data_content['data'] = content
                                logger.debug(f"[collect_sse_stream] 保存数据消息: {type(content)}")

                        elif event_type_to_use == 'progress' or event_type_to_use in ('brief_response_chunk', 'llm_chunk'):
                            content = msg.get('content', '')
                            if content:
                                stream_contents.append(content)
                                logger.debug(f"[collect_sse_stream] 收集到流式内容块: {len(content)} 字符")

                        elif event_type_to_use == 'complete' or event_type_to_use == 'brief_response_end':
                            if event_type_to_use == 'complete':
                                content = msg.get('content', '')
                                if content:
                                    stream_contents.append(content)
                                    logger.debug(f"[collect_sse_stream] 收集到完成时的剩余内容: {len(content)} 字符")
                                data_content['llm_completed'] = True
                                logger.debug(f"[collect_sse_stream] 流式传输完成标记")
                            else:
                                content = msg.get('content', '')
                                if content and not stream_contents:
                                    data_content['brief_response'] = content
                                    stream_contents.append(content)
                                    logger.debug(f"[collect_sse_stream] 简短答复兜底: {len(content)} 字符")
                                else:
                                    data_content['brief_response_completed'] = True
                                    logger.debug(f"[collect_sse_stream] 简短答复完成标记（内容已在 stream_content）")

                        elif event_type_to_use == 'llm_end':
                            data_content['llm_completed'] = True
                            logger.debug(f"[collect_sse_stream] LLM完成标记")

                        elif event_type_to_use == 'preset_questions':
                            questions = msg.get('questions', [])
                            if questions:
                                data_content['preset_questions'] = questions
                                logger.debug(f"[collect_sse_stream] 保存预设问题: {len(questions)} 个")

                        elif event_type_to_use == 'related_questions':
                            questions = msg.get('questions', [])
                            if questions:
                                data_content['related_questions'] = questions
                                logger.debug(f"[collect_sse_stream] 保存相关问题: {len(questions)} 个")

                        elif event_type_to_use == 'basic_analysis':
                            data_content['basic_analysis'] = msg
                            logger.debug(f"[collect_sse_stream] 保存基础分析结果")

                        elif event_type_to_use == 'performance':
                            data_content['performance'] = msg
                            logger.debug(f"[collect_sse_stream] 保存性能数据")

                        elif event_type_to_use == 'status':
                            data_content['last_status'] = msg
                            logger.debug(f"[collect_sse_stream] 更新状态: {msg.get('stage', 'unknown')}")

                        elif event_type_to_use == 'error':
                            error_content = msg.get('content') or msg.get('message') or str(msg)
                            logger.warning(f"[collect_sse_stream] 收到错误: {error_content}")

                        elif event_type_to_use == 'end':
                            logger.debug(f"[collect_sse_stream] 收到结束标记")
                            pass
                        else:
                            logger.debug(f"[collect_sse_stream] 未处理的事件类型: {event_type_to_use}")

                    except json.JSONDecodeError:
                        if current_event_type in ('brief_response_chunk', 'llm_chunk'):
                            stream_contents.append(json_str)
                            logger.debug(f"[collect_sse_stream] 收集到非JSON流式内容: {len(json_str)} 字符")
                    except Exception as e:
                        logger.warning(f"解析 SSE 消息失败: {e}, 事件类型: {current_event_type}, 原始数据: {line[:100]}")

        logger.info(f"[collect_sse_stream] 完成收集，共收到 {chunk_count} 个chunk, stream_contents={len(stream_contents)}, data_keys={list(data_content.keys())}")

        if error_content:
            return {
                "success": False,
                "error": error_content
            }

        stream_content = ''.join(stream_contents) if stream_contents else None
        data_content.pop('brief_response_completed', None)
        if stream_content and data_content.get('preset_questions') is not None and 'brief_response' not in data_content:
            data_content['brief_response'] = stream_content

        if not data_content and not stream_content:
            logger.warning(f"[collect_sse_stream] 警告：没有收集到任何数据，chunk_count={chunk_count}")

        result = {
            "success": True,
            "data": data_content if data_content else None,
            "stream_content": stream_content
        }

        logger.info(f"[collect_sse_stream] 返回结果: success={result['success']}, data_keys={list(result['data'].keys()) if result['data'] else None}, stream_content_len={len(stream_content) if stream_content else 0}")

        return result

    except Exception as e:
        logger.error(f"收集 SSE 流失败: {e}", exc_info=True)
        import traceback
        logger.error(f"堆栈跟踪: {traceback.format_exc()}")
        return {
            "success": False,
            "error": f"流式处理失败: {str(e)}"
        }
