# -*- coding: utf-8 -*-
"""
居家风水主分析器
整合视觉识别、命卦计算、规则匹配、图片生成
"""

import logging
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from vision_analyzer import HomeFengshuiVisionAnalyzer
from rule_engine import HomeFengshuiEngine
from mingua_calculator import get_mingua_info
from direction_mapper import parse_solar_year

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix='home_fengshui')

VISION_TIMEOUT = 45
RULE_TIMEOUT   = 10
BAZI_TIMEOUT   = 5


class HomeFengshuiAnalyzer:
    """居家风水主分析器"""

    def __init__(self):
        self.vision   = HomeFengshuiVisionAnalyzer()
        self.engine   = HomeFengshuiEngine()
        logger.info('✅ HomeFengshuiAnalyzer 初始化成功')

    async def analyze_multi_async(
        self,
        image_bytes_list: List[bytes],
        room_types: Optional[List[str]] = None,
        door_direction: Optional[str] = None,
        solar_date: Optional[str] = None,
        solar_time: Optional[str] = None,
        gender: Optional[str] = None,
        use_bazi: bool = True,
    ):
        """
        异步分析多张照片（支持不同房间类型）

        Args:
            image_bytes_list: 1-4 张照片
            room_types: 与 image_bytes_list 一一对应的房间类型列表；
                        None / 空字符串 / 'auto' → 自动识别
        Yields:
            dict，每张图分析完后逐个 yield，便于流式输出
        """
        room_types = room_types or []
        # 补齐 room_types 长度，不足部分视为自动识别
        while len(room_types) < len(image_bytes_list):
            room_types.append('auto')

        # 预加载规则（一次性）
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, self.engine.load_rules, False)

        for idx, (image_bytes, room_type) in enumerate(zip(image_bytes_list, room_types)):
            result = await self._analyze_single(
                image_bytes=image_bytes,
                room_type=room_type or 'auto',
                door_direction=door_direction,
                solar_date=solar_date,
                solar_time=solar_time,
                gender=gender,
                use_bazi=use_bazi,
                photo_index=idx,
                preload_rules=False,  # 已预加载
            )
            yield result

    async def _analyze_single(
        self,
        image_bytes: bytes,
        room_type: str = 'auto',
        door_direction: Optional[str] = None,
        solar_date: Optional[str] = None,
        solar_time: Optional[str] = None,
        gender: Optional[str] = None,
        use_bazi: bool = True,
        photo_index: int = 0,
        preload_rules: bool = True,
    ) -> Dict:
        """分析单张照片（内部方法，供单张和多张复用）"""
        total_start = time.time()
        stages_time = {}

        try:
            # 1. 视觉识别
            logger.info(f'[HomeFengshui] photo[{photo_index}] 开始视觉识别，room_type={room_type}')
            stage_start = time.time()
            try:
                vision_result = await asyncio.wait_for(
                    self.vision.analyze(image_bytes, room_type),
                    timeout=VISION_TIMEOUT,
                )
            except asyncio.TimeoutError:
                return {'success': False, 'error': f'图片识别超时（>{VISION_TIMEOUT}s）', 'photo_index': photo_index}
            stages_time['vision'] = time.time() - stage_start

            if not vision_result or not vision_result.get('success'):
                return {'success': False, 'error': vision_result.get('error', '视觉识别失败') if vision_result else '识别返回空结果', 'photo_index': photo_index}

            # 若自动识别，以视觉模型返回的类型为准
            actual_room_type = vision_result.get('detected_room_type') or room_type
            if actual_room_type in ('auto', '', None):
                actual_room_type = 'bedroom'
            auto_detected = vision_result.get('auto_detected', False)

            furnitures = vision_result.get('items', [])
            scene_info = vision_result.get('scene', {})
            logger.info(f'photo[{photo_index}] 识别到 {len(furnitures)} 件家具，房间={actual_room_type}（{"自动识别" if auto_detected else "手动指定"}）')

            # 2. 命卦计算
            mingua_info = None
            if use_bazi and solar_date and gender:
                stage_start = time.time()
                birth_year = parse_solar_year(solar_date)
                if birth_year:
                    try:
                        mingua_info = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                _executor, get_mingua_info, birth_year, gender, door_direction,
                            ),
                            timeout=BAZI_TIMEOUT,
                        )
                    except asyncio.TimeoutError:
                        logger.warning('命卦计算超时')
                stages_time['mingua'] = time.time() - stage_start

            # 3. 规则预加载（仅单独调用时）
            if preload_rules:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(_executor, self.engine.load_rules, False)

            # 4. 规则匹配
            stage_start = time.time()
            try:
                rule_result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        _executor, self.engine.match_rules,
                        furnitures, actual_room_type, door_direction, mingua_info,
                    ),
                    timeout=RULE_TIMEOUT,
                )
            except asyncio.TimeoutError:
                return {'success': False, 'error': '规则匹配超时', 'photo_index': photo_index}
            stages_time['rules'] = time.time() - stage_start

            if not rule_result or not rule_result.get('success'):
                return {'success': False, 'error': rule_result.get('error', '规则匹配失败') if rule_result else '规则匹配返回空', 'photo_index': photo_index}

            # 5. 命宅相配分
            mingua_score = 0
            if mingua_info:
                if mingua_info.get('is_compatible'):
                    mingua_score = 85
                elif door_direction:
                    mingua_score = 40
                else:
                    mingua_score = 60

            total_time = time.time() - total_start
            logger.info(f'✅ photo[{photo_index}] 分析完成，耗时 {total_time:.2f}s，评分 {rule_result.get("score")}')

            return {
                'success': True,
                'photo_index': photo_index,
                'room_type': actual_room_type,
                'auto_detected': auto_detected,
                'door_direction': door_direction or '',
                'furnitures': furnitures,
                'scene_info': scene_info,
                'critical_issues': rule_result.get('critical_issues', []),
                'suggestions': rule_result.get('suggestions', []),
                'tips': rule_result.get('tips', []),
                'overall_score': rule_result.get('score', 0),
                'mingua_score': mingua_score,
                'mingua_info': mingua_info,
                'summary': rule_result.get('summary', ''),
                'duration_ms': int(total_time * 1000),
                'performance': {'total_time': total_time, 'stages_time': stages_time},
            }
        except Exception as e:
            total_time = time.time() - total_start
            logger.error(f'❌ photo[{photo_index}] 分析失败（{total_time:.2f}s）: {e}', exc_info=True)
            return {'success': False, 'error': str(e), 'photo_index': photo_index}

    async def analyze_async(
        self,
        image_bytes_list: List[bytes],
        room_type: str = 'bedroom',
        door_direction: Optional[str] = None,
        solar_date: Optional[str] = None,
        solar_time: Optional[str] = None,
        gender: Optional[str] = None,
        use_bazi: bool = True,
    ) -> Dict:
        """
        单房间分析（向后兼容，内部复用 _analyze_single）

        Args:
            image_bytes_list: 1-4 张房间照片（仅使用第一张）
            room_type: 房间类型，传 'auto' 自动识别
        """
        return await self._analyze_single(
            image_bytes=image_bytes_list[0],
            room_type=room_type,
            door_direction=door_direction,
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            use_bazi=use_bazi,
            photo_index=0,
            preload_rules=True,
        )
