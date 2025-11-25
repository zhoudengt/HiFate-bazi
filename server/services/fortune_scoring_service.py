# -*- coding: utf-8 -*-
"""
运势评分服务 - 基于五行、十神、生克关系、调候、刑冲自动评分

职责：
- 根据命理分析结果自动计算运势评分
- 识别关键风险因素和有利因素
- 综合考虑调候平衡和刑冲合害关系
- 为LLM提供预判断依据，减少推理负担

设计原则：
- 基于传统命理规则
- 结果可解释
- 不替代LLM，只提供参考
"""

from typing import Dict, Any, List, Optional


class FortuneScoring:
    """运势评分计算器"""
    
    @staticmethod
    def calculate_wealth_score(
        balance_analysis: Dict[str, Any],
        relation_analysis: Dict[str, Any],
        xi_ji: Dict[str, Any],
        shishen_stats: Dict[str, Any],
        tiaohou: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        计算财运评分（1-10分）
        
        评分规则：
        - 基准分5分
        - 财星为喜神 +2分
        - 财星旺相 +1分
        - 劫财克财 -2分
        - 食神生财 +2分
        - 官印护财 +1分
        - 地支合财 +0.5分（新增）
        - 调候得当财运顺 +0.5分（新增）
        
        Args:
            balance_analysis: 五行平衡分析
            relation_analysis: 流年与八字关系分析
            xi_ji: 喜忌神信息
            shishen_stats: 十神统计
        
        Returns:
            {
                'score': 1-10,
                'level': '极好'/'好'/'中等'/'差'/'极差',
                'risk_factors': [...],  # 风险因素
                'favorable_factors': [...]  # 有利因素
            }
        """
        score = 5  # 基准分
        risk_factors = []
        favorable_factors = []
        
        # 获取五行变化
        analysis = balance_analysis.get('analysis', {})
        changes = analysis.get('changes', {})
        
        # 获取关系分析
        stem_relation = relation_analysis.get('stem_relation', {})
        branch_relation = relation_analysis.get('branch_relation', {})
        
        # 1. 检查财星（正财、偏财）
        cai_count = shishen_stats.get('正财', 0) + shishen_stats.get('偏财', 0)
        
        if cai_count > 0:
            favorable_factors.append('命局有财星')
            score += 0.5
            
            # 财星是否为喜神
            if '财' in str(xi_ji.get('xi_shen', [])):
                favorable_factors.append('财星为喜神')
                score += 2
            elif '财' in str(xi_ji.get('ji_shen', [])):
                risk_factors.append('财星为忌神')
                score -= 1.5
        else:
            risk_factors.append('命局无财星')
            score -= 1
        
        # 2. 检查劫财（克财）
        jiecai_count = shishen_stats.get('劫财', 0) + shishen_stats.get('比肩', 0)
        
        if jiecai_count > cai_count and jiecai_count > 0:
            risk_factors.append('劫财过多，有破财风险')
            score -= 2
        
        # 3. 检查食伤生财
        shishen_count = shishen_stats.get('食神', 0) + shishen_stats.get('伤官', 0)
        
        if shishen_count > 0 and cai_count > 0:
            favorable_factors.append('食伤生财，财源广')
            score += 1.5
        
        # 4. 检查五行生克关系
        # 如果流年天干生助财星
        if stem_relation.get('type') == 'sheng' and '财' in stem_relation.get('impact', ''):
            favorable_factors.append('流年天干生助财星')
            score += 1
        
        # 如果流年天干克制财星
        if stem_relation.get('type') == 'ke' and '财' in stem_relation.get('impact', ''):
            risk_factors.append('流年天干克制财星')
            score -= 1.5
        
        # 5. 五行平衡评估
        balance_status = analysis.get('balance_status', '')
        
        if '过旺' in balance_status or '过弱' in balance_status:
            risk_factors.append(f'五行失衡：{balance_status}')
            score -= 0.5
        
        # 6. 检查地支合局（新增）
        if branch_relation.get('type') in ['合', '三合']:
            favorable_factors.append(f'地支{branch_relation.get("type")}，财运顺畅')
            score += 0.5
        
        # 7. 检查调候对财运的影响（新增）
        if tiaohou:
            tiaohou_priority = tiaohou.get('tiaohou_priority', 'none')
            if tiaohou_priority == 'low':  # 调候平衡，各方面运势都好
                favorable_factors.append('调候得当，财运亨通')
                score += 0.5
        
        # 8. 特殊格局加分
        # （后续可根据实际情况扩展）
        
        # 限制分数范围
        score = max(1, min(10, score))
        
        # 确定等级
        if score >= 8:
            level = '极好'
        elif score >= 6.5:
            level = '好'
        elif score >= 4.5:
            level = '中等'
        elif score >= 3:
            level = '差'
        else:
            level = '极差'
        
        return {
            'score': round(score, 1),
            'level': level,
            'risk_factors': risk_factors,
            'favorable_factors': favorable_factors
        }
    
    @staticmethod
    def calculate_career_score(
        balance_analysis: Dict[str, Any],
        relation_analysis: Dict[str, Any],
        xi_ji: Dict[str, Any],
        shishen_stats: Dict[str, Any],
        tiaohou: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        计算事业运评分（1-10分）
        
        评分规则：
        - 基准分5分
        - 官星为喜神 +2分
        - 印星辅助 +1分
        - 伤官见官 -2分
        - 身旺有官 +1分
        
        Args:
            同 calculate_wealth_score
        
        Returns:
            同 calculate_wealth_score
        """
        score = 5
        risk_factors = []
        favorable_factors = []
        
        # 获取分析数据
        analysis = balance_analysis.get('analysis', {})
        stem_relation = relation_analysis.get('stem_relation', {})
        
        # 1. 检查官星（正官、偏官/七杀）
        guan_count = shishen_stats.get('正官', 0) + shishen_stats.get('偏官', 0) + shishen_stats.get('七杀', 0)
        
        if guan_count > 0:
            favorable_factors.append('命局有官星')
            score += 0.5
            
            # 官星是否为喜神
            if '官' in str(xi_ji.get('xi_shen', [])):
                favorable_factors.append('官星为喜神')
                score += 2
            elif '官' in str(xi_ji.get('ji_shen', [])):
                risk_factors.append('官星为忌神')
                score -= 1.5
        
        # 2. 检查印星（正印、偏印）
        yin_count = shishen_stats.get('正印', 0) + shishen_stats.get('偏印', 0)
        
        if yin_count > 0 and guan_count > 0:
            favorable_factors.append('官印相生，事业稳定')
            score += 1.5
        
        # 3. 检查伤官
        shangguan_count = shishen_stats.get('伤官', 0)
        
        if shangguan_count > 0 and guan_count > 0:
            risk_factors.append('伤官见官，职场波折')
            score -= 2
        
        # 4. 流年关系
        if stem_relation.get('type') == 'sheng' and '官' in stem_relation.get('impact', ''):
            favorable_factors.append('流年生助官星，事业有成')
            score += 1
        
        if stem_relation.get('type') == 'ke' and '官' in stem_relation.get('impact', ''):
            risk_factors.append('流年克制官星，压力增大')
            score -= 1.5
        
        # 限制分数范围
        score = max(1, min(10, score))
        
        # 确定等级
        if score >= 8:
            level = '极好'
        elif score >= 6.5:
            level = '好'
        elif score >= 4.5:
            level = '中等'
        elif score >= 3:
            level = '差'
        else:
            level = '极差'
        
        return {
            'score': round(score, 1),
            'level': level,
            'risk_factors': risk_factors,
            'favorable_factors': favorable_factors
        }
    
    @staticmethod
    def calculate_health_score(
        balance_analysis: Dict[str, Any],
        relation_analysis: Dict[str, Any],
        xi_ji: Dict[str, Any],
        wangshuai: str,
        tiaohou: Optional[Dict[str, Any]] = None,
        element_counts: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        计算健康运评分（1-10分）
        
        评分规则：
        - 基准分7分（健康较主观）
        - 五行失衡 -2分
        - 刑冲克害 -1.5分
        - 调候失衡 -1.5分（新增）
        - 八字内部刑冲 -1分（新增）
        - 喜神得力 +1分
        
        Args:
            balance_analysis: 五行平衡分析
            relation_analysis: 关系分析
            xi_ji: 喜忌神
            wangshuai: 旺衰状态
            tiaohou: 调候信息（新增）
            element_counts: 五行统计（新增）
        
        Returns:
            同 calculate_wealth_score
        """
        score = 7  # 健康基准分较高
        risk_factors = []
        favorable_factors = []
        
        analysis = balance_analysis.get('analysis', {})
        balance_status = analysis.get('balance_status', '')
        changes = analysis.get('changes', {})
        
        # 1. 五行平衡检查
        if '过旺' in balance_status:
            risk_factors.append(f'五行过旺：{balance_status}')
            score -= 1.5
        
        if '过弱' in balance_status:
            risk_factors.append(f'五行过弱：{balance_status}')
            score -= 1.5
        
        # 2. 检查克制关系（特别关注身体健康相关）
        stem_relation = relation_analysis.get('stem_relation', {})
        branch_relation = relation_analysis.get('branch_relation', {})
        
        if stem_relation.get('type') == 'ke':
            risk_factors.append('流年天干克制，注意健康')
            score -= 1
        
        if branch_relation.get('type') in ['冲', '刑', '害']:
            risk_factors.append(f'地支{branch_relation.get("type")}，注意身体')
            score -= 1.5
        
        # 2.5 检查八字内部刑冲关系（新增）
        internal_relations = relation_analysis.get('internal_relations', {})
        if internal_relations.get('has_chong'):
            risk_factors.append('八字内部有冲，身体易有问题')
            score -= 1
        if internal_relations.get('has_xing'):
            risk_factors.append('八字内部有刑，健康需注意')
            score -= 0.5
        
        # 2.6 检查调候平衡（新增）
        if tiaohou and element_counts:
            tiaohou_element = tiaohou.get('tiaohou_element')
            season = tiaohou.get('season', '')
            
            if tiaohou_element:
                tiaohou_count = element_counts.get(tiaohou_element, 0)
                
                if tiaohou_count == 0:
                    # 缺少调候五行，健康风险高
                    risk_factors.append(f'{season}缺{tiaohou_element}，调候失衡')
                    score -= 1.5
                elif tiaohou_count == 1:
                    # 调候五行不足
                    risk_factors.append(f'{season}{tiaohou_element}略弱，注意调理')
                    score -= 0.5
                else:
                    # 调候平衡良好
                    favorable_factors.append(f'{season}{tiaohou_element}充足，调候得当')
                    score += 0.5
        
        # 3. 旺衰状态
        if '极弱' in wangshuai or '极旺' in wangshuai:
            risk_factors.append(f'身体状态：{wangshuai}')
            score -= 1
        
        # 4. 喜神得力
        if analysis.get('xi_shen_favorable', False):
            favorable_factors.append('喜神得力，身心愉悦')
            score += 1
        
        # 限制分数范围
        score = max(1, min(10, score))
        
        # 确定等级
        if score >= 8:
            level = '极好'
        elif score >= 6.5:
            level = '好'
        elif score >= 4.5:
            level = '中等'
        elif score >= 3:
            level = '差'
        else:
            level = '极差'
        
        return {
            'score': round(score, 1),
            'level': level,
            'risk_factors': risk_factors,
            'favorable_factors': favorable_factors
        }
    
    @staticmethod
    def calculate_marriage_score(
        balance_analysis: Dict[str, Any],
        relation_analysis: Dict[str, Any],
        xi_ji: Dict[str, Any],
        shishen_stats: Dict[str, Any],
        gender: str,
        tiaohou: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        计算婚姻运评分（1-10分）
        
        评分规则：
        - 男：财星代表妻子
        - 女：官星代表丈夫
        - 基准分5分
        - 配偶星为喜神 +2分
        - 桃花星旺 +1分
        - 刑冲克害配偶星 -2分
        - 日支冲刑 -1.5分（新增）
        - 地支合婚 +1分（新增）
        
        Args:
            balance_analysis: 五行平衡分析
            relation_analysis: 关系分析
            xi_ji: 喜忌神
            shishen_stats: 十神统计
            gender: 性别（male/female）
        
        Returns:
            同 calculate_wealth_score
        """
        score = 5
        risk_factors = []
        favorable_factors = []
        
        # 确定配偶星
        if gender == 'male':
            # 男命看财星
            peiou_star = '财'
            peiou_count = shishen_stats.get('正财', 0) + shishen_stats.get('偏财', 0)
        else:
            # 女命看官星
            peiou_star = '官'
            peiou_count = shishen_stats.get('正官', 0) + shishen_stats.get('偏官', 0) + shishen_stats.get('七杀', 0)
        
        # 1. 配偶星数量
        if peiou_count == 0:
            risk_factors.append(f'命局无{peiou_star}星')
            score -= 1
        elif peiou_count == 1:
            favorable_factors.append(f'{peiou_star}星专一')
            score += 1
        elif peiou_count > 2:
            risk_factors.append(f'{peiou_star}星过多，感情复杂')
            score -= 1.5
        
        # 2. 配偶星喜忌
        if peiou_star in str(xi_ji.get('xi_shen', [])):
            favorable_factors.append(f'{peiou_star}星为喜神，婚姻美满')
            score += 2
        elif peiou_star in str(xi_ji.get('ji_shen', [])):
            risk_factors.append(f'{peiou_star}星为忌神，婚姻压力')
            score -= 1.5
        
        # 3. 流年关系
        stem_relation = relation_analysis.get('stem_relation', {})
        
        if stem_relation.get('type') == 'sheng' and peiou_star in stem_relation.get('impact', ''):
            favorable_factors.append('流年利于感情')
            score += 1
        
        if stem_relation.get('type') == 'ke' and peiou_star in stem_relation.get('impact', ''):
            risk_factors.append('流年不利感情')
            score -= 1.5
        
        # 4. 检查日支冲刑（新增）- 日支代表配偶宫
        internal_relations = relation_analysis.get('internal_relations', {})
        if internal_relations.get('day_branch_chong'):
            risk_factors.append('日支逢冲，婚姻不稳')
            score -= 1.5
        if internal_relations.get('day_branch_xing'):
            risk_factors.append('日支遭刑，感情波折')
            score -= 1
        
        # 5. 检查地支合婚（新增）
        branch_relation = relation_analysis.get('branch_relation', {})
        if branch_relation.get('type') in ['合', '六合']:
            favorable_factors.append('地支相合，婚姻和谐')
            score += 1
        
        # 限制分数范围
        score = max(1, min(10, score))
        
        # 确定等级
        if score >= 8:
            level = '极好'
        elif score >= 6.5:
            level = '好'
        elif score >= 4.5:
            level = '中等'
        elif score >= 3:
            level = '差'
        else:
            level = '极差'
        
        return {
            'score': round(score, 1),
            'level': level,
            'risk_factors': risk_factors,
            'favorable_factors': favorable_factors
        }
    
    @staticmethod
    def calculate_all_scores(
        balance_analysis: Dict[str, Any],
        relation_analysis: Dict[str, Any],
        xi_ji: Dict[str, Any],
        shishen_stats: Dict[str, Any],
        wangshuai: str,
        gender: str
    ) -> Dict[str, Any]:
        """
        计算所有维度的运势评分
        
        Returns:
            {
                'wealth': {...},
                'career': {...},
                'health': {...},
                'marriage': {...}
            }
        """
        return {
            'wealth': FortuneScoring.calculate_wealth_score(
                balance_analysis, relation_analysis, xi_ji, shishen_stats
            ),
            'career': FortuneScoring.calculate_career_score(
                balance_analysis, relation_analysis, xi_ji, shishen_stats
            ),
            'health': FortuneScoring.calculate_health_score(
                balance_analysis, relation_analysis, xi_ji, wangshuai
            ),
            'marriage': FortuneScoring.calculate_marriage_score(
                balance_analysis, relation_analysis, xi_ji, shishen_stats, gender
            )
        }

