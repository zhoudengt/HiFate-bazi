# -*- coding: utf-8 -*-
"""
居家风水规则引擎
从数据库加载规则，匹配家具与风水规则，生成三级建议
"""

import sys
import os
import json
import logging
import hashlib
from typing import List, Dict, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

logger = logging.getLogger(__name__)

try:
    from shared.config.redis import get_redis_client
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    get_redis_client = None


class HomeFengshuiEngine:
    """居家风水规则引擎"""

    RULES_CACHE_KEY = 'home_fengshui:rules:v2'
    RULES_CACHE_TTL = 3600  # 1小时

    POSITION_CATEGORIES = {
        'missing_corner', 'eight_mansion',
        'wealth_position', 'wenzhang_position',
        'peach_blossom', 'tianyi_position',
    }

    def __init__(self):
        self._rules: List[Dict] = []
        self._rules_hash: str = ''
        logger.info('✅ HomeFengshuiEngine 初始化')

    # ------------------------------------------------------------------
    # 规则加载
    # ------------------------------------------------------------------

    def load_rules(self, force_reload: bool = False) -> bool:
        """从数据库（或Redis缓存）加载风水规则"""
        try:
            # 尝试从Redis缓存读取
            if not force_reload and REDIS_AVAILABLE:
                cached = self._load_from_redis()
                if cached:
                    return True

            rules = self._load_from_db()
            if rules is not None:
                self._rules = rules
                new_hash = hashlib.md5(json.dumps(rules, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                self._rules_hash = new_hash
                if REDIS_AVAILABLE:
                    self._save_to_redis(rules)
                logger.info(f'✅ 已加载 {len(self._rules)} 条居家风水规则')
                return True
        except Exception as e:
            logger.error(f'加载规则失败: {e}', exc_info=True)
        return False

    def _load_from_db(self) -> Optional[List[Dict]]:
        try:
            from server.config.config_loader import get_db_connection
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM home_fengshui_rules WHERE enabled=1 ORDER BY priority DESC"
                )
                rows = cursor.fetchall()
            conn.close()
            rules = []
            for row in rows:
                rule = dict(row)
                for field in ('condition_json',):
                    if isinstance(rule.get(field), str):
                        try:
                            rule[field] = json.loads(rule[field])
                        except Exception:
                            rule[field] = {}
                rules.append(rule)
            return rules
        except Exception as e:
            logger.warning(f'从数据库加载规则失败: {e}')
            return None

    def _load_from_redis(self) -> bool:
        try:
            redis_client = get_redis_client()
            data = redis_client.get(self.RULES_CACHE_KEY)
            if data:
                self._rules = json.loads(data)
                logger.debug(f'从Redis缓存加载 {len(self._rules)} 条规则')
                return True
        except Exception as e:
            logger.warning(f'Redis缓存读取失败: {e}')
        return False

    def _save_to_redis(self, rules: List[Dict]) -> None:
        try:
            redis_client = get_redis_client()
            redis_client.setex(self.RULES_CACHE_KEY, self.RULES_CACHE_TTL, json.dumps(rules, ensure_ascii=False))
        except Exception as e:
            logger.warning(f'Redis缓存写入失败: {e}')

    # ------------------------------------------------------------------
    # 规则匹配
    # ------------------------------------------------------------------

    def match_rules(
        self,
        furnitures: List[Dict],
        room_type: str,
        door_direction: Optional[str] = None,
        mingua_info: Optional[Dict] = None,
    ) -> Dict:
        """
        匹配风水规则，生成三级建议

        Args:
            furnitures: 识别到的家具列表
            room_type: 房间类型
            door_direction: 大门朝向
            mingua_info: 命卦信息（可选）

        Returns:
            {'success': True, 'critical_issues': [...], 'suggestions': [...], 'tips': [...], 'score': 0-100}
        """
        if not self._rules:
            self.load_rules()

        try:
            furniture_names = {f.get('name', '').lower() for f in furnitures}
            furniture_states = {f.get('name', '').lower(): f.get('state', '') for f in furnitures}
            furniture_zones = {f.get('name', '').lower(): f.get('position_zone', '') for f in furnitures}

            critical_issues: List[Dict] = []
            suggestions: List[Dict] = []
            tips: List[Dict] = []

            for rule in self._rules:
                # 房间过滤
                rule_room = rule.get('room_type', 'all')
                if rule_room not in ('all', room_type):
                    continue

                # 需要大门朝向但未提供
                if rule.get('direction_req') == 'yes' and not door_direction:
                    continue

                # 需要命卦但未提供
                if rule.get('mingua_req') == 'yes' and not mingua_info:
                    continue

                # 物品名称匹配
                item_name = rule.get('item_name', '').lower()
                if item_name and item_name not in ('all', 'general'):
                    if not any(item_name in fn or fn in item_name for fn in furniture_names):
                        continue

                # 条件检查
                if not self._check_conditions(rule, furniture_states, furniture_zones, door_direction, mingua_info):
                    continue

                severity = rule.get('severity', 'warning')
                suggestion_item = {
                    'item_name': rule.get('item_name', ''),
                    'item_label': rule.get('item_label', ''),
                    'severity': severity,
                    'issue': self._build_issue_text(rule, mingua_info, door_direction),
                    'suggestion': self._build_suggestion_text(rule, mingua_info),
                    'reason': rule.get('reason', ''),
                    'priority': 'high' if severity == 'critical' else ('medium' if severity == 'warning' else 'low'),
                    'rule_code': rule.get('rule_code', ''),
                }

                if severity == 'critical':
                    critical_issues.append(suggestion_item)
                elif severity == 'warning':
                    suggestions.append(suggestion_item)
                else:
                    tips.append(suggestion_item)

            # 计算分数
            score = self._calc_score(critical_issues, suggestions, tips, furnitures)

            return {
                'success': True,
                'critical_issues': critical_issues,
                'suggestions': suggestions,
                'tips': tips,
                'score': score,
                'summary': self._build_summary(score, critical_issues, suggestions),
            }

        except Exception as e:
            logger.error(f'规则匹配失败: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}

    def _check_conditions(
        self,
        rule: Dict,
        furniture_states: Dict,
        furniture_zones: Dict,
        door_direction: Optional[str],
        mingua_info: Optional[Dict],
    ) -> bool:
        """检查规则触发条件"""
        cond = rule.get('condition_json') or {}
        if not cond:
            return True

        # 状态条件（如：镜子正对床）
        required_state = cond.get('state')
        item_name = rule.get('item_name', '').lower()
        if required_state:
            actual_state = furniture_states.get(item_name, '')
            if required_state not in actual_state:
                return False

        # 方位条件（家具所在九宫格位置）
        required_zone = cond.get('position_zone')
        if required_zone and item_name in furniture_zones:
            if furniture_zones[item_name] != required_zone:
                return False

        # 命卦条件
        required_mingua_type = cond.get('mingua_type')
        if required_mingua_type and mingua_info:
            if mingua_info.get('mingua_type') != required_mingua_type:
                return False

        return True

    def _build_issue_text(self, rule: Dict, mingua_info: Optional[Dict], door_direction: Optional[str]) -> str:
        """构建问题描述文本（支持模板变量替换）"""
        issue = rule.get('reason', '') or ''
        if mingua_info and '{mingua_name}' in issue:
            issue = issue.replace('{mingua_name}', mingua_info.get('mingua_name', ''))
        if door_direction and '{door_direction}' in issue:
            issue = issue.replace('{door_direction}', door_direction)
        return issue

    def _build_suggestion_text(self, rule: Dict, mingua_info: Optional[Dict]) -> str:
        """构建建议文本（支持命卦模板变量替换）"""
        sugg = rule.get('suggestion', '') or ''
        if mingua_info:
            dirs = mingua_info.get('directions', {})
            for key in ('生气方向', '天医方向', '延年方向'):
                level = key.replace('方向', '')
                sugg = sugg.replace(f'{{{key}}}', dirs.get(level, ''))
            sugg = sugg.replace('{mingua_name}', mingua_info.get('mingua_name', ''))
        return sugg

    def _calc_score(
        self,
        critical: List[Dict],
        warnings: List[Dict],
        tips: List[Dict],
        furnitures: List[Dict],
    ) -> int:
        """
        计算综合评分 0-100
        扣分逻辑：critical -15分/条，warning -5分/条，tip -1分/条
        """
        base = 100
        score = base - len(critical) * 15 - len(warnings) * 5 - len(tips) * 1
        return max(0, min(100, score))

    def _build_summary(self, score: int, critical: List[Dict], warnings: List[Dict]) -> str:
        """构建分析摘要"""
        if score >= 85:
            level = '整体风水布局良好'
        elif score >= 70:
            level = '整体风水布局中等，有优化空间'
        elif score >= 55:
            level = '风水布局存在多处不足，建议调整'
        else:
            level = '风水布局问题较多，建议重点改善'

        parts = [f'综合评分 {score} 分。{level}。']
        if critical:
            parts.append(f'发现 {len(critical)} 处需立即调整的风水问题（如：{critical[0]["item_label"]}）。')
        if warnings:
            parts.append(f'有 {len(warnings)} 条优化建议。')
        return ''.join(parts)

    # ------------------------------------------------------------------
    # 方位相关规则匹配（缺角、八宅、财位、文昌位、桃花位、天医位）
    # ------------------------------------------------------------------

    def match_position_rules(
        self,
        missing_corners: Optional[List[Dict]] = None,
        house_directions: Optional[Dict[str, str]] = None,
        room_positions: Optional[Dict[str, Dict]] = None,
        position_data: Optional[Dict] = None,
        mingua_info: Optional[Dict] = None,
    ) -> Dict:
        """
        匹配方位相关风水规则

        Args:
            missing_corners: 缺角列表
            house_directions: 宅卦吉凶方位
            room_positions: 房间→方位映射
            position_data: 综合方位数据（from position_calculator.get_all_positions）
            mingua_info: 命卦信息

        Returns:
            {'critical_issues': [...], 'suggestions': [...], 'tips': [...], 'score_deduction': int}
        """
        if not self._rules:
            self.load_rules()

        critical_issues: List[Dict] = []
        suggestions: List[Dict] = []
        tips: List[Dict] = []

        position_rules = [r for r in self._rules if r.get('rule_category') in self.POSITION_CATEGORIES]

        for rule in position_rules:
            category = rule.get('rule_category', '')
            cond = rule.get('condition_json') or {}

            matched = False

            if category == 'missing_corner' and missing_corners:
                matched = self._match_missing_corner_rule(cond, missing_corners)
            elif category == 'eight_mansion' and house_directions and room_positions:
                matched = self._match_eight_mansion_rule(cond, house_directions, room_positions)
            elif category in ('wealth_position', 'wenzhang_position', 'peach_blossom', 'tianyi_position'):
                matched = self._match_position_type_rule(
                    cond, position_data or {}, room_positions or {}, mingua_info
                )

            if not matched:
                continue

            severity = rule.get('severity', 'tip')
            item = {
                'item_name': rule.get('item_name', ''),
                'item_label': rule.get('item_label', ''),
                'severity': severity,
                'category': category,
                'issue': self._build_issue_text(rule, mingua_info, None),
                'suggestion': self._build_suggestion_text(rule, mingua_info),
                'reason': rule.get('reason', ''),
                'priority': 'high' if severity == 'critical' else ('medium' if severity == 'warning' else 'low'),
                'rule_code': rule.get('rule_code', ''),
            }

            if severity == 'critical':
                critical_issues.append(item)
            elif severity == 'warning':
                suggestions.append(item)
            else:
                tips.append(item)

        deduction = len(critical_issues) * 15 + len(suggestions) * 5 + len(tips) * 1

        return {
            'critical_issues': critical_issues,
            'suggestions': suggestions,
            'tips': tips,
            'score_deduction': deduction,
        }

    def _match_missing_corner_rule(self, cond: Dict, missing_corners: List[Dict]) -> bool:
        """检查缺角规则是否匹配"""
        target_dir = cond.get('missing_direction', '')
        min_pct = cond.get('min_missing_percent', 0)
        if not target_dir:
            return False

        dir_map = {
            'northwest': '西北', 'north': '正北', 'northeast': '东北',
            'west': '正西', 'east': '正东',
            'southwest': '西南', 'south': '正南', 'southeast': '东南',
        }

        for mc in missing_corners:
            mc_dir = mc.get('direction', '')
            mc_dir_en = mc.get('direction_en', '')
            mc_pct = mc.get('missing_percent', 0)

            matched_dir = (
                mc_dir_en == target_dir
                or mc_dir == dir_map.get(target_dir, target_dir)
                or mc_dir.replace('正', '') == dir_map.get(target_dir, target_dir).replace('正', '')
            )
            if matched_dir and mc_pct >= min_pct:
                return True
        return False

    def _match_eight_mansion_rule(
        self, cond: Dict, house_directions: Dict[str, str], room_positions: Dict[str, Dict]
    ) -> bool:
        """检查八宅凶星房间规则是否匹配"""
        target_star = cond.get('star', '')
        target_room = cond.get('room_type', '')
        if not target_star or not target_room:
            return False

        star_direction = house_directions.get(target_star, '')
        if not star_direction:
            return False

        for room_type, pos_info in room_positions.items():
            if room_type != target_room:
                continue
            room_zone = pos_info.get('zone_cn', '')
            if self._direction_match(room_zone, star_direction):
                return True
        return False

    def _match_position_type_rule(
        self, cond: Dict, position_data: Dict, room_positions: Dict, mingua_info: Optional[Dict]
    ) -> bool:
        """检查方位类型规则（财位/文昌/桃花/天医）"""
        pos_type = cond.get('position_type', '')
        if not pos_type:
            return False

        if pos_type == 'bright_wealth':
            return bool(position_data.get('wealth_position', {}).get('bright', {}).get('positions'))

        if pos_type == 'bright_wealth' and cond.get('is_taboo'):
            return bool(position_data.get('wealth_position', {}).get('bright', {}).get('positions'))

        if pos_type == 'dark_wealth_shengqi':
            return bool(position_data.get('wealth_position', {}).get('dark', {}).get('shengqi'))

        if pos_type == 'dark_wealth_tianyi':
            return bool(position_data.get('wealth_position', {}).get('dark', {}).get('tianyi'))

        if pos_type == 'wealth_overlap':
            return position_data.get('wealth_position', {}).get('has_overlap', False)

        if pos_type == 'wealth_door_clash':
            return self._check_wealth_door_clash(position_data, room_positions)

        if pos_type == 'wealth_bathroom':
            return self._check_position_has_room(
                position_data.get('wealth_position', {}).get('bright', {}).get('positions', []),
                'bathroom', room_positions
            )

        if pos_type == 'personal_wenzhang':
            return bool(position_data.get('wenzhang_position', {}).get('personal', {}).get('direction'))

        if pos_type == 'house_wenzhang':
            return bool(position_data.get('wenzhang_position', {}).get('house', {}).get('direction'))

        if pos_type == 'wenzhang_overlap':
            return position_data.get('wenzhang_position', {}).get('overlap', False)

        if pos_type == 'zodiac_peach_blossom':
            return bool(position_data.get('peach_blossom_position', {}).get('zodiac', {}).get('direction'))

        if pos_type == 'annual_peach_blossom':
            return bool(position_data.get('peach_blossom_position', {}).get('annual', {}).get('direction'))

        if pos_type == 'house_peach_blossom':
            return bool(position_data.get('peach_blossom_position', {}).get('house', {}).get('direction'))

        if pos_type == 'peach_overlap':
            return position_data.get('peach_blossom_position', {}).get('has_overlap', False)

        if pos_type == 'tianyi_good':
            return bool(position_data.get('tianyi_position', {}).get('direction'))

        if pos_type == 'tianyi_bathroom':
            tianyi_dir = position_data.get('tianyi_position', {}).get('direction', '')
            return self._check_position_has_room([tianyi_dir], 'bathroom', room_positions) if tianyi_dir else False

        if pos_type == 'tianyi_kitchen':
            tianyi_dir = position_data.get('tianyi_position', {}).get('direction', '')
            return self._check_position_has_room([tianyi_dir], 'kitchen', room_positions) if tianyi_dir else False

        if pos_type == 'study_at_wenzhang':
            wc_dirs = []
            personal = position_data.get('wenzhang_position', {}).get('personal', {})
            house_wc = position_data.get('wenzhang_position', {}).get('house', {})
            if personal:
                wc_dirs.append(personal.get('direction', ''))
            if house_wc:
                wc_dirs.append(house_wc.get('direction', ''))
            return self._check_position_has_room(wc_dirs, 'study', room_positions)

        if pos_type == 'study_not_at_wenzhang':
            wc_dirs = []
            personal = position_data.get('wenzhang_position', {}).get('personal', {})
            house_wc = position_data.get('wenzhang_position', {}).get('house', {})
            if personal:
                wc_dirs.append(personal.get('direction', ''))
            if house_wc:
                wc_dirs.append(house_wc.get('direction', ''))
            has_study = any(rt == 'study' for rt in room_positions)
            return has_study and not self._check_position_has_room(wc_dirs, 'study', room_positions)

        return False

    @staticmethod
    def _direction_match(d1: str, d2: str) -> bool:
        """方位模糊匹配（正北 == 北 == north）"""
        if not d1 or not d2:
            return False
        n1 = d1.replace('正', '').strip()
        n2 = d2.replace('正', '').strip()
        return n1 == n2

    def _check_position_has_room(
        self, directions: List[str], room_type: str, room_positions: Dict[str, Dict]
    ) -> bool:
        """检查某方位列表中是否有指定房间类型"""
        for rt, pos_info in room_positions.items():
            if rt != room_type:
                continue
            zone_cn = pos_info.get('zone_cn', '')
            for d in directions:
                if d and self._direction_match(zone_cn, d):
                    return True
        return False

    def _check_wealth_door_clash(self, position_data: Dict, room_positions: Dict) -> bool:
        """检查财位是否与门冲"""
        wealth = position_data.get('wealth_position', {})
        bright_positions = wealth.get('bright', {}).get('positions', [])
        door_info = room_positions.get('entrance', {})
        door_zone = door_info.get('zone_cn', '')
        if not door_zone or not bright_positions:
            return False
        return any(self._direction_match(door_zone, wp) for wp in bright_positions)
