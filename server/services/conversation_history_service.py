# -*- coding: utf-8 -*-
"""
对话历史服务
负责：
1. 异步保存对话记录到 MySQL
2. 提取关键词（3-5个）
3. 压缩问答为摘要（一句话<100字）
4. 管理 Redis 中的历史摘要缓存（最近5轮）
"""
import json
import logging
import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 命理相关关键词库（用于关键词提取）
FORTUNE_KEYWORDS = {
    # 十神
    '正官', '七杀', '偏官', '正印', '偏印', '枭神', '正财', '偏财', 
    '食神', '伤官', '比肩', '劫财',
    # 五行
    '金', '木', '水', '火', '土', '五行',
    # 宫位
    '婚姻宫', '事业宫', '财帛宫', '子女宫', '父母宫',
    # 神煞
    '桃花', '驿马', '华盖', '天乙贵人', '文昌',
    # 运势
    '大运', '流年', '流月', '旺', '衰', '喜神', '忌神', '用神',
    # 关系
    '刑', '冲', '合', '害', '破', '三合', '六合', '相生', '相克',
    # 话题
    '婚姻', '感情', '事业', '财运', '健康', '学业', '子女', '父母',
    '二婚', '离婚', '桃花运', '正缘', '配偶', '财富', '投资',
    # 四柱
    '年柱', '月柱', '日柱', '时柱', '日主', '日干', '天干', '地支',
    # 其他
    '格局', '身旺', '身弱', '从格', '化格'
}


