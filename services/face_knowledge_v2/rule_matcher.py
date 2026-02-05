# -*- coding: utf-8 -*-
"""
面相规则匹配引擎
实现规则互斥和去重合并逻辑
"""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)
from collections import defaultdict


class RuleMatcher:
    """规则匹配器 - 处理互斥和去重"""
    
    def __init__(self):
        pass
    
    def match_and_filter(self, rules: List[Dict], features: Dict, 
                         confidence_scores: Dict = None) -> List[Dict]:
        """
        匹配规则并应用互斥、去重逻辑（核心：基于实际识别特征过滤）
        
        Args:
            rules: 规则列表
            features: 识别到的特征字典，如 {'detected_features': ['圆润', '有肉'], ...}
            confidence_scores: 特征的置信度分数
        
        Returns:
            过滤后的规则列表
        """
        # 提取实际识别到的特征
        detected_features = features.get('detected_features', [])
        
        matched_rules = []
        
        for rule in rules:
            interpretations = rule.get('interpretations', [])
            
            for interp in interpretations:
                feature_desc = interp.get('feature', '')  # 如："鼻头圆润有肉"
                interpretation = interp.get('interpretation', '')
                category = interp.get('category', '')
                
                # 【关键】基于实际特征过滤：只保留匹配的interpretation
                if not self._match_detected_features(feature_desc, detected_features):
                    continue  # 跳过不匹配的interpretation
                
                # 调试日志
                logger.info(f"[DEBUG] 规则匹配: position={rule.get('position', '')}, feature={feature_desc}, detected={detected_features}, matched=True")
                
                # 计算置信度
                confidence = self._calculate_confidence(feature_desc, features, confidence_scores)
                
                matched_rules.append({
                    'position': rule.get('position', ''),
                    'feature': feature_desc,
                    'interpretation': interpretation,
                    'category': category,
                    'priority': rule.get('priority', 50),
                    'confidence': confidence
                })
        
        # 应用互斥规则（冗余保护，理论上已经通过特征匹配避免了互斥）
        filtered_rules = self._apply_mutex_rules(matched_rules)
        
        # 去重合并
        merged_rules = self._merge_duplicate_rules(filtered_rules)
        
        return merged_rules
    
    def _match_detected_features(self, feature_desc: str, detected_features: List[str]) -> bool:
        """
        判断interpretation的特征描述是否匹配实际识别到的特征（增强版：更严格的匹配，避免互斥）
        
        Args:
            feature_desc: interpretation中的feature字段，如"鼻头圆润有肉"、"平满光润"
            detected_features: 实际识别到的特征列表，如['圆润', '有肉']
        
        Returns:
            True if matched, False otherwise
        """
        # 定义负面关键词（需要排除的）
        negative_keywords = ['尖薄', '尖削', '凹陷', '暗沉', '狭窄', '短浅', '弯曲', 
                           '低陷', '孤独', '不利', '辛苦', '波折', '平平', '破财', 
                           '有疤', '有痣', '有横纹', '有节', '断节', '稀疏散乱', 
                           '鱼尾纹多且深', '眼袋深重', '削瘦凹陷']
        
        # 定义互斥特征对（确保不会同时匹配）
        mutex_feature_pairs = [
            (['眉毛浓密顺长'], ['眉毛稀疏散乱']),
            (['光洁饱满无纹'], ['鱼尾纹多且深', '有痣或疤', '色泽暗淡']),
            (['卧蚕饱满', '色泽明润'], ['眼袋深重', '有痣或纹']),
            (['饱满有肉'], ['削瘦凹陷']),
        ]
        
        # 1. 如果feature_desc包含负面关键词，检查是否应该返回
        has_negative = any(kw in feature_desc for kw in negative_keywords)
        
        if has_negative:
            # 如果没有detected_features，排除负面描述
            if not detected_features:
                return False
            
            # 如果detected_features包含正面特征，排除负面描述
            positive_detected = any(kw in detected_features 
                                   for kw in ['圆润', '饱满', '开阔', '红润', '深长', '有肉', 
                                             '方圆', '平润', '平满', '光润', '端正', '高起', '挺直',
                                             '眉间距宽', '光洁饱满无纹', '色泽明润', '饱满有肉'])
            if positive_detected:
                return False  # 排除负面描述
            
            # 如果没有正面特征，也不返回负面描述（保守策略）
            return False
        
        # 2. 检查互斥特征对（确保不会同时匹配互斥的特征）
        for positive_group, negative_group in mutex_feature_pairs:
            # 如果feature_desc包含正面组中的特征
            if any(kw in feature_desc for kw in positive_group):
                # 检查detected_features是否包含负面组中的特征
                if any(kw in str(detected_features) for kw in negative_group):
                    return False  # 互斥，不匹配
            # 如果feature_desc包含负面组中的特征
            elif any(kw in feature_desc for kw in negative_group):
                # 检查detected_features是否包含正面组中的特征
                if any(kw in str(detected_features) for kw in positive_group):
                    return False  # 互斥，不匹配
        
        # 3. 如果没有负面关键词，说明是正面或中性描述
        if not detected_features:
            # 没有detected_features，默认返回正面/中性描述
            return True
        
        # 4. 检查是否匹配detected_features（使用更严格的匹配）
        # 4.1 直接包含匹配（优先，最严格）
        for detected in detected_features:
            if detected in feature_desc:
                return True
        
        # 4.2 完整匹配（更严格）
        # 对于特定的特征描述，要求完整匹配（避免互斥特征同时匹配）
        specific_features = ['眉毛浓密顺长', '眉毛稀疏散乱', '眉间距宽', 
                           '光洁饱满无纹', '鱼尾纹多且深', '有痣或疤', '色泽暗淡',
                           '卧蚕饱满', '眼袋深重', '色泽明润', '有痣或纹',
                           '饱满有肉', '削瘦凹陷']
        
        # 定义互斥特征组（同一组内的特征互斥，不能同时匹配）
        mutex_feature_groups = [
            ['眉毛浓密顺长', '眉毛稀疏散乱', '眉间距宽'],  # 兄弟宫互斥特征
            ['光洁饱满无纹', '鱼尾纹多且深', '有痣或疤', '色泽暗淡'],  # 夫妻宫互斥特征
            ['卧蚕饱满', '眼袋深重', '色泽明润', '有痣或纹'],  # 子女宫互斥特征
            ['饱满有肉', '削瘦凹陷'],  # 奴仆宫互斥特征
        ]
        
        for specific in specific_features:
            if specific in feature_desc:
                # 要求detected_features中包含该特征的完整描述（严格匹配）
                if specific in detected_features:
                    return True
                
                # 对于互斥特征组，不允许部分匹配
                # 检查specific是否属于某个互斥组
                is_in_mutex_group = False
                for mutex_group in mutex_feature_groups:
                    if specific in mutex_group:
                        is_in_mutex_group = True
                        break
                
                # 如果specific属于互斥组，且没有完全匹配，则不允许匹配
                # 这样可以避免互斥特征同时匹配（如"眉毛浓密顺长"和"眉间距宽"）
                if is_in_mutex_group:
                    return False
        
        # 4.3 近义词匹配（放宽条件，但更谨慎）
        synonym_groups = [
            ['饱满', '平满', '丰满', '充实'],
            ['圆润', '圆满', '圆融'],
            ['开阔', '宽阔', '广阔'],
            ['光润', '光泽', '明润', '红润', '平润'],
            ['端正', '方正', '正直'],
            ['高起', '高隆', '高耸'],
            ['挺直', '笔直', '直立'],
            ['深长', '深邃', '长远'],
        ]
        
        # 检查近义词
        for detected in detected_features:
            for synonym_group in synonym_groups:
                if detected in synonym_group:
                    # detected是某个近义词组的成员，检查feature_desc是否包含同组的其他词
                    for synonym in synonym_group:
                        if synonym in feature_desc:
                            return True
        
        # 5. 其他情况，默认不匹配（保守策略，避免误匹配）
        # 注意：不再使用默认匹配，因为会导致互斥规则同时匹配
        return False
    
    def _calculate_confidence(self, feature: str, features: Dict, 
                              confidence_scores: Dict = None) -> float:
        """
        计算规则匹配的置信度
        
        根据特征关键词匹配度计算
        """
        if confidence_scores and feature in confidence_scores:
            return confidence_scores[feature]
        
        # 简化逻辑：根据特征关键词评分
        positive_keywords = ['饱满', '明润', '开阔', '圆润', '宽阔', '红润', '深长', '高起', '挺直']
        negative_keywords = ['凹陷', '暗沉', '狭窄', '尖薄', '窄小', '短浅', '低陷', '弯曲']
        
        confidence = 0.5  # 默认置信度
        
        # 检查特征中的关键词
        for keyword in positive_keywords:
            if keyword in feature:
                confidence += 0.1
        
        for keyword in negative_keywords:
            if keyword in feature:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _apply_mutex_rules(self, rules: List[Dict]) -> List[Dict]:
        """
        应用互斥规则
        
        逻辑：同一位置的规则，按照置信度排序，只保留置信度最高的
        """
        # 按位置分组
        position_groups = defaultdict(list)
        for rule in rules:
            position = rule['position']
            position_groups[position].append(rule)
        
        filtered = []
        
        for position, group in position_groups.items():
            if len(group) == 1:
                # 只有一条规则，直接保留
                filtered.extend(group)
            else:
                # 多条规则，需要互斥判断
                # 按置信度和优先级排序
                sorted_group = sorted(
                    group, 
                    key=lambda x: (x['confidence'], x['priority']), 
                    reverse=True
                )
                
                # 检查是否有互斥关系
                selected = []
                for i, rule in enumerate(sorted_group):
                    is_mutex = False
                    
                    # 检查与已选择的规则是否互斥
                    for selected_rule in selected:
                        if self._is_mutex(rule, selected_rule):
                            is_mutex = True
                            break
                    
                    if not is_mutex:
                        selected.append(rule)
                    # 如果互斥，跳过该规则（不添加到selected中）
                
                # 如果同一位置有多个规则，且存在互斥，只保留置信度最高的一个
                if len(selected) > 1:
                    # 检查selected中是否有互斥的规则
                    has_mutex_in_selected = False
                    for i, rule1 in enumerate(selected):
                        for j, rule2 in enumerate(selected):
                            if i != j and self._is_mutex(rule1, rule2):
                                has_mutex_in_selected = True
                                break
                        if has_mutex_in_selected:
                            break
                    
                    # 如果存在互斥，只保留置信度最高的一个
                    if has_mutex_in_selected:
                        selected = [sorted_group[0]]  # 只保留置信度最高的
                
                filtered.extend(selected)
        
        return filtered
    
    def _is_mutex(self, rule1: Dict, rule2: Dict) -> bool:
        """
        判断两条规则是否互斥（增强版：增加语义互斥检查）
        
        互斥条件：
        1. 同一位置
        2. 不同的特征描述（一个正面，一个负面）
        3. 语义互斥（interpretation字段中的语义互斥）
        """
        if rule1['position'] != rule2['position']:
            return False
        
        # 特征层面的互斥关键词对
        feature_mutex_pairs = [
            (['饱满', '明润', '开阔', '高起', '挺直'], ['凹陷', '暗沉', '狭窄', '低陷', '弯曲']),
            (['宽阔', '长'], ['窄小', '短']),
            (['圆润', '有肉'], ['尖薄', '削瘦']),
            (['红润', '光泽'], ['暗淡', '发黑']),
            (['得志', '顺利', '有成'], ['不利', '辛苦', '波折']),
            # 六亲宫位特征互斥
            (['眉毛浓密顺长', '眉间距宽'], ['眉毛稀疏散乱']),
            (['光洁饱满无纹'], ['鱼尾纹多且深', '有痣或疤', '色泽暗淡']),
            (['卧蚕饱满', '色泽明润'], ['眼袋深重', '有痣或纹']),
            (['饱满有肉'], ['削瘦凹陷']),
        ]
        
        feature1 = rule1['feature']
        feature2 = rule2['feature']
        
        # 检查特征层面的互斥
        for positive_keywords, negative_keywords in feature_mutex_pairs:
            has_positive_1 = any(kw in feature1 for kw in positive_keywords)
            has_negative_1 = any(kw in feature1 for kw in negative_keywords)
            has_positive_2 = any(kw in feature2 for kw in positive_keywords)
            has_negative_2 = any(kw in feature2 for kw in negative_keywords)
            
            # 如果一个是正面，一个是负面，则互斥
            if (has_positive_1 and has_negative_2) or (has_negative_1 and has_positive_2):
                return True
        
        # 语义层面的互斥检查（检查interpretation字段）
        interpretation1 = rule1.get('interpretation', '')
        interpretation2 = rule2.get('interpretation', '')
        
        # 定义语义互斥对（涵盖所有宫位）
        semantic_mutex_pairs = [
            # 兄弟宫语义互斥
            (['情深', '和睦', '互相帮助', '手足和睦'], ['缘薄', '少有往来', '各自为政']),
            # 夫妻宫语义互斥
            (['美满', '恩爱', '稳定长久'], ['波折', '冷淡', '需经营', '需加强沟通', '坎坷', '桃花劫']),
            # 子女宫语义互斥
            (['运佳', '满堂', '孝顺', '有出息', '健康聪明', '贵子'], ['缘薄', '不听话', '操心', '需注意', '有波折']),
            # 奴仆宫语义互斥
            (['得力', '真诚', '人缘好', '得人助'], ['不力', '朋友少', '需亲力亲为']),
            # 十神定位语义互斥
            (['得位', '有成', '旺盛', '有力', '得位'], ['受制', '不足', '受阻', '需提升', '需谨慎']),
        ]
        
        # 检查语义互斥
        for positive_keywords, negative_keywords in semantic_mutex_pairs:
            has_positive_1 = any(kw in interpretation1 for kw in positive_keywords)
            has_negative_1 = any(kw in interpretation1 for kw in negative_keywords)
            has_positive_2 = any(kw in interpretation2 for kw in positive_keywords)
            has_negative_2 = any(kw in interpretation2 for kw in negative_keywords)
            
            # 如果一个是正面语义，一个是负面语义，则互斥
            if (has_positive_1 and has_negative_2) or (has_negative_1 and has_positive_2):
                return True
        
        return False
    
    def _merge_duplicate_rules(self, rules: List[Dict]) -> List[Dict]:
        """
        合并重复规则
        
        逻辑：同一位置，合并所有断语（去重）
        """
        # 按位置分组（不再按category分组，避免重复）
        groups = defaultdict(list)
        
        for rule in rules:
            position = rule['position']
            groups[position].append(rule)
        
        merged = []
        
        for position, group in groups.items():
            # 收集所有断语，去重
            interpretations_set = set()  # 用于去重
            interpretations_list = []  # 保持顺序
            features_seen = set()
            categories = set()
            
            # 按置信度和优先级排序
            sorted_group = sorted(
                group,
                key=lambda x: (x['confidence'], x['priority']),
                reverse=True
            )
            
            for rule in sorted_group:
                interpretation = rule['interpretation']
                feature = rule['feature']
                category = rule['category']
                
                # 收集分类
                categories.add(category)
                
                # 去重：相同断语只保留一次
                if interpretation in interpretations_set:
                    continue
                
                # 检查与已添加的断语是否互斥
                is_mutex_with_existing = False
                for existing_interp in interpretations_list:
                    # 创建临时规则用于互斥检查
                    temp_rule1 = {
                        'position': position,
                        'feature': feature,
                        'interpretation': interpretation
                    }
                    temp_rule2 = {
                        'position': position,
                        'feature': '',  # 使用空字符串，主要检查interpretation
                        'interpretation': existing_interp
                    }
                    # 查找原始规则以获取完整的feature信息
                    for orig_rule in sorted_group:
                        if orig_rule['interpretation'] == existing_interp:
                            temp_rule2['feature'] = orig_rule['feature']
                            break
                    
                    if self._is_mutex(temp_rule1, temp_rule2):
                        is_mutex_with_existing = True
                        break
                
                # 如果与已添加的断语互斥，跳过（保留置信度更高的）
                if is_mutex_with_existing:
                    continue
                
                # 添加断语
                interpretations_list.append(interpretation)
                interpretations_set.add(interpretation)
                features_seen.add(feature)
            
            # 创建合并后的规则（每个位置只有一条）
            merged_rule = {
                'position': position,
                'category': '、'.join(sorted(categories)) if categories else '综合',  # 合并所有分类
                'interpretations': interpretations_list,
                'priority': max(r['priority'] for r in group),
                'confidence': max(r['confidence'] for r in group)
            }
            
            merged.append(merged_rule)
        
        # 按优先级排序
        merged.sort(key=lambda x: x['priority'], reverse=True)
        
        return merged
    
    def format_result(self, matched_rules: List[Dict]) -> Dict:
        """
        格式化输出结果
        
        按位置分组，便于前端展示
        """
        result = defaultdict(lambda: {
            'position': '',
            'analyses': []
        })
        
        for rule in matched_rules:
            position = rule['position']
            
            if not result[position]['position']:
                result[position]['position'] = position
            
            result[position]['analyses'].append({
                'category': rule['category'],
                'interpretations': rule['interpretations'] if isinstance(rule['interpretations'], list) else [rule['interpretations']],
                'confidence': rule['confidence']
            })
        
        return dict(result)

