#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命局旺衰分析器 - 四因子能量积分制（V新版）

公式：P = M×0.35 + R×0.40 + S×0.25 - K×0.30
核心改动：删除重复计分的 B（印星根基）项；K 归一化（÷10）：七杀12/正官6/财5/食伤4

判定体系（4级）：
  P≥25→身强 / 15-24→中和偏强 / 5-14→中和偏弱 / P<5→身弱
  条件触发（优先）：从旺格→从强 / 假从旺格→从强 / 从弱格→从弱 / 假从弱格→从弱 / 化气格
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple

from core.data.wangshuai_config import (
    ROOT_SCORES, ROOT_TYPE, STRONG_ROOT_TYPES, MEDIUM_ROOT_TYPES, WEAK_ROOT_TYPES,
    MONTH_STATUS_SCORES, SOLAR_TERM_CORRECTIONS, SOLAR_TERM_COEFF_EARLY, SOLAR_TERM_COEFF_LATE,
    S_TEN_GOD_SCORES, S_ROOT_COEFFICIENTS, S_YINXING_WUGEN_SCORE, S_CAP,
    B_ROOT_SCORES, B_ROOT_COEFFICIENTS,
    K_TEN_GOD_SCORES, K_ROOT_COEFFICIENTS, K_GUANSHA_ROOT_COEFFICIENTS,
    K_BRANCH_GUANSHA_SCORE, K_BRANCH_CAISHISHEN_SCORE,
    BRANCH_DESTRUCTION, LIUHE_HUA, STEM_WUHE_HUA,
    WANGSHUAI_THRESHOLDS, XI_JI_MAPPING,
    CONGWANG_P_MIN, CONGWANG_K_MAX, CONGWANG_MRS_MIN,
    JIACONGWANG_K_MIN, JIACONGWANG_K_MAX,
    CONGRUO_P_MAX, CONGRUO_K_MIN, CONGRUO_MRS_MAX,
    JIACONGRUO_MRS_MIN, JIACONGRUO_MRS_MAX,
    R_CAP_WITH_LUREN, R_CAP_NO_LUREN,
    SANHE_ELEMENT, SANHUI_ELEMENT, SANHE_BONUS,
    BANHE_PAIRS, GONGHE_PAIRS,
    SANHE_YINBI_BONUS, SANHE_CAIGUAN_BONUS, SANHUI_BONUS, BANHE_BONUS, GONGHE_BONUS,
)
from core.data.constants import HIDDEN_STEMS, STEM_ELEMENTS
from core.data.relations import (
    BRANCH_CHONG, BRANCH_XING, BRANCH_LIUHE,
    BRANCH_SANHE_GROUPS, BRANCH_SANHUI_GROUPS,
    BRANCH_HAI,
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
        logger.info(f"🔍 旺衰分析 v3 - {solar_date} {solar_time} {gender}")

        # ─── Step 1: 八字 ───────────────────────────────────
        bazi, calc_result = self._calculate_bazi_full(solar_date, solar_time, gender)
        day_stem = bazi['day_stem']
        day_element = STEM_ELEMENTS[day_stem]
        element_counts = calc_result.get('element_counts', {})

        # ─── Step 2: 节气深浅 ──────────────────────────────
        solar_term_days = self._get_solar_term_days(solar_date, solar_time)

        # ─── Step 3: 地支关系（冲刑合害空亡） ────────────
        branch_rels = self._get_branch_relationships(bazi)

        # ─── Step 4: 化气格检测（最优先）────────────────
        hua_qi = self._detect_hua_qi_ge(bazi, branch_rels)
        special_pattern = '化气格' if hua_qi else None
        effective_element = hua_qi if hua_qi else day_element

        # ─── Step 5: 各因子原始值 ─────────────────────────
        M = self._calculate_M(bazi, effective_element, solar_term_days)
        R, K_sanhe_bonus = self._calculate_R(bazi, effective_element, branch_rels)
        S = self._calculate_S(bazi, effective_element, branch_rels)
        # V新版：B 因子已从公式删除（避免与 S 中印星重复计分），保留计算仅供日志参考
        B = self._calculate_B(bazi, effective_element, branch_rels)
        K, K_guansha = self._calculate_K(bazi, effective_element, branch_rels)
        K += K_sanhe_bonus  # 三合财官局加成（不计入 guansha_k）

        # ─── Step 6: 动态修正 ──────────────────────────────
        K = self._apply_tongguan(bazi, effective_element, K, K_guansha)
        # V新版公式：P = M×0.35 + R×0.40 + S×0.25 - K×0.30（不含 B）
        P_raw = (M * 0.35) + (R * 0.40) + (S * 0.25) - (K * 0.30)
        P = self._apply_riganhe(bazi, effective_element, P_raw)

        # ─── Step 7: 从旺/假从旺/从弱/假从弱格检测 ────────
        if not special_pattern:
            special_pattern = self._detect_special_patterns(M, R, S, K, P, bazi, branch_rels)

        # ─── Step 8: 旺衰判定（4级P阈值 + 特殊格局覆盖）──
        if special_pattern == '从旺格':
            wangshuai = '从强'
        elif special_pattern == '假从旺格':
            wangshuai = '从强'    # 喜忌同从旺，大运遇克泄易破格
        elif special_pattern == '从弱格':
            wangshuai = '从弱'
        elif special_pattern == '假从弱格':
            wangshuai = '从弱'    # 喜忌同从弱，大运遇印比易破格
        elif special_pattern == '化气格':
            wangshuai = '化气格'
        else:
            wangshuai = self._determine_wangshuai_v2(P)

        total_score = int(round(P))
        wangshuai_degree = self._calculate_wangshuai_degree_v2(P, wangshuai)

        logger.info(f"   M={M:.1f} R={R:.1f} S={S:.1f} B={B:.1f} K={K:.1f} P={P:.1f} → {wangshuai}")

        # ─── Step 9: 喜忌 ──────────────────────────────────
        # V3.0：4级体系，中和偏强→同身强，中和偏弱→同身弱，统一走静态映射
        # 调候优先覆盖由 TiaohouXijiAnalyzer.determine_final_xi_ji 处理
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
        bazi_elements_ctx = {'element_counts': element_counts}
        final_xi_ji = TiaohouXijiAnalyzer.determine_final_xi_ji(
            ws_for_tiaohou, tiaohou_info, bazi_elements_ctx
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
                'B': 0.0,     # V新版：已从公式删除（避免与 S 中印星重复计分）
                'K': round(K, 2),
            },
            'special_pattern': special_pattern,
            # ── 喜忌（LLM 关键字段，key 名称不能改）──
            'xi_shen': xi_ji['xi_shen'],
            'ji_shen': xi_ji['ji_shen'],
            'xi_shen_elements': xi_ji_elements['xi_shen'],
            'ji_shen_elements': xi_ji_elements['ji_shen'],
            'xi_ji': xi_ji,
            'xi_ji_elements': xi_ji_elements,    # fortune_context & annual_report 需要此 key
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
        # 提取空亡（以日柱旬空为准）
        details = result.get('details', {})
        day_kongwang = details.get('day', {}).get('kongwang', set())
        if not isinstance(day_kongwang, set):
            day_kongwang = set(day_kongwang) if day_kongwang else set()
        bazi = {
            'year_stem': p['year']['stem'],   'year_branch': p['year']['branch'],
            'month_stem': p['month']['stem'], 'month_branch': p['month']['branch'],
            'day_stem': p['day']['stem'],     'day_branch': p['day']['branch'],
            'hour_stem': p['hour']['stem'],   'hour_branch': p['hour']['branch'],
            'void_branches': day_kongwang,    # 空亡地支集合
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
        return 10.0  # 默认取中气档位（7-14天）

    def _get_solar_term_stage(self, days: float) -> str:
        """根据入节天数返回节气档位（三档）"""
        if days < 7:
            return 'early'   # 初气（前 7 天）
        if days < 14:
            return 'mid'     # 中气（7-14 天）
        return 'late'        # 末气（14 天以上）

    def _get_solar_term_coeff(self, days: float) -> int:
        """兼容旧接口（不再使用），返回固定值"""
        return SOLAR_TERM_COEFF_LATE

    # ═══════════════════════════════════════════════════════
    #  地支关系检测
    # ═══════════════════════════════════════════════════════

    def _get_branch_relationships(self, bazi: Dict) -> Dict:
        """检测四柱地支间的冲、刑、六合、六害关系，以及空亡"""
        branches = [bazi['year_branch'], bazi['month_branch'],
                    bazi['day_branch'], bazi['hour_branch']]
        chong_set: Set[str] = set()
        xing_set: Set[str] = set()
        hai_set: Set[str] = set()                    # 六害
        he_pairs: Dict[str, Tuple[str, str]] = {}    # {branch: (partner, hua_element)}
        void_set: Set[str] = set()                   # 空亡（旬空）

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
                # 六害
                if b2 in BRANCH_HAI.get(b1, []):
                    hai_set.add(b1)
                    hai_set.add(b2)

        # 空亡：与日柱旬空交集
        void_branches = bazi.get('void_branches', set())
        for b in branches:
            if b in void_branches:
                void_set.add(b)

        return {'chong': chong_set, 'xing': xing_set, 'hai': hai_set,
                'he_pairs': he_pairs, 'void': void_set, 'branches': branches}

    def _get_branch_factor(self, branch: str, day_element: str,
                           branch_rels: Dict) -> float:
        """
        计算单个地支的破坏/增益系数。
        优先级：被冲（最强，直接返回）> 被合化 > 被刑 > 被害 > 被克 > 空亡（可叠加）
        """
        factor = 1.0
        # 被冲优先（同时被冲和合，冲优先）
        if branch in branch_rels['chong']:
            factor *= BRANCH_DESTRUCTION['被冲']
            return factor  # 被冲后不再叠加其他
        # 被合化
        if branch in branch_rels['he_pairs']:
            _, hua = branch_rels['he_pairs'][branch]
            if hua == day_element or ELEMENT_PRODUCES.get(hua) == day_element:
                factor *= BRANCH_DESTRUCTION['被合化帮身']
            else:
                factor *= BRANCH_DESTRUCTION['被合化他物']
        # 被刑
        if branch in branch_rels['xing']:
            factor *= BRANCH_DESTRUCTION['被刑']
        # 被害（六害）
        if branch in branch_rels.get('hai', set()):
            factor *= BRANCH_DESTRUCTION['被害']
        # 被克（邻近地支五行相克日主根所在地支）
        # 规则：四柱中若有地支的五行 克 该地支的五行，则该根被克
        branch_el = self._get_branch_element(branch)
        if branch_el:
            controllers_in_chart = {
                ELEMENT_CONTROLS.get(self._get_branch_element(b), '')
                for b in branch_rels['branches'] if b != branch
            }
            if branch_el in controllers_in_chart:
                factor *= BRANCH_DESTRUCTION['被克']
        # 空亡
        if branch in branch_rels.get('void', set()):
            factor *= BRANCH_DESTRUCTION['空亡']
        return factor

    def _get_branch_element(self, branch: str) -> str:
        """获取地支的主五行"""
        from core.data.constants import BRANCH_ELEMENTS
        return BRANCH_ELEMENTS.get(branch, '')

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
        月令能量（V3.0）：当令(40) / 得生(30) / 耗气(10) / 被克(0)
        加三档节气修正：初气(early) / 中气(mid) / 末气(late)
        """
        month_branch = bazi['month_branch']
        month_main_stem = self._branch_main_stem(month_branch)
        month_element = STEM_ELEMENTS.get(month_main_stem, '')

        # 处理土月：辰戌丑未主气为土
        from core.data.constants import BRANCH_ELEMENTS
        month_element = BRANCH_ELEMENTS.get(month_branch, month_element)

        if month_element == day_element:
            status = '当令'
        elif ELEMENT_PRODUCES.get(month_element) == day_element:
            status = '得生'
        elif ELEMENT_PRODUCES.get(day_element) == month_element:
            status = '耗气'
        else:
            status = '被克'

        base = MONTH_STATUS_SCORES[status]
        stage = self._get_solar_term_stage(solar_term_days)
        correction = SOLAR_TERM_CORRECTIONS[status][stage]
        score = base + correction

        logger.info(f"   M: {status}({month_branch}/{month_element}) "
                    f"base={base} +{correction}({stage}) = {score}")
        return float(score)

    # ═══════════════════════════════════════════════════════
    #  R 因子：地支通根能量
    # ═══════════════════════════════════════════════════════

    def _calculate_R(self, bazi: Dict, day_element: str, branch_rels: Dict) -> Tuple[float, float]:
        """
        地支通根能量（V3.0）。
        规则：
          - 禄/刃根(帝旺/临官)=40，长生根=20，余气/墓库根=10
          - 有禄刃根：上限 R_CAP_WITH_LUREN(40)；若禄刃受损可累加弱根但仍上限40
          - 无禄刃根：累加弱根，上限 R_CAP_NO_LUREN(30)
        返回 (R总值, K加成)
        """
        element_roots = ROOT_SCORES.get(day_element, {})
        branches = branch_rels['branches']

        lu_ren_score = 0.0   # 最强禄/刃根得分（取最高分的一个）
        other_score = 0.0    # 其他根（长生/余气/墓库）累加

        for branch in branches:
            base = element_roots.get(branch, 0)
            if base == 0:
                continue
            factor = self._get_branch_factor(branch, day_element, branch_rels)
            score = base * factor
            root_type = ROOT_TYPE.get(day_element, {}).get(branch, '?')
            logger.info(f"   R: {branch}({root_type}) base={base} ×{factor:.2f} = {score:.1f}")

            if root_type in STRONG_ROOT_TYPES:   # 帝旺根/临官根（禄/刃）
                lu_ren_score = max(lu_ren_score, score)
            else:
                other_score += score

        # 应用上限规则
        if lu_ren_score > 0:
            if lu_ren_score >= R_CAP_WITH_LUREN:
                total_r = float(R_CAP_WITH_LUREN)
            else:
                # 禄刃受损，可补充弱根，但总分不超上限
                total_r = min(lu_ren_score + other_score, R_CAP_WITH_LUREN)
        else:
            # 无禄刃根，累加弱根，上限30
            total_r = min(other_score, R_CAP_NO_LUREN)

        # 各类合局加成
        r_bonus, k_bonus = self._calculate_branch_group_bonuses(branches, day_element)
        if r_bonus > 0:
            # 合局视为"强根"，上限同有禄刃情况
            total_r = min(total_r + r_bonus, R_CAP_WITH_LUREN)

        logger.info(f"   R总计: {total_r:.1f}（禄刃={lu_ren_score:.1f} 弱根={other_score:.1f} "
                    f"合局R+={r_bonus:.1f} 合局K+={k_bonus:.1f}）")
        return total_r, k_bonus

    def _calculate_branch_group_bonuses(self, branches: List[str],
                                        day_element: str) -> Tuple[float, float]:
        """
        检测三合/三会/半合/拱合局，返回 (R加成, K加成)。

        R加成：三合印比(+100) / 三会印比(+120) / 半合印比(+50) / 拱合(+30)
        K加成：三合财官（合化元素克日主）→ +80 计入K
        """
        branch_set = set(branches)
        r_bonus = 0.0
        k_bonus = 0.0

        def _is_yinbi(el: str) -> bool:
            """合化五行是否帮扶日主（印比之局）"""
            return el == day_element or ELEMENT_PRODUCES.get(el) == day_element

        def _is_caiguan(el: str) -> bool:
            """合化五行是否克日主（财官之局：官杀克日主）"""
            return ELEMENT_CONTROLS.get(el) == day_element

        # 完整三合
        for group_tuple in BRANCH_SANHE_GROUPS:
            group = frozenset(group_tuple)
            el = SANHE_ELEMENT.get(group)
            if not el or not group.issubset(branch_set):
                continue
            if _is_yinbi(el):
                r_bonus += SANHE_YINBI_BONUS
                logger.info(f"   R: {''.join(sorted(group))} 三合{el}局(印比) +{SANHE_YINBI_BONUS}")
            elif _is_caiguan(el):
                k_bonus += SANHE_CAIGUAN_BONUS
                logger.info(f"   K: {''.join(sorted(group))} 三合{el}局(财官) +{SANHE_CAIGUAN_BONUS}")

        # 完整三会
        for group_tuple in BRANCH_SANHUI_GROUPS:
            group = frozenset(group_tuple)
            el = SANHUI_ELEMENT.get(group)
            if not el or not group.issubset(branch_set):
                continue
            if _is_yinbi(el):
                r_bonus += SANHUI_BONUS
                logger.info(f"   R: {''.join(sorted(group))} 三会{el}局(印比) +{SANHUI_BONUS}")

        # 半合（两合，帮身）
        for pair, el in BANHE_PAIRS.items():
            if pair.issubset(branch_set) and _is_yinbi(el):
                r_bonus += BANHE_BONUS
                logger.info(f"   R: {''.join(sorted(pair))} 半合{el}(印比) +{BANHE_BONUS}")

        # 拱合（两端拱合，帮身）
        for pair, el in GONGHE_PAIRS.items():
            if pair.issubset(branch_set) and _is_yinbi(el):
                r_bonus += GONGHE_BONUS
                logger.info(f"   R: {''.join(sorted(pair))} 拱合{el}(印比) +{GONGHE_BONUS}")

        return r_bonus, k_bonus

    # ═══════════════════════════════════════════════════════
    #  S 因子：天干生助能量
    # ═══════════════════════════════════════════════════════

    def _calculate_S(self, bazi: Dict, day_element: str, branch_rels: Dict) -> float:
        """
        天干生助能量（V3.0）：
          - 比肩/劫财：一律 10（有无根均等）
          - 正印/偏印：有根 = 5，虚浮无根 = 2.5
          - 累计上限 S_CAP(20)
        """
        stems = [bazi['year_stem'], bazi['month_stem'], bazi['hour_stem']]
        branches = branch_rels['branches']
        day_stem = bazi['day_stem']
        total_s = 0.0

        for stem in stems:
            tg = _get_ten_god(day_stem, stem)
            if tg not in S_TEN_GOD_SCORES:
                continue

            if tg in ('比肩', '劫财'):
                score = 10.0   # 比劫一律10，不论有无根
            else:
                # 印星：有根=5，虚浮=2.5
                stem_el = STEM_ELEMENTS.get(stem, '')
                root_type = self._get_stem_root_kind(stem_el, branches, branch_rels, day_element)
                if root_type == '虚浮无根':
                    score = S_YINXING_WUGEN_SCORE   # 2.5
                else:
                    score = S_TEN_GOD_SCORES[tg]    # 5

            logger.info(f"   S: {stem}({tg}) = {score:.1f}")
            total_s += score

        total_s = min(total_s, S_CAP)   # 上限 20
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
        印星根基能量（V3.0）：
          - 禄/刃根=30，长生根=20，余气/墓库根=10
          - 不再使用额外系数，仅乘地支破坏系数
          - 每个印星天干只计最强的一个根
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
                # 仅乘地支破坏系数（V3.0 不再乘额外权重系数）
                factor = self._get_branch_factor(branch, stem_el, branch_rels)
                score = base * factor
                logger.info(f"   B: {stem}({tg})根于{branch}({root_tp}) "
                            f"base={base} ×{factor:.2f} = {score:.1f}")
                total_b += score
                break  # 每个印星只计最强的一个根

        logger.info(f"   B总计: {total_b:.1f}")
        return total_b

    # ═══════════════════════════════════════════════════════
    #  K 因子：克泄耗能量
    # ═══════════════════════════════════════════════════════

    def _calculate_K(self, bazi: Dict, day_element: str,
                     branch_rels: Dict) -> Tuple[float, float]:
        """
        克泄耗能量（V3.0）：
          - 所有克泄耗十神（官杀/食伤/财）均使用根气系数：有根×1.2 / 半根×1.0 / 虚浮×0.5
          - 地支克泄耗补充：天干未透的克泄耗主气，官杀+20 / 食伤财+10（避免重复计入）
        返回 (total_k, guansha_k)：guansha_k 用于通关减克
        """
        stems = [bazi['year_stem'], bazi['month_stem'], bazi['hour_stem']]
        branches = branch_rels['branches']
        day_stem = bazi['day_stem']
        total_k = 0.0
        guansha_k = 0.0   # 仅官杀部分，供通关减克使用

        # 记录天干中已有的十神类型（用于地支补充时避免重复）
        stem_tg_set: set = set()

        for stem in stems:
            tg = _get_ten_god(day_stem, stem)
            if tg not in K_TEN_GOD_SCORES:
                continue
            stem_tg_set.add(tg)
            base = K_TEN_GOD_SCORES[tg]
            # V3.0：所有克泄耗十神统一使用根气系数
            stem_el = STEM_ELEMENTS.get(stem, '')
            root_kind = self._get_stem_root_kind(stem_el, branches, branch_rels, day_element)
            coeff = K_ROOT_COEFFICIENTS[root_kind]
            score = base * coeff
            logger.info(f"   K: {stem}({tg}) base={base} ×{coeff:.2f}({root_kind}) = {score:.1f}")
            total_k += score
            if tg in ('七杀', '正官'):
                guansha_k += score

        # 地支克泄耗补充（天干未透时）
        guansha_in_stems = any(t in ('七杀', '正官') for t in stem_tg_set)
        shishen_in_stems = any(t in ('食神', '伤官') for t in stem_tg_set)
        cai_in_stems = any(t in ('偏财', '正财') for t in stem_tg_set)

        from core.data.constants import HIDDEN_STEMS
        for branch in branches:
            hidden = HIDDEN_STEMS.get(branch, [])
            if not hidden:
                continue
            main_stem_char = hidden[0][0]
            tg = _get_ten_god(day_stem, main_stem_char)
            if tg not in K_TEN_GOD_SCORES:
                continue

            if tg in ('七杀', '正官') and not guansha_in_stems:
                logger.info(f"   K(地支): {branch}藏{main_stem_char}({tg}) +{K_BRANCH_GUANSHA_SCORE}")
                total_k += K_BRANCH_GUANSHA_SCORE
            elif tg in ('食神', '伤官') and not shishen_in_stems:
                logger.info(f"   K(地支): {branch}藏{main_stem_char}({tg}) +{K_BRANCH_CAISHISHEN_SCORE}")
                total_k += K_BRANCH_CAISHISHEN_SCORE
            elif tg in ('偏财', '正财') and not cai_in_stems:
                logger.info(f"   K(地支): {branch}藏{main_stem_char}({tg}) +{K_BRANCH_CAISHISHEN_SCORE}")
                total_k += K_BRANCH_CAISHISHEN_SCORE

        logger.info(f"   K总计: {total_k:.1f}（官杀K: {guansha_k:.1f}）")
        return total_k, guansha_k

    # ═══════════════════════════════════════════════════════
    #  动态修正
    # ═══════════════════════════════════════════════════════

    def _apply_tongguan(self, bazi: Dict, day_element: str,
                        K: float, K_guansha: float) -> float:
        """
        通关减克（V新版）：
          - 条件：印星透干（S 中印星分值 > 0，即有印星在天干即可，无论有无根）
          - 效果：仅官杀部分 K 减半（食伤财部分不受影响）
        """
        day_stem = bazi['day_stem']
        stems = [bazi['year_stem'], bazi['month_stem'], bazi['hour_stem']]
        has_guansha = any(_get_ten_god(day_stem, s) in ('七杀', '正官') for s in stems)
        has_yin = any(_get_ten_god(day_stem, s) in ('偏印', '正印') for s in stems)
        if has_guansha and has_yin:
            reduction = K_guansha * 0.5
            logger.info(f"   通关减克（印星透干）：官杀K减半 -{reduction:.1f} "
                        f"K: {K:.1f} → {K - reduction:.1f}")
            return K - reduction
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
    #  特殊格局辅助检测
    # ═══════════════════════════════════════════════════════

    def _has_broken_strong_root(self, day_element: str, branch_rels: Dict) -> bool:
        """
        从旺格"无强根被破"辅助判断。
        若四柱中有日主的帝旺根/临官根（禄刃根）且该地支被六冲，返回 True（有强根被破）。
        从旺格要求此方法返回 False。
        """
        chong_set = branch_rels['chong']
        el_root_type = ROOT_TYPE.get(day_element, {})
        el_root_scores = ROOT_SCORES.get(day_element, {})
        for branch in branch_rels['branches']:
            if branch in el_root_scores:
                if el_root_type.get(branch, '') in STRONG_ROOT_TYPES and branch in chong_set:
                    logger.info(f"   强根被破：{branch}({el_root_type[branch]}) 在冲集")
                    return True
        return False

    def _has_independent_root(self, day_element: str, branch_rels: Dict) -> bool:
        """
        从弱格"无独立根气"辅助判断（返回 True = 有独立根气 → 不满足从弱格）。
        有独立根气：
          - 有禄刃根（帝旺/临官），哪怕被冲，OR
          - 有完整弱根（长生/余气/墓库）且未被冲
        从弱格要求此方法返回 False。
        """
        branches = branch_rels['branches']
        chong_set = branch_rels['chong']
        el_root_type = ROOT_TYPE.get(day_element, {})
        el_root_scores = ROOT_SCORES.get(day_element, {})

        for branch in branches:
            if branch not in el_root_scores:
                continue
            root_tp = el_root_type.get(branch, '')
            if not root_tp:
                continue
            if root_tp in STRONG_ROOT_TYPES:
                # 有禄刃根存在（即使被冲）→ 有独立根气
                logger.info(f"   有独立根气（禄刃根）：{branch}({root_tp})")
                return True
            # 弱根未被冲 → 有独立根气
            if branch not in chong_set:
                logger.info(f"   有独立根气（完整弱根）：{branch}({root_tp})")
                return True
        return False

    # ═══════════════════════════════════════════════════════
    #  特殊格局检测
    # ═══════════════════════════════════════════════════════

    def _detect_special_patterns(self, M: float, R: float, S: float,
                                  K: float, P: float, bazi: Dict, branch_rels: Dict) -> Optional[str]:
        """
        检测从旺/假从旺/从弱/假从弱格。

        从旺格：  P ≥ 25 AND K ≤ 2 AND 无强根被破
        假从旺格：MRS ≥ 25 AND 3 ≤ K ≤ 4（大势旺但有小疵，不变）
        从弱格：  R = 0 AND P ≤ 4 AND K ≥ 6 AND 无独立根气
        假从弱格：R = 0 AND 3 ≤ MRS ≤ 4 AND K ≥ 6（不变）
        """
        day_element = STEM_ELEMENTS.get(bazi['day_stem'], '')
        mrs = M + R + S

        # 从旺格：P ≥ 25, K ≤ 2, 无强根被破
        if P >= CONGWANG_P_MIN and K <= CONGWANG_K_MAX:
            if not self._has_broken_strong_root(day_element, branch_rels):
                logger.info(f"   从旺格：P={P:.1f} ≥ {CONGWANG_P_MIN}, K={K:.1f} ≤ {CONGWANG_K_MAX}, 无强根被破")
                return '从旺格'
            else:
                logger.info(f"   P={P:.1f}/K={K:.1f} 满足从旺条件但有强根被破，不构成从旺格")

        # 假从旺格：MRS ≥ 25, 3 ≤ K ≤ 4（不变）
        if mrs >= CONGWANG_MRS_MIN and JIACONGWANG_K_MIN <= K <= JIACONGWANG_K_MAX:
            logger.info(f"   假从旺格：MRS={mrs:.1f} ≥ {CONGWANG_MRS_MIN}, "
                        f"K={K:.1f} ∈ [{JIACONGWANG_K_MIN},{JIACONGWANG_K_MAX}]")
            return '假从旺格'

        # 从弱格/假从弱格：前提是日主无根（R = 0）且 K ≥ 6
        if R == 0 and K >= CONGRUO_K_MIN:
            # 从弱格：P ≤ 4, 无独立根气
            if P <= CONGRUO_P_MAX and not self._has_independent_root(day_element, branch_rels):
                logger.info(f"   从弱格：R=0, P={P:.1f} ≤ {CONGRUO_P_MAX}, "
                            f"K={K:.1f} ≥ {CONGRUO_K_MIN}, 无独立根气")
                return '从弱格'
            # 假从弱格：3 ≤ MRS ≤ 4（不变）
            if JIACONGRUO_MRS_MIN <= mrs <= JIACONGRUO_MRS_MAX:
                logger.info(f"   假从弱格：R=0, MRS={mrs:.1f} ∈ "
                            f"[{JIACONGRUO_MRS_MIN},{JIACONGRUO_MRS_MAX}], K={K:.1f} ≥ {CONGRUO_K_MIN}")
                return '假从弱格'

        return None

    # ═══════════════════════════════════════════════════════
    #  5级旺衰判定
    # ═══════════════════════════════════════════════════════

    def _determine_wangshuai_v2(self, P: float) -> str:
        """根据 P 值判定4级旺衰（V3.0：身强/中和偏强/中和偏弱/身弱）"""
        for name, threshold in WANGSHUAI_THRESHOLDS:
            if threshold is None or P >= threshold:
                return name
        return '身弱'  # 兜底

    def _calculate_wangshuai_degree_v2(self, P: float, wangshuai: str) -> int:
        """
        将 P 值映射到 0-100 旺衰程度（V新版：4级 + 特殊格局）
        P 理论最大值约 37（M=45×0.35 + R=40×0.40 + S=20×0.25 = 37.75），最小值约 -10
        """
        if wangshuai == '从强':
            # 从旺格，P 通常超过 25，映射到 90-100
            degree = 90 + min(10, max(0, (P - 25) * 0.8))
        elif wangshuai == '身强':
            # P ≥ 25，理论最大约 37，映射到 65-90
            degree = 65 + min(25, max(0, (P - 25) * 2.1))
        elif wangshuai == '中和偏强':
            # 15 ≤ P < 25，映射到 50-64
            degree = 50 + min(14, max(0, (P - 15) * 1.4))
        elif wangshuai == '中和偏弱':
            # 5 ≤ P < 15，映射到 35-49
            degree = 35 + min(14, max(0, (P - 5) * 1.4))
        elif wangshuai == '身弱':
            # P < 5，映射到 5-34
            degree = max(5, 34 - max(0, (4 - min(P, 4)) * 2.9))
        elif wangshuai == '从弱':
            # 从弱格，P 通常极低（< 5 且 R=0），映射到 0-10
            degree = max(0, 10 - max(0, (2 - P) * 2))
        else:
            degree = 50.0
        return int(min(100, max(0, round(degree))))

    # ═══════════════════════════════════════════════════════
    #  喜忌神
    # ═══════════════════════════════════════════════════════

    def _determine_xi_ji(self, wangshuai: str) -> Dict[str, List[str]]:
        """根据旺衰级别返回喜忌十神列表（静态映射，中和格由_determine_xi_ji_zhonghe处理）"""
        mapping = XI_JI_MAPPING.get(wangshuai, {})
        return {
            'xi_shen': list(mapping.get('喜神', [])),
            'ji_shen': list(mapping.get('忌神', [])),
        }

    # ═══════════════════════════════════════════════════════
    #  中和格喜忌：动态四法（调候>通关>扶抑>气势）
    # ═══════════════════════════════════════════════════════

    def _determine_xi_ji_zhonghe(
        self, bazi: Dict, day_element: str,
        M: float, R: float, S: float, K: float,
        element_counts: Dict[str, int], branch_rels: Dict
    ) -> Dict[str, List[str]]:
        """
        中和格喜忌：依次执行调候法>通关法>扶抑法>气势法，合并结果。
        """
        day_stem = bazi['day_stem']
        stems = [bazi['year_stem'], bazi['month_stem'], bazi['hour_stem']]
        month_branch = bazi['month_branch']

        xi_shen: List[str] = []
        ji_shen: List[str] = []

        def _add_xi(*gods):
            for g in gods:
                if g not in xi_shen:
                    xi_shen.append(g)

        def _add_ji(*gods):
            for g in gods:
                if g not in ji_shen:
                    ji_shen.append(g)

        # 五行 → 十神 映射（根据日主推导）
        prod_el = ELEMENT_PRODUCES.get(day_element, '')        # 食伤
        ctrl_el = ELEMENT_CONTROLS.get(day_element, '')        # 财星
        ctrl_by_el = next((k for k, v in ELEMENT_CONTROLS.items() if v == day_element), '')  # 官杀
        prod_by_el = next((k for k, v in ELEMENT_PRODUCES.items() if v == day_element), '')  # 印星

        def _el_to_xi_gods(el: str) -> List[str]:
            """五行 → 对应的十神（喜神类）"""
            if el == day_element:
                return ['比肩', '劫财']
            if el == prod_by_el:
                return ['偏印', '正印']
            if el == ctrl_by_el:
                return ['七杀', '正官']
            if el == prod_el:
                return ['食神', '伤官']
            if el == ctrl_el:
                return ['偏财', '正财']
            return []

        # ═══ 法一：调候法 ═══
        tiaohou_el = self._get_tiaohou_for_zhonghe(month_branch, element_counts)
        if tiaohou_el:
            gods = _el_to_xi_gods(tiaohou_el)
            _add_xi(*gods)
            logger.info(f"   中和喜忌-调候法：喜{tiaohou_el} → {gods}")

        # ═══ 法二：通关法 ═══
        tongguan_el = self._detect_tongguan_zhonghe(element_counts, day_element)
        if tongguan_el:
            gods = _el_to_xi_gods(tongguan_el)
            _add_xi(*gods)
            logger.info(f"   中和喜忌-通关法：通关{tongguan_el} → {gods}")

        # ═══ 法三：扶抑法 ═══
        fuyi_xi, fuyi_ji = self._detect_fuyi_zhonghe(
            stems, day_stem, day_element, element_counts,
            ctrl_by_el, prod_el, ctrl_el, prod_by_el
        )
        _add_xi(*fuyi_xi)
        _add_ji(*fuyi_ji)
        if fuyi_xi or fuyi_ji:
            logger.info(f"   中和喜忌-扶抑法：喜{fuyi_xi} 忌{fuyi_ji}")

        # ═══ 法四：气势法 ═══
        qishi_xi = self._detect_qishi_zhonghe(stems, day_stem, prod_by_el, ctrl_by_el, prod_el)
        _add_xi(*qishi_xi)
        if qishi_xi:
            logger.info(f"   中和喜忌-气势法：喜{qishi_xi}")

        # 兜底：若四法均无结果，按中和格通用原则：调候为主
        if not xi_shen:
            # 无明确调候需求时，中和格倾向于维持平衡，微调喜食伤（泄秀）
            xi_shen = ['食神', '伤官']
            logger.info("   中和喜忌-兜底：无明确喜神，以食伤泄秀为喜")

        logger.info(f"   中和格最终喜忌 xi={xi_shen} ji={ji_shen}")
        return {'xi_shen': xi_shen, 'ji_shen': ji_shen}

    def _get_tiaohou_for_zhonghe(self, month_branch: str,
                                  element_counts: Dict[str, int]) -> Optional[str]:
        """调候法：根据月令和五行偏颇判断调候五行"""
        # 偏寒（冬月 or 水多）→ 喜火
        if month_branch in ('亥', '子', '丑') or element_counts.get('水', 0) >= 3:
            return '火'
        # 偏暖（夏月 or 火多）→ 喜水
        if month_branch in ('巳', '午', '未') or element_counts.get('火', 0) >= 3:
            return '水'
        # 偏燥（土火多）→ 喜水
        if (element_counts.get('土', 0) + element_counts.get('火', 0)) >= 4:
            return '水'
        # 偏湿（水金多）→ 喜火
        if (element_counts.get('水', 0) + element_counts.get('金', 0)) >= 4:
            return '火'
        return None

    def _detect_tongguan_zhonghe(self, element_counts: Dict[str, int],
                                  day_element: str) -> Optional[str]:
        """通关法：检测两行相战，返回通关五行"""
        # 通关对应表：{(强行A, 强行B): 通关五行}
        tongguan_table = {
            frozenset({'木', '金'}): '水',   # 木金相战 → 通关用水（水生木，金生水不通...其实水通木金：金生水，水生木）
            frozenset({'水', '火'}): '木',   # 水火相战 → 通关用木（水生木，木生火）
            frozenset({'火', '金'}): '土',   # 火金相战 → 通关用土（火生土，土生金）
            frozenset({'土', '水'}): '金',   # 土水相战 → 通关用金（土生金，金生水）
            frozenset({'木', '土'}): '火',   # 木土相战 → 通关用火（木生火，火生土）
        }
        STRONG_THRESHOLD = 2  # 两行各有≥2个才算"相战"
        for (a, b), tongguan in tongguan_table.items():
            pair = list(frozenset({a, b}))
            if (element_counts.get(pair[0], 0) >= STRONG_THRESHOLD and
                    element_counts.get(pair[1], 0) >= STRONG_THRESHOLD):
                # 确认是相克关系（不是所有两行都算相战）
                if (ELEMENT_CONTROLS.get(pair[0]) == pair[1] or
                        ELEMENT_CONTROLS.get(pair[1]) == pair[0]):
                    logger.info(f"   通关法：{pair[0]}-{pair[1]}相战，通关五行={tongguan}")
                    return tongguan
        return None

    def _detect_fuyi_zhonghe(
        self, stems: List[str], day_stem: str, day_element: str,
        element_counts: Dict[str, int],
        ctrl_by_el: str, prod_el: str, ctrl_el: str, prod_by_el: str
    ) -> Tuple[List[str], List[str]]:
        """
        扶抑法：检查各十神类别的强弱，过强则抑，过弱则扶。
        返回 (喜神十神列表, 忌神十神列表)
        """
        xi_gods: List[str] = []
        ji_gods: List[str] = []

        # 统计各类别元素数量
        guansha_cnt = element_counts.get(ctrl_by_el, 0)   # 官杀五行
        shishen_cnt = element_counts.get(prod_el, 0)       # 食伤五行
        cai_cnt = element_counts.get(ctrl_el, 0)           # 财星五行
        yin_cnt = element_counts.get(prod_by_el, 0)        # 印星五行
        biji_cnt = element_counts.get(day_element, 0)      # 比劫五行（含日主本身=1）

        OVER_STRONG = 2   # ≥2个为过强（中和格中相对过旺）
        VERY_WEAK = 0     # =0个为极弱（需补充）

        # 官杀过强 → 喜食伤制官杀，或喜印化官杀
        if guansha_cnt >= OVER_STRONG:
            xi_gods.extend(['食神', '伤官'])
        # 食伤过强 → 喜印制食伤，或喜财泄食伤
        if shishen_cnt >= OVER_STRONG:
            xi_gods.extend(['偏印', '正印'])
        # 财星过强 → 喜比劫帮身担财，或喜印生身
        if cai_cnt >= OVER_STRONG:
            xi_gods.extend(['比肩', '劫财'])
        # 印星过强 → 喜财制印，或喜比劫泄印
        if yin_cnt >= OVER_STRONG:
            xi_gods.extend(['偏财', '正财'])
            ji_gods.extend(['偏印', '正印'])
        # 官杀极弱 → 喜官杀（身强中和可用官）
        if guansha_cnt == VERY_WEAK and biji_cnt >= OVER_STRONG:
            xi_gods.extend(['七杀', '正官'])

        return xi_gods, ji_gods

    def _detect_qishi_zhonghe(
        self, stems: List[str], day_stem: str,
        prod_by_el: str, ctrl_by_el: str, prod_el: str
    ) -> List[str]:
        """
        气势法：检测特殊天干组合，顺其气势取喜神。
        """
        xi_gods: List[str] = []
        # 判断各十神是否出现在天干
        has_shishen = any(_get_ten_god(day_stem, s) in ('食神', '伤官') for s in stems)
        has_yin = any(_get_ten_god(day_stem, s) in ('偏印', '正印') for s in stems)
        has_guansha = any(_get_ten_god(day_stem, s) in ('七杀', '正官') for s in stems)
        has_cai = any(_get_ten_god(day_stem, s) in ('偏财', '正财') for s in stems)

        # 伤官佩印（伤官+印星同见）→ 喜印官
        if has_shishen and has_yin:
            xi_gods.extend(['偏印', '正印'])
        # 杀印相生（官杀+印星同见）→ 喜印比
        if has_guansha and has_yin:
            xi_gods.extend(['比肩', '劫财'])
        # 食神生财（食神+财星同见）→ 喜财官
        if has_shishen and has_cai:
            xi_gods.extend(['偏财', '正财', '七杀', '正官'])

        return xi_gods

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
