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
from typing import Dict, Any, Optional, List
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
        
        # 如果FORTUNE_ANALYSIS_BOT_ID不存在，尝试使用COZE_BOT_ID作为fallback
        if not self.bot_id:
            self.bot_id = os.getenv("COZE_BOT_ID")
            if self.bot_id:
                logger.warning("⚠️ FORTUNE_ANALYSIS_BOT_ID未设置，使用COZE_BOT_ID作为fallback")
        
        # 如果环境变量缺失，尝试从config/services.env加载
        if not self.access_token or not self.bot_id:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            services_env_path = os.path.join(project_root, "config", "services.env")
            if os.path.exists(services_env_path):
                try:
                    with open(services_env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            
                            # 解析 export KEY="VALUE" 格式
                            if line.startswith('export '):
                                line = line[7:].strip()  # 去掉 'export '
                                if '=' in line:
                                    key, value = line.split('=', 1)
                                    key = key.strip()
                                    value = value.strip().strip('"').strip("'")
                                    
                                    if not self.access_token and key == 'COZE_ACCESS_TOKEN' and value:
                                        self.access_token = value
                                        os.environ['COZE_ACCESS_TOKEN'] = value
                                        logger.info(f"✓ 从config/services.env加载COZE_ACCESS_TOKEN")
                                    
                                    if not self.bot_id and key == 'FORTUNE_ANALYSIS_BOT_ID' and value:
                                        self.bot_id = value
                                        os.environ['FORTUNE_ANALYSIS_BOT_ID'] = value
                                        logger.info(f"✓ 从config/services.env加载FORTUNE_ANALYSIS_BOT_ID: {self.bot_id}")
                except Exception as e:
                    logger.warning(f"⚠️ 读取config/services.env失败: {e}")
        
        if not self.access_token:
            raise ValueError("COZE_ACCESS_TOKEN not set in environment (also checked config/services.env)")
        if not self.bot_id:
            raise ValueError("FORTUNE_ANALYSIS_BOT_ID not set in environment (also checked COZE_BOT_ID and config/services.env)")
        
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
        use_cache: bool = True,
        category: Optional[str] = None,
        minimal_mode: bool = False
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
                matched_rules=matched_rules,
                category=category,
                minimal_mode=minimal_mode
            )
            
            logger.info(f"📊 准备调用命理分析Bot，意图: {intent}，问题: {question}，流式: {stream}，缓存: {use_cache}")
            logger.debug(f"输入数据: {json.dumps(input_data, ensure_ascii=False)[:500]}...")
            
            # 如果是流式输出，不使用缓存
            if stream:
                logger.info("🌊 流式输出模式，跳过缓存")
                logger.info(f"[fortune_llm_client] 📞 调用 _call_coze_api_stream，输入数据大小: {len(json.dumps(input_data, ensure_ascii=False))}字符")
                generator = self._call_coze_api_stream(input_data)
                
                # ⭐ 关键检查：确保返回的是生成器
                if isinstance(generator, dict):
                    logger.error(f"[fortune_llm_client] ❌ _call_coze_api_stream 返回了字典而不是生成器！")
                    logger.error(f"[fortune_llm_client] 返回值: {json.dumps(generator, ensure_ascii=False)[:500]}")
                    # 返回一个生成器，yield错误
                    def error_generator():
                        yield {'type': 'error', 'content': '', 'error': '流式输出配置错误：返回了字典类型'}
                    return error_generator()
                elif not hasattr(generator, '__iter__') or isinstance(generator, str):
                    logger.error(f"[fortune_llm_client] ❌ _call_coze_api_stream 返回的不是生成器！类型: {type(generator)}")
                    # 返回一个生成器，yield错误
                    def error_generator():
                        yield {'type': 'error', 'content': '', 'error': f'流式输出配置错误：返回了非生成器类型 {type(generator)}'}
                    return error_generator()
                
                logger.info(f"[fortune_llm_client] ✅ _call_coze_api_stream 返回生成器，类型: {type(generator)}")
                return generator
            
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
        matched_rules: List[Dict[str, Any]] = None,
        category: Optional[str] = None,
        minimal_mode: bool = False
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
        
        Args:
            minimal_mode: 精简模式，只传递必要数据（场景2使用）
        """
        # 精简模式：只传递必要数据
        if minimal_mode:
            input_data = {
                'intent': intent,
                'question': question,
                'category': category,
                'bazi': {
                    'pillars': bazi_data.get('bazi_pillars', {}),
                    'day_stem': bazi_data.get('day_stem', ''),
                },
                'language_style': '通俗易懂，避免专业术语，面向普通用户。用日常语言解释命理概念，如"正官"可以说成"稳定的工作机会"，"七杀"可以说成"挑战和压力"。',
                'note': '八字详细信息已在第一次调用时提供，本次只基于用户问题和类别生成答案。请快速响应，在10秒内生成内容。'
            }
            
            # 精简日志
            import json
            data_size = len(json.dumps(input_data, ensure_ascii=False))
            logger.info(f"[精简模式] 发送给LLM的数据: intent={intent}, category={category}, size={data_size}字符")
            return input_data
        
        # 完整模式：传递所有数据（场景1使用）
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
            
            # ⭐ 详细日志：记录规则匹配和分类结果
            rules_count = rules_data.get('rules_count', {})
            rules_by_intent = rules_data.get('rules_by_intent', {})
            logger.info(f"规则分类结果: 总规则数={len(matched_rules)}, 分类后={rules_count}")
            
            # 详细记录每个意图的规则摘要
            for intent_name, rule_summaries in rules_by_intent.items():
                logger.info(f"  {intent_name}意图: {len(rule_summaries)}条规则")
                for summary in rule_summaries[:3]:  # 只记录前3条
                    logger.debug(f"    - {summary[:80]}...")
        
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
            # ⭐ 新增：category字段（场景2中使用）
            **({'category': category} if category else {}),
            # ⭐ 新增：语言风格要求（避免专业术语，面向普通用户）
            'language_style': '通俗易懂，避免专业术语，面向普通用户。用日常语言解释命理概念，如"正官"可以说成"稳定的工作机会"，"七杀"可以说成"挑战和压力"。',
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
        
        # 如果input_data包含prompt字段，直接使用prompt；否则将input_data转为JSON字符串
        if 'prompt' in input_data:
            content = input_data['prompt']
        else:
            content = json.dumps(input_data, ensure_ascii=False)
        
        payload = {
            'bot_id': self.bot_id,
            'user_id': 'system',
            'stream': True,  # 启用流式输出
            'additional_messages': [
                {
                    'role': 'user',
                    'content': content,
                    'content_type': 'text'
                }
            ]
        }
        
        try:
            logger.info("🚀 开始流式调用 Coze API...")
            logger.info(f"[fortune_llm_client] 📤 请求URL: {self.api_base}")
            logger.info(f"[fortune_llm_client] 📤 Bot ID: {self.bot_id}")
            logger.info(f"[fortune_llm_client] 📤 请求体大小: {len(json.dumps(payload, ensure_ascii=False))}字符")
            
            self._content_received = False  # 重置内容接收标志
            logger.info(f"[fortune_llm_client] ✅ 发送 start chunk")
            yield {'type': 'start', 'content': '', 'error': None}
            
            logger.info(f"📤 发送请求到Coze API: {self.api_base}")
            logger.debug(f"   请求头: {headers}")
            logger.debug(f"   请求体: {json.dumps(payload, ensure_ascii=False)[:500]}...")
            
            response = requests.post(
                self.api_base,
                headers=headers,
                json=payload,
                stream=True,  # 启用流式接收
                timeout=60
            )
            
            logger.info(f"📥 Coze API响应: HTTP {response.status_code}")
            logger.info(f"[fortune_llm_client] 📥 响应状态码: {response.status_code}")
            logger.info(f"[fortune_llm_client] 📥 响应头: {dict(response.headers)}")
            
            if response.status_code != 200:
                error_msg = f'HTTP {response.status_code}: {response.text}'
                logger.error(f"❌ Coze API请求失败: {error_msg}")
                logger.error(f"[fortune_llm_client] ❌ 非200响应，返回错误chunk: {error_msg}")
                yield {'type': 'error', 'content': '', 'error': error_msg}
                return
            
            # 设置响应编码为 UTF-8
            response.encoding = 'utf-8'
            
            # 注意：start 事件已在第 685 行发送，这里不再重复发送
            
            # 逐行读取SSE数据（使用更大的chunk避免UTF-8截断）
            buffer = ""
            stream_ended = False  # ⭐ 标志：流是否已结束（通过error或end）
            current_event = None  # ⭐ 记录当前SSE事件名称
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if not chunk:
                    continue
                
                buffer += chunk
                lines = buffer.split('\n')
                buffer = lines[-1]  # 保留最后一行（可能不完整）
                
                for line in lines[:-1]:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # SSE格式: "data: {...}" 或 "event: xxx"
                    if line.startswith('event:'):
                        # ⭐ 记录事件名称（Coze API 的事件在 event: 行中）
                        current_event = line[6:].strip()
                        logger.debug(f"📨 收到SSE事件: {current_event}")
                        continue
                    
                    elif line.startswith('data:'):
                        data_str = line[5:].strip()  # 去掉 "data:" 前缀
                        
                        if data_str == '[DONE]':
                            logger.info("✅ 流式输出完成（收到[DONE]标记）")
                            yield {'type': 'end', 'content': '', 'error': None}
                            stream_ended = True
                            break
                        
                        try:
                            data = json.loads(data_str)
                            
                            # 防御性检查：确保 data 是字典
                            if not isinstance(data, dict):
                                logger.warning(f"⚠️ SSE数据不是字典: {type(data)}, 数据: {data_str[:100]}")
                                continue
                            
                            # ⭐ 使用 current_event（从 event: 行获取）或 data 中的 event 字段
                            event_type = current_event or data.get('event', '')
                            msg_type = data.get('type', '')
                            status = data.get('status', '')  # ⭐ 新增：检查status字段
                            
                            # ⭐ 详细日志：记录所有收到的数据（用于调试）
                            logger.debug(f"📨 处理SSE数据: event={event_type}, type={msg_type}, status={status}, keys={list(data.keys())[:10]}")
                            
                            # ⭐ 提前检查：如果是 verbose 类型且 content 很大，可能是 knowledge_recall
                            if msg_type == 'verbose' and 'content' in data:
                                content_str = str(data.get('content', ''))
                                if len(content_str) > 10000:  # 大内容很可能是 knowledge_recall JSON
                                    try:
                                        if content_str.strip().startswith('{'):
                                            test_parse = json.loads(content_str)
                                            if isinstance(test_parse, dict) and test_parse.get('msg_type') == 'knowledge_recall':
                                                logger.info(f"⏭️ 提前跳过 verbose 类型的 knowledge_recall 消息（content长度: {len(content_str)}）")
                                                continue
                                    except (json.JSONDecodeError, AttributeError, ValueError):
                                        pass
                            
                            # ⭐ 优先检查status字段（Coze API可能不设置event字段）
                            if status == 'failed':
                                last_error = data.get('last_error', {})
                                error_code = last_error.get('code', 0)
                                error_msg = last_error.get('msg', 'Bot处理失败')
                                logger.error(f"❌ Bot处理失败（通过status字段）: code={error_code}, msg={error_msg}")
                                yield {'type': 'error', 'content': '', 'error': f'Bot处理失败: {error_msg} (错误码: {error_code})'}
                                stream_ended = True
                                break
                            
                            # 新版格式：conversation.message.delta（事件在 event: 行中，内容在 data 中）
                            if event_type == 'conversation.message.delta':
                                # ⭐ Coze API 的 delta 格式：data 中直接包含 content 字段，不是嵌套在 delta 中
                                msg_type = data.get('type', '')
                                
                                # ⭐ 跳过 knowledge_recall 类型的消息
                                if msg_type == 'knowledge_recall' or msg_type == 'verbose':
                                    logger.debug(f"⏭️ 跳过 {msg_type} 类型的delta消息")
                                    continue
                                
                                content = data.get('content', '')
                                if content:
                                    # ⭐ 检查 content 是否是JSON字符串
                                    try:
                                        parsed_content = json.loads(content)
                                        if isinstance(parsed_content, dict):
                                            # 如果是 knowledge_recall JSON，跳过
                                            if parsed_content.get('msg_type') == 'knowledge_recall':
                                                logger.debug("⏭️ 跳过 knowledge_recall JSON delta")
                                                continue
                                            # 尝试提取文本
                                            text_content = parsed_content.get('text') or parsed_content.get('content')
                                            if text_content and isinstance(text_content, str):
                                                content = text_content
                                    except (json.JSONDecodeError, AttributeError):
                                        pass
                                    
                                    self._content_received = True
                                    logger.debug(f"📝 收到delta chunk ({msg_type}): {len(content)}字符")
                                    logger.info(f"[fortune_llm_client] 📝 发送chunk: {len(content)}字符, 预览: {content[:50]}...")
                                    yield {'type': 'chunk', 'content': content, 'error': None}
                                continue
                            
                            # 新版格式：conversation.chat.completed
                            elif event_type == 'conversation.chat.completed':
                                logger.info("✅ 对话完成（conversation.chat.completed）")
                                logger.info(f"[fortune_llm_client] ✅ 收到 conversation.chat.completed，发送 end chunk")
                                yield {'type': 'end', 'content': '', 'error': None}
                                stream_ended = True
                                break
                            
                            # 新版格式：conversation.message.completed（完整消息，可能包含大量内容）
                            elif event_type == 'conversation.message.completed':
                                # ⭐ 检查消息类型，只处理 answer 类型，跳过 knowledge_recall 等
                                msg_type = data.get('type', '')
                                content = data.get('content', '')
                                
                                # ⭐ 对于 verbose 类型，直接跳过（verbose 通常是知识库召回或调试信息）
                                if msg_type == 'verbose':
                                    logger.info(f"⏭️ 跳过 verbose 类型消息（知识库召回/调试信息，不是Bot回答），content长度: {len(str(content))}")
                                    continue
                                
                                # ⭐ 跳过 knowledge_recall 类型的消息（这是知识库召回，不是Bot回答）
                                if msg_type == 'knowledge_recall':
                                    logger.info(f"⏭️ 跳过 {msg_type} 类型消息（知识库召回，不是Bot回答）")
                                    continue
                                
                                # ⭐ 只处理 answer 类型的消息
                                if msg_type == 'answer' and content and isinstance(content, str) and len(content) > 10:
                                    # 检查 content 是否是JSON字符串（需要解析）
                                    try:
                                        # 尝试解析JSON
                                        if content.strip().startswith('{'):
                                            parsed_content = json.loads(content)
                                            # 如果是JSON，检查是否有实际文本内容
                                            if isinstance(parsed_content, dict):
                                                # 如果是 knowledge_recall 类型的JSON，跳过
                                                if parsed_content.get('msg_type') == 'knowledge_recall':
                                                    logger.info("⏭️ 跳过 knowledge_recall JSON内容")
                                                    continue
                                                # 尝试提取文本内容
                                                text_content = parsed_content.get('text') or parsed_content.get('content') or parsed_content.get('message')
                                                if text_content and isinstance(text_content, str):
                                                    content = text_content
                                    except (json.JSONDecodeError, AttributeError, ValueError):
                                        # 不是JSON，直接使用
                                        pass
                                    
                                    # ⭐ 最终检查 content 不是 knowledge_recall JSON
                                    try:
                                        if isinstance(content, str) and content.strip().startswith('{'):
                                            test_parse = json.loads(content)
                                            if isinstance(test_parse, dict) and test_parse.get('msg_type') == 'knowledge_recall':
                                                logger.info("⏭️ 最终检查：跳过 knowledge_recall JSON")
                                                continue
                                    except (json.JSONDecodeError, AttributeError, ValueError):
                                        pass
                                    
                                    self._content_received = True
                                    logger.info(f"📝 收到完整消息 ({msg_type}): {len(content)}字符")
                                    logger.info(f"[fortune_llm_client] 📝 发送完整消息chunk: {len(content)}字符, 预览: {content[:50]}...")
                                    yield {'type': 'chunk', 'content': content, 'error': None}
                                elif msg_type != 'answer':
                                    # ⭐ 非 answer 类型，直接跳过
                                    logger.debug(f"⏭️ 跳过非 answer 类型的消息: {msg_type}")
                                continue
                            
                            # 新版格式：conversation.chat.failed
                            elif event_type == 'conversation.chat.failed':
                                last_error = data.get('last_error', {})
                                error_code = last_error.get('code', 0)
                                error_msg = last_error.get('msg', '未知错误')
                                logger.error(f"❌ Bot处理失败: code={error_code}, msg={error_msg}")
                                yield {'type': 'error', 'content': '', 'error': f'Bot处理失败: {error_msg} (code: {error_code})'}
                                stream_ended = True
                                break
                            
                            # 旧版格式：answer消息
                            elif msg_type == 'answer':
                                content = data.get('content', '')
                                if content:
                                    self._content_received = True
                                    logger.info(f"📝 收到answer: {len(content)}字符")
                                    yield {'type': 'chunk', 'content': content, 'error': None}
                            
                            # 旧版格式：完整消息（可能包含完整内容）
                            elif 'content' in data and data.get('content'):
                                content = data.get('content', '')
                                if isinstance(content, str) and content:
                                    # ⭐ 检查是否是 knowledge_recall JSON
                                    try:
                                        if content.strip().startswith('{') and len(content) > 1000:
                                            parsed = json.loads(content)
                                            if isinstance(parsed, dict) and parsed.get('msg_type') == 'knowledge_recall':
                                                logger.info(f"⏭️ 跳过 knowledge_recall JSON content（长度: {len(content)}）")
                                                continue
                                    except (json.JSONDecodeError, AttributeError, ValueError):
                                        pass
                                    
                                    self._content_received = True
                                    logger.info(f"📝 收到content: {len(content)}字符")
                                    yield {'type': 'chunk', 'content': content, 'error': None}
                            
                            # follow_up消息，忽略
                            elif msg_type == 'follow_up':
                                logger.debug("⏭️ 跳过follow_up消息")
                                continue
                            
                            # 错误事件
                            elif event_type == 'error' or msg_type == 'error':
                                error_msg = data.get('message', data.get('content', data.get('error', '未知错误')))
                                logger.error(f"❌ Bot返回错误: {error_msg}")
                                yield {'type': 'error', 'content': '', 'error': error_msg}
                                stream_ended = True
                                break
                            
                            # 其他未知格式，记录日志但不中断
                            else:
                                logger.warning(f"⚠️ 未知SSE格式: event={event_type}, type={msg_type}, keys={list(data.keys())[:5]}, 完整数据: {json.dumps(data, ensure_ascii=False)[:200]}")
                                # 尝试提取任何可能的文本内容
                                for key in ['text', 'message', 'data', 'result', 'answer', 'content']:
                                    if key in data:
                                        value = data[key]
                                        if isinstance(value, str) and value.strip():
                                            logger.info(f"📝 从{key}字段提取内容: {len(value)}字符")
                                            yield {'type': 'chunk', 'content': value, 'error': None}
                                            break
                        
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ 解析SSE数据失败: {e}, 原始数据: {data_str[:200]}")
                            continue
                    
                    # 处理 event: 行
                    elif line.startswith('event:'):
                        event_name = line[6:].strip()
                        logger.debug(f"📨 收到SSE事件: {event_name}")
                    
                    # ⭐ 如果流已结束（通过error或end），跳出内层循环
                    if stream_ended:
                        break
                
                # ⭐ 如果流已结束，跳出外层循环
                if stream_ended:
                    break
            
            # 处理剩余的buffer
            if buffer.strip():
                logger.debug(f"⚠️ 有未处理的buffer: {buffer[:100]}")
            
            # 流结束（只有在没有通过error/end结束的情况下才yield end）
            if not stream_ended:
                logger.info("✅ SSE流结束（正常结束）")
                logger.info(f"[fortune_llm_client] ✅ SSE流正常结束，发送 end chunk")
                
                # ⚠️ 如果没有收到任何内容chunk，记录警告
                if not hasattr(self, '_content_received'):
                    self._content_received = False
                if not self._content_received:
                    logger.warning("⚠️ SSE流结束，但未收到任何内容chunk，可能Bot未生成内容或响应格式异常")
                    logger.warning(f"[fortune_llm_client] ⚠️ 未收到任何内容chunk")
                
                yield {'type': 'end', 'content': '', 'error': None}
            else:
                logger.info("✅ SSE流结束（已通过error/end事件结束）")
                logger.info(f"[fortune_llm_client] ✅ SSE流已通过事件结束")
            
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
        
        # 如果input_data包含prompt字段，直接使用prompt；否则将input_data转为JSON字符串
        if 'prompt' in input_data:
            content = input_data['prompt']
        else:
            content = json.dumps(input_data, ensure_ascii=False)
        
        payload = {
            'bot_id': self.bot_id,
            'user_id': 'system',
            'stream': False,
            'additional_messages': [
                {
                    'role': 'user',
                    'content': content,
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


    def generate_brief_response(
        self,
        bazi_data: Dict[str, Any],
        category: str
    ):
        """
        生成简短答复（100字内，流式输出）
        
        Args:
            bazi_data: 完整八字数据（包含bazi_result、detail_result等）
            category: 选择项（事业财富、婚姻、健康等）
            
        Returns:
            生成器，yield格式：{'type': 'start'/'chunk'/'end'/'error', 'content': str, 'error': str}
        """
        try:
            # 构建简短答复的Prompt
            prompt = self._build_brief_response_prompt(bazi_data, category)
            
            # 构建输入数据
            input_data = {
                'prompt': prompt,
                'category': category,
                'task_type': 'brief_response'
            }
            
            logger.info(f"📊 生成简短答复，category: {category}")
            return self._call_coze_api_stream(input_data)
            
        except Exception as e:
            logger.error(f"❌ generate_brief_response 异常: {e}", exc_info=True)
            def error_generator():
                yield {'type': 'error', 'content': '', 'error': str(e)}
            return error_generator()
    
    def generate_preset_questions(
        self,
        bazi_data: Dict[str, Any],
        category: str
    ):
        """
        生成预设问题列表（10-15个）
        
        Args:
            bazi_data: 完整八字数据
            category: 选择项
            
        Returns:
            生成器，yield格式：{'type': 'complete'/'error', 'questions': list, 'error': str}
        """
        try:
            # 构建预设问题的Prompt
            prompt = self._build_preset_questions_prompt(bazi_data, category)
            
            # 调用非流式API
            input_data = {
                'prompt': prompt,
                'category': category,
                'task_type': 'preset_questions'
            }
            
            logger.info(f"📊 生成预设问题列表，category: {category}")
            response = self._call_coze_api(input_data)
            
            if response.get('success'):
                analysis = response.get('analysis', '')
                # 解析JSON格式的问题列表
                questions = self._parse_questions_from_response(analysis)
                
                def complete_generator():
                    yield {'type': 'complete', 'questions': questions, 'error': None}
                return complete_generator()
            else:
                error_msg = response.get('error', '未知错误')
                def error_generator():
                    yield {'type': 'error', 'questions': [], 'error': error_msg}
                return error_generator()
            
        except Exception as e:
            logger.error(f"❌ generate_preset_questions 异常: {e}", exc_info=True)
            def error_generator():
                yield {'type': 'error', 'questions': [], 'error': str(e)}
            return error_generator()
    
    def generate_related_questions(
        self,
        bazi_response: str,
        user_intent: Dict[str, Any],
        bazi_data: Dict[str, Any],
        category: str
    ):
        """
        生成3个相关问题（基于流式回答内容和用户意图）
        
        Args:
            bazi_response: 流式回答的完整内容
            user_intent: 用户意图识别结果
            bazi_data: 完整八字数据
            category: 选择项
            
        Returns:
            生成器，yield格式：{'type': 'complete'/'error', 'questions': list, 'error': str}
        """
        try:
            # 构建相关问题的Prompt
            prompt = self._build_related_questions_prompt(
                bazi_response, user_intent, bazi_data, category
            )
            
            # 调用非流式API（优化：减少数据量以提升速度）
            input_data = {
                'prompt': prompt,
                'category': category,
                'response': bazi_response[:300],  # 优化：从500字减少到300字，提升响应速度
                'task_type': 'related_questions'
            }
            
            logger.info(f"📊 生成相关问题，category: {category}")
            response = self._call_coze_api(input_data)
            
            if response.get('success'):
                analysis = response.get('analysis', '')
                # 解析JSON格式的问题列表（只取前2个）
                questions = self._parse_questions_from_response(analysis)[:2]
                
                def complete_generator():
                    yield {'type': 'complete', 'questions': questions, 'error': None}
                return complete_generator()
            else:
                error_msg = response.get('error', '未知错误')
                def error_generator():
                    yield {'type': 'error', 'questions': [], 'error': error_msg}
                return error_generator()
            
        except Exception as e:
            logger.error(f"❌ generate_related_questions 异常: {e}", exc_info=True)
            def error_generator():
                yield {'type': 'error', 'questions': [], 'error': str(e)}
            return error_generator()
    
    def _build_brief_response_prompt(
        self,
        bazi_data: Dict[str, Any],
        category: str
    ) -> str:
        """构建简短答复的Prompt"""
        bazi_result = bazi_data.get("bazi_result", {})
        category_names = {
            "事业财富": "事业和财富",
            "婚姻": "婚姻感情",
            "健康": "健康运势",
            "子女": "子女运势",
            "流年运势": "流年运势",
            "年运报告": "年运报告"
        }
        category_cn = category_names.get(category, category)
        
        prompt = f"""请基于用户的八字信息，生成关于"{category_cn}"的简短答复（100字以内）。

