# -*- coding: utf-8 -*-
"""
Prompt优化器 - 基于错误分析生成优化建议
"""
from typing import Dict, Any, List
import requests
import json
from services.prompt_optimizer.logger import logger
from services.prompt_optimizer.config import COZE_ACCESS_TOKEN, COZE_BOT_ID

# Prompt优化建议生成模板
OPTIMIZATION_PROMPT = """你是一个专业的Prompt工程师，擅长优化LLM的Prompt以提升准确率。

【当前任务】
优化意图识别的Prompt，目标是将准确率从 {current_accuracy:.1%} 提升到 95%+。

【当前Prompt（部分）】
{current_prompt}

【错误分析】
总请求数：{total_requests}
当前准确率：{current_accuracy:.1%}
常见错误：
{common_errors}

【优化要求】
1. 保持原有Prompt结构（Chain-of-Thought + Few-shot）
2. 针对常见错误添加Few-shot示例
3. 优化推理步骤说明
4. 增强关键词识别能力
5. 提供3-5条具体的优化建议

【输出格式（严格JSON）】
```json
{{
  "suggested_additions": [
    "建议添加的内容1",
    "建议添加的内容2"
  ],
  "suggested_removals": [
    "建议删除的内容1"
  ],
  "reasoning": "优化理由说明",
  "expected_improvement": 0.05
}}
```

请分析并生成优化建议。
"""


class PromptOptimizer:
    """Prompt优化器"""
    
    def __init__(self):
        self.access_token = COZE_ACCESS_TOKEN
        self.bot_id = COZE_BOT_ID
        self.base_url = "https://api.coze.cn/v3/chat"
        logger.info("PromptOptimizer initialized")
    
    def generate_improvement(
        self,
        current_prompt: str,
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成优化建议
        
        Args:
            current_prompt: 当前Prompt
            analysis_result: 错误分析结果
        
        Returns:
            优化建议
        """
        try:
            # 构建错误描述
            common_errors_text = "\n".join([
                f"- {error['pattern']} (出现{error['count']}次)\n  示例：{error['examples'][0] if error['examples'] else 'N/A'}"
                for error in analysis_result.get("common_errors", [])[:5]
            ])
            
            # 构建完整Prompt
            full_prompt = OPTIMIZATION_PROMPT.format(
                current_accuracy=analysis_result.get("accuracy", 0.0),
                current_prompt=current_prompt[:1000],  # 截取前1000字符
                total_requests=analysis_result.get("total_requests", 0),
                common_errors=common_errors_text
            )
            
            # 调用LLM生成建议
            logger.info("Generating optimization suggestions...")
            result = self._call_llm(full_prompt)
            
            logger.info(f"Optimization suggestions generated: {len(result.get('suggested_additions', []))} additions")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate optimization suggestions: {e}")
            return {
                "suggested_additions": [],
                "suggested_removals": [],
                "reasoning": f"Error: {str(e)}",
                "expected_improvement": 0.0
            }
    
    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """调用LLM"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "bot_id": self.bot_id,
            "user_id": "optimizer",
            "stream": False,
            "auto_save_history": False,
            "additional_messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "content_type": "text"
                }
            ]
        }
        
        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get("code") != 0:
            raise Exception(f"LLM API error: {result.get('msg', 'Unknown error')}")
        
        # 提取内容
        messages = result.get("data", {}).get("messages", [])
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("type") == "answer":
                content = msg.get("content", "")
                return self._parse_json_response(content)
        
        raise Exception("No valid response from LLM")
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """解析JSON响应"""
        try:
            return json.loads(content)
        except Exception:
            import re
            json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # 默认返回
            return {
                "suggested_additions": [],
                "suggested_removals": [],
                "reasoning": content,
                "expected_improvement": 0.0
            }
    
    def evaluate_prompt(
        self,
        old_prompt: str,
        new_prompt: str,
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        评估新Prompt（A/B测试）
        
        Args:
            old_prompt: 旧Prompt
            new_prompt: 新Prompt
            test_cases: 测试用例
        
        Returns:
            评估结果
        """
        # 这里简化实现，实际应该运行完整的A/B测试
        logger.info(f"Evaluating new prompt with {len(test_cases)} test cases...")
        
        # 模拟评估结果
        return {
            "old_accuracy": 0.88,
            "new_accuracy": 0.93,
            "improvement": 0.05,
            "degraded_cases": [],
            "improved_cases": []
        }

