# -*- coding: utf-8 -*-
"""
问题过滤器 - 判断问题是否与命理相关
优化策略：关键词快速过滤 → LLM深度判断
"""
from typing import Dict, Any
from services.intent_service.llm_client import IntentLLMClient
from services.intent_service.logger import logger

# ==================== 关键词快速过滤配置 ====================

# 命理相关关键词（白名单）- 命中即通过
FORTUNE_KEYWORDS = {
    # 核心概念
    "运势", "财运", "事业", "婚姻", "健康", "性格", "命运", "命理", "算命", "占卜",
    "八字", "四柱", "命盘", "命局", "格局", "喜用神", "忌神", "用神", "调候",
    
    # 时间运势
    "流年", "大运", "流月", "流日", "年运", "月运", "日运", "今年", "明年", "后年",
    "本月", "下月", "今天", "明天", "最近",
    
    # 十神
    "正官", "偏官", "七杀", "正印", "偏印", "枭神", "食神", "伤官", 
    "正财", "偏财", "劫财", "比肩",
    
    # 五行
    "金木水火土", "五行", "木旺", "火旺", "土旺", "金旺", "水旺",
    "木弱", "火弱", "土弱", "金弱", "水弱",
    
    # 天干地支
    "甲乙丙丁戊己庚辛壬癸", "子丑寅卯辰巳午未申酉戌亥",
    "天干", "地支", "干支",
    
    # 关系
    "生克", "刑冲", "合化", "六合", "三合", "相冲", "相刑", "相害",
    
    # 问题场景
    "适合", "能否", "是否", "怎么样", "如何", "会不会", "有没有",
    "工作", "生意", "投资", "理财", "感情", "桃花", "姻缘", "配偶",
    "身体", "疾病", "病症", "脾胃", "肝胆", "心脏", "肾", "肺",
    "性格", "脾气", "品性", "特点", "优点", "缺点",
    
    # 吉凶
    "吉", "凶", "好", "坏", "顺", "不顺", "旺", "衰", "强", "弱"
}

# 明显不相关关键词（黑名单）- 命中即拒绝
NON_FORTUNE_KEYWORDS = {
    # 日常闲聊
    "你好", "您好", "在吗", "在不在", "hi", "hello", "早上好", "晚上好",
    "谢谢", "感谢", "拜拜", "再见", "886", "88",
    "吃饭", "吃了吗", "吃什么", "喝水", "睡觉", "起床",
    
    # 天气气象
    "天气", "气温", "下雨", "晴天", "阴天", "台风", "暴雨", "雪",
    
    # 新闻资讯
    "新闻", "头条", "热点", "时事", "最新消息", "报道",
    
    # 科技编程
    "代码", "编程", "python", "java", "javascript", "bug", "debug",
    "github", "git", "代码", "函数", "变量", "算法", "数据结构",
    
    # 股票金融（注意：不包含"财运"、"投资运势"等命理相关）
    "股票代码", "股价", "涨停", "跌停", "K线", "均线", "MACD",
    "基金代码", "ETF", "期货合约",
    
    # 体育娱乐
    "游戏", "电影", "电视剧", "综艺", "音乐", "歌曲", "明星",
    "足球", "篮球", "比赛", "球队", "球员",
    
    # 美食旅游
    "餐厅", "美食", "菜谱", "做菜", "旅游", "景点", "酒店", "机票",
    
    # 技术问答
    "怎么安装", "如何下载", "怎么操作", "怎么用", "教程",
    "密码", "账号", "登录", "注册"
}

# 强命理指示词（只要包含就99%是命理问题）
STRONG_FORTUNE_INDICATORS = {
    "八字", "命理", "算命", "占卜", "运势", "流年", "大运",
    "正官", "正财", "偏财", "劫财", "食神", "伤官", "正印", "偏印",
    "喜用神", "忌神", "命局", "格局"
}

# 问题过滤 Prompt 模板
QUESTION_FILTER_PROMPT = """你是一个专业的命理学问题识别助手。

【任务】
判断用户的问题是否与命理、运势、八字相关。

【用户问题】
{question}

【判断标准】
1. **命理相关**：涉及运势、事业、财富、婚姻、健康、性格、八字、命局等
2. **不相关**：纯闲聊、天气、新闻、编程、科学、历史等

【输出格式（严格JSON）】
```json
{{
  "is_fortune_related": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "判断理由",
  "suggested_response": "如果不相关，建议的回复话术"
}}
```

【示例】
问题："我的事业运势怎么样？"
```json
{{
  "is_fortune_related": true,
  "confidence": 0.99,
  "reasoning": "明确询问事业运势",
  "suggested_response": ""
}}
```

问题："今天天气怎么样？"
```json
{{
  "is_fortune_related": false,
  "confidence": 0.98,
  "reasoning": "询问天气，与命理无关",
  "suggested_response": "抱歉，我是专业的命理分析助手，无法回答天气相关的问题。您可以询问关于运势、事业、婚姻等命理方面的问题。"
}}
```

现在请判断上述用户问题，直接返回JSON格式结果。
"""


