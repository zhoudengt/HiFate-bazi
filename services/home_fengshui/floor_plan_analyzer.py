# -*- coding: utf-8 -*-
"""
户型图分析器
调用百炼 Qwen-VL 智能体分析户型图，识别缺角、房间布局、九宫格方位
"""

import os
import sys
import json
import base64
import logging
import asyncio
from typing import Dict, Any, Optional, List

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

FLOOR_PLAN_PROMPT = """请分析这张住宅户型图（平面图），完成以下任务：

1. 识别户型整体形状
2. 将户型按九宫格划分为9个方位区域
3. 判断每个方位是否存在缺角（建筑实体面积占该格子 < 60% 视为缺角）
4. 识别每个房间的类型和所在方位

以 JSON 格式输出，格式如下：
{
  "floor_plan_shape": "rectangular/L-shape/T-shape/U-shape/irregular",
  "total_rooms": 3,
  "orientation_note": "户型图朝向说明",
  "nine_palace_grid": {
    "northwest": {"gua": "乾", "has_building": true, "coverage_percent": 85, "is_missing_corner": false, "rooms_in_zone": ["master_bedroom"], "description": "西北方为主卧"},
    "north": {"gua": "坎", "has_building": true, "coverage_percent": 90, "is_missing_corner": false, "rooms_in_zone": ["bathroom"], "description": "正北方为卫生间"},
    "northeast": {"gua": "艮", "has_building": true, "coverage_percent": 70, "is_missing_corner": false, "rooms_in_zone": ["second_bedroom"], "description": "东北方为次卧"},
    "west": {"gua": "兑", "has_building": true, "coverage_percent": 95, "is_missing_corner": false, "rooms_in_zone": ["kitchen"], "description": "正西方为厨房"},
    "center": {"gua": "太极", "has_building": true, "coverage_percent": 100, "is_missing_corner": false, "rooms_in_zone": ["living_room"], "description": "中宫为客厅"},
    "east": {"gua": "震", "has_building": false, "coverage_percent": 30, "is_missing_corner": true, "rooms_in_zone": [], "description": "正东方缺角约70%"},
    "southwest": {"gua": "坤", "has_building": true, "coverage_percent": 80, "is_missing_corner": false, "rooms_in_zone": ["dining_room"], "description": "西南方为餐厅"},
    "south": {"gua": "离", "has_building": true, "coverage_percent": 95, "is_missing_corner": false, "rooms_in_zone": ["balcony"], "description": "正南方为阳台"},
    "southeast": {"gua": "巽", "has_building": true, "coverage_percent": 75, "is_missing_corner": false, "rooms_in_zone": ["study"], "description": "东南方为书房"}
  },
  "missing_corners": [
    {"direction": "正东", "direction_en": "east", "gua": "震", "missing_percent": 70, "severity": "critical", "description": "正东方（震宫）缺角约70%"}
  ],
  "room_positions": {
    "master_bedroom": {"zone": "northwest", "zone_cn": "西北", "gua": "乾"},
    "living_room": {"zone": "center", "zone_cn": "中宫", "gua": "太极"}
  },
  "door_position": {"detected": true, "zone": "south", "zone_cn": "正南", "description": "大门位于正南方"},
  "summary": "该户型为L形结构，正东方缺角严重。大门位于正南方。"
}

重要规则：
1. 只输出 JSON，不要输出解释文字
2. coverage_percent 是建筑实体在该格子中的面积占比（0-100）
3. is_missing_corner 当 coverage_percent < 60 时为 true
4. severity：missing_percent >= 50 为 critical，30-49 为 warning，< 30 为 minor
5. 如果户型图有文字标注优先使用
6. 没有标注朝向时默认上北下南左西右东
7. nine_palace_grid 必须包含全部9个方位
8. 房间类型使用：master_bedroom/second_bedroom/living_room/kitchen/bathroom/study/dining_room/balcony/storage/hallway/entrance"""

# 方位英文→中文映射
ZONE_EN_TO_CN = {
    'northwest': '西北', 'north': '正北', 'northeast': '东北',
    'west': '正西', 'center': '中宫', 'east': '正东',
    'southwest': '西南', 'south': '正南', 'southeast': '东南',
}

# 方位→八卦映射
ZONE_TO_GUA = {
    'northwest': '乾', 'north': '坎', 'northeast': '艮',
    'west': '兑', 'center': '太极', 'east': '震',
    'southwest': '坤', 'south': '离', 'southeast': '巽',
}


