# -*- coding: utf-8 -*-
"""
命理分析LLM客户端
专门用于调用命理分析专家Bot（7576211240901509174）
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FortuneAnalysisLLMClient:
    """
    命理分析专家Bot客户端
    
    职责：
    - 接收用户问题、意图、八字信息、流年大运数据
    - 调用Coze命理分析专家Bot
    - 返回深度命理解读和个性化建议
    """
    
    def __init__(self):
        """初始化客户端"""
        self.access_token = os.getenv("COZE_ACCESS_TOKEN")
        self.bot_id = os.getenv("FORTUNE_ANALYSIS_BOT_ID")
        self.api_base = "https://api.coze.cn/v1"
        
        if not self.access_token:
            raise ValueError("❌ COZE_ACCESS_TOKEN 未配置")
        if not self.bot_id:
            raise ValueError("❌ FORTUNE_ANALYSIS_BOT_ID 未配置")
        
        logger.info(f"✓ FortuneAnalysisLLMClient 初始化成功，Bot ID: {self.bot_id}")
    
    def analyze(
        self,
        question: str,
        intent: str,
        confidence: float,
        bazi_info: Dict[str, Any],
        fortune_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成深度命理分析
        
        Args:
            question: 用户问题
            intent: 意图类型（wealth/health/career/marriage）
            confidence: 意图识别置信度
            bazi_info: 八字信息
            fortune_context: 流年大运信息（可选）
        
        Returns:
            {
                "success": True/False,
                "analysis": "深度命理解读文本",
                "error": "错误信息（如有）"
            }
        """
        try:
            # 构建输入数据
            input_data = self._build_input_data(
                question, intent, confidence, bazi_info, fortune_context
            )
            
            # 调用Coze API
            response = self._call_coze_api(input_data)
            
            if response.get("success"):
                return {
                    "success": True,
                    "analysis": response.get("content", ""),
                    "error": None
                }
            else:
                logger.error(f"❌ Coze API返回错误: {response.get('error')}")
                return {
                    "success": False,
                    "analysis": None,
                    "error": response.get("error", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"❌ FortuneAnalysisLLMClient.analyze 异常: {e}", exc_info=True)
            return {
                "success": False,
                "analysis": None,
                "error": str(e)
            }
    
    def _build_input_data(
        self,
        question: str,
        intent: str,
        confidence: float,
        bazi_info: Dict[str, Any],
        fortune_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建传给Bot的输入数据
        
        将所有结构化数据组装成JSON格式
        """
        input_data = {
            "question": question,
            "intent": intent,
            "confidence": confidence,
            "bazi_info": {
                "solar_date": bazi_info.get("solar_date"),
                "solar_time": bazi_info.get("solar_time"),
                "gender": bazi_info.get("gender"),
                "pillars": bazi_info.get("pillars", {}),
                "day_stem": bazi_info.get("day_stem"),
                "element_counts": bazi_info.get("element_counts", {})
            }
        }
        
        # 添加流年大运信息（如果有）
        if fortune_context:
            input_data["fortune_context"] = fortune_context
        
        logger.debug(f"📊 构建的输入数据: {json.dumps(input_data, ensure_ascii=False, indent=2)}")
        
        return input_data
    
    def _call_coze_api(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用Coze Bot API
        
        Args:
            input_data: 输入数据字典
        
        Returns:
            {
                "success": True/False,
                "content": "Bot返回的文本",
                "error": "错误信息（如有）"
            }
        """
        try:
            url = f"{self.api_base}/bot/chat"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # 将input_data转为JSON字符串作为query
            query = json.dumps(input_data, ensure_ascii=False)
            
            payload = {
                "bot_id": self.bot_id,
                "user_id": "smart_fortune_user",
                "query": query,
                "stream": False
            }
            
            logger.debug(f"🔄 调用Coze API: {url}")
            logger.debug(f"📤 Payload: {json.dumps(payload, ensure_ascii=False)}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"📥 Coze API响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                # 解析Coze响应
                if result.get("code") == 0:
                    # 提取Bot的回复内容
                    messages = result.get("data", {}).get("messages", [])
                    content = ""
                    for msg in messages:
                        if msg.get("role") == "assistant" and msg.get("type") == "answer":
                            content = msg.get("content", "")
                            break
                    
                    if content:
                        logger.info("✅ Coze API调用成功，获取到分析内容")
                        return {
                            "success": True,
                            "content": content,
                            "error": None
                        }
                    else:
                        logger.warning("⚠️ Coze API响应中未找到有效内容")
                        return {
                            "success": False,
                            "content": None,
                            "error": "未找到有效内容"
                        }
                else:
                    error_msg = result.get("msg", "Unknown error")
                    logger.error(f"❌ Coze API返回错误码: {result.get('code')}, 消息: {error_msg}")
                    return {
                        "success": False,
                        "content": None,
                        "error": error_msg
                    }
            else:
                logger.error(f"❌ Coze API HTTP错误: {response.status_code}, {response.text}")
                return {
                    "success": False,
                    "content": None,
                    "error": f"HTTP {response.status_code}"
                }
        
        except requests.exceptions.Timeout:
            logger.error("❌ Coze API调用超时")
            return {
                "success": False,
                "content": None,
                "error": "API调用超时"
            }
        except Exception as e:
            logger.error(f"❌ Coze API调用异常: {e}", exc_info=True)
            return {
                "success": False,
                "content": None,
                "error": str(e)
            }


# 全局单例
_fortune_analysis_llm_client: Optional[FortuneAnalysisLLMClient] = None


def get_fortune_analysis_llm_client() -> FortuneAnalysisLLMClient:
    """获取全局FortuneAnalysisLLMClient实例"""
    global _fortune_analysis_llm_client
    if _fortune_analysis_llm_client is None:
        _fortune_analysis_llm_client = FortuneAnalysisLLMClient()
    return _fortune_analysis_llm_client

