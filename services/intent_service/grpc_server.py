# -*- coding: utf-8 -*-
"""
Intent Service gRPC 服务器
"""
import grpc
import logging

logger = logging.getLogger(__name__)
from concurrent import futures
import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# ✅ 加载环境变量（修复Token问题）
try:
    from dotenv import load_dotenv
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    
    # 1. 尝试加载 .env 文件
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        logger.info(f"✓ Intent Service 已加载 .env: {env_path}")
    else:
        logger.info(f"⚠ .env 文件不存在: {env_path}")
    
    # 2. ⭐ 同时加载 config/services.env（关键修复）
    services_env_path = os.path.join(project_root, 'config/services.env')
    if os.path.exists(services_env_path):
        load_dotenv(services_env_path, override=True)
        logger.info(f"✓ Intent Service 已加载 services.env: {services_env_path}")
    else:
        logger.info(f"⚠ services.env 文件不存在: {services_env_path}")
    
    # 3. 验证关键配置（从数据库读取）
    try:
        from shared.config.config_loader import get_config_from_db_only
        intent_bot_id = get_config_from_db_only("INTENT_BOT_ID")
        coze_token = get_config_from_db_only("COZE_ACCESS_TOKEN")
        if intent_bot_id:
            logger.info(f"✓ INTENT_BOT_ID (数据库): {intent_bot_id}")
        else:
            logger.info(f"⚠️ 警告：INTENT_BOT_ID 未在数据库中配置，将无法调用Coze API")
        if coze_token:
            logger.info(f"✓ COZE_ACCESS_TOKEN (数据库): {coze_token[:20]}...")
        else:
            logger.info(f"⚠️ 警告：COZE_ACCESS_TOKEN 未在数据库中配置，将无法调用Coze API")
    except Exception as e:
        logger.info(f"⚠️ 无法从数据库读取配置: {e}")
        
except ImportError:
    logger.info("⚠ python-dotenv 未安装，将使用系统环境变量")