【用户八字信息】
四柱八字：
{self._format_bazi_for_prompt(bazi_result)}

【要求】
1. 内容要简洁明了，控制在100字以内
2. 聚焦于{category_cn}方面
3. 语言通俗易懂
4. 直接给出核心结论，不需要详细分析

请直接回答，不要添加其他说明："""
        
        return prompt
    
    def _build_preset_questions_prompt(
        self,
        bazi_data: Dict[str, Any],
        category: str
    ) -> str:
        """构建预设问题的Prompt"""
        bazi_result = bazi_data.get("bazi_result", {})
        category_names = {
            "事业财富": "事业和财富",
            "婚姻": "婚姻感情",
            "健康": "健康运势",
            "子女": "子女运势",
            "流年运势": "流年运势",
            "年运报告": "年运报告"
        }
        category_cn = category_names.get(category, category)
        
        prompt = f"""请基于用户的八字信息，生成10-15个关于"{category_cn}"的预设问题。

【用户八字信息】
四柱八字：
{self._format_bazi_for_prompt(bazi_result)}

【要求】
1. 生成10-15个相关问题
2. 问题要具体、实用
3. 覆盖{category_cn}的各个方面
4. 问题要通俗易懂，符合用户关心的点
5. 必须以JSON数组格式返回，例如：["问题1", "问题2", "问题3"]

