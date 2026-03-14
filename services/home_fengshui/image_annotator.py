# -*- coding: utf-8 -*-
"""
居家风水标注图生成器
在房间照片上叠加九宫格 + 家具标注 + 吉凶色标
"""

import base64
import logging
from io import BytesIO
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 严重级别颜色
SEVERITY_COLORS = {
    'critical': (220, 50, 50),    # 红
    'warning':  (255, 165, 0),    # 橙
    'tip':      (50, 180, 50),    # 绿
}

# 方位颜色（吉凶）
AUSPICIOUS_COLOR   = (50, 200, 50, 60)    # 半透明绿
INAUSPICIOUS_COLOR = (220, 50, 50, 60)    # 半透明红
NEUTRAL_COLOR      = (150, 150, 150, 40)  # 半透明灰


def generate_annotated_image(
    image_bytes: bytes,
    furnitures: List[Dict],
    analysis_result: Dict,
    door_direction: Optional[str] = None,
    mingua_info: Optional[Dict] = None,
) -> Optional[str]:
    """
    生成居家风水标注图

    Args:
        image_bytes: 原始图片
        furnitures: 识别到的家具列表
        analysis_result: 分析结果
        door_direction: 大门朝向
        mingua_info: 命卦信息

    Returns:
        base64编码的标注图，失败返回None
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io

        img = Image.open(BytesIO(image_bytes)).convert('RGBA')
        width, height = img.size

        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 绘制九宫格线（半透明白色）
        for i in (1, 2):
            x = width * i // 3
            draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 100), width=1)
        for j in (1, 2):
            y = height * j // 3
            draw.line([(0, y), (width, y)], fill=(255, 255, 255, 100), width=1)

        # 获取问题家具集合
        critical_items = {s['item_name'].lower() for s in analysis_result.get('critical_issues', [])}
        warning_items  = {s['item_name'].lower() for s in analysis_result.get('suggestions', [])}

        # 标注家具
        try:
            font = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 14)
            font_small = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 11)
        except Exception:
            font = ImageFont.load_default()
            font_small = font

        for i, item in enumerate(furnitures):
            name = item.get('name', '').lower()
            label = item.get('label', name)
            bbox = item.get('bbox', [])

            if len(bbox) == 4:
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            else:
                # 根据position_zone估算位置
                zone = item.get('position_zone', 'center')
                x1, y1, x2, y2 = _zone_to_bbox(zone, width, height)

            if name in critical_items:
                color = SEVERITY_COLORS['critical']
                border_color = (*color, 200)
            elif name in warning_items:
                color = SEVERITY_COLORS['warning']
                border_color = (*color, 200)
            else:
                color = (100, 180, 100)
                border_color = (*color, 200)

            # 绘制边框
            draw.rectangle([x1, y1, x2, y2], outline=border_color, width=2)

            # 绘制标签背景
            text = label
            bbox_text = draw.textbbox((x1, y1 - 18), text, font=font)
            draw.rectangle(bbox_text, fill=(*color, 180))
            draw.text((x1, y1 - 18), text, fill=(255, 255, 255), font=font)

        # 大门朝向标注
        if door_direction:
            info_text = f'大门：{door_direction}'
            if mingua_info:
                info_text += f' | 命卦：{mingua_info.get("mingua_name", "")}（{mingua_info.get("mingua_type", "")}）'
            draw.rectangle([(0, 0), (len(info_text) * 8 + 10, 22)], fill=(0, 0, 0, 150))
            draw.text((5, 4), info_text, fill=(255, 255, 255), font=font_small)

        # 评分标注
        score = analysis_result.get('overall_score', 0)
        score_text = f'评分：{score}分'
        draw.rectangle([(width - 90, 0), (width, 22)], fill=(0, 0, 0, 150))
        draw.text((width - 85, 4), score_text, fill=(255, 215, 0), font=font_small)

        # 合成图层
        result_img = Image.alpha_composite(img, overlay).convert('RGB')

        buffer = BytesIO()
        result_img.save(buffer, format='JPEG', quality=85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    except ImportError:
        logger.warning('PIL 未安装，跳过标注图生成')
        return None
    except Exception as e:
        logger.error(f'生成标注图失败: {e}', exc_info=True)
        return None


def _zone_to_bbox(zone: str, width: int, height: int):
    """将九宫格区域名称转换为大致坐标"""
    zone_map = {
        'northwest': (0, 0), 'north': (1, 0), 'northeast': (2, 0),
        'west':      (0, 1), 'center': (1, 1), 'east':    (2, 1),
        'southwest': (0, 2), 'south': (1, 2), 'southeast': (2, 2),
    }
    col, row = zone_map.get(zone, (1, 1))
    cw, ch = width // 3, height // 3
    x1 = col * cw + cw // 4
    y1 = row * ch + ch // 4
    x2 = x1 + cw // 2
    y2 = y1 + ch // 2
    return x1, y1, x2, y2