except Exception as e:
    logger.info(f"⚠ 加载环境变量失败: {e}")

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
        request_id = f"req_{int(time.time() * 1000)}"
        try:
            question = request.question
            user_id = request.user_id or "anonymous"
            # Proto3的bool字段默认没有presence，直接使用值即可
            use_cache = True if not hasattr(request, 'use_cache') else request.use_cache
            prompt_version = request.prompt_version or PROMPT_VERSION
            
            logger.info(f"[{request_id}] ========== 意图识别请求开始 ==========")
            logger.info(f"[{request_id}] 📥 输入: user={user_id}, question={question}, use_cache={use_cache}, prompt_version={prompt_version}")
            
            start_time = time.time()
            
            # ==================== 步骤1：问题过滤 ====================
            logger.info(f"[{request_id}] [步骤1] 开始问题过滤...")
            filter_start = time.time()
            try:
                filter_result = self.question_filter.is_fortune_related(
                    question=question,
                    use_cache=use_cache,
                    prompt_version=prompt_version
                )
                filter_time = int((time.time() - filter_start) * 1000)
                logger.info(f"[{request_id}] [步骤1] ✅ 问题过滤完成: is_related={filter_result.get('is_fortune_related')}, "
                           f"confidence={filter_result.get('confidence', 0):.2f}, "
                           f"method={filter_result.get('filter_method', 'unknown')}, "
                           f"耗时={filter_time}ms")
                logger.info(f"[{request_id}] [步骤1] 📤 输出: {filter_result}")
            except Exception as e:
                filter_time = int((time.time() - filter_start) * 1000)
                logger.error(f"[{request_id}] [步骤1] ❌ 问题过滤失败: {e}, 耗时={filter_time}ms", exc_info=True)
                # 降级：默认认为相关
                filter_result = {
                    "is_fortune_related": True,
                    "confidence": 0.5,
                    "reasoning": f"Filter error: {str(e)}",
                    "filter_method": "error_fallback"
                }
            
            # 如果问题不相关，直接返回
            if not filter_result.get("is_fortune_related", True):
                total_time = int((time.time() - start_time) * 1000)
                logger.info(f"[{request_id}] [步骤1] ⛔ 问题不相关，直接返回，总耗时={total_time}ms")
                return intent_pb2.ClassifyResponse(
                    intents=["non_fortune"],
                    confidence=filter_result.get("confidence", 0.9),
                    rule_types=[],
                    keywords=[],
                    reasoning=filter_result.get("reasoning", "Not fortune-related"),
                    is_ambiguous=False,
                    prompt_version=prompt_version,
                    response_time_ms=total_time,
                    time_intent=intent_pb2.TimeIntent(),
                    is_fortune_related=False,
                    reject_message=filter_result.get("suggested_response", "您的问题似乎与命理运势无关")
                )
            
            # ==================== 步骤2：意图分类 ====================
            logger.info(f"[{request_id}] [步骤2] 开始意图分类...")
            classify_start = time.time()
            try:
                classification_result = self.classifier.classify(
                    question=question,
                    use_cache=use_cache,
                    prompt_version=prompt_version
                )
                classify_time = int((time.time() - classify_start) * 1000)
                logger.info(f"[{request_id}] [步骤2] ✅ 意图分类完成: intents={classification_result.get('intents')}, "
                           f"confidence={classification_result.get('confidence', 0):.2f}, "
                           f"method={classification_result.get('method', 'unknown')}, "
                           f"耗时={classify_time}ms")
                logger.info(f"[{request_id}] [步骤2] 📤 输出: {classification_result}")
            except Exception as e:
                classify_time = int((time.time() - classify_start) * 1000)
                logger.error(f"[{request_id}] [步骤2] ❌ 意图分类失败: {e}, 耗时={classify_time}ms", exc_info=True)
                # 降级：返回默认分类
                classification_result = {
                    "intents": ["general"],
                    "confidence": 0.5,
                    "rule_types": ["ALL"],
                    "keywords": [],
                    "reasoning": f"Classification error: {str(e)}",
                    "is_ambiguous": True,
                    "prompt_version": prompt_version,
                    "response_time_ms": classify_time,
                    "time_intent": {"type": "this_year", "target_years": [2025]},
                    "method": "error_fallback"
                }
            
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
            
            total_time = int((time.time() - start_time) * 1000)
            logger.info(f"[{request_id}] ========== 意图识别请求完成 ==========")
            logger.info(f"[{request_id}] 📊 总耗时: {total_time}ms (过滤={filter_time}ms, 分类={classify_time}ms)")
            logger.info(f"[{request_id}] 📤 最终输出: intents={response.intents}, confidence={response.confidence:.2f}, "
                       f"time_intent={response.time_intent.type if response.time_intent else 'N/A'}")
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
    """启动 gRPC 服务器（支持热更新）"""
    try:
        from server.hot_reload.microservice_reloader import (
            create_hot_reload_server,
            register_microservice_reloader
        )
        
        server_options = [
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),
        ]
        
        server, reloader = create_hot_reload_server(
            service_name="intent_service",
            module_path="services.intent_service.grpc_server",
            servicer_class_name="IntentServiceImpl",
            add_servicer_to_server_func=intent_pb2_grpc.add_IntentServiceServicer_to_server,
            port=SERVICE_PORT,
            server_options=server_options,
            max_workers=10,
            check_interval=30
        )
        
        register_microservice_reloader("intent_service", reloader)
        reloader.start()
        
        # create_hot_reload_server 已经绑定了端口（使用 [::]:port）
        # 如果需要使用 SERVICE_HOST，需要重新绑定
        server_address = f'{SERVICE_HOST}:{SERVICE_PORT}'
        if SERVICE_HOST != "0.0.0.0":
            # 如果指定了特定主机，需要重新绑定
            server.add_insecure_port(server_address)
        
        logger.info(f"Intent Service starting on {server_address} (热更新已启用)...")
        server.start()
        logger.info(f"Intent Service is running on {server_address}")
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("Intent Service shutting down...")
            reloader.stop()
            server.stop(0)
            
    except ImportError:
        # 降级到传统模式
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
        
        logger.info(f"Intent Service starting on {server_address} (传统模式)...")
        server.start()
        logger.info(f"Intent Service is running on {server_address}")
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("Intent Service shutting down...")
            server.stop(0)


if __name__ == '__main__':
    serve()

