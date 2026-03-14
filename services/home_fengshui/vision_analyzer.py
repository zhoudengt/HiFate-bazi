# -*- coding: utf-8 -*-
"""
居家风水视觉识别器
调用百炼 Qwen-VL 智能体识别室内家具、位置、状态
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

# 各房间类型识别Prompt
ROOM_PROMPTS = {
    'bedroom': """请分析这张卧室照片，识别室内家具和布局，以JSON格式输出：
{
  "items": [
    {
      "name": "bed",
      "label": "床",
      "confidence": 0.95,
      "position_zone": "north",
      "state": "床头朝北/镜子正对床/床头靠窗",
      "element": "土",
      "count": 1
    }
  ],
  "scene": {
    "has_window": true,
    "window_positions": ["east"],
    "has_beam": false,
    "beam_positions": [],
    "room_shape": "rectangular"
  },
  "summary": "卧室整体描述"
}

请识别以下家具（如存在）：床、衣柜、梳妆台、书桌、电视、镜子、窗户、门、床头柜、台灯、地毯
position_zone请使用：north/northeast/east/southeast/south/southwest/west/northwest/center
state请描述关键风水状态，如：床头朝北、镜子正对床、床头靠窗、床头对门、横梁在床上方等""",

    'living_room': """请分析这张客厅照片，识别室内家具和布局，以JSON格式输出：
{
  "items": [
    {
      "name": "sofa",
      "label": "沙发",
      "confidence": 0.95,
      "position_zone": "south",
      "state": "背靠实墙/背对落地窗/正对大门",
      "element": "土",
      "count": 1
    }
  ],
  "scene": {
    "has_window": true,
    "window_positions": ["south"],
    "front_back_aligned": false,
    "room_shape": "rectangular"
  },
  "summary": "客厅整体描述"
}

请识别以下家具（如存在）：沙发、茶几、电视柜、鱼缸、绿植、装饰画、窗户、大门、餐桌、储物柜
state请描述关键风水状态，如：背靠实墙、背对落地窗、正对大门、门窗成直线、沙发正对大门等""",

    'study': """请分析这张书房照片，识别室内家具和布局，以JSON格式输出：
{
  "items": [
    {
      "name": "desk",
      "label": "书桌",
      "confidence": 0.95,
      "position_zone": "north",
      "state": "背靠实墙/面对窗户/背对门",
      "element": "木",
      "count": 1
    }
  ],
  "scene": {
    "has_window": true,
    "window_positions": ["south"],
    "room_shape": "rectangular"
  },
  "summary": "书房整体描述"
}

请识别以下家具（如存在）：书桌、椅子、书架、书柜、台灯、电脑、窗户、门、绿植、文件柜
state请描述：背靠实墙、面对窗户/墙、背对门、书桌正对门等""",

    'kitchen': """请分析这张厨房照片，识别室内家具和布局，以JSON格式输出，识别：灶台、冰箱、洗碗池、橱柜等，
描述水火冲克（冰箱紧邻灶台）、刀具是否外露等风水状态。""",

    'dining_room': """请分析这张餐厅照片，识别室内家具和布局，以JSON格式输出，识别：餐桌、餐椅、酒柜、镜子等，
描述餐桌形状（圆形/方形）、镜子是否正对餐桌等风水状态。""",
}

DEFAULT_PROMPT = """请分析这张房间照片，识别室内家具和布局，以JSON格式输出家具清单、位置和风水相关状态。"""

# 自动识别房间类型的通用 prompt
AUTO_DETECT_PROMPT = """请分析这张室内照片，首先判断房间类型，然后识别家具和布局，以JSON格式输出：
{
  "detected_room_type": "bedroom",
  "items": [
    {
      "name": "bed",
      "label": "床",
      "confidence": 0.95,
      "position_zone": "north",
      "state": "床头朝北/镜子正对床/床头靠窗",
      "element": "土",
      "count": 1
    }
  ],
  "scene": {
    "has_window": true,
    "window_positions": ["east"],
    "has_beam": false,
    "room_shape": "rectangular"
  },
  "summary": "房间整体描述"
}

