#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
婚姻推理引擎

4个推理类别：
1. 配偶星分析（spouse_star）：男看财星，女看官杀
2. 婚姻宫分析（marriage_palace）：日支状态
3. 婚恋时机（marriage_timing）：大运引动配偶星/婚姻宫
4. 大运动态力场（dynamic_balance）：大运期间五行力量重算
"""

from __future__ import annotations
import logging
from typing import Dict, List, Any, Optional

from core.inference.base_engine import BaseInferenceEngine
from core.inference.models import InferenceInput, InferenceResult, CausalChain
from core.inference.force_balancer import DynamicForceBalancer
from core.inference.condition_matcher import InferenceConditionMatcher
from core.inference.condition_checkers.marriage import MarriageMatchContext
from core.inference.quality_filter import InferenceQualityFilter, FilterConfig, MARRIAGE_CONTRADICTIONS
import core.inference.condition_checkers  # noqa: F401 trigger registration
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from core.data.relations import BRANCH_LIUHE

logger = logging.getLogger(__name__)

PILLAR_CN = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}

SHISHEN_MAP_MALE_SPOUSE = {'正财', '偏财'}
SHISHEN_MAP_FEMALE_SPOUSE = {'正官', '七杀'}

SHISHEN_TO_LABEL = {
    '正财': '正财（正妻星）',
    '偏财': '偏财（偏缘星）',
    '正官': '正官（正夫星）',
    '七杀': '七杀（偏夫星）',
}

WUXING_NATURE = {
    '木': '温和仁慈、有条理、注重成长',
    '火': '热情开朗、有感染力、行动派',
    '土': '稳重务实、包容性强、踏实可靠',
    '金': '干练果断、有原则、重信义',
    '水': '聪慧灵活、善于沟通、变通能力强',
}

SHISHEN_SPOUSE_CHARACTER = {
    '正财': {'strong_xi': '务实能干、善于理财、勤俭持家', 'weak_ji': '性格保守、过于计较、感情表达不足'},
    '偏财': {'strong_xi': '大方豪爽、社交能力强、异性缘佳', 'weak_ji': '花销大、不安定、感情上不够专一'},
    '正官': {'strong_xi': '正派可靠、有事业心、顾家负责', 'weak_ji': '过于严肃、给人压力大、管束过多'},
    '七杀': {'strong_xi': '有魄力担当、能力强、有保护欲', 'weak_ji': '脾气急躁、控制欲强、感情波折多'},
}

MARRIAGE_PALACE_SHISHEN = {
    '比肩': '配偶与自己性格相近，但容易争执。婚姻中需注意避免竞争',
    '劫财': '容易遇到竞争者或第三方干扰，配偶个性强、可能有争财之象',
    '食神': '配偶温和体贴、生活情趣丰富，夫妻相处融洽',
    '伤官': '感情表达直接甚至尖锐，配偶有才华但脾气大',
    '正财': '（男命）妻星坐婚姻宫，婚姻基础好，妻子贤良持家',
    '偏财': '（男命）偏财坐婚姻宫，配偶大方活泼，但感情多波动',
    '正官': '（女命）夫星坐婚姻宫，丈夫正派可靠，婚姻稳固',
    '七杀': '（女命）偏夫坐婚姻宫，丈夫有魄力但性格强势，婚姻需磨合',
    '正印': '配偶包容大度、有文化修养，能给自己精神支持',
    '偏印': '配偶想法独特、内心丰富，但可能有情感压抑',
}


class MarriageInferenceEngine(BaseInferenceEngine):
    """婚姻领域推理引擎"""

    @property
    def domain(self) -> str:
        return 'marriage'

    BAZI_RULE_CATEGORY_MAP = {
        'marriage_day_pillar': 'day_pillar_judgment',
        'marriage_day_branch': 'day_branch_judgment',
        'marriage_day_stem': 'spouse_appearance',
        'marriage_ten_gods': 'ten_gods_judgment',
        'marriage_stem_pattern': 'stem_pattern_judgment',
        'marriage_branch_pattern': 'branch_pattern_judgment',
        'marriage_deity': 'deity_judgment',
        'marriage_general': 'general_judgment',
        'marriage_bazi_pattern': 'bazi_pattern_judgment',
        'marriage_month_branch': 'month_branch_judgment',
        'marriage_year_branch': 'year_branch_judgment',
        'marriage_year_stem': 'year_stem_judgment',
        'marriage_element': 'element_judgment',
        'marriage_hour_pillar': 'hour_pillar_judgment',
        'marriage_year_pillar': 'year_pillar_judgment',
        'marriage_nayin': 'nayin_judgment',
        'marriage_lunar_birthday': 'lunar_birthday_judgment',
        'marriage_luck_cycle': 'luck_cycle_judgment',
        'marriage_year_event': 'year_event_judgment',
        'marriage': 'general_judgment',
        'formula_marriage': 'formula_judgment',
    }

    FILTER_CONFIG = FilterConfig(
        confidence_threshold=0.5,
        category_top_n=8,
        dedup_prefix_len=15,
        category_limits={
            'marriage_timing': 5,
            'dynamic_balance': 4,
        },
        contradiction_pairs=list(MARRIAGE_CONTRADICTIONS),
    )

    def _run_inference(self, inp: InferenceInput) -> InferenceResult:
        chains: List[CausalChain] = []

        chains.extend(self._infer_spouse_star(inp))
        chains.extend(self._infer_marriage_palace(inp))
        chains.extend(self._infer_dynamic_balance(inp))
        chains.extend(self._infer_marriage_timing(inp))
        chains.extend(self._infer_from_db_rules(inp))
        chains.extend(self._infer_from_bazi_rules(inp))

        chains = InferenceQualityFilter.apply(chains, self.FILTER_CONFIG)

        return InferenceResult(domain='marriage', chains=chains)

    # ─── 类别1：配偶星分析 ───────────────────────────────

    def _infer_spouse_star(self, inp: InferenceInput) -> List[CausalChain]:
        chains = []
        spouse_stars = self._find_spouse_stars(inp)
        if not spouse_stars:
            return chains

        xi_elements = set(inp.xi_ji_elements.get('xi_shen', []))

        for star_info in spouse_stars:
            star_type = star_info['shishen']
            pillar = star_info['pillar']
            element = star_info.get('element', '')
            is_xi = element in xi_elements if element else False

            char_map = SHISHEN_SPOUSE_CHARACTER.get(star_type, {})
            if is_xi:
                character = char_map.get('strong_xi', '')
                quality = '正面'
            else:
                character = char_map.get('weak_ji', '')
                quality = '需注意'

            element_nature = WUXING_NATURE.get(element, '') if element else ''

            label = SHISHEN_TO_LABEL.get(star_type, star_type)
            gender_label = '男命' if inp.gender == 'male' else '女命'
            pillar_cn = PILLAR_CN.get(pillar, pillar)

            chains.append(CausalChain(
                category='spouse_star',
                condition=f"{gender_label}，{label}在{pillar_cn}" + (f"，五行属{element}" if element else ""),
                mechanism=f"{label}为{'喜用神' if is_xi else '忌神'}，{element_nature}" if element_nature else f"{label}为{'喜用神' if is_xi else '忌神'}",
                conclusion=f"配偶特质：{character}",
                confidence=0.8 if is_xi else 0.7,
                source='子平真诠·论妻/论夫',
                details={'star_type': star_type, 'pillar': pillar, 'element': element, 'is_xi': is_xi, 'quality': quality}
            ))

        if len(spouse_stars) > 1:
            types = set(s['shishen'] for s in spouse_stars)
            if inp.gender == 'male' and '正财' in types and '偏财' in types:
                chains.append(CausalChain(
                    category='spouse_star',
                    condition='命局中正财与偏财同现',
                    mechanism='财星混杂，正偏财同透或同藏',
                    conclusion='感情世界较复杂，易有多段情缘或对感情有犹豫，建议晚婚以利稳定',
                    confidence=0.75,
                    source='子平真诠·论妻',
                ))
            elif inp.gender == 'female' and '正官' in types and '七杀' in types:
                chains.append(CausalChain(
                    category='spouse_star',
                    condition='命局中正官与七杀同现',
                    mechanism='官杀混杂，感情压力大，夫星不纯',
                    conclusion='感情历程多波折，容易遇到不同类型的异性，需以印星化杀来稳定。建议在感情中保持理性',
                    confidence=0.75,
                    source='滴天髓·论官杀',
                ))

        return chains

    def _find_spouse_stars(self, inp: InferenceInput) -> List[Dict[str, Any]]:
        target_set = SHISHEN_MAP_MALE_SPOUSE if inp.gender == 'male' else SHISHEN_MAP_FEMALE_SPOUSE
        stars = []
        for pillar_name in ['year', 'month', 'day', 'hour']:
            tg = inp.ten_gods.get(pillar_name, {})
            main_star = tg.get('main_star', '')
            if main_star in target_set:
                stem = inp.bazi_pillars.get(pillar_name, {}).get('stem', '')
                element = STEM_ELEMENTS.get(stem, '')
                stars.append({
                    'shishen': main_star, 'pillar': pillar_name,
                    'stem': stem, 'element': element
                })
            hidden_stars = tg.get('hidden_stars', [])
            hidden_stems = tg.get('hidden_stems', [])
            for idx, hs in enumerate(hidden_stars):
                if isinstance(hs, str) and hs in target_set:
                    stem_info = hidden_stems[idx] if idx < len(hidden_stems) else ''
                    stem = stem_info[0] if stem_info else ''
                    element = STEM_ELEMENTS.get(stem, '')
                    stars.append({
                        'shishen': hs, 'pillar': pillar_name,
                        'stem': stem, 'element': element, 'hidden': True
                    })
        return stars

    # ─── 类别2：婚姻宫分析 ───────────────────────────────

    def _infer_marriage_palace(self, inp: InferenceInput) -> List[CausalChain]:
        chains = []
        day_branch = inp.day_branch
        if not day_branch:
            return chains

        day_tg = inp.ten_gods.get('day', {})
        day_main_star = day_tg.get('main_star', '')
        palace_desc = MARRIAGE_PALACE_SHISHEN.get(day_main_star, '')
        if palace_desc:
            chains.append(CausalChain(
                category='marriage_palace',
                condition=f"日支（婚姻宫）为{day_branch}，坐{day_main_star}",
                mechanism=f"婚姻宫坐{day_main_star}的命理含义",
                conclusion=palace_desc,
                confidence=0.8,
                source='子平真诠·论夫妻宫',
                details={'day_branch': day_branch, 'palace_star': day_main_star}
            ))

        br = inp.branch_relations
        chong_list = br.get('chong', [])
        if isinstance(chong_list, list):
            for pair in chong_list:
                pair_cn = self._format_branch_pair(pair)
                if day_branch in pair_cn:
                    chains.append(CausalChain(
                        category='marriage_palace',
                        condition=f"婚姻宫{day_branch}被冲（{pair_cn}）",
                        mechanism='婚姻宫逢冲，家庭关系易动荡',
                        conclusion='感情中容易有较大变动或冲突，婚姻宫不安稳，宜晚婚或多沟通化解',
                        confidence=0.8,
                        source='命理通则',
                        details={'relation_type': '冲', 'pair': pair_cn}
                    ))
                    break

        he_list = br.get('he', br.get('liuhe', []))
        if isinstance(he_list, list):
            for pair in he_list:
                pair_cn = self._format_branch_pair(pair)
                if day_branch in pair_cn:
                    chains.append(CausalChain(
                        category='marriage_palace',
                        condition=f"婚姻宫{day_branch}逢合（{pair_cn}）",
                        mechanism='婚姻宫逢合，配偶缘分到来的信号',
                        conclusion='婚姻宫被合动，利于婚恋缘分出现，配偶感情投入度高',
                        confidence=0.75,
                        source='命理通则',
                        details={'relation_type': '合', 'pair': pair_cn}
                    ))
                    break

        return chains

    # ─── 类别3：大运动态力场 ──────────────────────────────

    def _infer_dynamic_balance(self, inp: InferenceInput) -> List[CausalChain]:
        chains = []
        if not inp.dayun_sequence:
            return chains

        spouse_stars = self._find_spouse_stars(inp)
        spouse_element = ''
        if spouse_stars:
            for s in spouse_stars:
                if s.get('element'):
                    spouse_element = s['element']
                    break

        natal_power = DynamicForceBalancer.calculate_natal_wuxing_power(inp.bazi_pillars)
        natal_branches = inp.get_all_branches()
        natal_stems = [
            inp.bazi_pillars.get(p, {}).get('stem', '')
            for p in ['year', 'month', 'day', 'hour']
            if inp.bazi_pillars.get(p, {}).get('stem')
        ]

        balances = DynamicForceBalancer.calculate_all_dayun_balances(
            natal_power=natal_power,
            natal_branches=natal_branches,
            dayun_sequence=inp.dayun_sequence,
            day_branch=inp.day_branch,
            spouse_star_element=spouse_element,
            age_range=(18, 50),
            natal_stems=natal_stems,
        )

        for bal in balances:
            effects = []
            if bal.spouse_star_power_change > 1.0 and spouse_element:
                effects.append(f"配偶星（{spouse_element}）力量增强{bal.spouse_star_power_change:.1f}，利于婚恋")
            elif bal.spouse_star_power_change < -0.5 and spouse_element:
                effects.append(f"配偶星（{spouse_element}）力量减弱，感情运势偏淡")

            if bal.marriage_palace_activated:
                for rel in bal.activated_relations:
                    if inp.day_branch in rel.get('branches', ''):
                        rtype = rel['type']
                        if rtype == '冲':
                            effects.append('婚姻宫被大运地支冲动，感情或家庭有较大变化')
                        elif rtype == '合':
                            effects.append('婚姻宫被大运地支合动，利于缘分出现')

            if effects:
                chains.append(CausalChain(
                    category='dynamic_balance',
                    condition=f"第{bal.dayun_step}运 {bal.dayun_ganzhi}（{bal.age_display}）",
                    mechanism='大运干支加入原局后五行力量重算',
                    conclusion='；'.join(effects),
                    time_range=bal.age_display,
                    confidence=0.75,
                    details={
                        'dayun_ganzhi': bal.dayun_ganzhi,
                        'step': bal.dayun_step,
                        'wuxing_delta': bal.wuxing_delta,
                        'spouse_power_change': bal.spouse_star_power_change,
                        'palace_activated': bal.marriage_palace_activated,
                    }
                ))

        return chains

    # ─── 类别4：婚恋时机 ─────────────────────────────────

    def _infer_marriage_timing(self, inp: InferenceInput) -> List[CausalChain]:
        chains = []
        best_periods = []

        spouse_stars = self._find_spouse_stars(inp)
        spouse_elements = set()
        spouse_shishen = set()
        for s in spouse_stars:
            if s.get('element'):
                spouse_elements.add(s['element'])
            spouse_shishen.add(s['shishen'])

        xi_elements = set(inp.xi_ji_elements.get('xi_shen', []))

        for dayun in inp.dayun_sequence:
            ganzhi = dayun.get('ganzhi', '')
            if not ganzhi or len(ganzhi) < 2:
                stem = dayun.get('gan', dayun.get('stem', ''))
                branch = dayun.get('zhi', dayun.get('branch', ''))
            else:
                stem, branch = ganzhi[0], ganzhi[1]

            age_display = dayun.get('age_display', dayun.get('age_range', ''))
            start_age = DynamicForceBalancer._parse_start_age(age_display, dayun)
            if start_age is not None and (start_age > 50 or start_age < 15):
                continue

            score = 0
            reasons = []

            stem_elem = STEM_ELEMENTS.get(stem, '')
            branch_elem = BRANCH_ELEMENTS.get(branch, '')
            if stem_elem in spouse_elements:
                score += 3
                reasons.append(f'大运天干{stem}引动配偶星（{stem_elem}）')
            if branch_elem in spouse_elements:
                score += 2
                reasons.append(f'大运地支{branch}引动配偶星五行')

            if stem_elem in xi_elements:
                score += 1
                reasons.append('大运天干为喜用五行')
            if branch_elem in xi_elements:
                score += 1
                reasons.append('大运地支为喜用五行')

            if inp.day_branch and branch:
                if BRANCH_LIUHE.get(branch) == inp.day_branch:
                    score += 2
                    reasons.append(f'大运地支{branch}合动婚姻宫{inp.day_branch}')

            liunians = dayun.get('liunians', dayun.get('key_liunians', []))
            key_years = []
            for ly in liunians:
                ly_type = ly.get('type_display', ly.get('type', ''))
                ly_year = ly.get('year', '')
                ly_ganzhi = ly.get('ganzhi', '')
                if '天合地合' in str(ly_type):
                    key_years.append(f"{ly_year}{ly_ganzhi}（天合地合，婚恋大吉年）")
                elif '岁运并临' in str(ly_type):
                    key_years.append(f"{ly_year}{ly_ganzhi}（岁运并临，人生重大转折年）")
                elif '天克地冲' in str(ly_type):
                    key_years.append(f"{ly_year}{ly_ganzhi}（天克地冲，感情变动年）")

            if score >= 3 or key_years:
                best_periods.append({
                    'dayun': ganzhi, 'age': age_display,
                    'score': score, 'reasons': reasons, 'key_years': key_years,
                    'step': dayun.get('step', 0)
                })

        best_periods.sort(key=lambda x: x['score'], reverse=True)
        for period in best_periods[:3]:
            conclusion_parts = period['reasons']
            if period['key_years']:
                conclusion_parts.append('关键年份：' + '、'.join(period['key_years']))

            chains.append(CausalChain(
                category='marriage_timing',
                condition=f"第{period['step']}运 {period['dayun']}（{period['age']}）",
                mechanism='大运干支引动配偶星或婚姻宫',
                conclusion='；'.join(conclusion_parts),
                time_range=period['age'],
                confidence=min(0.9, 0.6 + period['score'] * 0.05),
                details=period,
            ))

        return chains

    # ─── 工具方法 ─────────────────────────────────────────

    @staticmethod
    def _format_branch_pair(pair) -> str:
        """将地支关系 pair 格式化为中文，处理 dict/list/str 等多种格式"""
        if isinstance(pair, str):
            return pair
        if isinstance(pair, dict):
            branches = pair.get('branches', [])
            if isinstance(branches, list) and len(branches) >= 2:
                return f"{branches[0]}{branches[1]}"
            elif isinstance(branches, str):
                return branches
            return ''.join(str(v) for v in pair.values() if isinstance(v, str))
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            return f"{pair[0]}{pair[1]}"
        return str(pair)

    # ─── bazi_rules 已匹配规则整合 ─────────────────────────

    def _infer_from_bazi_rules(self, inp: InferenceInput) -> List[CausalChain]:
        """
        将编排器已匹配的 bazi_rules 中的婚姻判词转为推理链。
        
        这些规则已由 EnhancedRuleCondition 在编排层完成匹配，
        这里只做分类整合和置信度标定。
        """
        chains = []
        if not inp.matched_bazi_rules:
            return chains

        for rule in inp.matched_bazi_rules:
            rule_type = rule.get('rule_type', '')
            if not any(k in rule_type.lower() for k in ('marriage', '婚姻')):
                continue

            content = rule.get('content', {})
            text = content.get('text', '') if isinstance(content, dict) else str(content)
            if not text or len(text) < 2:
                continue

            rule_name = rule.get('rule_name', '')
            rule_code = rule.get('rule_code', rule.get('rule_id', ''))
            priority = rule.get('priority', 100)
            confidence_raw = rule.get('confidence')

            category = self.BAZI_RULE_CATEGORY_MAP.get(rule_type, 'general_judgment')

            if confidence_raw is not None:
                confidence = float(confidence_raw)
            else:
                confidence = self._estimate_confidence_by_type(rule_type, priority)

            chains.append(CausalChain(
                category=category,
                condition=rule_name or rule_code,
                mechanism=f"bazi_rules规则匹配({rule_type})",
                conclusion=text,
                confidence=confidence,
                source=rule_type,
                details={
                    'rule_code': rule_code,
                    'rule_type': rule_type,
                    'from_bazi_rules': True,
                }
            ))

        return chains

    CONFIDENCE_BASE = {
        'marriage_day_pillar': 0.80,
        'marriage_ten_gods': 0.78,
        'marriage_bazi_pattern': 0.82,
        'marriage_day_branch': 0.78,
        'marriage_deity': 0.72,
        'marriage_stem_pattern': 0.75,
        'marriage_branch_pattern': 0.75,
        'marriage_general': 0.70,
        'marriage_day_stem': 0.72,
        'formula_marriage': 0.76,
        'marriage': 0.70,
        'marriage_month_branch': 0.74,
        'marriage_year_branch': 0.72,
        'marriage_year_stem': 0.72,
        'marriage_element': 0.70,
        'marriage_hour_pillar': 0.74,
        'marriage_year_pillar': 0.74,
        'marriage_nayin': 0.68,
        'marriage_lunar_birthday': 0.65,
        'marriage_luck_cycle': 0.76,
        'marriage_year_event': 0.72,
    }

    @classmethod
    def update_confidence_base(cls, overrides: dict):
        """运行时更新置信度参数（用于调参）"""
        cls.CONFIDENCE_BASE.update(overrides)

    @classmethod
    def _estimate_confidence_by_type(cls, rule_type: str, priority: int) -> float:
        """根据规则类型和优先级估算置信度"""
        base = cls.CONFIDENCE_BASE.get(rule_type, 0.68)
        priority_bonus = max(0, (priority - 100)) * 0.001
        return min(0.95, base + priority_bonus)

    # ─── 数据库规则匹配（通过 ConditionMatcher 严格匹配）─────

    def _infer_from_db_rules(self, inp: InferenceInput) -> List[CausalChain]:
        chains = []
        rules = self.load_rules()
        if not rules:
            return chains

        ctx = MarriageMatchContext.from_input(inp)
        matched = 0
        skipped = 0

        for rule in rules:
            cond = rule.get('conditions', {})
            conc = rule.get('conclusions', {})

            if InferenceConditionMatcher.match(cond, ctx):
                matched += 1
                chains.append(CausalChain(
                    category=rule.get('category', 'db_rule'),
                    condition=conc.get('causal_chain', rule.get('rule_name', '')).split('→')[0].strip() if conc.get('causal_chain') else rule.get('rule_name', ''),
                    mechanism=conc.get('causal_chain', ''),
                    conclusion=conc.get('spouse_character', '') or conc.get('conclusion', '') or conc.get('marriage_quality', ''),
                    confidence=conc.get('confidence', 0.7),
                    source=rule.get('source', ''),
                    details={'rule_code': rule.get('rule_code'), 'db_rule': True}
                ))
            else:
                skipped += 1

        logger.info(f"DB规则匹配完成: {matched} 条命中 / {skipped} 条跳过 / 共 {len(rules)} 条")
        return chains
