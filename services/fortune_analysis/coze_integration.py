#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coze API 集成模块
用于 AI 增强分析
"""

import os
import sys
import requests
import json
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = BASE_DIR
sys.path.insert(0, PROJECT_ROOT)

# 导入配置加载器（从数据库读取配置）
try:
    from shared.config.config_loader import get_config_from_db_only
except ImportError:
    # 如果导入失败，抛出错误（不允许降级）
    def get_config_from_db_only(key: str) -> Optional[str]:
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")


class CozeIntegration:
    """Coze API 集成"""
    
    def __init__(self):
        # 只从数据库读取，不降级到环境变量
        self.access_token = get_config_from_db_only("COZE_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError("数据库配置缺失: COZE_ACCESS_TOKEN，请在 service_configs 表中配置")
        
        self.bot_id = get_config_from_db_only("COZE_BOT_ID")
        if not self.bot_id:
            raise ValueError("数据库配置缺失: COZE_BOT_ID，请在 service_configs 表中配置")
        # Coze API 基础地址（不包含版本号）
        api_base_env = os.getenv("COZE_API_BASE", "https://api.coze.cn")
        # 移除可能的版本号
        self.api_base = api_base_env.rstrip('/').replace('/v1', '').replace('/v2', '')
        
        if not self.access_token or not self.bot_id:
            print("⚠️  Coze API 配置未找到，AI 增强功能将不可用")
            return
        
        # 设置请求头（与 bazi_ai_analyzer.py 保持一致）
        if self.access_token.startswith("pat_"):
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        else:
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        
        # 也准备一个使用 PAT 前缀的认证头
        self.headers_pat = {
            "Authorization": f"PAT {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def enhance_analysis(self, analysis_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        使用 Coze API 增强分析
        
        Args:
            analysis_data: 分析数据
            
        Returns:
            增强后的分析结果
        """
        if not self.access_token or not self.bot_id:
            return None
        
        try:
            # 准备提示词
            prompt = self._prepare_prompt(analysis_data)
            
            # 调用 Coze API
            result = self._call_coze_api(prompt, analysis_data)
            
            return result
            
        except Exception as e:
            print(f"⚠️  Coze API 调用失败: {e}")
            return None
    
    def _prepare_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """准备提示词"""
        analysis_type = analysis_data.get("type", "unknown")
        features = analysis_data.get("features", {})
        insights = analysis_data.get("insights", [])
        bazi_data = analysis_data.get("bazi_data")
        
        prompt_parts = []
        
        if analysis_type == "hand":
            prompt_parts.append("请基于以下手相分析结果，提供更深入的命理分析：")
            prompt_parts.append(f"手型：{features.get('hand_shape', '未知')}")
            prompt_parts.append(f"掌纹：{json.dumps(features.get('palm_lines', {}), ensure_ascii=False)}")
        elif analysis_type == "face":
            prompt_parts.append("请基于以下面相分析结果，提供更深入的命理分析：")
            prompt_parts.append(f"三停比例：{json.dumps(features.get('san_ting_ratio', {}), ensure_ascii=False)}")
        
        if insights:
            prompt_parts.append("初步分析结果：")
            for insight in insights[:5]:  # 只取前5个
                prompt_parts.append(f"- {insight.get('content', '')}")
        
        if bazi_data:
            prompt_parts.append("八字信息：")
            prompt_parts.append(f"四柱：{json.dumps(bazi_data.get('bazi_pillars', {}), ensure_ascii=False)}")
            prompt_parts.append(f"五行：{json.dumps(bazi_data.get('element_counts', {}), ensure_ascii=False)}")
        
        prompt_parts.append("\n请提供：")
        prompt_parts.append("1. 更深入的性格分析")
        prompt_parts.append("2. 事业建议")
        prompt_parts.append("3. 健康建议")
        prompt_parts.append("4. 财运建议")
        prompt_parts.append("5. 综合命理分析")
        
        return "\n".join(prompt_parts)
    
    def _call_coze_api(self, prompt: str, analysis_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用 Coze API（使用与 bazi_ai_analyzer.py 相同的逻辑）"""
        try:
            # Coze API 端点（根据官方文档）
            possible_endpoints = [
                "/open_api/v2/chat",  # Coze v2 标准端点（最可能正确）
                "/open_api/v2/chat/completions",  # 类似 OpenAI 格式
                "/v2/chat",            # 简化 v2 格式
                "/open_api/v1/chat",  # Coze v1 格式
                "/api/v1/chat",        # API v1 格式
                "/v1/chat",            # 简化格式
                "/chat"                # 最简格式
            ]
            
            # 尝试不同的端点和 payload 格式
            last_error = None
            url = None
            
            # 使用正确的 payload 格式（根据测试，使用 user 字段）
            payload_formats = [
                # 格式1: 使用 user 字段（Coze 标准格式，已验证可用）
                {
                    "bot_id": str(self.bot_id),
                    "user": "fortune_analysis",
                    "query": prompt,
                    "stream": False
                },
                # 格式2: 不包含 stream
                {
                    "bot_id": str(self.bot_id),
                    "user": "fortune_analysis",
                    "query": prompt
                },
                # 格式3: 最简格式
                {
                    "bot_id": str(self.bot_id),
                    "query": prompt
                }
            ]
            
            # 尝试不同的端点和 payload 格式
            for endpoint in possible_endpoints:
                test_url = f"{self.api_base}{endpoint}"
                
                for payload in payload_formats:
                    # 清理 payload，移除 None 值
                    clean_payload = {k: v for k, v in payload.items() if v is not None}
                    
                    # 尝试两种认证方式
                    for headers_to_use in [self.headers, self.headers_pat]:
                        try:
                            response = requests.post(test_url, headers=headers_to_use, json=clean_payload, timeout=30)
                            
                            if response.status_code == 200:
                                result = response.json()
                                if "code" in result and result.get("code") != 0:
                                    # 有错误码，尝试下一个格式
                                    error_msg = result.get("msg", "未知错误")
                                    if "not a valid json" in error_msg or "chat request" in error_msg:
                                        # 格式错误，继续尝试下一个格式
                                        continue
                                    # 其他错误，记录但继续尝试
                                    last_error = error_msg
                                    continue
                                # 成功
                                parsed_result = self._parse_coze_response(result)
                                if parsed_result:
                                    return parsed_result
                                # 如果解析失败，继续尝试
                            elif response.status_code == 401 or response.status_code == 403:
                                # 认证失败，记录错误
                                try:
                                    error_detail = response.json()
                                    error_msg = error_detail.get("msg", response.text[:200])
                                    last_error = f"认证失败: {error_msg}"
                                except:
                                    last_error = f"认证失败: {response.text[:200]}"
                                continue
                            elif response.status_code == 404:
                                # 端点不存在，跳出 payload 循环，尝试下一个端点
                                break
                        except Exception as e:
                            last_error = str(e)
                            continue
            
            # 所有尝试都失败
            print(f"⚠️  所有 Coze API 端点都失败，最后错误: {last_error}")
            print(f"💡 提示：请检查 Token 是否正确，Bot 是否已发布")
            return None
            
        except Exception as e:
            print(f"⚠️  Coze API 调用异常: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_coze_response(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析 Coze API 响应"""
        try:
            content = None
            
            # 根据实际测试，Coze API 返回格式是 messages 数组
            if "messages" in result:
                messages = result.get("messages", [])
                # 查找 role 为 assistant 且 type 为 answer 的消息
                for msg in reversed(messages):  # 从后往前找，找到最后一个
                    if msg.get("role") == "assistant" and msg.get("type") == "answer":
                        content = msg.get("content", "")
                        if content:
                            break
                # 如果没找到，取最后一个消息
                if not content and messages:
                    content = messages[-1].get("content", "")
            
            # 尝试其他可能的格式
            if not content:
                if "data" in result and result["data"]:
                    # 格式1: data.messages[].content
                    messages = result["data"].get("messages", [])
                    if messages:
                        content = messages[-1].get("content", "")
                    # 格式2: data.content
                    if not content:
                        content = result["data"].get("content", "")
            
            # 格式3: 直接 content
            if not content:
                content = result.get("content", "")
            
            # 格式4: message
            if not content:
                content = result.get("message", "")
            
            # 格式5: text
            if not content:
                content = result.get("text", "")
            
            # 格式6: answer
            if not content:
                content = result.get("answer", "")
            
            if content:
                # 解析 AI 返回的内容
                enhanced_insights = self._parse_ai_response(content)
                
                return {
                    "enhanced_insights": enhanced_insights,
                    "raw_response": content
                }
            
            return None
            
        except Exception as e:
            print(f"⚠️  解析 Coze 响应失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_ai_response(self, content: str) -> List[Dict[str, Any]]:
        """解析 AI 响应"""
        insights = []
        
        # 简单解析：按行分割
        lines = content.split("\n")
        current_category = "综合"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测类别
            if "性格" in line or "性格分析" in line:
                current_category = "性格"
            elif "事业" in line or "事业建议" in line:
                current_category = "事业"
            elif "健康" in line or "健康建议" in line:
                current_category = "健康"
            elif "财运" in line or "财运建议" in line:
                current_category = "财运"
            elif "综合" in line or "命理分析" in line:
                current_category = "综合"
            
            # 提取洞察（简单实现）
            if line.startswith("-") or line.startswith("•") or line.startswith("1.") or line.startswith("2."):
                content_text = line.lstrip("- •1234567890. ")
                if len(content_text) > 10:  # 过滤太短的内容
                    insights.append({
                        "category": current_category,
                        "content": content_text,
                        "confidence": 0.8,
                        "source": "ai"
                    })
        
        # 如果没有解析到，使用整个内容作为综合洞察
        if not insights and content:
            insights.append({
                "category": "综合",
                "content": content[:500],  # 限制长度
                "confidence": 0.8,
                "source": "ai"
            })
        
        return insights

