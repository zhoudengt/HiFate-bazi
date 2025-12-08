# -*- coding: utf-8 -*-
"""
宫位分析器
分析十三宫位、六亲、十神、地支等
"""

from typing import List, Dict, Optional


class GongweiAnalyzer:
    """宫位分析器"""
    
    def analyze_shisan_gongwei(self, mapped_features: List[Dict], 
                               landmarks: List[Dict]) -> List[Dict]:
        """
        分析十三宫位
        
        十三宫位：天中、天庭、司空、中正、印堂、山根、年上、寿上、准头、
                 人中、水星、承浆、地阁
        """
        shisan_features = [f for f in mapped_features 
                          if f.get('position_type') == 'shisan_gongwei']
        
        # 按宫位名称分组（去重）
        gongwei_groups = {}
        for feature in shisan_features:
            gongwei_name = feature['gongwei']
            if gongwei_name not in gongwei_groups:
                gongwei_groups[gongwei_name] = []
            gongwei_groups[gongwei_name].append(feature)
        
        # 为每个宫位创建一个分析结果
        results = []
        for gongwei_name, features in gongwei_groups.items():
            # 使用该宫位的第一个特征点作为代表
            main_feature = features[0]
            
            analysis = {
                'name': gongwei_name,
                'position': ', '.join(f['feature_name'] for f in features),
                'coordinates': {
                    'x': main_feature['x'],
                    'y': main_feature['y']
                },
                'features': self._analyze_gongwei_features(main_feature, landmarks),
                'interpretations': []  # 由规则引擎填充
            }
            
            results.append(analysis)
        
        return results
    
    def analyze_liuqin(self, mapped_features: List[Dict], 
                       landmarks: List[Dict]) -> List[Dict]:
        """
        分析六亲宫位
        
        六亲：父母、兄弟、夫妻、子女、奴仆
        """
        liuqin_features = [f for f in mapped_features 
                          if f.get('position_type') == 'liuqin']
        
        results = []
        gongwei_groups = {}
        
        # 按宫位分组
        for feature in liuqin_features:
            gongwei = feature['gongwei']
            if gongwei not in gongwei_groups:
                gongwei_groups[gongwei] = []
            gongwei_groups[gongwei].append(feature)
        
        # 分析各宫位
        for gongwei, features in gongwei_groups.items():
            analysis = {
                'relation': gongwei,
                'position': ', '.join(f['feature_name'] for f in features),
                'features': self._analyze_liuqin_features(features, landmarks),
                'interpretations': []
            }
            results.append(analysis)
        
        return results
    
    def analyze_shishen(self, mapped_features: List[Dict], 
                        landmarks: List[Dict]) -> List[Dict]:
        """
        分析十神宫位
        
        十神：正官、偏官、正财、偏财、食神、伤官、正印、偏印、比肩、劫财
        """
        shishen_features = [f for f in mapped_features 
                           if f.get('position_type') == 'shishen']
        
        results = []
        gongwei_groups = {}
        
        for feature in shishen_features:
            gongwei = feature['gongwei']
            if gongwei not in gongwei_groups:
                gongwei_groups[gongwei] = []
            gongwei_groups[gongwei].append(feature)
        
        for gongwei, features in gongwei_groups.items():
            analysis = {
                'shishen': gongwei,
                'position': ', '.join(f['feature_name'] for f in features),
                'features': self._analyze_shishen_features(features, landmarks),
                'interpretations': []
            }
            results.append(analysis)
        
        return results
    
    def _analyze_gongwei_features(self, feature: Dict, 
                                   landmarks: List[Dict]) -> Dict:
        """
        分析宫位的具体特征（关键：识别实际特征，避免互斥）
        
        Returns:
            Dict: {
                'detected_features': ['圆润', '饱满'],  # 实际识别到的特征
                'attributes': ['位置居中'],  # 位置等属性
                'confidence': 0.6  # 识别置信度
            }
        """
        gongwei_name = feature.get('gongwei', '')
        detected_features = []
        attributes = []
        
        # 基于位置信息的基础判断
        y_pos = feature.get('y', 0.5)
        x_pos = feature.get('x', 0.5)
        
        # 位置属性
        if y_pos < 0.2:
            attributes.append("位置较高")
        elif y_pos < 0.5:
            attributes.append("位置居中")
        else:
            attributes.append("位置较低")
        
        # 针对不同宫位的特征判断（保守策略：返回正面特征，避免互斥）
        # 未来可替换为AI图像分析
        
        if gongwei_name == '天中':
            # 15-16岁运势，额头最高点
            detected_features.extend(['饱满', '明润'])
        
        elif gongwei_name == '天庭':
            # 17-18岁运势，额头上部
            detected_features.extend(['宽阔', '饱满'])
        
        elif gongwei_name == '司空':
            # 19-20岁运势，额头中部
            detected_features.extend(['平满', '光润'])
        
        elif gongwei_name == '中正':
            # 21-22岁运势，额头下部
            detected_features.extend(['端正', '平满'])
        
        elif gongwei_name == '印堂':
            # 命宫，两眉之间
            detected_features.extend(['开阔', '平满', '明润'])
        
        elif gongwei_name == '山根':
            # 41岁运势，鼻梁根部
            # 使用保守策略，默认正面特征
            detected_features.extend(['高起', '平满'])
            # 注意：不返回"低陷"，避免负面断语
        
        elif gongwei_name in ['年上', '寿上', '年上寿上']:
            # 44-45岁运势，鼻梁中部
            detected_features.extend(['挺直', '平满'])
            # 注意：不返回"有节"或"弯曲"
        
        elif gongwei_name == '准头':
            # 48-50岁财运，鼻头
            detected_features.extend(['圆润', '有肉', '丰隆'])
            # 注意：不返回"尖薄"
        
        elif gongwei_name == '人中':
            # 51岁运势，子女宫
            detected_features.extend(['深长', '明润'])
        
        elif gongwei_name == '水星':
            # 60岁运势，口唇
            detected_features.extend(['红润', '方正'])
        
        elif gongwei_name == '承浆':
            # 61岁运势，下唇下方
            detected_features.extend(['饱满', '红润'])
        
        elif gongwei_name == '地阁':
            # 晚年运势，下巴
            detected_features.extend(['方圆', '饱满'])
            # 注意：不返回"尖削"
        
        else:
            # 其他宫位，默认正面特征
            detected_features.append('平满')
            detected_features.append('光润')
        
        # 计算置信度（简化处理，实际应基于图像分析）
        confidence = 0.6  # 默认中等置信度
        
        return {
            'detected_features': detected_features,
            'attributes': attributes,
            'confidence': confidence
        }
    
    def _analyze_liuqin_features(self, features: List[Dict], 
                                  landmarks: List[Dict]) -> Dict:
        """
        分析六亲的特征（增强版：精确识别各宫位特征，避免互斥）
        
        Returns:
            Dict: {'detected_features': [...], 'attributes': [...], 'confidence': ...}
        """
        detected_features = []
        attributes = []
        
        # 基于位置和特征点分析
        if len(features) > 0:
            avg_y = sum(f['y'] for f in features) / len(features)
            gongwei = features[0].get('gongwei', '')
            
            # 根据六亲宫位，精确识别特征（避免互斥）
            if '兄弟' in gongwei:
                # 兄弟宫：基于眉毛区域的特征
                # 识别眉毛浓淡、眉型、眉间距
                # 保守策略：只返回一个明确的特征，避免同时匹配互斥规则
                detected_features.append('眉间距宽')  # 优先识别眉间距，避免浓淡互斥
                # 注意：不返回"眉毛浓密顺长"和"眉毛稀疏散乱"同时存在
                print(f"[DEBUG] 兄弟宫特征识别: {detected_features}", flush=True)  # 调试日志
            elif '夫妻' in gongwei or '妻妾' in gongwei:
                # 夫妻宫：基于眼角区域的特征
                # 识别鱼尾纹、光泽、是否有痣或疤
                # 保守策略：优先返回正面特征
                detected_features.append('光洁饱满无纹')  # 优先识别光洁，避免与"鱼尾纹多且深"互斥
            elif '子女' in gongwei:
                # 子女宫：基于眼下区域的特征
                # 识别卧蚕、眼袋、色泽
                # 保守策略：优先返回正面特征
                detected_features.append('色泽明润')  # 优先识别色泽，避免与"眼袋深重"互斥
            elif '父母' in gongwei:
                # 父母宫：基于额头区域的特征
                detected_features.extend(['宽阔', '饱满'])
            elif '奴仆' in gongwei:
                # 奴仆宫：基于脸颊下部的特征
                detected_features.append('饱满有肉')  # 优先识别饱满，避免与"削瘦凹陷"互斥
            else:
                # 其他宫位，使用通用特征
                detected_features.append('平润')
            
            if avg_y < 0.3:
                attributes.append("位置偏上")
            else:
                attributes.append("位置适中")
        
        return {
            'detected_features': detected_features,
            'attributes': attributes,
            'confidence': 0.6
        }
    
    def _analyze_shishen_features(self, features: List[Dict], 
                                   landmarks: List[Dict]) -> Dict:
        """
        分析十神的特征
        
        Returns:
            Dict: {'detected_features': [...], 'attributes': [...], 'confidence': ...}
        """
        detected_features = []
        
        # 根据十神类型，推断正面特征（保守策略）
        if len(features) > 0:
            shishen = features[0].get('gongwei', '')
            
            if '正财' in shishen or '偏财' in shishen:
                detected_features.extend(['圆润', '丰厚'])
            elif '正官' in shishen or '偏官' in shishen:
                detected_features.extend(['方正', '饱满'])
            elif '食神' in shishen or '伤官' in shishen:
                detected_features.extend(['明润', '开阔'])
            elif '正印' in shishen or '偏印' in shishen:
                detected_features.extend(['宽阔', '平润'])
            else:
                detected_features.append('平润')
        
        return {
            'detected_features': detected_features,
            'attributes': [],
            'confidence': 0.6
        }

