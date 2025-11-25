# -*- coding: utf-8 -*-
"""
Intent Service gRPC 服务器
"""
import grpc
from concurrent import futures
import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from proto import intent_pb2, intent_pb2_grpc
from services.intent_service.question_filter import QuestionFilter
from services.intent_service.classifier import IntentClassifier
from services.intent_service.config import SERVICE_HOST, SERVICE_PORT, PROMPT_VERSION
from services.intent_service.logger import logger


class IntentServiceImpl(intent_pb2_grpc.IntentServiceServicer):
    """Intent Service 实现"""
    
    def __init__(self):
        self.question_filter = QuestionFilter()
        self.classifier = IntentClassifier()
        logger.info("IntentServiceImpl initialized")
    
    def Classify(self, request, context):
        """分类用户问题"""
        try:
            question = request.question
            user_id = request.user_id or "anonymous"
            # Proto3的bool字段默认没有presence，直接使用值即可
            use_cache = True if not hasattr(request, 'use_cache') else request.use_cache
            prompt_version = request.prompt_version or PROMPT_VERSION
            
            logger.info(f"Received classify request: user={user_id}, question={question[:50]}...")
            
            start_time = time.time()
            
            # 步骤1：问题过滤
            filter_result = self.question_filter.is_fortune_related(
                question=question,
                use_cache=use_cache,
                prompt_version=prompt_version
            )
            
            # 如果问题不相关，直接返回
            if not filter_result.get("is_fortune_related", True):
                logger.info(f"Question filtered as non-fortune-related")
                return intent_pb2.ClassifyResponse(
                    intents=["non_fortune"],
                    confidence=filter_result.get("confidence", 0.9),
                    rule_types=[],
                    keywords=[],
                    reasoning=filter_result.get("reasoning", "Not fortune-related"),
                    is_ambiguous=False,
                    prompt_version=prompt_version,
                    response_time_ms=int((time.time() - start_time) * 1000),
                    time_intent=intent_pb2.TimeIntent(),
                    is_fortune_related=False,
                    reject_message=filter_result.get("suggested_response", "您的问题似乎与命理运势无关")
                )
            
            # 步骤2：意图分类
            classification_result = self.classifier.classify(
                question=question,
                use_cache=use_cache,
                prompt_version=prompt_version
            )
            
            # 构建响应（包含time_intent等新字段）
            # 提取时间意图
            time_intent_data = classification_result.get("time_intent")
            time_intent_pb = None
            if time_intent_data and isinstance(time_intent_data, dict):
                time_intent_pb = intent_pb2.TimeIntent(
                    type=time_intent_data.get("type", ""),
                    target_years=time_intent_data.get("target_years", []),
                    description=time_intent_data.get("description", ""),
                    is_explicit=time_intent_data.get("is_explicit", False)
                )
            
            response = intent_pb2.ClassifyResponse(
                intents=classification_result.get("intents", ["general"]),
                confidence=classification_result.get("confidence", 0.7),
                rule_types=classification_result.get("rule_types", ["ALL"]),
                keywords=classification_result.get("keywords", []),
                reasoning=classification_result.get("reasoning", ""),
                is_ambiguous=classification_result.get("is_ambiguous", False),
                prompt_version=classification_result.get("prompt_version", prompt_version),
                response_time_ms=classification_result.get("response_time_ms", 0),
                time_intent=time_intent_pb if time_intent_pb else intent_pb2.TimeIntent(),
                is_fortune_related=classification_result.get("is_fortune_related", True),
                reject_message=classification_result.get("reject_message", "")
            )
            
            logger.info(f"Classify successful: intents={response.intents}, confidence={response.confidence}")
            return response
            
        except Exception as e:
            logger.error(f"Classify error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return intent_pb2.ClassifyResponse(
                intents=["general"],
                confidence=0.5,
                rule_types=["ALL"],
                keywords=[],
                reasoning=f"Error: {str(e)}",
                is_ambiguous=True,
                prompt_version=PROMPT_VERSION,
                response_time_ms=0,
                time_intent=intent_pb2.TimeIntent(),
                is_fortune_related=True,
                reject_message=""
            )
    
    def BatchClassify(self, request, context):
        """批量分类"""
        try:
            logger.info(f"Received batch classify request: {len(request.requests)} questions")
            
            responses = []
            for req in request.requests:
                response = self.Classify(req, context)
                responses.append(response)
            
            return intent_pb2.BatchClassifyResponse(responses=responses)
            
        except Exception as e:
            logger.error(f"BatchClassify error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return intent_pb2.BatchClassifyResponse(responses=[])
    
    def HealthCheck(self, request, context):
        """健康检查"""
        try:
            # 检查 LLM 客户端健康状态
            is_healthy = self.classifier.llm_client.health_check()
            
            status = "healthy" if is_healthy else "unhealthy"
            logger.info(f"Health check: {status}")
            
            return intent_pb2.HealthCheckResponse(
                status=status,
                version="1.0.0",
                prompt_version=PROMPT_VERSION
            )
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return intent_pb2.HealthCheckResponse(
                status="unhealthy",
                version="1.0.0",
                prompt_version=PROMPT_VERSION
            )


def serve():
    """启动 gRPC 服务器"""
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),
        ]
    )
    
    intent_pb2_grpc.add_IntentServiceServicer_to_server(
        IntentServiceImpl(), server
    )
    
    server_address = f'{SERVICE_HOST}:{SERVICE_PORT}'
    server.add_insecure_port(server_address)
    
    logger.info(f"Intent Service starting on {server_address}...")
    server.start()
    logger.info(f"Intent Service is running on {server_address}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Intent Service shutting down...")
        server.stop(0)


if __name__ == '__main__':
    serve()

