# -*- coding: utf-8 -*-
"""
命理分析专用 LLM 客户端

职责：
- 调用 Coze Bot（命理分析专家）
- 将结构化命理数据转换为深度解读
- 不负责意图识别（由 Intent Service 完成）
- Redis缓存优化（相同八字+问题直接返回缓存）

使用的 Bot ID: FORTUNE_ANALYSIS_BOT_ID
"""

import os
import json
import requests
import hashlib
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 尝试导入Redis（可选依赖）
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis module not available, caching disabled")


class FortuneLLMClient:
    """命理分析专用 LLM 客户端（支持Redis缓存）"""
    
    def __init__(self):
        """初始化客户端"""
        self.access_token = os.getenv("COZE_ACCESS_TOKEN")
        self.bot_id = os.getenv("FORTUNE_ANALYSIS_BOT_ID")
        self.api_base = "https://api.coze.cn/v3/chat"  # 使用Chat API而非Workflow API
        
        if not self.access_token:
            raise ValueError("COZE_ACCESS_TOKEN not set in environment")
        if not self.bot_id:
            raise ValueError("FORTUNE_ANALYSIS_BOT_ID not set in environment")
        
        # 初始化Redis客户端（如果可用）
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                redis_host = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", "16379"))
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                # 测试连接
                self.redis_client.ping()
                logger.info(f"✅ Redis缓存已启用: {redis_host}:{redis_port}")
            except Exception as e:
                logger.warning(f"⚠️ Redis连接失败，缓存不可用: {e}")
                self.redis_client = None
        else:
            logger.info("ℹ️ Redis模块未安装，缓存功能不可用")
        
        # 缓存配置
        self.cache_ttl = int(os.getenv("FORTUNE_CACHE_TTL", "86400"))  # 默认24小时
        self.cache_prefix = "fortune_analysis:"
        
        logger.info(f"✅ FortuneLLMClient 初始化成功，Bot ID: {self.bot_id}")
    
    def _generate_cache_key(
        self,
        intent: str,
        question: str,
        bazi_data: Dict[str, Any],
        fortune_context: Dict[str, Any]
    ) -> str:
        """
        生成缓存key
        
        基于以下信息生成唯一key：
        - intent: 用户意图
        - question: 用户问题（标准化）
        - bazi_pillars: 八字四柱（核心标识）
        - time_range: 查询的流年范围
        
        Returns:
            Redis key，格式：fortune_analysis:<md5_hash>
        """
        # 提取关键信息
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        pillar_str = json.dumps(bazi_pillars, sort_keys=True, ensure_ascii=False)
        
        # 提取流年范围
        time_analysis = fortune_context.get('time_analysis', {})
        liunian_list = time_analysis.get('liunian_list', [])
        years = [ln.get('year') for ln in liunian_list]
        year_str = ','.join(str(y) for y in years)
        
        # 问题标准化（去除空格、转小写）
        normalized_question = question.strip().lower()
        
        # 组合所有信息
        cache_data = f"{intent}|{normalized_question}|{pillar_str}|{year_str}"
        
        # 生成MD5哈希
        hash_obj = hashlib.md5(cache_data.encode('utf-8'))
        hash_str = hash_obj.hexdigest()
        
        return f"{self.cache_prefix}{hash_str}"
    
    def _get_cached_analysis(self, cache_key: str) -> Optional[str]:
        """
        从Redis获取缓存的分析结果
        
        Args:
            cache_key: 缓存key
        
        Returns:
            缓存的分析文本，如果不存在或Redis不可用则返回None
        """
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.info(f"✅ 命中缓存: {cache_key[:50]}...")
                return cached
            return None
        except Exception as e:
            logger.error(f"❌ Redis读取失败: {e}")
            return None
    
    def _cache_analysis(self, cache_key: str, analysis: str) -> bool:
        """
        将分析结果缓存到Redis
        
        Args:
            cache_key: 缓存key
            analysis: 分析文本
        
        Returns:
            是否缓存成功
        """
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.setex(
                name=cache_key,
                time=self.cache_ttl,
                value=analysis
            )
            logger.info(f"✅ 分析结果已缓存: {cache_key[:50]}... (TTL: {self.cache_ttl}秒)")
            return True
        except Exception as e:
            logger.error(f"❌ Redis写入失败: {e}")
            return False
    
    def analyze_fortune(
        self,
        intent: str,
        question: str,
        bazi_data: Dict[str, Any],
        fortune_context: Dict[str, Any],
        matched_rules: List[Dict[str, Any]] = None,
        stream: bool = False,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        调用命理分析Bot，生成深度解读（支持缓存）
        
        Args:
            intent: 用户意图（wealth/health/career/marriage/character）
            question: 用户原始问题
            bazi_data: 八字原局数据
            fortune_context: 流年大运上下文（包含balance_analysis, relation_analysis等）
            matched_rules: 匹配到的规则列表（可选）
            stream: 是否使用流式输出（默认False）
            use_cache: 是否使用缓存（默认True）
        
        Returns:
            如果stream=False:
            {
                'success': bool,
                'analysis': str,  # 深度解读文本（Markdown格式）
                'error': str | None,
                'from_cache': bool  # 是否来自缓存
            }
            
            如果stream=True:
            返回一个生成器（generator），逐个yield分析片段
            注意：流式输出不支持缓存
        """
        try:
            # 构建输入数据（包含规则内容）
            input_data = self._build_input_data(
                intent=intent,
                question=question,
                bazi_data=bazi_data,
                fortune_context=fortune_context,
                matched_rules=matched_rules
            )
            
            logger.info(f"📊 准备调用命理分析Bot，意图: {intent}，问题: {question}，流式: {stream}，缓存: {use_cache}")
            logger.debug(f"输入数据: {json.dumps(input_data, ensure_ascii=False)[:500]}...")
            
            # 如果是流式输出，不使用缓存
            if stream:
                logger.info("🌊 流式输出模式，跳过缓存")
                return self._call_coze_api_stream(input_data)
            
            # 尝试从缓存获取（非流式模式）
            cache_key = None
            if use_cache:
                cache_key = self._generate_cache_key(intent, question, bazi_data, fortune_context)
                cached_analysis = self._get_cached_analysis(cache_key)
                
                if cached_analysis:
                    logger.info(f"✅ 返回缓存结果（节省LLM调用）")
                    return {
                        'success': True,
                        'analysis': cached_analysis,
                        'error': None,
                        'from_cache': True
                    }
                else:
                    logger.info("🔍 缓存未命中，调用LLM生成新分析")
            
            # 阻塞式调用LLM
            response = self._call_coze_api(input_data)
            
            if response['success']:
                analysis = response['analysis']
                logger.info(f"✅ 命理分析Bot调用成功，返回长度: {len(analysis)} 字符")
                
                # 缓存结果
                if use_cache and cache_key:
                    self._cache_analysis(cache_key, analysis)
                
                response['from_cache'] = False
                return response
            else:
                logger.error(f"❌ 命理分析Bot调用失败: {response['error']}")
                return response
                
        except Exception as e:
            logger.error(f"❌ analyze_fortune 异常: {e}", exc_info=True)
            return {
                'success': False,
                'analysis': None,
                'error': str(e),
                'from_cache': False
            }
    
    def _build_input_data(
        self,
        intent: str,
        question: str,
        bazi_data: Dict[str, Any],
        fortune_context: Dict[str, Any],
        matched_rules: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        构建发送给Bot的输入数据
        
        将分散的数据整合为结构化JSON，包含：
        - intent: 用户意图
        - question: 用户问题
        - bazi: 八字原局数据
        - liunian: 流年数据
        - dayun: 大运数据
        - balance_analysis: 五行平衡分析
        - relation_analysis: 关系分析
        - xi_ji: 喜忌神
        - wangshuai: 旺衰
        - matched_rules: 匹配到的规则（按意图分类）
        """
        # ⚠️ 防御性检查：fortune_context可能为None
        if not fortune_context:
            fortune_context = {}
        
        # 提取流年数据（智能匹配用户问题中的年份）
        time_analysis = fortune_context.get('time_analysis', {})
        liunian_list = time_analysis.get('liunian_list', [])
        
        # ⚠️ 修复：从用户问题中提取年份，匹配对应的流年数据
        liunian = {}
        target_year_from_question = None
        
        if liunian_list:
            # 尝试从问题中提取年份
            import re
            year_match = re.search(r'(\d{4})年?', question)
            if year_match:
                target_year_from_question = int(year_match.group(1))
                # 从liunian_list中找到对应年份的数据
                liunian = next(
                    (ln for ln in liunian_list if ln.get('year') == target_year_from_question), 
                    liunian_list[-1]  # 如果没找到，取最后一个（最新的年份）
                )
                logger.debug(f"用户问题包含年份{target_year_from_question}，匹配到流年：{liunian.get('year')}")
            else:
                # 没有明确年份，取最后一个（最新的年份）
                liunian = liunian_list[-1]
                logger.debug(f"用户问题无明确年份，取最新流年：{liunian.get('year')}")
        else:
            # ⚠️ 防御：如果liunian_list为空，从问题中提取年份，构造基础数据
            import re
            year_match = re.search(r'(\d{4})年?', question)
            if year_match:
                target_year_from_question = int(year_match.group(1))
                logger.debug(f"liunian_list为空，从问题提取年份：{target_year_from_question}，构造占位数据")
                liunian = {
                    'year': target_year_from_question,
                    'stem': '',  # 天干未知
                    'branch': '',  # 地支未知
                    'stem_element': '',
                    'branch_element': '',
                    'stem_shishen': '',
                    'branch_shishen': '',
                    'balance_analysis': {},
                    'relation_analysis': {}
                }
            else:
                logger.debug(f"liunian_list为空且问题中无年份，使用空数据")
        
        # 提取大运数据
        dayun = time_analysis.get('dayun', {})
        
        # 提取喜忌神
        xi_ji = fortune_context.get('xi_ji', {})
        
        # 提取旺衰
        wangshuai = fortune_context.get('wangshuai', '')
        
        # 构建精简输入（只保留LLM分析必需的核心数据）
        # 提取摘要而非完整对象，大幅减少token消耗
        balance_analysis = liunian.get('balance_analysis', {}) if liunian else {}
        balance_summary = balance_analysis.get('analysis', {}).get('summary', '')[:300] if balance_analysis else ''  # 限制长度
        
        relation_analysis = liunian.get('relation_analysis', {}) if liunian else {}
        relation_summary = relation_analysis.get('summary', '')[:300] if relation_analysis else ''  # 限制长度
        
        # ⭐ 新增：处理规则内容（按用户意图过滤和分类）
        rules_data = {}
        if matched_rules:
            from server.services.rule_classifier import build_rules_for_llm
            
            # 只传递当前意图相关的规则（减少 token 消耗）
            target_intents = [intent] if intent != 'general' else None
            
            rules_data = build_rules_for_llm(
                matched_rules=matched_rules,
                target_intents=target_intents,
                max_rules_per_intent=10  # 每个意图最多10条规则
            )
            
            logger.debug(f"规则分类结果: {rules_data.get('rules_count', {})}")
        
        input_data = {
            'intent': intent,
            'question': question,
            'bazi': {
                'pillars': bazi_data.get('bazi_pillars', {}),
                'day_stem': bazi_data.get('day_stem', ''),
                # 删除详细 shishen 和 wuxing 字典，LLM不需要完整统计
            },
            'liunian': {
                'year': liunian.get('year', ''),
                'stem': liunian.get('stem', ''),
                'branch': liunian.get('branch', ''),
                'stem_element': liunian.get('stem_element', ''),
                'branch_element': liunian.get('branch_element', ''),
                'stem_shishen': liunian.get('stem_shishen', ''),
                'branch_shishen': liunian.get('branch_shishen', ''),
                # 只传递摘要，不传完整分析对象
                'balance_summary': balance_summary,
                'relation_summary': relation_summary,
            },
            'dayun': {
                'stem': dayun.get('stem', ''),
                'branch': dayun.get('branch', ''),
                # 删除 age_range、stem_shishen、branch_shishen（非必需）
            },
            'xi_ji': {
                # 只保留前5个，避免列表过长
                'xi_shen': xi_ji.get('xi_shen', [])[:5],
                'ji_shen': xi_ji.get('ji_shen', [])[:5]
            },
            'wangshuai': wangshuai,
            # ⭐ 新增：按意图分类的规则内容
            'matched_rules': rules_data.get('rules_by_intent', {}),
            'rules_count': rules_data.get('rules_count', {}),
            # 删除以下冗余字段（LLM可通过其他信息推断）：
            # - data_completeness（元数据）
            # - tiaohou（调候信息）
            # - final_xi_ji（综合喜忌）
            # - internal_relations（刑冲合害破详细数据）
        }
        
        # 精简日志：只在 DEBUG 级别输出关键信息
        import json
        data_size = len(json.dumps(input_data, ensure_ascii=False))
        logger.debug(f"[STEP5] 发送给LLM的数据: intent={intent}, year={liunian.get('year', 'N/A')}, size={data_size}字符")
        
        return input_data
    
    def _get_messages(self, conversation_id: str, chat_id: str) -> Dict[str, Any]:
        """
        获取对话消息列表
        
        Args:
            conversation_id: 对话ID
            chat_id: Chat ID
        
        Returns:
            {
                'success': bool,
                'messages': list,
                'error': str | None
            }
        """
        message_list_url = "https://api.coze.cn/v3/chat/message/list"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'conversation_id': conversation_id,
            'chat_id': chat_id
        }
        
        try:
            response = requests.get(message_list_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') == 0:
                    data = result.get('data', [])
                    logger.info(f"📨 消息列表API返回{len(data)}条消息")
                    return {
                        'success': True,
                        'messages': data,
                        'error': None
                    }
                else:
                    error_msg = result.get('msg', '未知错误')
                    logger.error(f"❌ 消息列表API错误: {error_msg}")
                    return {
                        'success': False,
                        'messages': [],
                        'error': f'消息列表API错误: {error_msg}'
                    }
            else:
                logger.error(f"❌ 消息列表HTTP错误: {response.status_code}")
                return {
                    'success': False,
                    'messages': [],
                    'error': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"❌ 获取消息列表异常: {e}")
            return {
                'success': False,
                'messages': [],
                'error': str(e)
            }
    
    def _poll_chat_result(self, conversation_id: str, chat_id: str, max_retries: int = 30) -> Dict[str, Any]:
        """
        轮询获取Chat结果
        
        Args:
            conversation_id: 对话ID
            chat_id: Chat ID
            max_retries: 最大重试次数（默认30次，每次2秒，共60秒）
        
        Returns:
            {
                'success': bool,
                'data': dict | None,
                'error': str | None
            }
        """
        import time
        
        retrieve_url = f"https://api.coze.cn/v3/chat/retrieve"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'conversation_id': conversation_id,
            'chat_id': chat_id
        }
        
        for i in range(max_retries):
            try:
                time.sleep(2)  # 等待2秒再查询
                
                logger.debug(f"🔄 轮询第{i+1}次...")
                response = requests.get(retrieve_url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('code') == 0:
                        data = result.get('data', {})
                        status = data.get('status', '')
                        
                        logger.debug(f"  状态: {status}")
                        
                        if status == 'completed':
                            logger.info(f"✅ Bot处理完成（耗时{(i+1)*2}秒）")
                            # 打印完整data用于调试
                            logger.info(f"📋 完整data: {json.dumps(data, ensure_ascii=False)[:2000]}...")
                            
                            # retrieve API不返回messages，需要调用message list API
                            logger.info("📬 调用消息列表API获取Bot回复...")
                            messages_result = self._get_messages(conversation_id, chat_id)
                            if messages_result.get('success'):
                                # 将messages添加到data中
                                data['messages'] = messages_result.get('messages', [])
                                logger.info(f"✅ 获取到{len(data['messages'])}条消息")
                            else:
                                logger.error(f"❌ 获取消息失败: {messages_result.get('error')}")
                            
                            return {
                                'success': True,
                                'data': data,
                                'error': None
                            }
                        elif status == 'failed':
                            error = data.get('last_error', {})
                            error_msg = error.get('msg', '未知错误')
                            logger.error(f"❌ Bot处理失败: {error_msg}")
                            return {
                                'success': False,
                                'data': None,
                                'error': f'Bot处理失败: {error_msg}'
                            }
                        # 其他状态（in_progress, requires_action等）继续轮询
                    else:
                        error_msg = result.get('msg', '未知错误')
                        logger.error(f"❌ 轮询API错误: {error_msg}")
                        return {
                            'success': False,
                            'data': None,
                            'error': f'轮询API错误: {error_msg}'
                        }
                else:
                    logger.error(f"❌ 轮询HTTP错误: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ 轮询异常: {e}")
        
        # 超时
        logger.error(f"❌ 轮询超时（{max_retries*2}秒）")
        return {
            'success': False,
            'data': None,
            'error': f'Bot处理超时（>{max_retries*2}秒）'
        }
    
    def _call_coze_api_stream(self, input_data: Dict[str, Any]):
        """
        调用Coze API（流式输出）
        
        Args:
            input_data: 结构化输入数据
        
        Yields:
            每次yield一个字典:
            {
                'type': 'start' | 'chunk' | 'end' | 'error',
                'content': str,  # chunk类型时是文本片段
                'error': str  # error类型时的错误信息
            }
        """
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'  # 指定接收SSE格式
        }
        
        # 将input_data转为JSON字符串
        input_json = json.dumps(input_data, ensure_ascii=False)
        
        payload = {
            'bot_id': self.bot_id,
            'user_id': 'system',
            'stream': True,  # 启用流式输出
            'additional_messages': [
                {
                    'role': 'user',
                    'content': input_json,
                    'content_type': 'text'
                }
            ]
        }
        
        try:
            logger.info("🚀 开始流式调用 Coze API...")
            yield {'type': 'start', 'content': '', 'error': None}
            
            response = requests.post(
                self.api_base,
                headers=headers,
                json=payload,
                stream=True,  # 启用流式接收
                timeout=60
            )
            
            if response.status_code != 200:
                error_msg = f'HTTP {response.status_code}: {response.text}'
                logger.error(f"❌ Coze API请求失败: {error_msg}")
                yield {'type': 'error', 'content': '', 'error': error_msg}
                return
            
            # 设置响应编码为 UTF-8
            response.encoding = 'utf-8'
            
            # 发送开始事件
            yield {'type': 'start', 'content': '', 'error': None}
            
            # 逐行读取SSE数据（使用更大的chunk避免UTF-8截断）
            for line in response.iter_lines(decode_unicode=True, chunk_size=8192):
                if not line:
                    continue
                
                # SSE格式: "data: {...}"
                if line.startswith('data:'):
                    data_str = line[5:].strip()  # 去掉 "data:" 前缀
                    
                    if data_str == '[DONE]':
                        logger.info("✅ 流式输出完成")
                        yield {'type': 'end', 'content': '', 'error': None}
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        # 防御性检查：确保 data 是字典
                        if not isinstance(data, dict):
                            logger.warning(f"⚠️ SSE数据不是字典: {type(data)}, 数据: {data_str[:100]}")
                            continue
                        
                        # Coze API 有两种格式：
                        # 1. 带 event 字段的（新版）
                        # 2. 直接消息对象的（当前版本）
                        event_type = data.get('event', '')
                        msg_type = data.get('type', '')
                        
                        if event_type == 'conversation.message.delta':
                            # 新版格式：消息增量
                            delta = data.get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                logger.debug(f"📝 收到chunk: {content[:50]}...")
                                yield {'type': 'chunk', 'content': content, 'error': None}
                        
                        elif event_type == 'conversation.chat.completed':
                            # 新版格式：对话完成
                            logger.info("✅ 对话完成")
                            yield {'type': 'end', 'content': '', 'error': None}
                            break
                        
                        elif msg_type == 'answer':
                            # 当前版本格式：直接返回answer消息
                            content = data.get('content', '')
                            if content:
                                logger.debug(f"📝 收到answer: {content[:50]}...")
                                yield {'type': 'chunk', 'content': content, 'error': None}
                        
                        elif msg_type == 'follow_up':
                            # 后续问题，忽略
                            logger.debug("⏭️ 跳过follow_up消息")
                            continue
                        
                        elif event_type == 'error' or msg_type == 'error':
                            # 错误事件
                            error_msg = data.get('message', data.get('content', '未知错误'))
                            logger.error(f"❌ Bot返回错误: {error_msg}")
                            yield {'type': 'error', 'content': '', 'error': error_msg}
                            break
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ 解析SSE数据失败: {e}, 原始数据: {data_str[:200]}")
                        continue
            
            # 流结束
            logger.info("✅ SSE流结束")
            yield {'type': 'end', 'content': '', 'error': None}
            
        except requests.exceptions.Timeout:
            error_msg = '流式请求超时（60秒）'
            logger.error(f"❌ {error_msg}")
            yield {'type': 'error', 'content': '', 'error': error_msg}
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 流式调用异常: {e}", exc_info=True)
            yield {'type': 'error', 'content': '', 'error': error_msg}
    
    def _call_coze_api(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用Coze API
        
        Args:
            input_data: 结构化输入数据
        
        Returns:
            {
                'success': bool,
                'analysis': str | None,
                'error': str | None
            }
        """
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # 将input_data转为JSON字符串
        input_json = json.dumps(input_data, ensure_ascii=False)
        
        payload = {
            'bot_id': self.bot_id,
            'user_id': 'system',
            'stream': False,
            'additional_messages': [
                {
                    'role': 'user',
                    'content': input_json,
                    'content_type': 'text'
                }
            ]
        }
        
        try:
            logger.debug(f"🚀 发送请求到 Coze API: {self.api_base}")
            response = requests.post(
                self.api_base,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            logger.debug(f"📥 Coze API 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"📥 Coze API 完整响应: {json.dumps(result, ensure_ascii=False)[:1000]}...")
                
                # 解析响应
                if result.get('code') == 0:
                    data = result.get('data', {})
                    status = data.get('status', '')
                    conversation_id = data.get('conversation_id', '')
                    chat_id = data.get('id', '')
                    
                    logger.info(f"📊 任务状态: {status}, conversation_id: {conversation_id}, chat_id: {chat_id}")
                    
                    # 如果状态是 in_progress，需要轮询等待
                    if status == 'in_progress':
                        logger.info("⏳ Bot处理中，开始轮询等待...")
                        result = self._poll_chat_result(conversation_id, chat_id)
                        if not result.get('success'):
                            return result
                        data = result.get('data', {})
                    
                    # Chat API返回messages数组，提取Bot的最后一条回复
                    messages = data.get('messages', [])
                    logger.info(f"📨 收到 {len(messages)} 条消息")
                    
                    # 打印所有消息用于调试
                    for i, msg in enumerate(messages):
                        logger.info(f"  消息{i+1}: role={msg.get('role')}, type={msg.get('type')}, content长度={len(msg.get('content', ''))}")
                    
                    # 筛选出Bot的回复（role='assistant'，type='answer'）
                    bot_messages = [
                        msg for msg in messages 
                        if msg.get('role') == 'assistant' and msg.get('type') == 'answer'
                    ]
                    
                    logger.info(f"🤖 筛选出 {len(bot_messages)} 条Bot回复")
                    
                    if bot_messages:
                        # 取最后一条Bot回复
                        last_message = bot_messages[-1]
                        content = last_message.get('content', '')
                        
                        if content:
                            logger.info(f"✅ Bot回复成功，长度: {len(content)} 字符")
                            return {
                                'success': True,
                                'analysis': content,
                                'error': None
                            }
                        else:
                            logger.error("❌ Bot回复内容为空")
                            return {
                                'success': False,
                                'analysis': None,
                                'error': 'Bot回复内容为空'
                            }
                    else:
                        logger.error(f"❌ Bot未返回有效消息，总消息数: {len(messages)}")
                        # 打印第一条消息看看是什么
                        if messages:
                            logger.error(f"第一条消息示例: {json.dumps(messages[0], ensure_ascii=False)[:200]}")
                        return {
                            'success': False,
                            'analysis': None,
                            'error': f'Bot未返回有效消息（共{len(messages)}条消息，但无assistant/answer类型）'
                        }
                else:
                    error_msg = result.get('msg', '未知错误')
                    return {
                        'success': False,
                        'analysis': None,
                        'error': f'Coze API错误: {error_msg}'
                    }
            else:
                error_text = response.text
                logger.error(f"❌ Coze API请求失败: {response.status_code}, {error_text}")
                return {
                    'success': False,
                    'analysis': None,
                    'error': f'HTTP {response.status_code}: {error_text}'
                }
                
        except requests.exceptions.Timeout:
            logger.error("❌ Coze API请求超时")
            return {
                'success': False,
                'analysis': None,
                'error': '请求超时（30秒）'
            }
        except Exception as e:
            logger.error(f"❌ Coze API调用异常: {e}", exc_info=True)
            return {
                'success': False,
                'analysis': None,
                'error': str(e)
            }


# 全局单例
_fortune_llm_client: Optional[FortuneLLMClient] = None


def get_fortune_llm_client() -> FortuneLLMClient:
    """获取命理分析LLM客户端单例"""
    global _fortune_llm_client
    if _fortune_llm_client is None:
        _fortune_llm_client = FortuneLLMClient()
    return _fortune_llm_client