请直接返回JSON数组，不要添加其他说明："""
        
        return prompt
    
    def _build_related_questions_prompt(
        self,
        bazi_response: str,
        user_intent: Dict[str, Any],
        bazi_data: Dict[str, Any],
        category: str
    ) -> str:
        """构建相关问题的Prompt"""
        category_names = {
            "事业财富": "事业和财富",
            "婚姻": "婚姻感情",
            "健康": "健康运势",
            "子女": "子女运势",
            "流年运势": "流年运势",
            "年运报告": "年运报告"
        }
        category_cn = category_names.get(category, category)
        
        # 优化：简化user_intent数据，只传递关键字段，减少token消耗
        simplified_intent = {
            'intents': user_intent.get('intents', []),
            'confidence': user_intent.get('confidence', 0)
        }
        
        prompt = f"""请基于以下内容，快速生成2个相关问题：

【已回答内容】
{bazi_response[:300]}

【用户意图】
{json.dumps(simplified_intent, ensure_ascii=False)}

【要求】
1. 只生成2个相关问题
2. 问题要基于已回答的内容，能够深入展开
3. 问题要具体、实用
4. **问题必须用通俗易懂的语言，不能包含任何专业术语**
5. **禁止使用以下专业术语**：乙巳年、巳申六合、财星、七杀、正官、食神、比肩、劫财、偏财、正财、印星、伤官等
6. **用日常语言表达**：如"今年"而不是"乙巳年"，"缘分机会"而不是"巳申六合"，"工作压力"而不是"七杀"
7. 必须以JSON数组格式返回，例如：["问题1", "问题2"]
8. 快速生成，不要过度思考

