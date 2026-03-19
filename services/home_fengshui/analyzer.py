# -*- coding: utf-8 -*-
"""
居家风水主分析器
整合视觉识别、命卦计算、规则匹配、方位计算、户型图分析、煞位分析
"""

import logging
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any

from vision_analyzer import HomeFengshuiVisionAnalyzer
from rule_engine import HomeFengshuiEngine
from mingua_calculator import get_mingua_info, get_house_directions
from direction_mapper import parse_solar_year
from floor_plan_analyzer import FloorPlanAnalyzer
from position_calculator import get_all_positions
from sha_analyzer import ShaAnalyzer

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix='home_fengshui')

VISION_TIMEOUT     = 45
FLOOR_PLAN_TIMEOUT = 60
RULE_TIMEOUT       = 10
BAZI_TIMEOUT       = 5


class HomeFengshuiAnalyzer:
    """居家风水主分析器"""

    def __init__(self):
        self.vision         = HomeFengshuiVisionAnalyzer()
        self.engine         = HomeFengshuiEngine()
        self.floor_analyzer = FloorPlanAnalyzer()
        self.sha_analyzer   = ShaAnalyzer()
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

    # ------------------------------------------------------------------
    # 全屋分析（户型图 + 多房间 + 方位 + 煞位）
    # ------------------------------------------------------------------

    async def analyze_full_house_async(
        self,
        image_bytes_list: List[bytes],
        room_types: Optional[List[str]] = None,
        floor_plan_bytes: Optional[bytes] = None,
        door_direction: Optional[str] = None,
        birth_year: Optional[int] = None,
        gender: Optional[str] = None,
        solar_date: Optional[str] = None,
        solar_time: Optional[str] = None,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        全屋风水分析（编排所有子模块）

        处理流程：
        阶段1（并行）：户型图分析 + 规则加载 + 命卦计算
        阶段2（并行）：各房间视觉识别
        阶段3（串行）：方位计算 → 煞位分析 → 方位规则匹配
        阶段4：数据汇总

        Args:
            image_bytes_list: 房间照片列表
            room_types: 房间类型列表
            floor_plan_bytes: 户型图字节（可选）
            door_direction: 大门朝向
            birth_year: 出生年份
            gender: 性别
            solar_date: 出生日期（用于命卦计算）
            solar_time: 出生时间
            progress_callback: async 回调函数，(stage, data) -> None

        Yields (via progress_callback):
            ('floor_plan_result', {...})
            ('room_result', {...})
            ('position_analysis', {...})
            ('sha_analysis', {...})
        """
        total_start = time.time()
        stages_time = {}

        result = {
            'success': True,
            'is_whole_house': floor_plan_bytes is not None,
            'door_direction': door_direction or '',
            'floor_plan': None,
            'room_results': [],
            'position_data': None,
            'sha_data': None,
            'position_rules': None,
            'mingua_info': None,
            'overall_score': 0,
            'summary': '',
        }

        async def _notify(stage: str, data: Any):
            if progress_callback:
                try:
                    await progress_callback(stage, data)
                except Exception as e:
                    logger.warning(f'progress_callback 失败: {e}')

        try:
            # ==================== 阶段1：并行预处理 ====================
            stage_start = time.time()

            tasks_phase1 = []

            if floor_plan_bytes:
                tasks_phase1.append(('floor_plan', self._run_floor_plan_analysis(floor_plan_bytes, door_direction)))

            loop = asyncio.get_event_loop()
            tasks_phase1.append(('rules', loop.run_in_executor(_executor, self.engine.load_rules, False)))

            mingua_info = None
            if birth_year and gender:
                tasks_phase1.append(('mingua', loop.run_in_executor(
                    _executor, get_mingua_info, birth_year, gender, door_direction
                )))
            elif solar_date and gender:
                by = parse_solar_year(solar_date)
                if by:
                    birth_year = by
                    tasks_phase1.append(('mingua', loop.run_in_executor(
                        _executor, get_mingua_info, by, gender, door_direction
                    )))

            phase1_results = {}
            if tasks_phase1:
                gathered = await asyncio.gather(
                    *[t[1] for t in tasks_phase1], return_exceptions=True
                )
                for (name, _), res in zip(tasks_phase1, gathered):
                    if isinstance(res, Exception):
                        logger.warning(f'阶段1 {name} 失败: {res}')
                        phase1_results[name] = None
                    else:
                        phase1_results[name] = res

            stages_time['phase1'] = time.time() - stage_start

            floor_plan_result = phase1_results.get('floor_plan')
            if floor_plan_result and floor_plan_result.get('success'):
                result['floor_plan'] = floor_plan_result
                await _notify('floor_plan_result', floor_plan_result)

                detected_door = floor_plan_result.get('door_position', {})
                if not door_direction and detected_door.get('detected'):
                    door_direction = detected_door.get('zone_cn', '')
                    result['door_direction'] = door_direction
                    logger.info(f'从户型图检测到大门方位: {door_direction}')

            mingua_info = phase1_results.get('mingua')
            result['mingua_info'] = mingua_info

            # ==================== 阶段2：并行房间分析 ====================
            stage_start = time.time()
            room_types = room_types or []
            while len(room_types) < len(image_bytes_list):
                room_types.append('auto')

            room_tasks = []
            for idx, (img_bytes, rt) in enumerate(zip(image_bytes_list, room_types)):
                room_tasks.append(self._analyze_single(
                    image_bytes=img_bytes,
                    room_type=rt or 'auto',
                    door_direction=door_direction,
                    solar_date=solar_date,
                    solar_time=solar_time,
                    gender=gender,
                    use_bazi=False,
                    photo_index=idx,
                    preload_rules=False,
                ))

            room_results = await asyncio.gather(*room_tasks, return_exceptions=True)
            for i, rr in enumerate(room_results):
                if isinstance(rr, Exception):
                    rr = {'success': False, 'error': str(rr), 'photo_index': i}
                result['room_results'].append(rr)
                await _notify('room_result', rr)

            stages_time['phase2_rooms'] = time.time() - stage_start

            # ==================== 阶段3：方位计算 + 煞位分析 ====================
            stage_start = time.time()

            house_dirs = get_house_directions(door_direction) if door_direction else None

            position_data = await loop.run_in_executor(
                _executor, get_all_positions, door_direction, birth_year, gender, None
            )
            result['position_data'] = position_data
            await _notify('position_analysis', position_data)

            room_positions = {}
            if floor_plan_result and floor_plan_result.get('success'):
                room_positions = floor_plan_result.get('room_positions', {})

            all_vision_items = []
            for rr in result['room_results']:
                if rr.get('success'):
                    for item in rr.get('furnitures', []):
                        item_copy = dict(item)
                        item_copy['room_type'] = rr.get('room_type', '')
                        all_vision_items.append(item_copy)

            missing_corners = []
            if floor_plan_result and floor_plan_result.get('success'):
                missing_corners = floor_plan_result.get('missing_corners', [])

            sha_result = self.sha_analyzer.analyze_all(
                missing_corners=missing_corners,
                house_directions=house_dirs,
                room_positions=room_positions,
                vision_items=all_vision_items,
                door_direction=door_direction,
            )
            result['sha_data'] = sha_result
            await _notify('sha_analysis', sha_result)

            position_rules = self.engine.match_position_rules(
                missing_corners=missing_corners,
                house_directions=house_dirs,
                room_positions=room_positions,
                position_data=position_data,
                mingua_info=mingua_info,
            )
            result['position_rules'] = position_rules

            stages_time['phase3_positions'] = time.time() - stage_start

            # ==================== 阶段4：评分汇总 ====================
            room_scores = [rr.get('overall_score', 0) for rr in result['room_results'] if rr.get('success')]
            avg_room_score = sum(room_scores) / len(room_scores) if room_scores else 70
            position_deduction = position_rules.get('score_deduction', 0) if position_rules else 0

            overall_score = max(0, min(100, int(avg_room_score - position_deduction * 0.3)))
            result['overall_score'] = overall_score

            all_critical = []
            all_suggestions = []
            all_tips = []
            for rr in result['room_results']:
                if rr.get('success'):
                    all_critical.extend(rr.get('critical_issues', []))
                    all_suggestions.extend(rr.get('suggestions', []))
                    all_tips.extend(rr.get('tips', []))
            if position_rules:
                all_critical.extend(position_rules.get('critical_issues', []))
                all_suggestions.extend(position_rules.get('suggestions', []))
                all_tips.extend(position_rules.get('tips', []))

            result['all_critical_issues'] = all_critical
            result['all_suggestions'] = all_suggestions
            result['all_tips'] = all_tips
            result['summary'] = self.engine._build_summary(overall_score, all_critical, all_suggestions)

            total_time = time.time() - total_start
            result['duration_ms'] = int(total_time * 1000)
            result['performance'] = {'total_time': total_time, 'stages_time': stages_time}
            logger.info(f'✅ 全屋分析完成，耗时 {total_time:.2f}s，评分 {overall_score}')

            return result

        except Exception as e:
            logger.error(f'❌ 全屋分析失败: {e}', exc_info=True)
            result['success'] = False
            result['error'] = str(e)
            return result

    async def _run_floor_plan_analysis(
        self, floor_plan_bytes: bytes, door_direction: Optional[str]
    ) -> Dict:
        """运行户型图分析（带超时）"""
        try:
            return await asyncio.wait_for(
                self.floor_analyzer.analyze(floor_plan_bytes, door_direction),
                timeout=FLOOR_PLAN_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(f'户型图分析超时（>{FLOOR_PLAN_TIMEOUT}s）')
            return {'success': False, 'error': '户型图分析超时'}
        except Exception as e:
            logger.error(f'户型图分析异常: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}
