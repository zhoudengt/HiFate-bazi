#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命局旺衰分析器 - 五因子能量积分制（v2）

公式：P = (M×0.35) + (R×0.40) + (S×0.25) + (B×0.10) - (K×0.30)

5级判定：
  P ≥ 220   → 从强（专旺）
  160 ≤ P < 220 → 身强
  80 ≤ P < 160  → 中和
  30 ≤ P < 80   → 身弱
  P < 30    → 从弱
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple

from core.data.wangshuai_config import (
    ROOT_SCORES, ROOT_TYPE, STRONG_ROOT_TYPES, MEDIUM_ROOT_TYPES, WEAK_ROOT_TYPES,
    MONTH_STATUS_SCORES, SOLAR_TERM_COEFF_EARLY, SOLAR_TERM_COEFF_LATE,
    S_TEN_GOD_SCORES, S_ROOT_COEFFICIENTS,
    B_ROOT_SCORES, B_ROOT_COEFFICIENTS,
    K_TEN_GOD_SCORES, K_GUANSHA_ROOT_COEFFICIENTS,
    BRANCH_DESTRUCTION, LIUHE_HUA, STEM_WUHE_HUA,
    WANGSHUAI_THRESHOLDS, XI_JI_MAPPING,
    CONGWANG_MRS_MIN, CONGWANG_K_MAX, CONGRUO_K_MIN, CONGRUO_MRS_MAX,
    SANHE_ELEMENT, SANHUI_ELEMENT, SANHE_BONUS,
)
from core.data.constants import HIDDEN_STEMS, STEM_ELEMENTS
from core.data.relations import (
    BRANCH_CHONG, BRANCH_XING, BRANCH_LIUHE,
    BRANCH_SANHE_GROUPS, BRANCH_SANHUI_GROUPS,
)
from core.calculators.BaziCalculator import BaziCalculator

logger = logging.getLogger(__name__)

# 五行生克关系
ELEMENT_PRODUCES = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
ELEMENT_CONTROLS = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}

# 天干序列（用于阴阳判断）
HEAVENLY_STEMS_ORDER = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']


def _is_yang_stem(stem: str) -> bool:
    """判断天干阴阳：甲丙戊庚壬为阳（偶数索引0,2,4,6,8）"""
    idx = HEAVENLY_STEMS_ORDER.index(stem) if stem in HEAVENLY_STEMS_ORDER else -1
    return idx % 2 == 0


def _get_ten_god(day_stem: str, other_stem: str) -> Optional[str]:
    """根据日干和另一天干求十神"""
    if day_stem == other_stem:
        return None
    day_el = STEM_ELEMENTS.get(day_stem)
    other_el = STEM_ELEMENTS.get(other_stem)
    if not day_el or not other_el:
        return None
    same_pol = _is_yang_stem(day_stem) == _is_yang_stem(other_stem)
    if day_el == other_el:
        return '比肩' if same_pol else '劫财'
    if ELEMENT_PRODUCES.get(day_el) == other_el:
        return '食神' if same_pol else '伤官'
    if ELEMENT_PRODUCES.get(other_el) == day_el:
        return '偏印' if same_pol else '正印'
    if ELEMENT_CONTROLS.get(day_el) == other_el:
        return '偏财' if same_pol else '正财'
    if ELEMENT_CONTROLS.get(other_el) == day_el:
        return '七杀' if same_pol else '正官'
    return None


