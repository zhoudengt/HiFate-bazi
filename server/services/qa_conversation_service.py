#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA 多轮对话服务
支持问题分类引导、智能问题生成和流式回答
严格遵循项目开发规范，使用统一数据接口获取命理元数据
"""

import os
import sys
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple
from datetime import datetime
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.services.coze_stream_service import CozeStreamService
from server.services.bazi_data_orchestrator import BaziDataOrchestrator
from server.services.qa_question_generator import QAQuestionGenerator
from server.config.mysql_config import get_mysql_connection, return_mysql_connection
from server.utils.data_validator import validate_bazi_data
from server.utils.bazi_input_processor import BaziInputProcessor
from server.utils.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)

# 延迟导入 intent_client（避免 grpc 依赖问题导致模块导入失败）
def _get_intent_client():
    """延迟导入 IntentServiceClient"""
    try:
        from server.services.intent_client import IntentServiceClient
        return IntentServiceClient()
    except ImportError as e:
        logger.warning(f"IntentServiceClient 导入失败（可选依赖）: {e}")
        return None
    except Exception as e:
        logger.error(f"IntentServiceClient 初始化失败: {e}", exc_info=True)
        return None


class QAConversationService:
    """多轮问答对话服务"""
    
    def __init__(self):
        # 导入配置加载器（从数据库读取配置）
        try:
            from server.config.config_loader import get_config_from_db_only
        except ImportError:
            def get_config_from_db_only(key: str) -> Optional[str]:
                raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")
        
        # Coze 服务（主分析 Bot）
        # 只从数据库读取，不降级到环境变量
        self.analysis_bot_id = get_config_from_db_only("QA_ANALYSIS_BOT_ID") or get_config_from_db_only("COZE_BOT_ID")
        if not self.analysis_bot_id:
            raise ValueError("数据库配置缺失: QA_ANALYSIS_BOT_ID 或 COZE_BOT_ID，请在 service_configs 表中配置")
        try:
            self.coze_service = CozeStreamService(bot_id=self.analysis_bot_id)
        except Exception as e:
            logger.warning(f"CozeStreamService 初始化失败（可选依赖）: {e}")
            self.coze_service = None
        
        # 意图识别客户端（延迟初始化）
        self.intent_client = None
        self._intent_client_initialized = False
        
        # 问题生成服务
        try:
            self.question_generator = QAQuestionGenerator()
        except Exception as e:
            logger.warning(f"QAQuestionGenerator 初始化失败（可选依赖）: {e}")
            self.question_generator = None
        
        # 使用统一数据接口
        self.data_orchestrator = BaziDataOrchestrator
    
    def _ensure_intent_client(self):
        """确保意图识别客户端已初始化"""
        if not self._intent_client_initialized:
            self.intent_client = _get_intent_client()
            self._intent_client_initialized = True
        return self.intent_client
    
    async def start_conversation(
        self,
        user_id: str,
        solar_date: str,
        solar_time: str,
        gender: str
    ) -> Dict[str, Any]:
        """
        开始新对话
        
        Args:
            user_id: 用户ID
            solar_date: 出生日期
            solar_time: 出生时间
            gender: 性别
        
        Returns:
            {
                'session_id': str,
                'initial_question': str,
                'categories': List[Dict[str, str]]
            }
        """
        session_id = None
        conn = None
        monitor = PerformanceMonitor(request_id=f"qa_start_{int(__import__('time').time() * 1000)}")
        
        try:
            # 1. 生成会话ID
            session_id = str(uuid.uuid4())
            logger.info(f"🔄 开始创建新对话会话: {session_id}, 用户: {user_id}, 日期: {solar_date} {solar_time}, 性别: {gender}")
            
            # 2. 创建会话记录（使用事务确保数据一致性）
            with monitor.stage("db_session_insert", "数据库会话插入"):
                conn = get_mysql_connection()
                try:
                    # 开始事务
                    conn.autocommit = False
                    
                    with conn.cursor() as cursor:
                        # 插入会话记录
                        cursor.execute(
                            """INSERT INTO qa_conversation_sessions 
                               (session_id, user_id, solar_date, solar_time, gender, created_at) 
                               VALUES (%s, %s, %s, %s, %s, NOW())""",
                            (session_id, user_id, solar_date, solar_time, gender)
                        )
                        
                        # 提交事务
                        conn.commit()
                        logger.info(f"✅ 会话记录已提交到数据库: {session_id}")
                    
                    # 3. 验证插入是否成功（直接查询，不依赖 rowcount）
                    # 注意：PyMySQL 的 rowcount 在 commit 后可能失效，直接查询更可靠
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """SELECT session_id, user_id, solar_date, solar_time, gender, created_at 
                               FROM qa_conversation_sessions 
                               WHERE session_id = %s""",
                            (session_id,)
                        )
                        verification_row = cursor.fetchone()
                        
                        if not verification_row:
                            raise Exception(f"会话验证失败：插入后无法查询到会话记录 {session_id}")
                        
                        # 注意：PyMySQL 返回字典格式，使用键访问而不是索引
                        logger.info(f"✅ 会话验证成功: {session_id}, 用户: {verification_row.get('user_id', 'N/A')}, 创建时间: {verification_row.get('created_at', 'N/A')}")
                        monitor.add_metric("db_session_insert", "session_id", session_id)
                        
                except Exception as db_error:
                    # 回滚事务
                    if conn:
                        try:
                            conn.rollback()
                            logger.warning(f"⚠️ 数据库操作失败，已回滚事务: {db_error}")
                        except Exception as rollback_error:
                            logger.error(f"❌ 回滚事务失败: {rollback_error}", exc_info=True)
                    raise db_error
                finally:
                    if conn:
                        return_mysql_connection(conn)
            
            # 4. 计算并缓存完整八字数据（阶段1优化：数据缓存）
            with monitor.stage("bazi_data_calculation", "计算并缓存八字数据"):
                modules = {
                    'bazi': True,
                    'wangshuai': True,
                    'dayun': {'mode': 'current_with_neighbors'},
                    'liunian': True,
                    'rules': {'types': ['ALL']},  # 匹配所有规则
                    'special_liunian': True
                }
                
                data = await BaziDataOrchestrator.fetch_data(
                    solar_date=solar_date,
                    solar_time=solar_time,
                    gender=gender,
                    modules=modules,
                    use_cache=True,
                    parallel=True
                )
                
                # 保存到 session 缓存（使用 BaziSessionService）
                from server.services.bazi_session_service import BaziSessionService
                BaziSessionService.save_bazi_session(user_id, data)
                logger.info(f"✅ 八字数据已计算并缓存: user_id={user_id}")
                monitor.add_metric("bazi_data_calculation", "modules_count", len(modules))
            
            # 5. 获取初始问题
            with monitor.stage("get_initial_question", "获取初始问题"):
                initial_question = await self._get_initial_question()
                monitor.add_metric("get_initial_question", "question_length", len(initial_question))
            
            # 6. 获取分类列表
            with monitor.stage("get_categories", "获取分类列表"):
                categories = await self._get_categories()
                monitor.add_metric("get_categories", "categories_count", len(categories))
            
            logger.info(f"✅ 创建新对话会话成功: {session_id}, 用户: {user_id}, 初始问题: {initial_question[:50]}...")
            
            # 输出性能摘要
            monitor.log_summary()
            
            return {
                'success': True,
                'session_id': session_id,
                'initial_question': initial_question,
                'categories': categories,
                'performance': monitor.get_summary()  # 添加性能摘要
            }
        except Exception as e:
            error_msg = f"创建对话会话失败: {str(e)}"
            logger.error(f"❌ {error_msg}, session_id: {session_id}, 用户: {user_id}", exc_info=True)
            if monitor.current_stage:
                monitor.end_stage(monitor.current_stage, success=False, error=error_msg)
            monitor.log_summary()
            return {
                'success': False,
                'error': error_msg,
                'session_id': session_id,  # 即使失败也返回 session_id，便于调试
                'performance': monitor.get_summary()  # 即使失败也返回性能摘要
            }
    
    async def get_category_questions(
        self,
        category: str
    ) -> List[Dict[str, Any]]:
        """
        获取分类下的问题列表
        
        Args:
            category: 分类名称
        
        Returns:
            问题列表
        """
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """SELECT id, question_text, priority 
                           FROM qa_question_templates 
                           WHERE category = %s AND enabled = 1 
                           ORDER BY priority ASC, id ASC""",
                        (category,)
                    )
                    rows = cursor.fetchall()
                    
                    questions = []
                    for row in rows:
                        questions.append({
                            'id': row[0],
                            'text': row[1],
                            'priority': row[2]
                        })
                    
                    return questions
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"❌ 获取分类问题失败: {e}", exc_info=True)
            return []
    
    async def ask_question(
        self,
        session_id: str,
        question: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        提问并生成答案（流式）
        
        Args:
            session_id: 会话ID
            question: 用户问题
        
        Yields:
            dict: 包含 type 和 content 的字典
        """
        try:
            # 1. 获取会话信息
            session = await self._get_session(session_id)
            if not session:
                yield {
                    'type': 'error',
                    'content': '会话不存在或已过期'
                }
                return
            
            solar_date = session['solar_date']
            solar_time = session['solar_time']
            gender = session['gender']
            user_id = session.get('user_id', 'anonymous')
            
            # 2. 获取对话历史（用于意图识别 context）
            conversation_history = await self._get_conversation_history(session_id)
            
            # 3. 意图识别（阶段5优化：如果category明确，可选跳过意图识别）
            # Category到规则类型的映射（参考 smart_fortune.py）
            CATEGORY_TO_RULE_TYPE = {
                "事业财富": "wealth",
                "婚姻": "marriage",
                "健康": "health",
                "子女": "children",
                "流年运势": "general",
                "年运报告": "general",
                "career_wealth": "wealth",
                "marriage": "marriage",
                "health": "health",
                "children": "children",
                "liunian": "general",
                "yearly_report": "general"
            }
            
            current_category = session.get('current_category', '')
            
            # 如果对话历史中有明确的 category，跳过意图识别
            if current_category:
                rule_type = CATEGORY_TO_RULE_TYPE.get(current_category, "general")
                intent_result = {
                    "intents": [rule_type],
                    "rule_types": [rule_type],
                    "confidence": 1.0,  # 直接使用category，置信度为1.0
                    "is_fortune_related": True,
                    "time_intent": {}
                }
                logger.info(f"✅ 使用category跳过意图识别: category={current_category}, rule_type={rule_type}")
            else:
                # 进行意图识别（传递对话历史 context）
                previous_intents = []
                for h in conversation_history[-5:]:
                    intent_result = h.get('intent_result', {})
                    if isinstance(intent_result, str):
                        try:
                            intent_result = json.loads(intent_result)
                        except:
                            intent_result = {}
                    intents = intent_result.get('intents', []) if isinstance(intent_result, dict) else []
                    previous_intents.append(intents)
                
                context = {
                    'previous_questions': [h['question'] for h in conversation_history[-5:]],  # 最近5轮
                    'previous_answers': [h['answer'] for h in conversation_history[-5:] if h.get('answer')],
                    'previous_intents': previous_intents,
                    'current_category': current_category
                }
                
                # 确保意图识别客户端已初始化
                intent_client = self._ensure_intent_client()
                if not intent_client:
                    error_msg = {
                        'type': 'error',
                        'content': '意图识别服务不可用，请稍后重试'
                    }
                    yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                    return
                
                intent_result = intent_client.classify(
                    question=question,
                    user_id=user_id,
                    context=context,  # ⚠️ 关键：传递对话历史
                    use_cache=True
                )
                
                logger.info(f"✅ 意图识别完成: {intent_result.get('intents', [])}, 置信度: {intent_result.get('confidence', 0)}")
            
            # 4. 从 session 缓存获取数据（阶段1优化：避免重复计算）
            from server.services.bazi_session_service import BaziSessionService
            cached_data = BaziSessionService.get_bazi_session(user_id)
            
            if not cached_data:
                # 如果缓存不存在，降级到重新计算（防御性处理）
                logger.warning(f"⚠️ 会话缓存不存在，降级到重新计算: user_id={user_id}")
                modules = {
                    'bazi': True,
                    'wangshuai': True,
                    'dayun': {'mode': 'current_with_neighbors'},
                    'liunian': True,
                    'rules': {'types': intent_result.get('rule_types', [])},
                    'special_liunian': True
                }
                
                cached_data = await BaziDataOrchestrator.fetch_data(
                    solar_date=solar_date,
                    solar_time=solar_time,
                    gender=gender,
                    modules=modules,
                    use_cache=True,
                    parallel=True
                )
                
                # 保存到缓存
                BaziSessionService.save_bazi_session(user_id, cached_data)
            
            # 5. 验证数据完整性
            is_valid, validation_error = self._validate_input_data(cached_data)
            if not is_valid:
                yield {
                    'type': 'error',
                    'content': f'数据不完整: {validation_error}'
                }
                return
            
            # 6. 提取数据
            bazi_data = validate_bazi_data(cached_data.get('bazi', {}).get('bazi', cached_data.get('bazi', {})))
            wangshuai_data = cached_data.get('wangshuai', {})
            dayun_sequence = cached_data.get('dayun', {}).get('sequence', [])
            liunian_sequence = cached_data.get('liunian', {}).get('sequence', [])
            
            # 处理规则数据（可能是列表或字典）
            # 如果意图识别指定了规则类型，过滤规则；否则使用所有规则
            rules_data = cached_data.get('rules', [])
            if isinstance(rules_data, dict):
                matched_rules = rules_data.get('matched', [])
            elif isinstance(rules_data, list):
                matched_rules = rules_data
            else:
                matched_rules = []
            
            # 根据意图过滤规则（如果需要）
            rule_types = intent_result.get('rule_types', [])
            if rule_types and 'ALL' not in rule_types:
                matched_rules = [r for r in matched_rules if r.get('rule_type') in rule_types]
            
            # 7. 构建结构化数据（优先使用数据库格式定义）
            try:
                from server.config.input_format_loader import build_input_data_from_result
                input_data = build_input_data_from_result(
                    format_name='qa_conversation',
                    bazi_data=bazi_data,
                    detail_result={'dayun_sequence': dayun_sequence, 'liunian_sequence': liunian_sequence},
                    wangshuai_result=wangshuai_data,
                    rule_result={'matched_rules': matched_rules},
                    user_question=question,
                    intent=intent_result.get('intents', []),
                    conversation_context={
                        'previous_questions': context['previous_questions'],
                        'previous_answers': context['previous_answers'],
                        'current_category': context['current_category']
                    }
                )
                logger.info("✅ 使用数据库格式定义构建 input_data: qa_conversation")
            except Exception as e:
                # 降级到硬编码结构
                logger.warning(f"⚠️ 格式定义构建失败，使用硬编码结构: {e}")
                input_data = {
                    'user_question': question,
                    'bazi_data': bazi_data,
                    'wangshuai': wangshuai_data,
                    'dayun_sequence': dayun_sequence,
                    'liunian_sequence': liunian_sequence,
                    'matched_rules': matched_rules,
                    'intent': intent_result.get('intents', []),
                    'conversation_context': {
                        'previous_questions': context['previous_questions'],
                        'previous_answers': context['previous_answers'],
                        'current_category': context['current_category']
                    }
                }
            
            # 8. 使用方案2：format_input_data_for_coze（提示词在 Coze Bot 中）
            formatted_data = self.format_input_data_for_coze(input_data)
            
            logger.info(f"📝 格式化数据大小: {len(formatted_data)}字符")
            
            # 9. 调用 Coze API 生成答案（流式，使用方案2）
            # 阶段3优化：并行生成问题（答案生成到150字时开始）
            answer_parts = []
            questions_task = None  # 后台任务
            cached_questions = []  # 缓存的问题
            
            async for chunk in self.coze_service.stream_custom_analysis(formatted_data, bot_id=self.analysis_bot_id):
                if chunk.get('type') == 'progress':
                    content = chunk.get('content', '')
                    if content:
                        answer_parts.append(content)
                        yield chunk
                        
                        # 当累积内容达到150字时，开始并行生成问题
                        current_answer = ''.join(answer_parts)
                        if not questions_task and len(current_answer) >= 150:
                            questions_task = asyncio.create_task(
                                self.question_generator.generate_questions_after_answer(
                                    user_question=question,
                                    answer=current_answer[:200],  # 只传递前200字
                                    bazi_data=bazi_data,
                                    intent_result=intent_result,
                                    conversation_history=conversation_history
                                )
                            )
                            logger.info("✅ 开始并行生成相关问题（答案已输出150字）")
                elif chunk.get('type') == 'complete':
                    answer_parts.append(chunk.get('content', ''))
                    yield chunk
                    break
                elif chunk.get('type') == 'error':
                    yield chunk
                    return
            
            answer = ''.join(answer_parts)
            
            # 10. 处理相关问题（并行生成或等待完成）
            if not answer or len(answer.strip()) < 50:
                logger.warning("详细回答内容为空或太短，跳过相关问题生成")
                cached_questions = []
            else:
                # 如果已经启动了并行任务，等待完成
                if questions_task:
                    if not questions_task.done():
                        logger.info("⏳ 答案已完成，等待问题生成完成...")
                        try:
                            cached_questions = await questions_task
                        except Exception as e:
                            logger.error(f"并行生成相关问题失败: {e}", exc_info=True)
                            cached_questions = []
                    else:
                        # 问题已经生成完成
                        try:
                            cached_questions = questions_task.result()
                        except Exception as e:
                            logger.error(f"获取并行生成的问题失败: {e}", exc_info=True)
                            cached_questions = []
                    
                    # 如果并行生成失败，使用降级方案
                    if not cached_questions:
                        logger.warning("并行生成问题失败，使用降级方案")
                        cached_questions = await self.question_generator.generate_questions_after_answer(
                            user_question=question,
                            answer=answer,
                            bazi_data=bazi_data,
                            intent_result=intent_result,
                            conversation_history=conversation_history
                        )
                else:
                    # 如果没有启动并行任务（答案太短），串行生成
                    logger.info(f"详细回答已完成（{len(answer)}字），开始生成相关问题")
                    cached_questions = await self.question_generator.generate_questions_after_answer(
                        user_question=question,
                        answer=answer,
                        bazi_data=bazi_data,
                        intent_result=intent_result,
                        conversation_history=conversation_history
                    )
            
            if cached_questions:
                yield {
                    'type': 'questions_after',
                    'content': cached_questions[:2]  # 只返回2个问题（根据用户提示词要求）
                }
            
            # 11. 保存对话历史
            turn_number = len(conversation_history) + 1
            await self._save_conversation_history(
                session_id=session_id,
                turn_number=turn_number,
                question=question,
                answer=answer,
                generated_questions_before=[],  # 不再生成提问前的问题
                generated_questions_after=cached_questions,
                intent_result=intent_result
            )
            
        except Exception as e:
            logger.error(f"❌ 提问处理失败: {e}", exc_info=True)
            yield {
                'type': 'error',
                'content': f'处理失败: {str(e)}'
            }
    
    def _validate_input_data(self, data: dict) -> Tuple[bool, str]:
        """验证输入数据完整性"""
        required_modules = ['bazi', 'wangshuai']
        missing_modules = []
        
        for module in required_modules:
            if module not in data or not data[module]:
                missing_modules.append(module)
        
        if missing_modules:
            return False, f"缺失模块：{', '.join(missing_modules)}"
        return True, ""
    
    def format_input_data_for_coze(self, input_data: Dict[str, Any]) -> str:
        """
        将结构化数据格式化为 JSON 字符串（用于 Coze Bot System Prompt 的 {{input}} 占位符）
        
        ⚠️ 方案2：使用占位符模板，数据不重复，节省 Token
        提示词模板已配置在 Coze Bot 的 System Prompt 中，代码只发送数据
        
        Args:
            input_data: 结构化输入数据
            
        Returns:
            str: JSON 格式的字符串，可以直接替换 {{input}} 占位符
        """
        import json
        
        # 优化数据结构，使用引用避免重复
        optimized_data = {
            'user_question': input_data.get('user_question', ''),
            'bazi_data': input_data.get('bazi_data', {}),
            'wangshuai': input_data.get('wangshuai', {}),
            'dayun_sequence': input_data.get('dayun_sequence', []),
            'liunian_sequence': input_data.get('liunian_sequence', []),
            'matched_rules': input_data.get('matched_rules', []),
            'intent': input_data.get('intent', []),
            'conversation_context': input_data.get('conversation_context', {})
        }
        
        return json.dumps(optimized_data, ensure_ascii=False, indent=2)
    
    def _build_natural_language_prompt(self, data: dict) -> str:
        """
        将 JSON 数据转换为自然语言格式的提示词
        参考 wuxing_proportion_service.py 的 build_llm_prompt 实现
        
        Args:
            data: 分析所需的完整数据
        
        Returns:
            str: 自然语言格式的提示词
        """
        prompt_lines = []
        
        # 1. 用户问题
        prompt_lines.append("【用户问题】")
        prompt_lines.append(f"{data.get('user_question', '')}")
        prompt_lines.append("")
        
        # 2. 八字信息
        bazi_data = data.get('bazi_data', {})
        prompt_lines.append("【八字信息】")
        
        # 四柱
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        if bazi_pillars:
            prompt_lines.append("四柱排盘：")
            pillar_names = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}
            for eng_name, cn_name in pillar_names.items():
                pillar = bazi_pillars.get(eng_name, {})
                stem = pillar.get('stem', '')
                branch = pillar.get('branch', '')
                if stem and branch:
                    prompt_lines.append(f"  {cn_name}：{stem}{branch}")
        
        # 十神
        ten_gods_stats = bazi_data.get('ten_gods_stats', {})
        if ten_gods_stats:
            prompt_lines.append("十神配置：")
            for key, value in ten_gods_stats.items():
                prompt_lines.append(f"  {key}：{value}")
        
        # 五行
        element_counts = bazi_data.get('element_counts', {})
        if element_counts:
            prompt_lines.append("五行分布：")
            for element, count in element_counts.items():
                prompt_lines.append(f"  {element}：{count}个")
        
        prompt_lines.append("")
        
        # 3. 旺衰信息
        wangshuai = data.get('wangshuai', {})
        if wangshuai:
            prompt_lines.append("【旺衰分析】")
            wangshuai_text = wangshuai.get('wangshuai', '')
            if wangshuai_text:
                prompt_lines.append(f"身旺身弱：{wangshuai_text}")
            prompt_lines.append("")
        
        # 4. 大运流年
        dayun_sequence = data.get('dayun_sequence', [])
        if dayun_sequence:
            prompt_lines.append("【大运序列】")
            for i, dayun in enumerate(dayun_sequence[:5], 1):  # 只显示前5个
                age_range = dayun.get('age_range', {})
                age_str = f"{age_range.get('start', '')}-{age_range.get('end', '')}岁" if age_range else ""
                prompt_lines.append(f"  第{i}步大运：{dayun.get('dayun', '')} {age_str}")
            prompt_lines.append("")
        
        liunian_sequence = data.get('liunian_sequence', [])
        if liunian_sequence:
            prompt_lines.append("【流年序列】")
            for liunian in liunian_sequence[:5]:  # 只显示前5个
                prompt_lines.append(f"  {liunian.get('year', '')}年：{liunian.get('liunian', '')}")
            prompt_lines.append("")
        
        # 5. 规则匹配结果
        matched_rules = data.get('matched_rules', [])
        if matched_rules:
            prompt_lines.append("【规则匹配结果】")
            for rule in matched_rules[:10]:  # 只显示前10个
                rule_type = rule.get('rule_type', '')
                content = rule.get('content', {})
                if isinstance(content, dict):
                    text = content.get('text', '')
                    if text:
                        prompt_lines.append(f"  {rule_type}：{text[:100]}...")
            prompt_lines.append("")
        
        # 6. 对话上下文
        conversation_context = data.get('conversation_context', {})
        previous_questions = conversation_context.get('previous_questions', [])
        if previous_questions:
            prompt_lines.append("【对话历史】")
            for i, q in enumerate(previous_questions[-3:], 1):  # 只显示最近3轮
                prompt_lines.append(f"  问题{i}：{q}")
            prompt_lines.append("")
        
        return '\n'.join(prompt_lines)
    
    # ⚠️ 已废弃：_build_natural_language_prompt 方法（方案1已废弃，使用方案2：format_input_data_for_coze）
    # 保留此方法仅用于向后兼容，新代码应使用 format_input_data_for_coze
    
    async def _get_initial_question(self) -> str:
        """获取初始问题"""
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """SELECT question_text FROM qa_question_templates 
                           WHERE category = 'initial' AND enabled = 1 
                           ORDER BY priority ASC, id ASC LIMIT 1"""
                    )
                    row = cursor.fetchone()
                    if row:
                        return row[0]
                    return "看了命盘解读，你是最关注哪一方面呢"
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"获取初始问题失败: {e}")
            return "看了命盘解读，你是最关注哪一方面呢"
    
    async def _get_categories(self) -> List[Dict[str, str]]:
        """获取分类列表"""
        categories = [
            {'key': 'career_wealth', 'name': '事业财富'},
            {'key': 'marriage', 'name': '婚姻'},
            {'key': 'health', 'name': '健康'},
            {'key': 'children', 'name': '子女'},
            {'key': 'liunian', 'name': '流年运势'},
            {'key': 'yearly_report', 'name': '年运报告'},
        ]
        return categories
    
    async def _get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
        
        Returns:
            会话信息字典，如果不存在则返回 None
        """
        if not session_id:
            logger.warning(f"⚠️ 获取会话信息失败: session_id 为空")
            return None
        
        conn = None
        try:
            logger.debug(f"🔄 开始查询会话信息: {session_id}")
            
            # 获取数据库连接
            try:
                conn = get_mysql_connection()
                if not conn:
                    raise Exception("无法获取数据库连接")
            except Exception as conn_error:
                logger.error(f"❌ 数据库连接失败: {conn_error}, session_id: {session_id}", exc_info=True)
                return None
            
            try:
                with conn.cursor() as cursor:
                    # 执行查询
                    cursor.execute(
                        """SELECT user_id, solar_date, solar_time, gender, current_category, created_at, updated_at
                           FROM qa_conversation_sessions 
                           WHERE session_id = %s""",
                        (session_id,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        session_data = {
                            'user_id': row[0],
                            'solar_date': row[1],
                            'solar_time': row[2],
                            'gender': row[3],
                            'current_category': row[4],
                            'created_at': row[5].isoformat() if row[5] else None,
                            'updated_at': row[6].isoformat() if row[6] else None
                        }
                        logger.info(f"✅ 会话查询成功: {session_id}, 用户: {session_data.get('user_id')}, 创建时间: {session_data.get('created_at')}")
                        return session_data
                    else:
                        logger.warning(f"⚠️ 会话不存在: {session_id}")
                        return None
            except Exception as query_error:
                logger.error(f"❌ 查询会话信息失败: {query_error}, session_id: {session_id}", exc_info=True)
                return None
            finally:
                if conn:
                    return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"❌ 获取会话信息异常: {e}, session_id: {session_id}", exc_info=True)
            return None
    
    async def _validate_session(self, session_id: str) -> Dict[str, Any]:
        """
        验证会话是否存在
        
        Args:
            session_id: 会话ID
        
        Returns:
            {
                'valid': bool,
                'session_id': str,
                'exists': bool,
                'session_data': Optional[Dict],
                'error': Optional[str]
            }
        """
        if not session_id:
            return {
                'valid': False,
                'session_id': session_id or '',
                'exists': False,
                'session_data': None,
                'error': 'session_id 为空'
            }
        
        try:
            session_data = await self._get_session(session_id)
            if session_data:
                return {
                    'valid': True,
                    'session_id': session_id,
                    'exists': True,
                    'session_data': session_data,
                    'error': None
                }
            else:
                return {
                    'valid': False,
                    'session_id': session_id,
                    'exists': False,
                    'session_data': None,
                    'error': '会话不存在或已过期'
                }
        except Exception as e:
            logger.error(f"❌ 验证会话失败: {e}, session_id: {session_id}", exc_info=True)
            return {
                'valid': False,
                'session_id': session_id,
                'exists': False,
                'session_data': None,
                'error': f'验证会话时发生错误: {str(e)}'
            }
    
    async def _get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """获取对话历史"""
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """SELECT turn_number, question, answer, generated_questions_before, 
                                  generated_questions_after, intent_result, category 
                           FROM qa_conversation_history 
                           WHERE session_id = %s 
                           ORDER BY turn_number ASC""",
                        (session_id,)
                    )
                    rows = cursor.fetchall()
                    
                    history = []
                    for row in rows:
                        history.append({
                            'turn_number': row[0],
                            'question': row[1],
                            'answer': row[2],
                            'generated_questions_before': json.loads(row[3]) if row[3] else [],
                            'generated_questions_after': json.loads(row[4]) if row[4] else [],
                            'intent_result': json.loads(row[5]) if row[5] else {},
                            'category': row[6]
                        })
                    
                    return history
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []
    
    async def _save_conversation_history(
        self,
        session_id: str,
        turn_number: int,
        question: str,
        answer: str,
        generated_questions_before: List[str],
        generated_questions_after: List[str],
        intent_result: Dict[str, Any]
    ):
        """保存对话历史"""
        try:
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO qa_conversation_history 
                           (session_id, turn_number, question, answer, generated_questions_before, 
                            generated_questions_after, intent_result, category) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            session_id,
                            turn_number,
                            question,
                            answer,
                            json.dumps(generated_questions_before, ensure_ascii=False),
                            json.dumps(generated_questions_after, ensure_ascii=False),
                            json.dumps(intent_result, ensure_ascii=False),
                            intent_result.get('intents', ['general'])[0] if intent_result.get('intents') else 'general'
                        )
                    )
                    conn.commit()
            finally:
                return_mysql_connection(conn)
        except Exception as e:
            logger.error(f"保存对话历史失败: {e}", exc_info=True)