detected_room_type 必须是以下之一：bedroom（卧室）/ living_room（客厅）/ study（书房）/ kitchen（厨房）/ dining_room（餐厅）/ other（其他）
position_zone 请使用：north/northeast/east/southeast/south/southwest/west/northwest/center
state 请描述关键风水状态，如：床头朝北、镜子正对床、背靠实墙、沙发正对大门、书桌面对窗户等"""

# 房间类型中文映射
ROOM_TYPE_LABELS = {
    'bedroom': '卧室', 'living_room': '客厅', 'study': '书房',
    'kitchen': '厨房', 'dining_room': '餐厅', 'other': '其他',
}

# 家具五行属性
FURNITURE_ELEMENT = {
    'bed': '土', 'sofa': '土', 'desk': '木', 'bookshelf': '木',
    'fish_tank': '水', 'aquarium': '水', 'mirror': '金',
    'tv': '火', 'refrigerator': '水', 'stove': '火', 'oven': '火',
    'plant': '木', 'candle': '火', 'clock': '金', 'wardrobe': '木',
    'dresser': '金', 'lamp': '火',
}


class HomeFengshuiVisionAnalyzer:
    """居家风水视觉识别器（调用百炼 Qwen-VL）"""

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
            raise ValueError('未配置百炼 API Key（BAILIAN_API_KEY / DASHSCOPE_API_KEY）')
        dashscope.api_key = api_key
        self._sdk_ready = True

    def _get_app_id(self) -> str:
        if self._app_id:
            return self._app_id
        try:
            from server.config.config_loader import get_config_from_db_only
            app_id = get_config_from_db_only('BAILIAN_HOME_FENGSHUI_VISION_APP_ID')
            if app_id:
                return app_id
        except Exception:
            pass
        raise ValueError('未配置 BAILIAN_HOME_FENGSHUI_VISION_APP_ID（值：626cf5733b6b493e8e31ff9f6081a24f）')

    async def analyze(self, image_bytes: bytes, room_type: str = 'bedroom') -> Dict[str, Any]:
        """
        调用百炼 Qwen-VL 智能体识别室内家具

        Args:
            image_bytes: 图片字节
            room_type: 房间类型；传 'auto' 或空字符串时自动识别
        """
        try:
            self._ensure_sdk()
            from dashscope import Application

            app_id = self._get_app_id()
            img_b64 = base64.b64encode(image_bytes).decode('utf-8')

            auto_detect = not room_type or room_type == 'auto'
            prompt = AUTO_DETECT_PROMPT if auto_detect else ROOM_PROMPTS.get(room_type, DEFAULT_PROMPT)

            loop = asyncio.get_event_loop()
            raw_text = await loop.run_in_executor(
                None, self._call_vision_app, Application, app_id, img_b64, prompt
            )

            vision_data = self._parse_response(raw_text)
            items = self._convert_items(vision_data.get('items', []))

            # 自动识别时，从返回结果中提取房间类型
            detected_room_type = room_type
            if auto_detect:
                detected_room_type = vision_data.get('detected_room_type', 'bedroom')
                if detected_room_type not in ROOM_TYPE_LABELS:
                    detected_room_type = 'bedroom'
                logger.info(f'自动识别房间类型：{ROOM_TYPE_LABELS.get(detected_room_type, detected_room_type)}')

            return {
                'success': True,
                'items': items,
                'scene': vision_data.get('scene', {}),
                'total_items': len(items),
                'summary': vision_data.get('summary', ''),
                'detected_room_type': detected_room_type,
                'auto_detected': auto_detect,
                'source': 'qwen_vl',
            }
        except Exception as e:
            logger.error(f'HomeFengshuiVisionAnalyzer 失败: {e}', exc_info=True)
            return {'success': False, 'error': str(e), 'source': 'qwen_vl'}

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
                f'百炼视觉应用错误: {response.status_code} '
                f'{getattr(response, "code", "")} - {getattr(response, "message", "")}'
            )
        text = (response.output or {}).get('text', '')
        if not text:
            raise ValueError(f'百炼视觉应用返回空文本, output={response.output}')
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
            raise ValueError(f'无法解析视觉模型返回的 JSON: {text[:200]}')

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
            raise ValueError(f'JSON 解析失败: {e}, 原文前200字: {text[:200]}')

    @staticmethod
    def _convert_items(raw_items: List[Dict]) -> List[Dict]:
        """将 vision LLM 输出的 items 转换为规则引擎可消费的格式"""
        converted = []
        for item in raw_items:
            name = item.get('name', 'unknown').lower()
            converted.append({
                'name': name,
                'label': item.get('label', name),
                'confidence': item.get('confidence', 0.9),
                'count': item.get('count', 1),
                'state': item.get('state', ''),
                'position_zone': item.get('position_zone', 'center'),
                'element': item.get('element') or FURNITURE_ELEMENT.get(name, ''),
                'bbox': [],
            })
        return converted