class WangShuaiAnalyzer:
    """命局旺衰分析器（五因子能量积分制 v2）"""

    def __init__(self, config_loader=None):
        # config_loader 参数保留以兼容旧调用，不再使用
        logger.info("✅ 旺衰分析器初始化（五因子能量积分制 v2）")

    # ═══════════════════════════════════════════════════════
    #  主入口
    # ═══════════════════════════════════════════════════════

    def analyze(self, solar_date: str, solar_time: str, gender: str) -> Dict[str, Any]:
        """
        分析命局旺衰，返回完整结果。

        Returns dict with keys:
          wangshuai, total_score, p_score, wangshuai_degree,
          score_breakdown, special_pattern,
          xi_shen, ji_shen, xi_shen_elements, ji_shen_elements,
          xi_ji, xi_ji_elements, tiaohou, final_xi_ji, bazi_info
        """
        logger.info(f"🔍 旺衰分析 v2 - {solar_date} {solar_time} {gender}")

        # ─── Step 1: 八字 ───────────────────────────────────
        bazi, calc_result = self._calculate_bazi_full(solar_date, solar_time, gender)
        day_stem = bazi['day_stem']
        day_element = STEM_ELEMENTS[day_stem]

        # ─── Step 2: 节气深浅 ──────────────────────────────
        solar_term_days = self._get_solar_term_days(solar_date, solar_time)

        # ─── Step 3: 地支关系（冲刑合） ──────────────────
        branch_rels = self._get_branch_relationships(bazi)

        # ─── Step 4: 化气格检测（最优先）────────────────
        hua_qi = self._detect_hua_qi_ge(bazi, branch_rels)
        special_pattern = '化气格' if hua_qi else None
        effective_element = hua_qi if hua_qi else day_element

        # ─── Step 5: 各因子原始值 ─────────────────────────
        M = self._calculate_M(bazi, effective_element, solar_term_days)
        R = self._calculate_R(bazi, effective_element, branch_rels)
        S = self._calculate_S(bazi, effective_element, branch_rels)
        B = self._calculate_B(bazi, effective_element, branch_rels)
        K = self._calculate_K(bazi, effective_element, branch_rels)

        # ─── Step 6: 动态修正 ──────────────────────────────
        K = self._apply_tongguan(bazi, effective_element, K)
        P_raw = (M * 0.35) + (R * 0.40) + (S * 0.25) + (B * 0.10) - (K * 0.30)
        P = self._apply_riganhe(bazi, effective_element, P_raw)

        # ─── Step 7: 从旺/从弱格检测 ──────────────────────
        if not special_pattern:
            special_pattern = self._detect_special_patterns(M, R, S, K)

        # ─── Step 8: 5级旺衰判定 ──────────────────────────
        if special_pattern == '从旺格':
            wangshuai = '从强'
        elif special_pattern == '从弱格':
            wangshuai = '从弱'
        else:
            wangshuai = self._determine_wangshuai_v2(P)

        total_score = int(round(P))
        wangshuai_degree = self._calculate_wangshuai_degree_v2(P, wangshuai)

        logger.info(f"   M={M:.1f} R={R:.1f} S={S:.1f} B={B:.1f} K={K:.1f} P={P:.1f} → {wangshuai}")

        # ─── Step 9: 喜忌 ──────────────────────────────────
        xi_ji = self._determine_xi_ji(wangshuai)
        xi_ji_elements = self._calculate_xi_ji_elements(xi_ji, day_stem, effective_element)

        # ─── Step 10: 调候 ─────────────────────────────────
        tiaohou_info = self.calculate_tiaohou(bazi['month_branch'])

        # ─── Step 11: 综合调候喜忌 ────────────────────────
        from core.analyzers.tiaohou_xiji_analyzer import TiaohouXijiAnalyzer
        ws_for_tiaohou = {
            'wangshuai': wangshuai,
            'xi_ji': xi_ji,
            'xi_ji_elements': xi_ji_elements,
        }
        bazi_elements = {'element_counts': calc_result.get('element_counts', {})}
        final_xi_ji = TiaohouXijiAnalyzer.determine_final_xi_ji(
            ws_for_tiaohou, tiaohou_info, bazi_elements
        )

        return {
            # ── 核心字段（LLM 和前端均使用）──
            'wangshuai': wangshuai,
            'total_score': total_score,          # 兼容旧接口：int(P)
            'wangshuai_degree': wangshuai_degree,
            # ── 新增字段 ──
            'p_score': round(P, 2),
            'score_breakdown': {
                'M': round(M, 2),
                'R': round(R, 2),
                'S': round(S, 2),
                'B': round(B, 2),
                'K': round(K, 2),
            },
            'special_pattern': special_pattern,
            # ── 喜忌（LLM 关键字段，key 名称不能改）──
            'xi_shen': xi_ji['xi_shen'],
            'ji_shen': xi_ji['ji_shen'],
            'xi_shen_elements': xi_ji_elements['xi_shen'],
            'ji_shen_elements': xi_ji_elements['ji_shen'],
            'xi_ji': xi_ji,
            'xi_ji_elements': xi_ji_elements,    # Bug fix: fortune_context & annual_report 需要此 key
            'tiaohou': tiaohou_info,
            'final_xi_ji': final_xi_ji,          # xishen_jishen 接口优先读取此字段
            'bazi_info': {
                'day_stem': day_stem,
                'month_branch': bazi['month_branch'],
            },
        }

    # ═══════════════════════════════════════════════════════
    #  八字计算
    # ═══════════════════════════════════════════════════════

    def _calculate_bazi_full(self, solar_date: str, solar_time: str, gender: str):
        """返回 (bazi_dict, full_calc_result)"""
        calculator = BaziCalculator(solar_date, solar_time, gender)
        result = calculator.calculate()
        if not result or 'bazi_pillars' not in result:
            raise ValueError("八字计算结果为空")
        p = result['bazi_pillars']
        bazi = {
            'year_stem': p['year']['stem'],   'year_branch': p['year']['branch'],
            'month_stem': p['month']['stem'], 'month_branch': p['month']['branch'],
            'day_stem': p['day']['stem'],     'day_branch': p['day']['branch'],
            'hour_stem': p['hour']['stem'],   'hour_branch': p['hour']['branch'],
        }
        return bazi, result

    # ═══════════════════════════════════════════════════════
    #  节气深浅（入节天数）
    # ═══════════════════════════════════════════════════════

    def _get_solar_term_days(self, solar_date: str, solar_time: str) -> float:
        """获取距上一节气的天数（节气深浅）"""
        try:
            from lunar_python import Solar
            parts = solar_date.split('-')
            time_parts = (solar_time or '00:00').split(':')
            solar = Solar.fromYmdHms(
                int(parts[0]), int(parts[1]), int(parts[2]),
                int(time_parts[0]), int(time_parts[1]), 0
            )
            lunar = solar.getLunar()
            prev_jie = lunar.getPrevJie()
            if prev_jie:
                prev_solar = prev_jie.getSolar()
                # 计算时间差（天）
                from datetime import datetime
                birth_dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]),
                                    int(time_parts[0]), int(time_parts[1]))
                term_dt = datetime(prev_solar.getYear(), prev_solar.getMonth(),
                                   prev_solar.getDay(), prev_solar.getHour(),
                                   prev_solar.getMinute())
                delta = birth_dt - term_dt
                return max(0.0, delta.total_seconds() / 86400.0)
        except Exception as e:
            logger.debug(f"节气计算失败，使用默认值: {e}")
        return 15.0  # 默认月中，取中气系数

    def _get_solar_term_coeff(self, days: float) -> int:
        """根据入节天数返回节气系数"""
        if days < 7:
            return SOLAR_TERM_COEFF_EARLY   # 初气 +10
        return SOLAR_TERM_COEFF_LATE        # 中气 +20

    # ═══════════════════════════════════════════════════════
    #  地支关系检测
    # ═══════════════════════════════════════════════════════

    def _get_branch_relationships(self, bazi: Dict) -> Dict:
        """检测四柱地支间的冲、刑、六合关系"""
        branches = [bazi['year_branch'], bazi['month_branch'],
                    bazi['day_branch'], bazi['hour_branch']]
        chong_set: Set[str] = set()
        xing_set: Set[str] = set()
        he_pairs: Dict[str, Tuple[str, str]] = {}  # {branch: (partner, hua_element)}

        for i in range(len(branches)):
            for j in range(i + 1, len(branches)):
                b1, b2 = branches[i], branches[j]
                # 六冲
                if BRANCH_CHONG.get(b1) == b2:
                    chong_set.add(b1)
                    chong_set.add(b2)
                # 六刑
                if b2 in BRANCH_XING.get(b1, []):
                    xing_set.add(b1)
                    xing_set.add(b2)
                # 六合
                key = frozenset({b1, b2})
                if key in LIUHE_HUA:
                    hua = LIUHE_HUA[key]
                    if b1 not in he_pairs:
                        he_pairs[b1] = (b2, hua)
                    if b2 not in he_pairs:
                        he_pairs[b2] = (b1, hua)

        return {'chong': chong_set, 'xing': xing_set, 'he_pairs': he_pairs,
                'branches': branches}

    def _get_branch_factor(self, branch: str, day_element: str,
                           branch_rels: Dict) -> float:
        """计算单个地支的破坏系数（冲/刑/合化叠加）"""
        factor = 1.0
        # 被冲优先（同时被冲和合，冲优先）
        if branch in branch_rels['chong']:
            factor *= BRANCH_DESTRUCTION['被冲']
            return factor  # 被冲后不再叠加其他
        # 被刑
        if branch in branch_rels['xing']:
            factor *= BRANCH_DESTRUCTION['被刑']
        # 被合化
        if branch in branch_rels['he_pairs']:
            _, hua = branch_rels['he_pairs'][branch]
            if hua == day_element or ELEMENT_PRODUCES.get(hua) == day_element:
                factor *= BRANCH_DESTRUCTION['被合化帮身']
            else:
                factor *= BRANCH_DESTRUCTION['被合化他物']
        return factor

    # ═══════════════════════════════════════════════════════
    #  化气格检测
    # ═══════════════════════════════════════════════════════

    def _detect_hua_qi_ge(self, bazi: Dict, branch_rels: Dict) -> Optional[str]:
        """
        化气格：日主与月干或时干逢五合，且合化五行在月令当令。
        返回合化元素（如 '土'），否则 None。
        """
        day_stem = bazi['day_stem']
        month_element = STEM_ELEMENTS.get(
            self._get_branch_main_element_stem(bazi['month_branch']), '')
        for other_stem_key in ('month_stem', 'hour_stem'):
            other_stem = bazi[other_stem_key]
            key = frozenset({day_stem, other_stem})
            if key in STEM_WUHE_HUA:
                hua_el = STEM_WUHE_HUA[key]
                # 合化五行须在月令当令（月令主元素 == 合化元素）
                if hua_el == STEM_ELEMENTS.get(self._branch_main_stem(bazi['month_branch'])):
                    logger.info(f"   🔮 化气格：{day_stem}+{other_stem} 化{hua_el}")
                    return hua_el
        return None

    def _branch_main_stem(self, branch: str) -> str:
        """取地支的主气天干（第一个藏干）"""
        hidden = HIDDEN_STEMS.get(branch, [])
        return hidden[0][0] if hidden else ''

    def _get_branch_main_element_stem(self, branch: str) -> str:
        """取地支主气天干字符"""
        return self._branch_main_stem(branch)

    # ═══════════════════════════════════════════════════════
    #  M 因子：月令能量
    # ═══════════════════════════════════════════════════════

    def _calculate_M(self, bazi: Dict, day_element: str,
                     solar_term_days: float) -> float:
        """
        月令能量：当令(100+系数) / 得生(60+系数) / 耗气(20) / 被克(0)
        """
        month_branch = bazi['month_branch']
        month_main_stem = self._branch_main_stem(month_branch)
        month_element = STEM_ELEMENTS.get(month_main_stem, '')

        # 处理土月：辰戌丑未主气为土
        from core.data.constants import BRANCH_ELEMENTS
        month_element = BRANCH_ELEMENTS.get(month_branch, month_element)

        coeff = self._get_solar_term_coeff(solar_term_days)

        if month_element == day_element:
            score = MONTH_STATUS_SCORES['当令'] + coeff
            logger.info(f"   M: 当令({month_branch}/{month_element}) = {score}")
        elif ELEMENT_PRODUCES.get(month_element) == day_element:
            score = MONTH_STATUS_SCORES['得生'] + coeff
            logger.info(f"   M: 得生({month_branch}/{month_element}生{day_element}) = {score}")
        elif ELEMENT_PRODUCES.get(day_element) == month_element:
            score = MONTH_STATUS_SCORES['耗气']
            logger.info(f"   M: 耗气({day_element}生{month_branch}/{month_element}) = {score}")
        else:
            score = MONTH_STATUS_SCORES['被克']
            logger.info(f"   M: 被克/反克({month_branch}/{month_element}↔{day_element}) = {score}")

        return float(score)

    # ═══════════════════════════════════════════════════════
    #  R 因子：地支通根能量
    # ═══════════════════════════════════════════════════════

    def _calculate_R(self, bazi: Dict, day_element: str, branch_rels: Dict) -> float:
        """
        地支通根能量：扫描四柱地支，累加通根分值并应用破坏系数。
        最后检查三合/三会局加成。
        """
        element_roots = ROOT_SCORES.get(day_element, {})
        branches = branch_rels['branches']
        total_r = 0.0

        for branch in branches:
            base = element_roots.get(branch, 0)
            if base == 0:
                continue
            factor = self._get_branch_factor(branch, day_element, branch_rels)
            score = base * factor
            root_type = ROOT_TYPE.get(day_element, {}).get(branch, '?')
            logger.info(f"   R: {branch}({root_type}) base={base} ×{factor:.2f} = {score:.1f}")
            total_r += score

        # 三合/三会加成：若四柱地支构成完整三合/三会且该局五行帮扶日主
        bonus = self._calculate_sanhe_bonus(branches, day_element)
        if bonus > 0:
            logger.info(f"   R: 三合/三会加成 +{bonus}")
            total_r += bonus

        logger.info(f"   R总计: {total_r:.1f}")
        return total_r

    def _calculate_sanhe_bonus(self, branches: List[str], day_element: str) -> float:
        """检测三合/三会局，若形成印比之局则加成"""
        branch_set = set(branches)
        bonus = 0.0
        # 三合
        for group_tuple in BRANCH_SANHE_GROUPS:
            group = set(group_tuple)
            el = SANHE_ELEMENT.get(frozenset(group))
            if group.issubset(branch_set) and el and (
                    el == day_element or ELEMENT_PRODUCES.get(el) == day_element):
                bonus += SANHE_BONUS
                logger.info(f"   R: {''.join(group_tuple)} 三合{el}局 加成 +{SANHE_BONUS}")
        # 三会
        for group_tuple in BRANCH_SANHUI_GROUPS:
            group = set(group_tuple)
            el = SANHUI_ELEMENT.get(frozenset(group))
            if el and group.issubset(branch_set) and (
                    el == day_element or ELEMENT_PRODUCES.get(el) == day_element):
                bonus += SANHE_BONUS
                logger.info(f"   R: {''.join(group_tuple)} 三会{el}局 加成 +{SANHE_BONUS}")
        return bonus

    # ═══════════════════════════════════════════════════════
    #  S 因子：天干生助能量
    # ═══════════════════════════════════════════════════════

    def _calculate_S(self, bazi: Dict, day_element: str, branch_rels: Dict) -> float:
        """
        天干生助能量：年干/月干/时干中的比劫(50)和印星(40)，乘以真假系数。
        """
        stems = [bazi['year_stem'], bazi['month_stem'], bazi['hour_stem']]
        branches = branch_rels['branches']
        day_stem = bazi['day_stem']
        total_s = 0.0

        for stem in stems:
            tg = _get_ten_god(day_stem, stem)
            if tg not in S_TEN_GOD_SCORES:
                continue
            base = S_TEN_GOD_SCORES[tg]
            stem_el = STEM_ELEMENTS.get(stem, '')
            root_type = self._get_stem_root_kind(stem_el, branches, branch_rels, day_element)
            coeff = S_ROOT_COEFFICIENTS[root_type]
            score = base * coeff
            logger.info(f"   S: {stem}({tg}) base={base} ×{coeff} ({root_type}) = {score:.1f}")
            total_s += score

        logger.info(f"   S总计: {total_s:.1f}")
        return total_s

    def _get_stem_root_kind(self, stem_el: str, branches: List[str],
                            branch_rels: Dict, day_element: str) -> str:
        """判断天干的通根状况：真通根/半真根/虚浮无根"""
        el_roots = ROOT_SCORES.get(stem_el, {})
        for branch in branches:
            if branch in el_roots:
                root_tp = ROOT_TYPE.get(stem_el, {}).get(branch, '')
                # 被冲的根不计
                if branch in branch_rels['chong']:
                    continue
                if root_tp in STRONG_ROOT_TYPES | MEDIUM_ROOT_TYPES:
                    return '真通根'
                if root_tp in WEAK_ROOT_TYPES:
                    return '半真根'
        return '虚浮无根'

    # ═══════════════════════════════════════════════════════
    #  B 因子：印星根基能量
    # ═══════════════════════════════════════════════════════

    def _calculate_B(self, bazi: Dict, day_element: str, branch_rels: Dict) -> float:
        """
        印星根基能量：对每个印星天干，检查其在地支的根气强度。
        """
        stems = [bazi['year_stem'], bazi['month_stem'], bazi['hour_stem']]
        branches = branch_rels['branches']
        day_stem = bazi['day_stem']
        total_b = 0.0

        for stem in stems:
            tg = _get_ten_god(day_stem, stem)
            if tg not in ('偏印', '正印'):
                continue
            stem_el = STEM_ELEMENTS.get(stem, '')
            el_roots = ROOT_SCORES.get(stem_el, {})
            for branch in branches:
                if branch not in el_roots:
                    continue
                if branch in branch_rels['chong']:
                    continue  # 被冲的根不计
                root_tp = ROOT_TYPE.get(stem_el, {}).get(branch, '')
                base = B_ROOT_SCORES.get(root_tp, 0)
                if base == 0:
                    continue
                # 权重系数
                if root_tp in STRONG_ROOT_TYPES | MEDIUM_ROOT_TYPES:
                    coeff = B_ROOT_COEFFICIENTS['真通根']
                elif root_tp in WEAK_ROOT_TYPES:
                    coeff = B_ROOT_COEFFICIENTS['墓库根']
                else:
                    coeff = B_ROOT_COEFFICIENTS['半真根']
                # 破坏系数
                factor = self._get_branch_factor(branch, stem_el, branch_rels)
                score = base * coeff * factor
                logger.info(f"   B: {stem}({tg})根于{branch}({root_tp}) "
                            f"base={base} ×{coeff} ×{factor:.2f} = {score:.1f}")
                total_b += score
                break  # 每个印星只计最强的一个根

        logger.info(f"   B总计: {total_b:.1f}")
        return total_b

    # ═══════════════════════════════════════════════════════
    #  K 因子：克泄耗能量
    # ═══════════════════════════════════════════════════════

    def _calculate_K(self, bazi: Dict, day_element: str, branch_rels: Dict) -> float:
        """
        克泄耗能量：七杀(120)/正官(60)/食伤(40)/财星(50)
        官杀根据根气强弱附加系数（1.3 / 1.0 / 0.5）
        """
        stems = [bazi['year_stem'], bazi['month_stem'], bazi['hour_stem']]
        branches = branch_rels['branches']
        day_stem = bazi['day_stem']
        total_k = 0.0

        for stem in stems:
            tg = _get_ten_god(day_stem, stem)
            if tg not in K_TEN_GOD_SCORES:
                continue
            base = K_TEN_GOD_SCORES[tg]
            if tg in ('七杀', '正官'):
                stem_el = STEM_ELEMENTS.get(stem, '')
                root_kind = self._get_stem_root_kind(stem_el, branches, branch_rels, day_element)
                coeff = K_GUANSHA_ROOT_COEFFICIENTS[root_kind]
            else:
                coeff = 1.0
            score = base * coeff
            logger.info(f"   K: {stem}({tg}) base={base} ×{coeff:.2f} = {score:.1f}")
            total_k += score

        logger.info(f"   K总计: {total_k:.1f}")
        return total_k

    # ═══════════════════════════════════════════════════════
    #  动态修正
    # ═══════════════════════════════════════════════════════

    def _apply_tongguan(self, bazi: Dict, day_element: str, K: float) -> float:
        """
        通关减克：若有印星介于日主与官杀之间（官杀→印→日主连续相生），
        官杀克力减半。
        """
        day_stem = bazi['day_stem']
        stems = [bazi['year_stem'], bazi['month_stem'], bazi['hour_stem']]
        has_guansha = any(_get_ten_god(day_stem, s) in ('七杀', '正官') for s in stems)
        has_yin = any(_get_ten_god(day_stem, s) in ('偏印', '正印') for s in stems)
        if has_guansha and has_yin:
            logger.info(f"   通关减克：官杀克力减半 K: {K:.1f} → {K * 0.5:.1f}")
            return K * 0.5
        return K

    def _apply_riganhe(self, bazi: Dict, day_element: str, P: float) -> float:
        """
        日主合绊修正：
        - 日主被合化（化气格已单独处理，此处不重复）：P × 0 → 已在检测时处理
        - 日主被合绊（形成合但不化）：P × 0.70
        """
        day_stem = bazi['day_stem']
        for other_key in ('year_stem', 'month_stem', 'hour_stem'):
            other_stem = bazi[other_key]
            key = frozenset({day_stem, other_stem})
            if key in STEM_WUHE_HUA:
                # 检查是否合化（化气格已处理），此处只处理合绊
                hua_el = STEM_WUHE_HUA[key]
                month_main = STEM_ELEMENTS.get(self._branch_main_stem(bazi['month_branch']), '')
                from core.data.constants import BRANCH_ELEMENTS
                month_el = BRANCH_ELEMENTS.get(bazi['month_branch'], month_main)
                if hua_el != month_el:
                    # 合绊（不化），P 扣减 30%
                    logger.info(f"   日主合绊({day_stem}+{other_stem})：P × 0.70")
                    return P * 0.70
        return P

    # ═══════════════════════════════════════════════════════
    #  特殊格局检测
    # ═══════════════════════════════════════════════════════

    def _detect_special_patterns(self, M: float, R: float,
                                  S: float, K: float) -> Optional[str]:
        """检测从旺格/从弱格（使用原始因子值，不加权重）"""
        mrs = M + R + S
        if mrs > CONGWANG_MRS_MIN and K < CONGWANG_K_MAX:
            logger.info(f"   🔮 从旺格：M+R+S={mrs:.1f} > {CONGWANG_MRS_MIN}, K={K:.1f} < {CONGWANG_K_MAX}")
            return '从旺格'
        if K > CONGRUO_K_MIN and mrs < CONGRUO_MRS_MAX:
            logger.info(f"   🔮 从弱格：K={K:.1f} > {CONGRUO_K_MIN}, M+R+S={mrs:.1f} < {CONGRUO_MRS_MAX}")
            return '从弱格'
        return None

    # ═══════════════════════════════════════════════════════
    #  5级旺衰判定
    # ═══════════════════════════════════════════════════════

    def _determine_wangshuai_v2(self, P: float) -> str:
        """根据 P 值判定5级旺衰"""
        for name, threshold in WANGSHUAI_THRESHOLDS:
            if threshold is None or P >= threshold:
                return name
        return '从弱'

    def _calculate_wangshuai_degree_v2(self, P: float, wangshuai: str) -> int:
        """将 P 值映射到 0-100 旺衰程度"""
        if wangshuai in ('从强',):
            degree = 90 + min(10, (P - 220) / 10)
        elif wangshuai == '身强':
            degree = 70 + (P - 160) / 6.0
        elif wangshuai == '中和':
            degree = 40 + (P - 80) / 2.67
        elif wangshuai == '身弱':
            degree = 15 + (P - 30) / 2.0
        elif wangshuai == '从弱':
            degree = max(0, 15 + P / 2.0)
        else:
            degree = 50.0
        return int(min(100, max(0, round(degree))))

    # ═══════════════════════════════════════════════════════
    #  喜忌神
    # ═══════════════════════════════════════════════════════

    def _determine_xi_ji(self, wangshuai: str) -> Dict[str, List[str]]:
        """根据5级旺衰返回喜忌十神列表"""
        mapping = XI_JI_MAPPING.get(wangshuai, {})
        return {
            'xi_shen': list(mapping.get('喜神', [])),
            'ji_shen': list(mapping.get('忌神', [])),
        }

    def _calculate_xi_ji_elements(self, xi_ji: Dict, day_stem: str,
                                   day_element: str) -> Dict[str, List[str]]:
        """将喜忌十神转换为五行列表"""
        relations = {
            'produces': ELEMENT_PRODUCES.get(day_element, ''),
            'controls': ELEMENT_CONTROLS.get(day_element, ''),
            'produced_by': next((k for k, v in ELEMENT_PRODUCES.items() if v == day_element), ''),
            'controlled_by': next((k for k, v in ELEMENT_CONTROLS.items() if v == day_element), ''),
        }
        ten_god_element_map = {
            '比肩': day_element, '劫财': day_element,
            '食神': relations['produces'],  '伤官': relations['produces'],
            '偏财': relations['controls'],  '正财': relations['controls'],
            '七杀': relations['controlled_by'], '正官': relations['controlled_by'],
            '偏印': relations['produced_by'],   '正印': relations['produced_by'],
        }
        xi_els, ji_els = [], []
        for tg in xi_ji['xi_shen']:
            el = ten_god_element_map.get(tg)
            if el and el not in xi_els:
                xi_els.append(el)
        for tg in xi_ji['ji_shen']:
            el = ten_god_element_map.get(tg)
            if el and el not in ji_els:
                ji_els.append(el)
        return {'xi_shen': xi_els, 'ji_shen': ji_els}

    # ═══════════════════════════════════════════════════════
    #  调候（保持不变，供外部调用）
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def calculate_tiaohou(month_branch: str) -> Dict[str, Any]:
        """计算调候五行（夏喜水，冬喜火，春秋不调）"""
        if month_branch in ('巳', '午', '未'):
            return {'tiaohou_element': '水', 'season': '夏季',
                    'month_branch': month_branch, 'description': '夏月炎热，需水调候'}
        if month_branch in ('亥', '子', '丑'):
            return {'tiaohou_element': '火', 'season': '冬季',
                    'month_branch': month_branch, 'description': '冬月寒冷，需火调候'}
        return {'tiaohou_element': None, 'season': '春秋',
                'month_branch': month_branch, 'description': '春秋气候适中，无需特别调候'}
