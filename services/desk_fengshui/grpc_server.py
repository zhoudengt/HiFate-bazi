# -*- coding: utf-8 -*-
"""
办公桌风水 gRPC 服务器
"""

import sys
import os
import logging
from concurrent import futures
import grpc

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入生成的 proto 文件
try:
    from proto.generated import desk_fengshui_pb2, desk_fengshui_pb2_grpc
except ImportError:
    print("⚠️ proto文件未生成，请先运行生成脚本")
    # 临时创建占位符
    desk_fengshui_pb2 = None
    desk_fengshui_pb2_grpc = None

from analyzer import DeskFengshuiAnalyzer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/desk_fengshui.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DeskFengshuiServicer:
    """办公桌风水服务实现"""
    
    def __init__(self):
        """初始化服务"""
        self.analyzer = DeskFengshuiAnalyzer()
        logger.info("✅ DeskFengshuiServicer 初始化成功")
    
    def AnalyzeDesk(self, request, context):
        """分析办公桌风水"""
        try:
            logger.info(f"收到分析请求: use_bazi={request.use_bazi}")
            
            # 调用分析器
            result = self.analyzer.analyze(
                image_bytes=request.image_data,
                solar_date=request.solar_date if request.solar_date else None,
                solar_time=request.solar_time if request.solar_time else None,
                gender=request.gender if request.gender else None,
                use_bazi=request.use_bazi
            )
            
            if not result.get('success'):
                return self._build_error_response(result.get('error', '分析失败'))
            
            # 构建响应
            response = self._build_success_response(result)
            
            logger.info(f"分析成功，评分: {result.get('score', 0)}")
            
            return response
            
        except Exception as e:
            logger.error(f"分析请求处理失败: {e}", exc_info=True)
            return self._build_error_response(str(e))
    
    def HealthCheck(self, request, context):
        """健康检查"""
        if desk_fengshui_pb2:
            return desk_fengshui_pb2.HealthCheckResponse(status="healthy")
        else:
            # 占位符实现
            class Response:
                status = "healthy"
            return Response()
    
    def _build_success_response(self, result: dict):
        """构建成功响应"""
        if not desk_fengshui_pb2:
            # 占位符实现
            class Response:
                success = True
                score = 0
                summary = ""
                items = []
                adjustments = []
                additions = []
                removals = []
            return Response()
        
        # 转换检测到的物品
        items = []
        for item in result.get('items', []):
            position = item.get('position', {})
            detected_item = desk_fengshui_pb2.DetectedItem(
                name=item.get('name', ''),
                label=item.get('label', ''),
                confidence=item.get('confidence', 0.0),
                bbox=item.get('bbox', []),
                relative_position=position.get('relative', ''),
                bagua_direction=position.get('bagua_direction', '')
            )
            items.append(detected_item)
        
        # 转换调整建议
        adjustments = self._build_suggestions(result.get('adjustments', []))
        additions = self._build_suggestions(result.get('additions', []))
        removals = self._build_suggestions(result.get('removals', []))
        
        # 构建响应
        response = desk_fengshui_pb2.DeskAnalysisResponse(
            success=True,
            items=items,
            adjustments=adjustments,
            additions=additions,
            removals=removals,
            score=result.get('score', 0),
            summary=result.get('summary', ''),
            xishen=result.get('xishen', ''),
            jishen=result.get('jishen', '')
        )
        
        return response
    
    def _build_suggestions(self, suggestions: list):
        """构建建议列表"""
        if not desk_fengshui_pb2:
            return []
        
        result = []
        for sugg in suggestions:
            suggestion = desk_fengshui_pb2.Suggestion(
                item=sugg.get('item', ''),
                item_label=sugg.get('item_label', ''),
                current_position=sugg.get('current_position', ''),
                ideal_position=sugg.get('ideal_position', sugg.get('position', '')),
                reason=sugg.get('reason', ''),
                priority=sugg.get('priority', ''),
                action=sugg.get('action', ''),
                element=sugg.get('element', '')
            )
            result.append(suggestion)
        
        return result
    
    def _build_error_response(self, error: str):
        """构建错误响应"""
        if not desk_fengshui_pb2:
            class Response:
                success = False
                error = ""
            resp = Response()
            resp.error = error
            return resp
        
        return desk_fengshui_pb2.DeskAnalysisResponse(
            success=False,
            error=error
        )


def serve(port: int = 9010):
    """启动 gRPC 服务器（支持热更新）"""
    if not desk_fengshui_pb2_grpc:
        logger.error("❌ proto文件未生成，无法启动服务")
        return
    
    try:
        from server.hot_reload.microservice_reloader import (
            create_hot_reload_server,
            register_microservice_reloader
        )
        
        server_options = [
            ('grpc.keepalive_time_ms', 300000),
            ('grpc.keepalive_timeout_ms', 20000),
        ]
        
        server, reloader = create_hot_reload_server(
            service_name="desk_fengshui",
            module_path="services.desk_fengshui.grpc_server",
            servicer_class_name="DeskFengshuiServicer",
            add_servicer_to_server_func=desk_fengshui_pb2_grpc.add_DeskFengshuiServiceServicer_to_server,
            port=port,
            server_options=server_options,
            max_workers=10,
            check_interval=30
        )
        
        register_microservice_reloader("desk_fengshui", reloader)
        reloader.start()
        
        # create_hot_reload_server 已经绑定了端口，不需要再次绑定
        logger.info(f"🚀 办公桌风水服务启动在端口 {port} (热更新已启用)")
        server.start()
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("服务停止")
            reloader.stop()
            server.stop(0)
            
    except ImportError:
        # 降级到传统模式
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        
        servicer = DeskFengshuiServicer()
        desk_fengshui_pb2_grpc.add_DeskFengshuiServiceServicer_to_server(servicer, server)
        
        server.add_insecure_port(f'[::]:{port}')
        
        logger.info(f"🚀 办公桌风水服务启动在端口 {port} (传统模式)")
        server.start()
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("服务停止")
            server.stop(0)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='办公桌风水 gRPC 服务')
    parser.add_argument('--port', type=int, default=9010, help='服务端口')
    
    args = parser.parse_args()
    
    serve(port=args.port)

