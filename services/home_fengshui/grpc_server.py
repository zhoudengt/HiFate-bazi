# -*- coding: utf-8 -*-
"""居家风水 gRPC 服务器（端口 9006）"""

import sys
import os
import logging
import asyncio
from concurrent import futures
import grpc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from proto.generated import home_fengshui_pb2, home_fengshui_pb2_grpc
except ImportError:
    home_fengshui_pb2 = None
    home_fengshui_pb2_grpc = None

from analyzer import HomeFengshuiAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/home_fengshui.log'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class HomeFengshuiServicer:
    """居家风水服务实现"""

    def __init__(self):
        self.analyzer = HomeFengshuiAnalyzer()
        self._loop = asyncio.new_event_loop()
        logger.info('✅ HomeFengshuiServicer 初始化成功')

    def AnalyzeRoom(self, request, context):
        """分析房间风水"""
        try:
            logger.info(f'收到分析请求: room_type={request.room_type}, use_bazi={request.use_bazi}')

            image_bytes_list = list(request.image_data) if request.image_data else []
            if not image_bytes_list:
                return self._build_error_response('未上传房间照片')

            result = self._loop.run_until_complete(
                self.analyzer.analyze_async(
                    image_bytes_list=image_bytes_list,
                    room_type=request.room_type or 'bedroom',
                    door_direction=request.door_direction or None,
                    solar_date=request.solar_date or None,
                    solar_time=request.solar_time or None,
                    gender=request.gender or None,
                    use_bazi=request.use_bazi,
                )
            )

            if not result.get('success'):
                return self._build_error_response(result.get('error', '分析失败'))

            return self._build_success_response(result)

        except Exception as e:
            logger.error(f'AnalyzeRoom 异常: {e}', exc_info=True)
            return self._build_error_response(str(e))

    def HealthCheck(self, request, context):
        if home_fengshui_pb2:
            return home_fengshui_pb2.HealthCheckResponse(status='healthy')
        class R:
            status = 'healthy'
        return R()

    def _build_success_response(self, result: dict):
        if not home_fengshui_pb2:
            class R:
                success = True
            return R()

        furnitures = []
        for item in result.get('furnitures', []):
            furnitures.append(home_fengshui_pb2.DetectedFurniture(
                name=item.get('name', ''),
                label=item.get('label', ''),
                confidence=item.get('confidence', 0.0),
                bbox=item.get('bbox', []),
                position_zone=item.get('position_zone', ''),
                element=item.get('element', ''),
                state=item.get('state', ''),
            ))

        def build_suggestions(issues):
            result_list = []
            for s in issues:
                result_list.append(home_fengshui_pb2.FengshuiSuggestion(
                    item_name=s.get('item_name', ''),
                    item_label=s.get('item_label', ''),
                    severity=s.get('severity', ''),
                    issue=s.get('issue', ''),
                    suggestion=s.get('suggestion', ''),
                    reason=s.get('reason', ''),
                    priority=s.get('priority', ''),
                    rule_code=s.get('rule_code', ''),
                ))
            return result_list

        mingua_pb = None
        mingua_info = result.get('mingua_info')
        if mingua_info and home_fengshui_pb2:
            mingua_pb = home_fengshui_pb2.MinguaInfo(
                mingua=mingua_info.get('mingua', 0),
                mingua_name=mingua_info.get('mingua_name', ''),
                mingua_type=mingua_info.get('mingua_type', ''),
                house_type=mingua_info.get('house_type', ''),
                is_compatible=mingua_info.get('is_compatible', False),
                direction_map=mingua_info.get('direction_map', {}),
                compatibility_message=mingua_info.get('compatibility_message', ''),
            )

        kwargs = dict(
            success=True,
            furnitures=furnitures,
            critical_issues=build_suggestions(result.get('critical_issues', [])),
            suggestions=build_suggestions(result.get('suggestions', [])),
            tips=build_suggestions(result.get('tips', [])),
            overall_score=result.get('overall_score', 0),
            mingua_score=result.get('mingua_score', 0),
            summary=result.get('summary', ''),
            annotated_image_b64=result.get('annotated_image_b64', ''),
            ideal_layout_b64=result.get('ideal_layout_b64', ''),
            room_type=result.get('room_type', ''),
            door_direction=result.get('door_direction', ''),
        )
        if mingua_pb:
            kwargs['mingua_info'] = mingua_pb

        return home_fengshui_pb2.RoomAnalysisResponse(**kwargs)

    def _build_error_response(self, error: str):
        if not home_fengshui_pb2:
            class R:
                success = False
                error = ''
            r = R(); r.error = error; return r
        return home_fengshui_pb2.RoomAnalysisResponse(success=False, error=error)


def serve(port: int = 9006):
    """启动 gRPC 服务器（支持热更新）"""
    if not home_fengshui_pb2_grpc:
        logger.error('❌ proto 文件未生成，无法启动服务')
        return

    try:
        from server.hot_reload.microservice_reloader import (
            create_hot_reload_server, register_microservice_reloader,
        )

        server, reloader = create_hot_reload_server(
            service_name='home_fengshui',
            module_path='services.home_fengshui.grpc_server',
            servicer_class_name='HomeFengshuiServicer',
            add_servicer_to_server_func=home_fengshui_pb2_grpc.add_HomeFengshuiServiceServicer_to_server,
            port=port,
            server_options=[
                ('grpc.keepalive_time_ms', 300000),
                ('grpc.keepalive_timeout_ms', 20000),
            ],
            max_workers=10,
            check_interval=30,
        )

        register_microservice_reloader('home_fengshui', reloader)
        reloader.start()
        logger.info(f'🚀 居家风水服务启动在端口 {port}（热更新已启用）')
        server.start()

        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info('服务停止')
            reloader.stop()
            server.stop(0)

    except ImportError:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        servicer = HomeFengshuiServicer()
        home_fengshui_pb2_grpc.add_HomeFengshuiServiceServicer_to_server(servicer, server)
        server.add_insecure_port(f'[::]:{port}')
        logger.info(f'🚀 居家风水服务启动在端口 {port}（传统模式）')
        server.start()
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            server.stop(0)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='居家风水 gRPC 服务')
    parser.add_argument('--port', type=int, default=9006, help='服务端口')
    args = parser.parse_args()
    serve(port=args.port)
