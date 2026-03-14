# -*- coding: utf-8 -*-
"""
居家理想布局图生成器
调用 DashScope 通义万相 (Wanx) API 生成风水理想房间布局图
"""

import os
import sys
import logging
import asyncio
import base64
from typing import Dict, Any, List, Optional
from urllib.request import urlopen

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

ROOM_TYPE_LABELS = {
    'bedroom':     '卧室',
    'living_room': '客厅',
    'study':       '书房',
    'kitchen':     '厨房',
    'dining_room': '餐厅',
}


def _build_prompt(furnitures: List[Dict], analysis_result: Dict[str, Any], room_type: str) -> str:
    """根据识别结果和风水建议构造图片生成 prompt"""
    room_label = ROOM_TYPE_LABELS.get(room_type, '房间')
    item_names = [it.get('label', it.get('name', '')) for it in furnitures]

    critical = analysis_result.get('critical_issues', [])
    suggestions = analysis_result.get('suggestions', [])

    fix_hints = []
    for issue in (critical + suggestions)[:3]:
        sugg = issue.get('suggestion', '')
        if sugg:
            fix_hints.append(sugg[:30])

    parts = [
        f'一张整洁的现代{room_label}效果图，明亮室内环境，自然光线充足',
    ]
    if item_names:
        parts.append('房间内有：' + '、'.join(item_names[:8]))

    room_hints = {
        'bedroom':     '床头背靠实墙，镜子不正对床，床不在横梁下，整洁舒适',
        'living_room': '沙发背靠实墙，大门不正对沙发，客厅开阔明亮，财位有摆件',
        'study':       '书桌背靠实墙面向门，书架整齐，采光良好，文昌位有绿植',
        'kitchen':     '灶台整洁，冰箱不紧邻灶台，刀具收纳整齐，厨房明亮通风',
        'dining_room': '餐桌圆形，位置居中，灯光明亮温馨，餐椅摆放整齐',
    }
    parts.append(room_hints.get(room_type, '布局合理，整洁舒适'))
    if fix_hints:
        parts.append('布局特点：' + '，'.join(fix_hints))
    parts.append('写实风格，高清室内设计效果图，温馨和谐的居家氛围')

    return '，'.join(p for p in parts if p)


async def generate_layout_image(
    furnitures: List[Dict],
    analysis_result: Dict[str, Any],
    room_type: str = 'bedroom',
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    生成居家理想布局图（base64）

    Args:
        furnitures: 识别到的家具列表
        analysis_result: 分析结果
        room_type: 房间类型
        api_key: DashScope API Key（可选，默认从数据库配置读取）

    Returns:
        base64编码的图片，失败返回 None
    """
    try:
        import dashscope
        if not api_key:
            try:
                from server.config.config_loader import get_config_from_db_only
                api_key = get_config_from_db_only('BAILIAN_API_KEY')
            except Exception:
                pass
        if not api_key:
            api_key = os.environ.get('DASHSCOPE_API_KEY', '')
        if not api_key:
            logger.warning('未配置 BAILIAN_API_KEY，跳过布局图生成')
            return None

        dashscope.api_key = api_key
        prompt = _build_prompt(furnitures, analysis_result, room_type)
        logger.info(f'[LayoutGenerator] 生成布局图，room_type={room_type}, prompt 长度={len(prompt)}')

        loop = asyncio.get_event_loop()
        image_url = await asyncio.wait_for(
            loop.run_in_executor(None, _call_wanx, dashscope, prompt),
            timeout=60.0,
        )
        if not image_url:
            return None

        image_b64 = await loop.run_in_executor(None, _download_to_b64, image_url)
        logger.info('✅ 居家布局图生成成功')
        return image_b64

    except asyncio.TimeoutError:
        logger.warning('布局图生成超时（>60s）')
        return None
    except Exception as e:
        logger.warning(f'布局图生成失败（不影响主流程）: {e}')
        return None


def _call_wanx(dashscope, prompt: str) -> Optional[str]:
    from dashscope import ImageSynthesis
    response = ImageSynthesis.call(
        model='wanx-v1',
        prompt=prompt,
        n=1,
        size='1024*1024',
    )
    if response.status_code == 200:
        results = response.output.get('results', [])
        if results:
            return results[0].get('url')
    logger.warning(f'Wanx 生成失败: {response.status_code} {getattr(response, "message", "")}')
    return None


def _download_to_b64(url: str) -> Optional[str]:
    try:
        with urlopen(url, timeout=30) as resp:
            return base64.b64encode(resp.read()).decode('utf-8')
    except Exception as e:
        logger.warning(f'下载布局图失败: {e}')
        return None
