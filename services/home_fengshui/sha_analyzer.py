# -*- coding: utf-8 -*-
"""
居家风水煞位分析器
汇总缺角煞、八宅凶星房间分析、内部煞气（视觉识别结果）
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 缺角方位 → 影响的家庭成员 + 五行 + 健康影响
# ---------------------------------------------------------------------------
MISSING_CORNER_IMPACT = {
    '西北': {
        'gua': '乾', 'element': '金', 'family': '父亲/男主人',
        'health': '头部、骨骼',
        'impact': '影响男主人事业运和权威，家中缺乏主心骨',
        'remedies': ['摆放金属材质的装饰品', '放置铜钟或铜葫芦', '此处保持明亮整洁'],
    },
    '西南': {
        'gua': '坤', 'element': '土', 'family': '母亲/女主人',
        'health': '脾胃、腹部',
        'impact': '影响女主人健康运和家庭和睦',
        'remedies': ['摆放陶瓷花瓶', '放置黄水晶或黄色装饰', '种植宽叶绿植'],
    },
    '正东': {
        'gua': '震', 'element': '木', 'family': '长子',
        'health': '肝胆、足部',
        'impact': '影响长子发展运势，家中缺乏活力',
        'remedies': ['摆放绿色植物', '放置木质工艺品', '挂山水画增加生气'],
    },
    '东南': {
        'gua': '巽', 'element': '木', 'family': '长女',
        'health': '肝胆、臀部',
        'impact': '影响长女运势和家庭财运',
        'remedies': ['摆放常青绿植', '挂风景画', '放置木雕或竹制品'],
    },
    '正北': {
        'gua': '坎', 'element': '水', 'family': '中男',
        'health': '肾脏、耳朵、泌尿系统',
        'impact': '影响中男健康和学业，事业发展受阻',
        'remedies': ['摆放鱼缸或水景', '放置黑色或蓝色装饰', '挂山水画（水多）'],
    },
    '正南': {
        'gua': '离', 'element': '火', 'family': '中女',
        'health': '心脏、眼睛',
        'impact': '影响中女健康和家庭声誉',
        'remedies': ['放置红色装饰品', '增加照明', '挂日出或红色系画作'],
    },
    '东北': {
        'gua': '艮', 'element': '土', 'family': '幼子',
        'health': '脾胃、手指',
        'impact': '影响幼子学业和家庭子嗣运',
        'remedies': ['摆放陶瓷或石质装饰', '放置水晶球', '此处保持整洁有序'],
    },
    '正西': {
        'gua': '兑', 'element': '金', 'family': '幼女',
        'health': '呼吸系统、口腔',
        'impact': '影响幼女健康和家庭口福、社交',
        'remedies': ['摆放金属风铃', '放置白色或金色装饰', '此处宜通风明亮'],
    },
}

# ---------------------------------------------------------------------------
# 八宅凶星 + 房间类型 → 煞气严重程度
# ---------------------------------------------------------------------------
INAUSPICIOUS_ROOM_SEVERITY = {
    ('绝命', 'master_bedroom'): 'critical',
    ('绝命', 'second_bedroom'): 'critical',
    ('绝命', 'kitchen'): 'warning',
    ('五鬼', 'master_bedroom'): 'critical',
    ('五鬼', 'kitchen'): 'critical',
    ('五鬼', 'study'): 'warning',
    ('六煞', 'master_bedroom'): 'warning',
    ('六煞', 'kitchen'): 'warning',
    ('祸害', 'master_bedroom'): 'warning',
    ('祸害', 'study'): 'minor',
}

# 凶星含义
STAR_MEANING = {
    '绝命': {'level': '大凶', 'meaning': '重病、凶险、破大财', 'priority': 1},
    '五鬼': {'level': '大凶', 'meaning': '火灾、盗贼、是非口舌', 'priority': 2},
    '六煞': {'level': '次凶', 'meaning': '桃花劫、感情纠葛、破财', 'priority': 3},
    '祸害': {'level': '小凶', 'meaning': '小病小痛、小人干扰', 'priority': 4},
}


class ShaAnalyzer:
    """居家风水煞位综合分析器"""

    def analyze_all(
        self,
        missing_corners: Optional[List[Dict]] = None,
        house_directions: Optional[Dict[str, str]] = None,
        room_positions: Optional[Dict[str, Dict]] = None,
        vision_items: Optional[List[Dict]] = None,
        door_direction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        综合煞位分析

        Args:
            missing_corners: 缺角列表（from FloorPlanAnalyzer）
            house_directions: 宅卦吉凶方位 {'生气': '东南', ...}
            room_positions: 房间→方位映射 {'master_bedroom': {'zone_cn': '西北'}}
            vision_items: 视觉识别的家具/布局问题（from VisionAnalyzer rooms）
            door_direction: 大门朝向

        Returns:
            综合煞位分析结果
        """
        result = {
            'missing_corner_sha': [],
            'eight_mansion_sha': [],
            'internal_sha': [],
            'summary': {'total_sha_count': 0, 'critical_count': 0, 'warning_count': 0},
        }

        if missing_corners:
            result['missing_corner_sha'] = self.analyze_missing_corner_sha(missing_corners)

        if house_directions and room_positions:
            result['eight_mansion_sha'] = self.analyze_eight_mansion_sha(
                house_directions, room_positions
            )

        if vision_items:
            result['internal_sha'] = self.analyze_internal_sha(vision_items)

        all_sha = (
            result['missing_corner_sha']
            + result['eight_mansion_sha']
            + result['internal_sha']
        )
        result['summary']['total_sha_count'] = len(all_sha)
        result['summary']['critical_count'] = sum(1 for s in all_sha if s.get('severity') == 'critical')
        result['summary']['warning_count'] = sum(1 for s in all_sha if s.get('severity') == 'warning')

        return result

    def analyze_missing_corner_sha(self, missing_corners: List[Dict]) -> List[Dict]:
        """
        缺角煞分析

        Args:
            missing_corners: [{'direction': '正东', 'missing_percent': 70, 'severity': 'critical', ...}]
        """
        sha_list = []
        for mc in missing_corners:
            direction = mc.get('direction', '')
            direction_key = direction.replace('正', '')
            if direction_key not in MISSING_CORNER_IMPACT:
                direction_key = direction
            impact = MISSING_CORNER_IMPACT.get(direction_key, {})
            if not impact:
                continue

            severity = mc.get('severity', 'minor')
            mp = mc.get('missing_percent', 0)

            sha_list.append({
                'type': 'missing_corner',
                'direction': direction,
                'gua': impact.get('gua', mc.get('gua', '')),
                'element': impact.get('element', ''),
                'severity': severity,
                'missing_percent': mp,
                'affected_family': impact.get('family', ''),
                'health_risk': impact.get('health', ''),
                'impact_description': impact.get('impact', ''),
                'remedies': impact.get('remedies', []),
            })

        sha_list.sort(key=lambda x: {'critical': 0, 'warning': 1, 'minor': 2}.get(x['severity'], 9))
        return sha_list

    def analyze_eight_mansion_sha(
        self,
        house_directions: Dict[str, str],
        room_positions: Dict[str, Dict],
    ) -> List[Dict]:
        """
        八宅凶星房间分析
        检查哪些房间落在凶星方位上

        Args:
            house_directions: 宅卦方位 {'绝命': '西南', '五鬼': '东北', ...}
            room_positions: {'master_bedroom': {'zone_cn': '西北', 'gua': '乾'}}
        """
        inauspicious_stars = {'绝命', '五鬼', '六煞', '祸害'}
        direction_to_star = {}
        for star, direction in house_directions.items():
            if star in inauspicious_stars:
                direction_to_star[direction] = star

        sha_list = []
        for room_type, pos_info in room_positions.items():
            zone_cn = pos_info.get('zone_cn', '')
            if not zone_cn:
                continue
            zone_cn_normalized = zone_cn.replace('正', '')
            star = direction_to_star.get(zone_cn) or direction_to_star.get(zone_cn_normalized) or direction_to_star.get(f'正{zone_cn_normalized}')
            if not star:
                continue

            star_info = STAR_MEANING.get(star, {})
            severity_key = (star, room_type)
            severity = INAUSPICIOUS_ROOM_SEVERITY.get(severity_key, 'minor')

            sha_list.append({
                'type': 'eight_mansion',
                'star': star,
                'star_level': star_info.get('level', ''),
                'star_meaning': star_info.get('meaning', ''),
                'room_type': room_type,
                'room_zone': zone_cn,
                'severity': severity,
                'description': f'{zone_cn}方（{star}位）有{_room_type_cn(room_type)}，{star_info.get("meaning", "")}',
                'remedies': _get_star_room_remedies(star, room_type),
            })

        sha_list.sort(key=lambda x: STAR_MEANING.get(x.get('star', ''), {}).get('priority', 9))
        return sha_list

    def analyze_internal_sha(self, vision_items: List[Dict]) -> List[Dict]:
        """
        内部煞气分析（基于视觉识别的家具状态）
        从各房间的 vision 结果中提取煞气
        """
        sha_list = []
        sha_patterns = [
            ('横梁压床', 'critical', '床铺正上方有横梁，形成压顶之势', ['移床避梁', '安装吊顶遮盖', '悬挂葫芦或五帝钱化解']),
            ('镜子对床', 'warning', '镜子正对床铺，影响睡眠和夫妻感情', ['移走镜子或用布遮盖', '将镜子转向', '放在衣柜内']),
            ('门窗直冲', 'warning', '门窗成一条直线，形成穿堂风格局', ['在中间放置屏风或隔断', '摆放绿植阻挡', '悬挂珠帘']),
            ('床头靠窗', 'minor', '床头靠窗缺少靠山', ['床头移靠实墙', '窗帘加厚遮挡', '放置靠背板']),
            ('厕所居中', 'critical', '卫生间位于房屋中心，污秽之气扩散', ['保持厕所门常关', '增加排气扇', '放置活性炭或绿植净化']),
        ]

        for item in vision_items:
            state = item.get('state', '')
            if not state:
                continue
            for pattern, severity, desc, remedies in sha_patterns:
                if pattern in state or any(k in state for k in pattern.split()):
                    sha_list.append({
                        'type': 'internal',
                        'pattern': pattern,
                        'severity': severity,
                        'source_item': item.get('name', ''),
                        'room_type': item.get('room_type', ''),
                        'description': desc,
                        'remedies': remedies,
                    })
                    break

        return sha_list


