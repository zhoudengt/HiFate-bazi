#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则匹配 Mixin

从 bazi_calculator.py 提取的规则匹配相关方法。
包含本地规则匹配、规则输入构建、规则筛选条件管理。
"""

import json

from core.calculators.bazi_logging import safe_log


class BaziRuleMatcherMixin:
    """规则匹配方法，以 Mixin 方式注入 WenZhenBazi"""

    _rule_filter_map = None

    def match_rules(self, rule_types=None, use_cache=False):
        """匹配规则，返回 (matched_rules, unmatched_rules_with_reason) 并记录上下文"""
        from server.services.rule_service import RuleService
        from server.engines.rule_condition import EnhancedRuleCondition

        if not self.last_result:
            self.calculate()

        try:
            remote_result = self._match_rules_via_service(rule_types, use_cache)
            if remote_result is not None:
                return remote_result
        except RuntimeError as exc:
            if "未设置" in str(exc):
                safe_log('warning', f"⚠️  bazi_calculator.py: {exc}")
            else:
                raise
        except Exception as exc:
            import traceback
            safe_log('warning', f"⚠️  bazi_calculator.py: 微服务规则匹配失败，使用本地匹配: {exc}")

        return self._match_rules_locally(rule_types=rule_types, use_cache=use_cache)

    def _match_rules_locally(self, rule_types=None, use_cache=False):
        """本地规则匹配（仅在微服务挂掉时使用）"""
        from server.services.rule_service import RuleService
        from server.engines.rule_condition import EnhancedRuleCondition

        if not self.last_result:
            self.calculate()

        try:
            bazi_data = self.build_rule_input()
        except Exception as e:
            safe_log('error', f"❌ build_rule_input 失败: {e}")
            import traceback
            traceback.print_exc()
            return [], []

        try:
            matched = RuleService.match_rules(
                bazi_data,
                rule_types=rule_types,
                use_cache=use_cache
            )
        except Exception as e:
            safe_log('error', f"❌ RuleService.match_rules 调用失败: {e}")
            import traceback
            traceback.print_exc()
            return [], []

        if not isinstance(matched, list):
            safe_log('warning', f"⚠️  RuleService.match_rules 返回了非列表类型: {type(matched)}, 值: {matched}")
            matched = []

        filtered_matched = []
        for idx, rule in enumerate(matched):
            if not isinstance(rule, dict):
                safe_log('warning', f"⚠️  匹配规则列表中的第 {idx} 个元素不是字典: {type(rule)}, 值: {repr(rule)[:100]}")
                continue
            filtered_matched.append(rule)
        matched = filtered_matched
        self.last_matched_rules = matched

        try:
            engine = RuleService.get_engine()
        except Exception as e:
            safe_log('error', f"❌ RuleService.get_engine 失败: {e}")
            import traceback
            traceback.print_exc()
            return matched, []

        if not isinstance(engine.rules, list):
            safe_log('warning', f"⚠️  engine.rules 不是列表类型: {type(engine.rules)}")
            engine.rules = []

        relevant_rules = []
        for idx, rule in enumerate(engine.rules):
            if not isinstance(rule, dict):
                safe_log('warning', f"⚠️  engine.rules 中第 {idx} 个元素不是字典: {type(rule)}, 值: {repr(rule)[:100]}")
                continue
            try:
                rule_type = rule.get('rule_type')
                if not rule_types or rule_type in rule_types:
                    relevant_rules.append(rule)
            except Exception as e:
                safe_log('warning', f"⚠️  处理规则时出错 (索引 {idx}): {e}")
                continue

        matched_ids = set()
        for idx, rule in enumerate(matched):
            if not isinstance(rule, dict):
                safe_log('warning', f"⚠️  匹配规则列表中第 {idx} 个元素不是字典: {type(rule)}, 值: {repr(rule)[:100]}")
                continue
            try:
                rule_id = rule.get('rule_code') or rule.get('rule_id')
                if rule_id:
                    matched_ids.add(rule_id)
            except Exception as e:
                safe_log('warning', f"⚠️  获取规则 ID 时出错 (索引 {idx}): {e}, 规则: {repr(rule)[:100]}")
                continue

        def explain(condition, path=""):
            if not condition:
                return "条件为空"
            if not isinstance(condition, dict):
                return f"条件不是字典类型: {type(condition)}"
            try:
                for k, v in condition.items():
                    current_path = f"{path}/{k}" if path else k
                    if k == "all":
                        if not isinstance(v, list):
                            return f"{current_path} 应该是列表类型，但实际是: {type(v)}"
                        for i, sub in enumerate(v or []):
                            if not EnhancedRuleCondition.match(sub, bazi_data):
                                return explain(sub, f"{current_path}[{i}]")
                    elif k == "any":
                        if not isinstance(v, list):
                            return f"{current_path} 应该是列表类型，但实际是: {type(v)}"
                        if any(EnhancedRuleCondition.match(sub, bazi_data) for sub in (v or [])):
                            continue
                        return f"{current_path} 中所有分支均未满足"
                    elif k == "not":
                        if EnhancedRuleCondition.match(v, bazi_data):
                            return f"{current_path} 应该不成立，但实际成立"
                    else:
                        if not EnhancedRuleCondition.match({k: v}, bazi_data):
                            return f"{current_path} 条件未满足，期望 {v}"
            except Exception as e:
                return f"解释条件时出错: {e}"
            return f"{path or '条件'} 未满足（原因未知）"

        unmatched = []
        context_map = {}
        for idx, rule in enumerate(relevant_rules):
            try:
                if not isinstance(rule, dict):
                    safe_log('warning', f"⚠️  relevant_rules 中第 {idx} 个元素不是字典: {type(rule)}, 值: {repr(rule)[:100]}")
                    continue

                rule_id = rule.get('rule_id') or rule.get('rule_code')
                if not rule_id:
                    continue

                if rule_id in matched_ids:
                    conditions = rule.get('conditions', {})
                    if isinstance(conditions, dict):
                        try:
                            context_map[rule_id] = self._collect_condition_values(conditions, bazi_data)
                        except Exception as e:
                            safe_log('warning', f"⚠️  收集条件值时出错 (规则 {rule_id}): {e}")
                    continue

                conditions = rule.get('conditions', {})
                if not isinstance(conditions, dict):
                    safe_log('warning', f"⚠️  规则 {rule_id} 的 conditions 不是字典类型: {type(conditions)}, 值: {repr(conditions)[:100]}")
                    conditions = {}

                try:
                    if EnhancedRuleCondition.match(conditions, bazi_data):
                        try:
                            context_map[rule_id] = self._collect_condition_values(conditions, bazi_data)
                        except Exception as e:
                            safe_log('warning', f"⚠️  收集条件值时出错 (规则 {rule_id}): {e}")
                        continue
                except Exception as e:
                    safe_log('warning', f"⚠️  匹配规则 {rule_id} 时出错: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

                reason = explain(conditions)
                try:
                    rule_snapshot = {
                        k: rule.get(k)
                        for k in ('rule_id', 'rule_code', 'rule_name', 'rule_type', 'conditions', 'content')
                    }
                except Exception as e:
                    safe_log('warning', f"⚠️  构建 rule_snapshot 时出错 (规则 {rule_id}): {e}")
                    rule_snapshot = {}

                unmatched.append({
                    'rule_id': rule_id,
                    'rule_name': rule.get('rule_name', '') if isinstance(rule, dict) else '',
                    'rule_type': rule.get('rule_type', '') if isinstance(rule, dict) else '',
                    'reason': reason,
                    'rule': rule_snapshot,
                })

                try:
                    context_map[rule_id] = self._collect_condition_values(conditions, bazi_data)
                except Exception as e:
                    safe_log('warning', f"⚠️  收集条件值时出错 (规则 {rule_id}): {e}")
            except Exception as e:
                safe_log('error', f"❌ 处理规则时发生未捕获的异常 (索引 {idx}): {e}")
                import traceback
                traceback.print_exc()
                continue

        self.last_rule_context = context_map
        self.last_unmatched_rules = unmatched

        return matched, unmatched

    def build_rule_input(self, current_time=None):
        if not self.last_result:
            self.calculate()

        try:
            fortune_snapshot = self._ensure_fortune_snapshot(current_time=current_time)
        except Exception:
            fortune_snapshot = {}

        ten_gods_stats = self.last_result.get('ten_gods_stats', {})
        if isinstance(ten_gods_stats, str):
            try:
                ten_gods_stats = json.loads(ten_gods_stats)
            except (json.JSONDecodeError, TypeError):
                ten_gods_stats = {}
        elif not isinstance(ten_gods_stats, dict):
            ten_gods_stats = {}

        if isinstance(ten_gods_stats, dict):
            for key in ['main', 'sub', 'totals', 'ten_gods_main', 'ten_gods_sub', 'ten_gods_total']:
                stats_value = ten_gods_stats.get(key)
                if isinstance(stats_value, str):
                    try:
                        ten_gods_stats[key] = json.loads(stats_value)
                    except (json.JSONDecodeError, TypeError):
                        ten_gods_stats[key] = {}
                elif not isinstance(stats_value, dict) and stats_value is not None:
                    ten_gods_stats[key] = {}

        return {
            'basic_info': self.last_result.get('basic_info', {}),
            'bazi_pillars': self.last_result.get('bazi_pillars', {}),
            'details': self.last_result.get('details', {}),
            'ten_gods_stats': ten_gods_stats,
            'elements': self.last_result.get('elements', {}),
            'element_counts': self.last_result.get('element_counts', {}),
            'relationships': self.last_result.get('relationships', {}),
            'fortune': fortune_snapshot
        }

    @classmethod
    def _load_rule_filters(cls):
        """加载规则筛选条件（已移除外部文件依赖，使用数据库规则）"""
        if cls._rule_filter_map is not None:
            return
        cls._rule_filter_map = {}

    @classmethod
    def _get_rule_filters(cls, rule_id: str):
        """获取规则筛选条件（已移除外部文件依赖）"""
        cls._load_rule_filters()
        return cls._rule_filter_map.get(rule_id, {})
