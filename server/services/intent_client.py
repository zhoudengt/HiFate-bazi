# -*- coding: utf-8 -*-
"""
Intent Service gRPC 客户端
"""
import grpc
import os
import sys
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from proto import intent_pb2, intent_pb2_grpc
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class IntentServiceClient:
    """Intent Service 客户端"""
    
    def __init__(self, service_url: str = None):
        """
        初始化客户端
        
        Args:
            service_url: 服务地址，默认从环境变量获取
        """
        self.service_url = service_url or os.getenv("INTENT_SERVICE_URL", "127.0.0.1:9008")
        self.channel = None
        self.stub = None
        self._connect()
    
    def _connect(self):
        """建立连接"""
        try:
            self.channel = grpc.insecure_channel(
                self.service_url,
                options=[
                    ('grpc.max_send_message_length', 50 * 1024 * 1024),
                    ('grpc.max_receive_message_length', 50 * 1024 * 1024),
                ]
            )
            self.stub = intent_pb2_grpc.IntentServiceStub(self.channel)
            logger.info(f"Intent Service client connected to {self.service_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Intent Service: {e}")
            raise
    
    def classify(
        self,
        question: str,
        user_id: str = "anonymous",
        use_cache: bool = True,
        prompt_version: str = ""
    ) -> Dict[str, Any]:
        """
        分类用户问题
        
        Args:
            question: 用户问题
            user_id: 用户ID
            use_cache: 是否使用缓存
            prompt_version: Prompt版本
        
        Returns:
            分类结果
        """
        try:
            request = intent_pb2.ClassifyRequest(
                question=question,
                user_id=user_id,
                use_cache=use_cache,
                prompt_version=prompt_version
            )
            
            response = self.stub.Classify(request, timeout=40)  # 增加超时时间以支持LLM轮询（最长30秒轮询 + 10秒缓冲）
            
            # 解析时间意图（安全访问）
            time_intent = None
            if hasattr(response, 'time_intent') and response.time_intent:
                try:
                    ti = response.time_intent
                    if hasattr(ti, 'type') and ti.type:
                        time_intent = {
                            "type": ti.type,
                            "target_years": list(ti.target_years) if hasattr(ti, 'target_years') else [],
                            "description": ti.description if hasattr(ti, 'description') else "",
                            "is_explicit": ti.is_explicit if hasattr(ti, 'is_explicit') else False
                        }
                except Exception as e:
                    logger.warning(f"Failed to parse time_intent: {e}")
            
            return {
                "intents": list(response.intents),
                "confidence": response.confidence,
                "rule_types": list(response.rule_types),
                "keywords": list(response.keywords),
                "reasoning": response.reasoning,
                "is_ambiguous": response.is_ambiguous,
                "prompt_version": response.prompt_version,
                "response_time_ms": response.response_time_ms,
                "time_intent": time_intent,
                "is_fortune_related": response.is_fortune_related if hasattr(response, 'is_fortune_related') else True,
                "reject_message": response.reject_message if (hasattr(response, 'reject_message') and response.reject_message) else None
            }
            
        except grpc.RpcError as e:
            logger.error(f"Intent Service RPC error: {e}")
            # 返回默认分类
            return {
                "intents": ["general"],
                "confidence": 0.5,
                "rule_types": ["ALL"],
                "keywords": [],
                "reasoning": f"Service error: {str(e)}",
                "is_ambiguous": True,
                "prompt_version": "",
                "response_time_ms": 0,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Intent classification error: {e}", exc_info=True)
            return {
                "intents": ["general"],
                "confidence": 0.5,
                "rule_types": ["ALL"],
                "keywords": [],
                "reasoning": f"Error: {str(e)}",
                "is_ambiguous": True,
                "prompt_version": "",
                "response_time_ms": 0,
                "error": str(e)
            }
    
    def classify_batch(self, questions: List[str]) -> List[Dict[str, Any]]:
        """批量分类"""
        try:
            requests = [
                intent_pb2.ClassifyRequest(question=q)
                for q in questions
            ]
            
            batch_request = intent_pb2.BatchClassifyRequest(requests=requests)
            response = self.stub.BatchClassify(batch_request, timeout=30)
            
            results = []
            for r in response.responses:
                results.append({
                    "intents": list(r.intents),
                    "confidence": r.confidence,
                    "rule_types": list(r.rule_types),
                    "keywords": list(r.keywords),
                    "reasoning": r.reasoning,
                    "is_ambiguous": r.is_ambiguous
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Batch classification error: {e}", exc_info=True)
            return [self.classify(q) for q in questions]
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            request = intent_pb2.HealthCheckRequest()
            response = self.stub.HealthCheck(request, timeout=5)
            return response.status == "healthy"
        except:
            return False
    
    def close(self):
        """关闭连接"""
        if self.channel:
            self.channel.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

