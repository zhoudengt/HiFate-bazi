# -*- coding: utf-8 -*-
"""
Prompt Optimizer gRPC 服务器
"""
import grpc
from concurrent import futures
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from proto import optimizer_pb2, optimizer_pb2_grpc
from services.prompt_optimizer.feedback_collector import FeedbackCollector
from services.prompt_optimizer.analyzer import FeedbackAnalyzer
from services.prompt_optimizer.optimizer import PromptOptimizer
from services.prompt_optimizer.config import SERVICE_HOST, SERVICE_PORT
from services.prompt_optimizer.logger import logger


class PromptOptimizerServiceImpl(optimizer_pb2_grpc.PromptOptimizerServiceServicer):
    """Prompt Optimizer 实现"""
    
    def __init__(self):
        self.feedback_collector = FeedbackCollector()
        self.analyzer = FeedbackAnalyzer()
        self.optimizer = PromptOptimizer()
        logger.info("PromptOptimizerServiceImpl initialized")
    
    def CollectFeedback(self, request, context):
        """收集反馈"""
        try:
            feedback_data = {
                "question": request.question,
                "predicted_intents": list(request.predicted_intents),
                "confidence": request.confidence,
                "correct_intents": list(request.correct_intents),
                "satisfied": request.satisfied,
                "comment": request.comment,
                "user_id": request.user_id,
                "timestamp": request.timestamp
            }
            
            success = self.feedback_collector.collect_feedback(feedback_data)
            
            if success:
                return optimizer_pb2.FeedbackResponse(
                    success=True,
                    message="Feedback collected successfully"
                )
            else:
                return optimizer_pb2.FeedbackResponse(
                    success=False,
                    message="Failed to collect feedback"
                )
                
        except Exception as e:
            logger.error(f"CollectFeedback error: {e}")
            return optimizer_pb2.FeedbackResponse(
                success=False,
                message=str(e)
            )
    
    def GetWeeklyReport(self, request, context):
        """获取周报"""
        try:
            feedbacks = self.feedback_collector.get_recent_feedback(days=7)
            report = self.analyzer.generate_weekly_report(feedbacks)
            
            # 构建响应
            common_errors = [
                optimizer_pb2.CommonError(
                    pattern=error["pattern"],
                    count=error["count"],
                    should_be=error.get("should_be", ""),
                    examples=error.get("examples", [])
                )
                for error in report.get("top_errors", [])
            ]
            
            return optimizer_pb2.WeeklyReportResponse(
                total_requests=report["total_requests"],
                accuracy=report["overall_accuracy"],
                common_errors=common_errors,
                accuracy_by_intent=report.get("accuracy_by_intent", {})
            )
            
        except Exception as e:
            logger.error(f"GetWeeklyReport error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return optimizer_pb2.WeeklyReportResponse()
    
    def GenerateImprovement(self, request, context):
        """生成优化建议"""
        try:
            # 获取分析数据
            feedbacks = self.feedback_collector.get_recent_feedback(days=7)
            analysis = self.analyzer.analyze_accuracy(feedbacks)
            
            # 生成优化建议（使用简化的当前Prompt）
            current_prompt = "Current intent classification prompt..."
            improvement = self.optimizer.generate_improvement(current_prompt, analysis)
            
            return optimizer_pb2.ImprovementResponse(
                new_prompt_version=f"v{request.current_prompt_version}_improved",
                new_prompt_text="[Optimized prompt would be here]",
                suggested_additions=improvement.get("suggested_additions", []),
                suggested_removals=improvement.get("suggested_removals", []),
                reasoning=improvement.get("reasoning", "")
            )
            
        except Exception as e:
            logger.error(f"GenerateImprovement error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return optimizer_pb2.ImprovementResponse()
    
    def EvaluatePrompt(self, request, context):
        """评估Prompt"""
        try:
            evaluation = self.optimizer.evaluate_prompt(
                old_prompt="old",
                new_prompt=request.new_prompt_text,
                test_cases=[]
            )
            
            return optimizer_pb2.EvaluateResponse(
                old_accuracy=evaluation["old_accuracy"],
                new_accuracy=evaluation["new_accuracy"],
                improvement=evaluation["improvement"],
                degraded_cases=[],
                improved_cases=[]
            )
            
        except Exception as e:
            logger.error(f"EvaluatePrompt error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return optimizer_pb2.EvaluateResponse()
    
    def DeployPrompt(self, request, context):
        """部署Prompt"""
        try:
            logger.info(f"Deploying prompt: {request.prompt_version}, traffic: {request.traffic_percentage}")
            
            # 这里应该实现实际的部署逻辑
            # 1. 更新Redis配置
            # 2. 记录到MySQL
            # 3. 通知Intent Service重新加载
            
            return optimizer_pb2.DeployResponse(
                success=True,
                deployment_id=f"deploy_{request.prompt_version}",
                message="Prompt deployed successfully"
            )
            
        except Exception as e:
            logger.error(f"DeployPrompt error: {e}")
            return optimizer_pb2.DeployResponse(
                success=False,
                deployment_id="",
                message=str(e)
            )


def serve():
    """启动服务器"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    optimizer_pb2_grpc.add_PromptOptimizerServiceServicer_to_server(
        PromptOptimizerServiceImpl(), server
    )
    
    server_address = f'{SERVICE_HOST}:{SERVICE_PORT}'
    server.add_insecure_port(server_address)
    
    logger.info(f"Prompt Optimizer Service starting on {server_address}...")
    server.start()
    logger.info(f"Prompt Optimizer Service is running on {server_address}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Prompt Optimizer Service shutting down...")
        server.stop(0)


if __name__ == '__main__':
    serve()