class QuestionFilter:
    """问题过滤器"""
    
    def __init__(self):
        self.llm_client = IntentLLMClient()
        logger.info("QuestionFilter initialized")
    
    def is_fortune_related(
        self,
        question: str,
        use_cache: bool = True,
        prompt_version: str = "v1.0"
    ) -> Dict[str, Any]:
        """
        判断问题是否与命理相关（三级过滤）
        
        优化策略：
        1. 强指示词检查（0ms） - 99%是命理问题
        2. 关键词快速过滤（0ms） - 明显相关/不相关
        3. LLM深度判断（200-300ms） - 模糊情况
        
        Args:
            question: 用户问题
            use_cache: 是否使用缓存
            prompt_version: Prompt版本
        
        Returns:
            {
                "is_fortune_related": bool,
                "confidence": float,
                "reasoning": str,
                "suggested_response": str,
                "filter_method": "strong_indicator" | "keyword" | "llm"
            }
        """
        try:
            logger.info(f"[QuestionFilter] 开始过滤问题: {question[:50]}...")
            question_lower = question.lower()
            
            # ==================== 第1级：强命理指示词检查（最高优先级）====================
            for indicator in STRONG_FORTUNE_INDICATORS:
                if indicator in question:
                    logger.info(f"[QuestionFilter] ✅ 强指示词命中: '{indicator}' -> 直接通过")
                    return {
                        "is_fortune_related": True,
                        "confidence": 0.99,
                        "reasoning": f"包含强命理指示词：{indicator}",
                        "suggested_response": "",
                        "filter_method": "strong_indicator"
                    }
            
            # ==================== 第2级：黑名单快速拒绝 ====================
            # 检查是否包含明显不相关的关键词
            non_fortune_hits = []
            for keyword in NON_FORTUNE_KEYWORDS:
                if keyword in question or keyword in question_lower:
                    non_fortune_hits.append(keyword)
            
            # 如果命中黑名单且没有命理关键词，则拒绝
            if non_fortune_hits:
                # 再检查是否有命理关键词（避免误杀）
                has_fortune_keyword = any(kw in question for kw in FORTUNE_KEYWORDS)
                
                if not has_fortune_keyword:
                    logger.info(f"[QuestionFilter] ❌ 黑名单命中: {non_fortune_hits} -> 拒绝")
                    return {
                        "is_fortune_related": False,
                        "confidence": 0.95,
                        "reasoning": f"包含非命理关键词：{', '.join(non_fortune_hits[:3])}",
                        "suggested_response": "抱歉，我是专业的命理分析助手，只能回答关于运势、事业、财富、婚姻、健康等命理相关的问题。",
                        "filter_method": "keyword_blacklist"
                    }
                else:
                    logger.info(f"[QuestionFilter] ⚠️ 黑名单命中但有命理词，继续LLM判断")
            
            # ==================== 第3级：白名单快速通过 ====================
            fortune_hits = []
            for keyword in FORTUNE_KEYWORDS:
                if keyword in question:
                    fortune_hits.append(keyword)
            
            # 命中2个及以上命理关键词，直接通过
            if len(fortune_hits) >= 2:
                logger.info(f"[QuestionFilter] ✅ 白名单命中: {fortune_hits[:3]} -> 直接通过")
                return {
                    "is_fortune_related": True,
                    "confidence": 0.92,
                    "reasoning": f"包含多个命理关键词：{', '.join(fortune_hits[:3])}",
                    "suggested_response": "",
                    "filter_method": "keyword_whitelist"
                }
            
            # 命中1个命理关键词，且问题较长（>10字），也通过
            if len(fortune_hits) == 1 and len(question) >= 10:
                logger.info(f"[QuestionFilter] ✅ 白名单命中: {fortune_hits[0]} + 长问题 -> 通过")
                return {
                    "is_fortune_related": True,
                    "confidence": 0.85,
                    "reasoning": f"包含命理关键词：{fortune_hits[0]}",
                    "suggested_response": "",
                    "filter_method": "keyword_whitelist"
                }
            
            # ==================== 第4级：LLM深度判断（模糊情况）====================
            logger.info(f"[QuestionFilter] 🤖 关键词不确定，调用LLM判断...")
            
            result = self.llm_client.call_coze_api(
                question=question,
                prompt_template=QUESTION_FILTER_PROMPT,
                use_cache=use_cache,
                prompt_version=prompt_version
            )
            
            # 确保返回必需字段
            if "is_fortune_related" not in result:
                result["is_fortune_related"] = True  # 默认认为相关（降低误拒率）
            if "confidence" not in result:
                result["confidence"] = 0.5
            if "reasoning" not in result:
                result["reasoning"] = "LLM判断结果"
            if "suggested_response" not in result:
                result["suggested_response"] = ""
            
            result["filter_method"] = "llm"
            
            logger.info(f"[QuestionFilter] LLM判断: is_related={result['is_fortune_related']}, confidence={result['confidence']}")
            return result
            
        except Exception as e:
            logger.error(f"[QuestionFilter] 过滤失败: {e}")
            # 发生错误时，默认认为相关（降低误拒率）
            return {
                "is_fortune_related": True,
                "confidence": 0.5,
                "reasoning": f"Filter error: {str(e)}",
                "suggested_response": "",
                "filter_method": "error_fallback",
                "error": str(e)
            }
    
    def filter_batch(self, questions: list) -> list:
        """批量过滤问题"""
        results = []
        for question in questions:
            result = self.is_fortune_related(question)
            results.append(result)
        return results