请直接返回JSON数组，不要添加其他说明："""
        
        return prompt
    
    def _format_bazi_for_prompt(self, bazi_result: Dict[str, Any]) -> str:
        """格式化八字信息用于Prompt"""
        # 尝试多种可能的键名（BaziService.calculate_bazi_full返回{"bazi": {...}, ...}）
        pillars = None
        
        # 1. 直接查找bazi_pillars
        if "bazi_pillars" in bazi_result:
            pillars = bazi_result.get("bazi_pillars")
        # 2. 查找bazi.bazi_pillars（BaziService.calculate_bazi_full的返回格式）
        elif "bazi" in bazi_result:
            bazi_data = bazi_result.get("bazi", {})
            if isinstance(bazi_data, dict):
                pillars = bazi_data.get("bazi_pillars")
        # 3. 如果bazi_result本身就是pillars结构（直接包含year/month/day/hour键）
        elif any(key in bazi_result for key in ["year", "month", "day", "hour"]):
            pillars = bazi_result
        
        if not pillars:
            pillars = {}
        
        pillar_names = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
        
        # 调试日志
        logger.debug(f"📊 _format_bazi_for_prompt: bazi_result keys: {list(bazi_result.keys())}")
        if "bazi" in bazi_result:
            bazi_data = bazi_result.get("bazi", {})
            logger.debug(f"📊 _format_bazi_for_prompt: bazi keys: {list(bazi_data.keys()) if isinstance(bazi_data, dict) else 'N/A'}")
        logger.debug(f"📊 _format_bazi_for_prompt: pillars type: {type(pillars)}, keys: {list(pillars.keys()) if isinstance(pillars, dict) else 'N/A'}")
        
        formatted = []
        for eng_name, cn_name in pillar_names.items():
            if eng_name in pillars:
                pillar = pillars[eng_name]
                # 处理pillar可能是字典或字符串的情况
                if isinstance(pillar, dict):
                    stem = pillar.get("stem", "")
                    branch = pillar.get("branch", "")
                elif isinstance(pillar, str):
                    # 如果是字符串格式（如"甲子"），尝试解析
                    if len(pillar) >= 2:
                        stem = pillar[0]
                        branch = pillar[1]
                    else:
                        stem = ""
                        branch = ""
                else:
                    stem = ""
                    branch = ""
                
                if stem and branch:
                    formatted.append(f"{cn_name}：{stem}{branch}")
                else:
                    logger.warning(f"⚠️  {cn_name}的stem或branch为空: stem={stem}, branch={branch}, pillar={pillar}")
            else:
                logger.warning(f"⚠️  pillars中缺少{eng_name}字段")
        
        result = "\n".join(formatted) if formatted else "八字信息不完整"
        logger.debug(f"📊 格式化后的八字信息: {result}")
        return result
    
    def _parse_questions_from_response(self, response_text: str) -> list:
        """从LLM响应中解析问题列表"""
        try:
            # 尝试直接解析JSON
            questions = json.loads(response_text)
            if isinstance(questions, list):
                return questions
            
            # 尝试从文本中提取JSON数组
            import re
            json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if json_match:
                questions = json.loads(json_match.group())
                if isinstance(questions, list):
                    return questions
            
            # 如果都失败，尝试按行分割
            lines = response_text.strip().split('\n')
            questions = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
            return questions[:15]  # 最多返回15个
            
        except Exception as e:
            logger.warning(f"解析问题列表失败: {e}, 原始响应: {response_text[:200]}")
            return []


# 全局单例
_fortune_llm_client: Optional[FortuneLLMClient] = None


def get_fortune_llm_client() -> FortuneLLMClient:
    """获取命理分析LLM客户端单例"""
    global _fortune_llm_client
    if _fortune_llm_client is None:
        _fortune_llm_client = FortuneLLMClient()
    return _fortune_llm_client