class ConversationHistoryService:
    """对话历史服务"""
    
    # Redis key前缀
    HISTORY_KEY_PREFIX = "conversation_history:"
    # 最大保留轮数
    MAX_HISTORY_ROUNDS = 5
    # 默认TTL：24小时
    DEFAULT_TTL = 86400
    
    @staticmethod
    def extract_keywords(question: str, answer: str = "", max_keywords: int = 5) -> List[str]:
        """
        从问题和回答中提取关键词（3-5个）
        
        Args:
            question: 用户问题
            answer: LLM回答（可选）
            max_keywords: 最大关键词数量
            
        Returns:
            关键词列表
        """
        keywords = set()
        
        # 合并文本
        text = f"{question} {answer}"
        
        # 1. 先匹配命理关键词库
        for keyword in FORTUNE_KEYWORDS:
            if keyword in text:
                keywords.add(keyword)
                if len(keywords) >= max_keywords:
                    break
        
        # 2. 如果关键词不足，尝试用jieba提取
        if len(keywords) < 3:
            try:
                import jieba
                import jieba.analyse
                # 使用TF-IDF提取关键词
                jieba_keywords = jieba.analyse.extract_tags(text, topK=max_keywords - len(keywords))
                for kw in jieba_keywords:
                    if len(kw) >= 2:  # 只保留2字以上的词
                        keywords.add(kw)
                        if len(keywords) >= max_keywords:
                            break
            except ImportError:
                logger.warning("jieba未安装，跳过额外关键词提取")
            except Exception as e:
                logger.warning(f"jieba关键词提取失败: {e}")
        
        # 3. 如果还是不足，从问题中提取名词短语
        if len(keywords) < 3:
            # 简单规则：提取中文词组
            patterns = re.findall(r'[\u4e00-\u9fa5]{2,4}', question)
            for p in patterns[:max_keywords - len(keywords)]:
                if p not in ['什么', '怎么', '如何', '是否', '能否', '会不会', '有没有']:
                    keywords.add(p)
        
        return list(keywords)[:max_keywords]
    
    @staticmethod
    def compress_to_summary(question: str, answer: str, max_length: int = 100) -> str:
        """
        将问答压缩为一句话摘要（<100字）
        
        格式：用户询问{问题关键词}，回答{结论关键词}
        
        Args:
            question: 用户问题
            answer: LLM回答
            max_length: 最大长度
            
        Returns:
            压缩后的摘要
        """
        # 提取问题关键词
        question_keywords = ConversationHistoryService.extract_keywords(question, "", max_keywords=2)
        question_part = "、".join(question_keywords) if question_keywords else question[:20]
        
        # 从回答中提取核心结论
        # 策略：提取第一段或包含关键词的句子
        answer_summary = ""
        
        if answer:
            # 按句子分割
            sentences = re.split(r'[。！？\n]', answer)
            
            # 找包含命理关键词的句子
            for sentence in sentences[:5]:  # 只看前5句
                sentence = sentence.strip()
                if len(sentence) > 10:
                    # 检查是否包含命理关键词
                    for keyword in FORTUNE_KEYWORDS:
                        if keyword in sentence:
                            answer_summary = sentence[:50]  # 截取前50字
                            break
                    if answer_summary:
                        break
            
            # 如果没找到，取第一个有意义的句子
            if not answer_summary:
                for sentence in sentences[:3]:
                    sentence = sentence.strip()
                    if len(sentence) > 15:
                        answer_summary = sentence[:50]
                        break
        
        # 构建摘要
        summary = f"用户询问{question_part}"
        if answer_summary:
            summary += f"，回答{answer_summary}"
        
        # 确保不超过最大长度
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary
    
    @staticmethod
    async def save_conversation_async(
        user_id: str,
        session_id: str,
        category: str,
        question: str,
        answer: str,
        intent: str,
        bazi_summary: str = "",
        round_number: int = 1,
        response_time_ms: int = 0,
        conversation_id: str = "",
        scenario_type: str = "scenario2"
    ) -> bool:
        """
        异步保存对话记录到 MySQL
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            category: 分类
            question: 用户问题
            answer: LLM回答
            intent: 意图
            bazi_summary: 八字摘要
            round_number: 对话轮次
            response_time_ms: 响应时间
            conversation_id: Coze对话ID
            scenario_type: 场景类型（scenario1=选择项, scenario2=问答）
            
        Returns:
            是否保存成功
        """
        try:
            # 提取关键词和生成摘要
            keywords = ConversationHistoryService.extract_keywords(question, answer)
            summary = ConversationHistoryService.compress_to_summary(question, answer)
            
            # 在事件循环中执行同步数据库操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                ConversationHistoryService._save_to_mysql,
                user_id, session_id, category, question, answer, intent,
                keywords, summary, bazi_summary, round_number, response_time_ms, conversation_id,
                scenario_type
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 异步保存对话记录失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    def _save_to_mysql(
        user_id: str,
        session_id: str,
        category: str,
        question: str,
        answer: str,
        intent: str,
        keywords: List[str],
        summary: str,
        bazi_summary: str,
        round_number: int,
        response_time_ms: int,
        conversation_id: str,
        scenario_type: str = "scenario2"
    ) -> bool:
        """
        同步保存到 MySQL（供异步调用）
        
        Args:
            scenario_type: 场景类型（scenario1=选择项, scenario2=问答）
        """
        try:
            from shared.config.database import get_mysql_connection, return_mysql_connection
            
            conn = get_mysql_connection()
            if not conn:
                logger.warning("获取MySQL连接失败，跳过保存对话记录")
                return False
            
            try:
                with conn.cursor() as cursor:
                    sql = """
                        INSERT INTO ai_conversation_history 
                        (user_id, session_id, category, scenario_type, question, answer, intent, 
                         keywords, summary, bazi_summary, round_number, response_time_ms, conversation_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (
                        user_id, session_id, category, scenario_type, question, answer, intent,
                        json.dumps(keywords, ensure_ascii=False),
                        summary, bazi_summary, round_number, response_time_ms, conversation_id
                    ))
                conn.commit()
                logger.info(f"✅ 保存对话记录成功: user_id={user_id}, scenario={scenario_type}, round={round_number}, keywords={keywords}")
                return True
            finally:
                return_mysql_connection(conn)
                
        except Exception as e:
            logger.error(f"❌ 保存对话记录到MySQL失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    def save_history_to_redis(
        user_id: str,
        round_data: Dict[str, Any],
        max_rounds: int = 5
    ) -> bool:
        """
        保存历史摘要到 Redis（用于传递给LLM）
        
        Args:
            user_id: 用户ID
            round_data: 单轮数据 {round: int, keywords: [], summary: str}
            max_rounds: 最大保留轮数
            
        Returns:
            是否保存成功
        """
        try:
            from shared.config.redis import get_redis_client
            
            redis_client = get_redis_client()
            if not redis_client:
                logger.warning("Redis不可用，无法保存历史摘要")
                return False
            
            key = f"{ConversationHistoryService.HISTORY_KEY_PREFIX}{user_id}"
            
            # 获取现有历史
            existing = redis_client.get(key)
            if existing:
                if isinstance(existing, bytes):
                    existing = existing.decode('utf-8')
                history = json.loads(existing)
            else:
                history = []
            
            # 添加新的一轮
            history.append(round_data)
            
            # 保留最近N轮
            if len(history) > max_rounds:
                history = history[-max_rounds:]
            
            # 保存回Redis
            redis_client.setex(
                key,
                ConversationHistoryService.DEFAULT_TTL,
                json.dumps(history, ensure_ascii=False)
            )
            
            logger.info(f"✅ 保存历史摘要到Redis: user_id={user_id}, total_rounds={len(history)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存历史摘要到Redis失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_history_from_redis(user_id: str) -> List[Dict[str, Any]]:
        """
        从 Redis 获取历史摘要
        
        Args:
            user_id: 用户ID
            
        Returns:
            历史摘要列表 [{round: int, keywords: [], summary: str}, ...]
        """
        try:
            from shared.config.redis import get_redis_client
            
            redis_client = get_redis_client()
            if not redis_client:
                logger.warning("Redis不可用，无法获取历史摘要")
                return []
            
            key = f"{ConversationHistoryService.HISTORY_KEY_PREFIX}{user_id}"
            
            data = redis_client.get(key)
            if not data:
                return []
            
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            history = json.loads(data)
            logger.info(f"✅ 获取历史摘要: user_id={user_id}, rounds={len(history)}")
            return history
            
        except Exception as e:
            logger.error(f"❌ 获取历史摘要失败: {e}", exc_info=True)
            return []
    
    @staticmethod
    def clear_history(user_id: str) -> bool:
        """
        清除用户的历史摘要（开始新对话时调用）
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否清除成功
        """
        try:
            from shared.config.redis import get_redis_client
            
            redis_client = get_redis_client()
            if not redis_client:
                return False
            
            key = f"{ConversationHistoryService.HISTORY_KEY_PREFIX}{user_id}"
            redis_client.delete(key)
            
            logger.info(f"✅ 清除历史摘要: user_id={user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 清除历史摘要失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_current_round(user_id: str) -> int:
        """
        获取当前对话轮次
        
        Args:
            user_id: 用户ID
            
        Returns:
            当前轮次（从1开始）
        """
        history = ConversationHistoryService.get_history_from_redis(user_id)
        return len(history) + 1

