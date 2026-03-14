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

    RULES_CACHE_KEY = 'home_fengshui:rules:v1'
    RULES_CACHE_TTL = 3600  # 1小时

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
