# -*- coding: utf-8 -*-
"""
办公桌风水主分析器
整合物品检测、方位计算、规则匹配、八字融合
支持异步处理以提升并发性能
"""

import logging
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

from item_detector import DeskItemDetector
from position_calculator import PositionCalculator
from rule_engine import DeskFengshuiEngine
from bazi_client import BaziClient
from vision_analyzer import VisionAnalyzer

logger = logging.getLogger(__name__)

# 全局线程池（优化：增加线程数，添加名称前缀）
_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="desk_fengshui")

# 超时配置
BAZI_TIMEOUT = 8  # 八字服务超时（秒）
DETECTION_TIMEOUT = 30  # 检测超时（秒）
RULE_TIMEOUT = 10  # 规则匹配超时（秒）


class DeskFengshuiAnalyzer:
    """办公桌风水分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.detector = DeskItemDetector()
        self.vision = VisionAnalyzer()
        self.engine = DeskFengshuiEngine()
        self.bazi_client = BaziClient()
        
        logger.info("✅ 办公桌风水分析器初始化成功")
    
    async def analyze_async(self, image_bytes: bytes, solar_date: Optional[str] = None,
                            solar_time: Optional[str] = None, gender: Optional[str] = None,
                            use_bazi: bool = True) -> Dict:
        """
        异步分析办公桌风水（推荐使用，支持并发）
        
        Args:
            image_bytes: 办公桌照片
            solar_date: 用户出生日期（可选）
            solar_time: 用户出生时间（可选）
            gender: 性别（可选）
            use_bazi: 是否使用八字分析
        
        Returns:
            分析结果
        """
        total_start = time.time()
        stages_time = {}
        
        try:
            # 1. 物品检测：优先使用 VisionAnalyzer（Qwen-VL），失败则降级到 DeskItemDetector
            logger.info("开始物品检测（VisionAnalyzer 优先）...")
            stage_start = time.time()
            detection_result = None
            use_vision = False

            try:
                vision_result = await asyncio.wait_for(
                    self.vision.analyze(image_bytes),
                    timeout=DETECTION_TIMEOUT
                )
                if vision_result and vision_result.get('success'):
                    detection_result = vision_result
                    use_vision = True
                    logger.info(
                        f"✅ VisionAnalyzer 识别成功，检测到 {len(vision_result.get('items', []))} 个物品"
                    )
                else:
                    logger.warning(
                        f"VisionAnalyzer 返回失败: {vision_result.get('error') if vision_result else 'None'}，降级到 YOLO"
                    )
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ VisionAnalyzer 超时（>{DETECTION_TIMEOUT}s），降级到 YOLO")
            except Exception as e:
                logger.warning(f"⚠️ VisionAnalyzer 异常: {e}，降级到 YOLO")

            # 降级：使用旧 YOLO/OpenCV 检测器
            if not use_vision:
                try:
                    detection_result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            _executor,
                            self.detector.detect,
                            image_bytes
                        ),
                        timeout=DETECTION_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    elapsed = time.time() - stage_start
                    logger.error(f"❌ 物品检测超时（>{DETECTION_TIMEOUT}秒，已耗时: {elapsed:.2f}秒）")
                    return {
                        'success': False,
                        'error': f'物品检测超时（超过{DETECTION_TIMEOUT}秒），请尝试上传更小的图片'
                    }

            stages_time['detection'] = time.time() - stage_start

            if detection_result is None:
                logger.error("物品检测返回 None")
                return {'success': False, 'error': '物品检测服务返回空结果，请稍后重试'}

            if not detection_result.get('success'):
                return {'success': False, 'error': detection_result.get('error', '物品检测失败')}

            items = detection_result.get('items', [])
            img_shape = detection_result.get('image_shape')

            logger.info(f"检测到 {len(items)} 个物品（耗时: {stages_time['detection']:.2f}秒，来源: {'qwen_vl' if use_vision else 'yolo'}）")

            # 2. 计算位置
            # VisionAnalyzer 的 items 已由 _convert_items 填充 position，无需再计算
            # YOLO 的 items 只有 bbox，需要 PositionCalculator
            stage_start = time.time()
            if use_vision:
                enriched_items = items  # position 已内嵌
            else:
                logger.info("计算物品位置...")
                enriched_items = PositionCalculator.calculate_all_positions(items, img_shape)
            stages_time['position'] = time.time() - stage_start
            
            # 3. 并行获取八字信息和加载规则
            logger.info("并行获取八字信息和规则...")
            bazi_info = None
            loop = asyncio.get_event_loop()
            stage_start = time.time()
            
            # 创建八字获取Future（如果需要）
            bazi_future = None
            if use_bazi and solar_date and solar_time and gender:
                bazi_future = loop.run_in_executor(
                    _executor,
                    self.bazi_client.get_xishen_jishen,
                    solar_date, solar_time, gender
                )
            
            # 创建规则加载Future（在后台预加载）
            rules_future = loop.run_in_executor(
                _executor,
                self.engine.load_rules,
                False  # force_reload
            )
            
            # 等待八字信息（如果启用，带超时）
            if bazi_future:
                try:
                    bazi_result = await asyncio.wait_for(bazi_future, timeout=BAZI_TIMEOUT)
                    # 🔴 防御性检查：确保 bazi_result 不为 None
                    if bazi_result is not None and bazi_result.get('success'):
                        bazi_info = bazi_result
                        stages_time['bazi'] = time.time() - stage_start
                        logger.info(f"✅ 获取八字信息成功（耗时: {stages_time['bazi']:.2f}秒）: 喜神={bazi_info.get('xishen')}, 忌神={bazi_info.get('jishen')}")
                    else:
                        error_msg = bazi_result.get('error', '未知错误') if bazi_result else '返回空结果'
                        logger.warning(f"获取八字信息失败: {error_msg}，将不使用八字分析")
                        stages_time['bazi'] = time.time() - stage_start
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ 获取八字信息超时（>{BAZI_TIMEOUT}秒），将不使用八字分析")
                    stages_time['bazi'] = BAZI_TIMEOUT
                except Exception as e:
                    error_msg = str(e)
                    # 检查是否是 gRPC 相关错误
                    if 'aborted' in error_msg.lower() or 'signal' in error_msg.lower():
                        logger.warning(f"⚠️ 八字服务连接中断: {error_msg}，将不使用八字分析")
                    else:
                        logger.warning(f"获取八字信息异常: {e}，将不使用八字分析")
                    stages_time['bazi'] = time.time() - stage_start
            
            # 等待规则加载完成
            await rules_future
            
            # 4. 匹配规则（CPU密集型，在线程池中执行，带超时）
            logger.info("匹配风水规则（异步）...")
            stage_start = time.time()
            try:
                rule_result = await asyncio.wait_for(
                    loop.run_in_executor(
                        _executor,
                        self.engine.match_rules,
                        enriched_items,
                        bazi_info
                    ),
                    timeout=RULE_TIMEOUT
                )
            except asyncio.TimeoutError:
                elapsed = time.time() - stage_start
                logger.error(f"❌ 规则匹配超时（>{RULE_TIMEOUT}秒，已耗时: {elapsed:.2f}秒）")
                return {
                    'success': False,
                    'error': f'规则匹配超时（超过{RULE_TIMEOUT}秒）'
                }
            
            stages_time['rules'] = time.time() - stage_start
            
            # 🔴 防御性检查：确保 rule_result 不为 None
            if rule_result is None:
                logger.error("规则匹配返回 None")
                return {
                    'success': False,
                    'error': '规则匹配服务返回空结果'
                }
            
            if not rule_result.get('success'):
                return {
                    'success': False,
                    'error': rule_result.get('error', '规则匹配失败')
                }
            
            # 4.1 为每个物品生成详细分析（核心新功能，带超时）
            logger.info("生成物品级详细分析...")
            stage_start = time.time()
            try:
                item_analyses = await asyncio.wait_for(
                    loop.run_in_executor(
                        _executor,
                        self.engine.analyze_all_items,
                        enriched_items,
                        bazi_info
                    ),
                    timeout=10
                )
            except asyncio.TimeoutError:
                logger.warning("物品分析超时，使用空列表")
                item_analyses = []
            
            stages_time['item_analysis'] = time.time() - stage_start
            
            # 🔴 防御性检查：确保 item_analyses 不为 None
            if item_analyses is None:
                logger.warning("物品分析返回 None，使用空列表")
                item_analyses = []
            
            # 4.2 生成三级建议体系（带超时）
            logger.info("生成三级建议体系...")
            stage_start = time.time()
            try:
                recommendations = await asyncio.wait_for(
                    loop.run_in_executor(
                        _executor,
                        self.engine.generate_recommendations,
                        enriched_items,
                        bazi_info
                    ),
                    timeout=10
                )
            except asyncio.TimeoutError:
                logger.warning("建议生成超时，使用空字典")
                recommendations = {
                    'must_adjust': [],
                    'should_add': [],
                    'optional_optimize': []
                }
            
            stages_time['recommendations'] = time.time() - stage_start
            
            # 🔴 防御性检查：确保 recommendations 不为 None
            if recommendations is None:
                logger.warning("建议生成返回 None，使用默认值")
                recommendations = {
                    'must_adjust': [],
                    'should_add': [],
                    'optional_optimize': []
                }
            
            # 4.3 生成深度八字融合分析
            logger.info("生成八字深度融合分析...")
            bazi_analysis = await asyncio.get_event_loop().run_in_executor(
                _executor,
                self.engine.generate_bazi_analysis,
                enriched_items,
                bazi_info
            )
            
            # 🔴 防御性检查：确保 bazi_analysis 不为 None
            if bazi_analysis is None:
                logger.warning("八字分析返回 None，使用默认值")
                bazi_analysis = {
                    'has_bazi': bool(bazi_info),
                    'message': '八字分析失败' if bazi_info else '未提供八字信息'
                }
            
            # 5. 构建响应
            # 计算总耗时
            total_time = time.time() - total_start
            
            # 记录性能信息
            logger.info(f"✅ 分析完成，总耗时: {total_time:.2f}秒")
            logger.info(f"   各阶段耗时: {stages_time}")
            
            # 如果总耗时过长，记录警告
            if total_time > 60:
                logger.warning(f"⚠️ 分析耗时过长: {total_time:.2f}秒")
            
            response = {
                'success': True,
                'items': enriched_items,
                'item_analyses': item_analyses,  # 新增：物品级详细分析
                'recommendations': recommendations,  # 新增：三级建议体系
                'bazi_analysis': bazi_analysis,  # 新增：八字深度融合分析
                'adjustments': rule_result.get('adjustments', []),
                'additions': rule_result.get('additions', []),
                'removals': rule_result.get('removals', []),
                'categorized_additions': rule_result.get('categorized_additions', {}),
                'statistics': rule_result.get('statistics', {}),
                'score': rule_result.get('score', 0),
                'summary': rule_result.get('summary', ''),
                'bazi_info': bazi_info,
                'duration_ms': int(total_time * 1000),
                'performance': {
                    'total_time': total_time,
                    'stages_time': stages_time
                },
                'detection_source': detection_result.get('source', 'yolo'),
                'using_backup': detection_result.get('using_backup', False),
                'warning': detection_result.get('warning')
            }

            # 日志已在上面记录
            return response
            
        except Exception as e:
            total_time = time.time() - total_start
            logger.error(f"❌ 分析失败，已耗时: {total_time:.2f}秒，错误: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'performance': {
                    'total_time': total_time,
                    'stages_time': stages_time
                }
            }
    
    def analyze(self, image_bytes: bytes, solar_date: Optional[str] = None,
                solar_time: Optional[str] = None, gender: Optional[str] = None,
                use_bazi: bool = True) -> Dict:
        """
        分析办公桌风水
        
        Args:
            image_bytes: 办公桌照片
            solar_date: 用户出生日期（可选）
            solar_time: 用户出生时间（可选）
            gender: 性别（可选）
            use_bazi: 是否使用八字分析
        
        Returns:
            分析结果
        """
        start_time = time.time()
        
        try:
            # 1. 检测物品
            logger.info("开始物品检测...")
            detection_result = self.detector.detect(image_bytes)
            
            # 🔴 防御性检查：确保 detection_result 不为 None
            if detection_result is None:
                logger.error("物品检测返回 None")
                return {
                    'success': False,
                    'error': '物品检测服务返回空结果，请稍后重试'
                }
            
            # 🔴 防御性检查：确保 detection_result 是字典类型
            if not isinstance(detection_result, dict):
                logger.error(f"物品检测返回了非字典类型: {type(detection_result)}")
                return {
                    'success': False,
                    'error': f'物品检测服务返回了无效的数据类型: {type(detection_result).__name__}'
                }
            
            if not detection_result.get('success'):
                return {
                    'success': False,
                    'error': detection_result.get('error', '物品检测失败')
                }
            
            items = detection_result.get('items', [])
            img_shape = detection_result.get('image_shape')
            
            logger.info(f"检测到 {len(items)} 个物品")
            
            # 2. 计算位置
            logger.info("计算物品位置...")
            enriched_items = PositionCalculator.calculate_all_positions(items, img_shape)
            
            # 3. 获取八字信息（如果需要）
            bazi_info = None
            if use_bazi and solar_date and solar_time and gender:
                logger.info("获取八字信息...")
                bazi_result = self.bazi_client.get_xishen_jishen(solar_date, solar_time, gender)
                
                # 🔴 防御性检查：确保 bazi_result 不为 None
                if bazi_result is not None and isinstance(bazi_result, dict):
                    if bazi_result.get('success'):
                        bazi_info = bazi_result
                    else:
                        error_msg = bazi_result.get('error', '未知错误')
                        logger.warning(f"获取八字信息失败: {error_msg}")
                else:
                    logger.warning(f"获取八字信息返回无效结果: {type(bazi_result)}")
            
            # 4. 匹配规则
            logger.info("匹配风水规则...")
            rule_result = self.engine.match_rules(enriched_items, bazi_info)
            
            # 🔴 防御性检查：确保 rule_result 不为 None
            if rule_result is None:
                logger.error("规则匹配返回 None")
                return {
                    'success': False,
                    'error': '规则匹配服务返回空结果，请稍后重试'
                }
            
            # 🔴 防御性检查：确保 rule_result 是字典类型
            if not isinstance(rule_result, dict):
                logger.error(f"规则匹配返回了非字典类型: {type(rule_result)}")
                return {
                    'success': False,
                    'error': f'规则匹配服务返回了无效的数据类型: {type(rule_result).__name__}'
                }
            
            if not rule_result.get('success'):
                return {
                    'success': False,
                    'error': rule_result.get('error', '规则匹配失败')
                }
            
            # 4.1 为每个物品生成详细分析
            logger.info("生成物品级详细分析...")
            item_analyses = self.engine.analyze_all_items(enriched_items, bazi_info)
            
            # 🔴 防御性检查：确保 item_analyses 不为 None
            if item_analyses is None:
                logger.warning("物品分析返回 None，使用空列表")
                item_analyses = []
            
            # 4.2 生成三级建议体系
            logger.info("生成三级建议体系...")
            recommendations = self.engine.generate_recommendations(enriched_items, bazi_info)
            
            # 🔴 防御性检查：确保 recommendations 不为 None
            if recommendations is None:
                logger.warning("建议生成返回 None，使用默认值")
                recommendations = {
                    'must_adjust': [],
                    'should_add': [],
                    'optional_optimize': []
                }
            
            # 4.3 生成深度八字融合分析
            logger.info("生成八字深度融合分析...")
            bazi_analysis = self.engine.generate_bazi_analysis(enriched_items, bazi_info)
            
            # 🔴 防御性检查：确保 bazi_analysis 不为 None
            if bazi_analysis is None:
                logger.warning("八字分析返回 None，使用默认值")
                bazi_analysis = {
                    'has_bazi': bool(bazi_info),
                    'message': '八字分析失败' if bazi_info else '未提供八字信息'
                }
            
            # 5. 构建响应
            duration = int((time.time() - start_time) * 1000)
            
            response = {
                'success': True,
                'items': enriched_items,
                'item_analyses': item_analyses,  # 新增：物品级详细分析
                'recommendations': recommendations,  # 新增：三级建议体系
                'bazi_analysis': bazi_analysis,  # 新增：八字深度融合分析
                'adjustments': rule_result.get('adjustments', []),
                'additions': rule_result.get('additions', []),
                'removals': rule_result.get('removals', []),
                'categorized_additions': rule_result.get('categorized_additions', {}),
                'statistics': rule_result.get('statistics', {}),
                'score': rule_result.get('score', 0),
                'summary': rule_result.get('summary', ''),
                'duration': duration
            }
            
            # 添加八字信息（如果有）
            if bazi_info:
                response['xishen'] = bazi_info.get('xishen', '')
                response['jishen'] = bazi_info.get('jishen', '')
                response['bazi_info'] = bazi_info
            
            # 添加检测警告（如果有）
            if detection_result.get('warning'):
                response['warning'] = detection_result['warning']
                logger.warning(f"⚠️ 检测警告: {response['warning']}")

            logger.info(f"分析完成，耗时 {duration}ms，评分 {response['score']}分")
            
            return response
            
        except Exception as e:
            total_time = time.time() - total_start if 'total_start' in locals() else 0
            logger.error(f"❌ 分析失败，已耗时: {total_time:.2f}秒，错误: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'performance': {
                    'total_time': total_time,
                    'stages_time': stages_time if 'stages_time' in locals() else {}
                }
            }


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    analyzer = DeskFengshuiAnalyzer()
    
    # 加载测试图像
    with open("test_desk.jpg", "rb") as f:
        image_bytes = f.read()
    
    result = analyzer.analyze(
        image_bytes=image_bytes,
        solar_date="1990-01-01",
        solar_time="12:00",
        gender="male",
        use_bazi=True
    )
    
    logger.info(f"分析结果: {result}")

