# -*- coding: utf-8 -*-
"""
办公桌风水视觉识别器
直接调用 dashscope SDK (Application.call) 进行图片物品识别，零外部依赖
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

_POSITION_MAP = {
    'left_front':    {'relative': 'left',   'vertical': 'front',  'bagua_direction': 'southeast'},
    'center_front':  {'relative': 'center', 'vertical': 'front',  'bagua_direction': 'south'},
    'right_front':   {'relative': 'right',  'vertical': 'front',  'bagua_direction': 'southwest'},
    'left_center':   {'relative': 'left',   'vertical': 'center', 'bagua_direction': 'east'},
    'center':        {'relative': 'center', 'vertical': 'center', 'bagua_direction': 'center'},
    'right_center':  {'relative': 'right',  'vertical': 'center', 'bagua_direction': 'west'},
    'left_back':     {'relative': 'left',   'vertical': 'back',   'bagua_direction': 'northeast'},
    'center_back':   {'relative': 'center', 'vertical': 'back',   'bagua_direction': 'north'},
    'right_back':    {'relative': 'right',  'vertical': 'back',   'bagua_direction': 'northwest'},
}

_RELATIVE_NAMES = {'left': '左侧（青龙位）', 'center': '中间', 'right': '右侧（白虎位）'}
_VERTICAL_NAMES = {'front': '前方（朱雀位）', 'center': '中间', 'back': '后方（玄武位）'}


class VisionAnalyzer:
    """直接调用 dashscope Application API 识别办公桌物品，不依赖 scripts/ 目录"""

    def __init__(self, app_id: Optional[str] = None, api_key: Optional[str] = None):
        self._app_id = app_id
        self._api_key = api_key
        self._sdk_ready = False

    def _ensure_sdk(self):
        """懒初始化 dashscope SDK"""
        if self._sdk_ready:
            return
        import dashscope
        api_key = self._api_key
        if not api_key:
            try:
                from server.config.config_loader import get_config_from_db_only
                api_key = get_config_from_db_only("BAILIAN_API_KEY")
            except Exception:
                pass
        if not api_key:
            api_key = os.environ.get("DASHSCOPE_API_KEY", "")
        if not api_key:
            raise ValueError("未配置百炼 API Key（BAILIAN_API_KEY / DASHSCOPE_API_KEY）")
        dashscope.api_key = api_key
        self._sdk_ready = True

    def _get_app_id(self) -> str:
        if self._app_id:
            return self._app_id
        try:
            from server.config.config_loader import get_config_from_db_only
            app_id = get_config_from_db_only("BAILIAN_DESK_FENGSHUI_VISION_APP_ID")
            if app_id:
                return app_id
        except Exception:
            pass
        raise ValueError("未配置 BAILIAN_DESK_FENGSHUI_VISION_APP_ID")

    async def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        """调用百炼 Qwen-VL 智能体识别桌面物品"""
        try:
            self._ensure_sdk()
            from dashscope import Application

            app_id = self._get_app_id()
            img_b64 = base64.b64encode(image_bytes).decode('utf-8')

            loop = asyncio.get_event_loop()
            raw_text = await loop.run_in_executor(
                None,
                self._call_vision_app,
                Application, app_id, img_b64,
            )

            vision_data = self._parse_response(raw_text)
            items = self._convert_items(vision_data.get('items', []))

            return {
                'success': True,
                'items': items,
                'scene': vision_data.get('scene', {}),
                'total_items': vision_data.get('total_items', len(items)),
                'summary': vision_data.get('summary', ''),
                'image_shape': None,
                'source': 'qwen_vl',
            }
        except Exception as e:
            logger.error(f"VisionAnalyzer 失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'source': 'qwen_vl'}

    @staticmethod
    def _call_vision_app(Application, app_id: str, img_b64: str) -> str:
        """同步调用百炼视觉应用（在 executor 中运行）"""
        response = Application.call(
            app_id=app_id,
            messages=[{
                "role": "user",
                "content": [
                    {"image": f"data:image/jpeg;base64,{img_b64}"},
                    {"text": "请分析这张办公桌照片"},
                ],
            }],
            stream=False,
        )
        if response.status_code != 200:
            raise ValueError(
                f"百炼视觉应用错误: {response.status_code} "
                f"{getattr(response, 'code', '')} - {getattr(response, 'message', '')}"
            )
        text = (response.output or {}).get('text', '')
        if not text:
            raise ValueError(f"百炼视觉应用返回空文本, output={response.output}")
        return text

    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(text: str) -> Dict[str, Any]:
        """从 LLM 返回的文本中提取 JSON（兼容 ```json{...}``` 等格式）"""
        import re
        cleaned = text.strip()

        # 去掉 markdown code fence（```json ... ``` 或 ``` ... ```）
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned)
        cleaned = cleaned.strip()

        # 尝试直接解析
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 提取最外层 { ... } 块
        start = cleaned.find('{')
        if start == -1:
            raise ValueError(f"无法解析视觉模型返回的 JSON: {text[:200]}")

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
            raise ValueError(f"JSON 解析失败: {e}, 原文前 200 字: {text[:200]}")

    @staticmethod
    def _convert_items(raw_items: List[Dict]) -> List[Dict]:
        """将 vision LLM 输出的 items 转换为规则引擎可消费的格式"""
        converted = []
        for item in raw_items:
            pos_key = item.get('position', 'center')
            pos_info = _POSITION_MAP.get(pos_key, _POSITION_MAP['center'])

            converted.append({
                'name': item.get('name', 'unknown'),
                'label': item.get('label', item.get('name', '')),
                'confidence': item.get('confidence', 0.9),
                'count': item.get('count', 1),
                'description': item.get('description', ''),
                'bbox': [],
                'position': {
                    'relative': pos_info['relative'],
                    'relative_name': _RELATIVE_NAMES.get(pos_info['relative'], ''),
                    'vertical': pos_info['vertical'],
                    'vertical_name': _VERTICAL_NAMES.get(pos_info['vertical'], ''),
                    'bagua_direction': pos_info['bagua_direction'],
                    'center': [],
                    'normalized': {},
                },
            })
        return converted