class FloorPlanAnalyzer:
    """户型图分析器（调用百炼 Qwen-VL）"""

    def __init__(self, app_id: Optional[str] = None, api_key: Optional[str] = None):
        self._app_id = app_id
        self._api_key = api_key
        self._sdk_ready = False

    def _ensure_sdk(self):
        if self._sdk_ready:
            return
        import dashscope
        api_key = self._api_key
        if not api_key:
            try:
                from server.config.config_loader import get_config_from_db_only
                api_key = get_config_from_db_only('BAILIAN_API_KEY')
            except Exception:
                pass
        if not api_key:
            api_key = os.environ.get('DASHSCOPE_API_KEY', '')
        if not api_key:
            raise ValueError('未配置百炼 API Key')
        dashscope.api_key = api_key
        self._sdk_ready = True

    def _get_app_id(self) -> str:
        if self._app_id:
            return self._app_id
        try:
            from server.config.config_loader import get_config_from_db_only
            app_id = get_config_from_db_only('BAILIAN_HOME_FENGSHUI_FLOORPLAN_APP_ID')
            if app_id:
                return app_id
        except Exception:
            pass
        raise ValueError('未配置 BAILIAN_HOME_FENGSHUI_FLOORPLAN_APP_ID')

    async def analyze(self, image_bytes: bytes, door_direction: Optional[str] = None) -> Dict[str, Any]:
        """
        分析户型图

        Args:
            image_bytes: 户型图图片字节
            door_direction: 用户提供的大门朝向（可选，用于校准）

        Returns:
            包含缺角信息和房间布局的字典
        """
        try:
            self._ensure_sdk()
            from dashscope import Application

            app_id = self._get_app_id()
            img_b64 = base64.b64encode(image_bytes).decode('utf-8')

            prompt = FLOOR_PLAN_PROMPT
            if door_direction:
                prompt += f'\n\n注意：用户已告知大门朝向为{door_direction}方，请以此为参考确定九宫格方位。'

            loop = asyncio.get_event_loop()
            raw_text = await loop.run_in_executor(
                None, self._call_vision_app, Application, app_id, img_b64, prompt
            )

            data = self._parse_response(raw_text)
            return self._normalize_result(data, door_direction)

        except Exception as e:
            logger.error(f'FloorPlanAnalyzer 失败: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _call_vision_app(Application, app_id: str, img_b64: str, prompt: str) -> str:
        response = Application.call(
            app_id=app_id,
            messages=[{
                'role': 'user',
                'content': [
                    {'image': f'data:image/jpeg;base64,{img_b64}'},
                    {'text': prompt},
                ],
            }],
            stream=False,
        )
        if response.status_code != 200:
            raise ValueError(
                f'百炼户型图分析错误: {response.status_code} '
                f'{getattr(response, "code", "")} - {getattr(response, "message", "")}'
            )
        text = (response.output or {}).get('text', '')
        if not text:
            raise ValueError(f'百炼户型图分析返回空文本')
        return text

    @staticmethod
    def _parse_response(text: str) -> Dict[str, Any]:
        """从 LLM 返回文本中提取 JSON"""
        import re
        cleaned = text.strip()
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        start = cleaned.find('{')
        if start == -1:
            raise ValueError(f'无法解析户型图分析返回的 JSON: {text[:200]}')

        depth = 0
        end = start
        for i in range(start, len(cleaned)):
            if cleaned[i] == '{':
                depth += 1
            elif cleaned[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break

        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError as e:
            raise ValueError(f'JSON 解析失败: {e}')

    def _normalize_result(self, data: Dict, door_direction: Optional[str]) -> Dict:
        """标准化并校验分析结果"""
        missing_corners = data.get('missing_corners', [])

        for mc in missing_corners:
            if 'missing_percent' not in mc and 'coverage_percent' in mc:
                mc['missing_percent'] = 100 - mc['coverage_percent']
            mp = mc.get('missing_percent', 0)
            if 'severity' not in mc:
                mc['severity'] = 'critical' if mp >= 50 else ('warning' if mp >= 30 else 'minor')
            if 'gua' not in mc:
                zone_en = mc.get('direction_en', '')
                mc['gua'] = ZONE_TO_GUA.get(zone_en, '')

        grid = data.get('nine_palace_grid', {})
        for zone_en in ['northwest', 'north', 'northeast', 'west', 'center', 'east',
                        'southwest', 'south', 'southeast']:
            if zone_en not in grid:
                grid[zone_en] = {
                    'gua': ZONE_TO_GUA.get(zone_en, ''),
                    'has_building': True,
                    'coverage_percent': 100,
                    'is_missing_corner': False,
                    'rooms_in_zone': [],
                    'description': '',
                }
            zone_data = grid[zone_en]
            if zone_data.get('is_missing_corner') and zone_en not in [mc.get('direction_en') for mc in missing_corners]:
                cp = zone_data.get('coverage_percent', 100)
                mp = 100 - cp
                missing_corners.append({
                    'direction': ZONE_EN_TO_CN.get(zone_en, zone_en),
                    'direction_en': zone_en,
                    'gua': ZONE_TO_GUA.get(zone_en, ''),
                    'missing_percent': mp,
                    'coverage_percent': cp,
                    'severity': 'critical' if mp >= 50 else ('warning' if mp >= 30 else 'minor'),
                    'description': zone_data.get('description', ''),
                })

        return {
            'success': True,
            'floor_plan_shape': data.get('floor_plan_shape', 'unknown'),
            'total_rooms': data.get('total_rooms', 0),
            'nine_palace_grid': grid,
            'missing_corners': missing_corners,
            'room_positions': data.get('room_positions', {}),
            'door_position': data.get('door_position', {}),
            'summary': data.get('summary', ''),
            'source': 'qwen_vl_floor_plan',
        }