def _room_type_cn(room_type: str) -> str:
    mapping = {
        'master_bedroom': '主卧', 'second_bedroom': '次卧', 'bedroom': '卧室',
        'living_room': '客厅', 'kitchen': '厨房', 'bathroom': '卫生间',
        'study': '书房', 'dining_room': '餐厅', 'balcony': '阳台',
        'storage': '储物间', 'hallway': '走廊', 'entrance': '玄关',
    }
    return mapping.get(room_type, room_type)


def _get_star_room_remedies(star: str, room_type: str) -> List[str]:
    """根据凶星类型和房间类型给出化解方案"""
    base_remedies = {
        '绝命': ['此方位避免做卧室', '摆放铜葫芦或五帝钱化解'],
        '五鬼': ['避免明火（厨房尤其注意）', '摆放风水葫芦化解', '放置水晶球或鱼缸'],
        '六煞': ['避免做主卧', '此处宜放杂物间', '摆放铜器化解'],
        '祸害': ['保持整洁明亮', '摆放绿植增加生气'],
    }
    remedies = list(base_remedies.get(star, []))

    if room_type in ('master_bedroom', 'second_bedroom', 'bedroom'):
        if star in ('绝命', '五鬼'):
            remedies.insert(0, '**建议换房间**：此方位不宜做卧室')
        remedies.append('床头朝向个人生气位方向')
    elif room_type == 'kitchen':
        if star == '五鬼':
            remedies.insert(0, '**重点注意**：五鬼位厨房有火灾隐患，加强安全')
        remedies.append('灶台朝向宜调整')

    return remedies
