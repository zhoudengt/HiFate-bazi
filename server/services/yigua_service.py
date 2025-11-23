#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一事一卦服务 - 基于《周易》六十四卦进行占卜
类似 FateTell 的"一事一卦"功能
"""

import sys
import os
import random
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)


# 《周易》六十四卦数据
YI_JING_64_GUA = [
    {"number": 1, "name": "乾", "pinyin": "qián", "meaning": "天", "description": "元亨利贞"},
    {"number": 2, "name": "坤", "pinyin": "kūn", "meaning": "地", "description": "元亨，利牝马之贞"},
    {"number": 3, "name": "屯", "pinyin": "zhūn", "meaning": "水雷", "description": "元亨，利贞。勿用有攸往，利建侯"},
    {"number": 4, "name": "蒙", "pinyin": "méng", "meaning": "山水", "description": "亨。匪我求童蒙，童蒙求我"},
    {"number": 5, "name": "需", "pinyin": "xū", "meaning": "水天", "description": "有孚，光亨，贞吉，利涉大川"},
    {"number": 6, "name": "讼", "pinyin": "sòng", "meaning": "天水", "description": "有孚，窒惕，中吉，终凶"},
    {"number": 7, "name": "师", "pinyin": "shī", "meaning": "地水", "description": "贞，丈人吉，无咎"},
    {"number": 8, "name": "比", "pinyin": "bǐ", "meaning": "水地", "description": "吉。原筮，元永贞，无咎"},
    {"number": 9, "name": "小畜", "pinyin": "xiǎo chù", "meaning": "风天", "description": "亨。密云不雨，自我西郊"},
    {"number": 10, "name": "履", "pinyin": "lǚ", "meaning": "天泽", "description": "履虎尾，不咥人，亨"},
    {"number": 11, "name": "泰", "pinyin": "tài", "meaning": "天地", "description": "小往大来，吉亨"},
    {"number": 12, "name": "否", "pinyin": "pǐ", "meaning": "地天", "description": "否之匪人，不利君子贞"},
    {"number": 13, "name": "同人", "pinyin": "tóng rén", "meaning": "天火", "description": "同人于野，亨。利涉大川，利君子贞"},
    {"number": 14, "name": "大有", "pinyin": "dà yǒu", "meaning": "火天", "description": "元亨"},
    {"number": 15, "name": "谦", "pinyin": "qiān", "meaning": "地山", "description": "亨，君子有终"},
    {"number": 16, "name": "豫", "pinyin": "yù", "meaning": "雷地", "description": "利建侯行师"},
    {"number": 17, "name": "随", "pinyin": "suí", "meaning": "泽雷", "description": "元亨，利贞，无咎"},
    {"number": 18, "name": "蛊", "pinyin": "gǔ", "meaning": "山风", "description": "元亨，利涉大川"},
    {"number": 19, "name": "临", "pinyin": "lín", "meaning": "地泽", "description": "元亨，利贞。至于八月有凶"},
    {"number": 20, "name": "观", "pinyin": "guān", "meaning": "风地", "description": "盥而不荐，有孚颙若"},
    {"number": 21, "name": "噬嗑", "pinyin": "shì kè", "meaning": "火雷", "description": "亨。利用狱"},
    {"number": 22, "name": "贲", "pinyin": "bì", "meaning": "山火", "description": "亨。小利有攸往"},
    {"number": 23, "name": "剥", "pinyin": "bō", "meaning": "山地", "description": "不利有攸往"},
    {"number": 24, "name": "复", "pinyin": "fù", "meaning": "地雷", "description": "亨。出入无疾，朋来无咎"},
    {"number": 25, "name": "无妄", "pinyin": "wú wàng", "meaning": "天雷", "description": "元亨，利贞"},
    {"number": 26, "name": "大畜", "pinyin": "dà chù", "meaning": "山天", "description": "利贞，不家食吉，利涉大川"},
    {"number": 27, "name": "颐", "pinyin": "yí", "meaning": "山雷", "description": "贞吉。观颐，自求口实"},
    {"number": 28, "name": "大过", "pinyin": "dà guò", "meaning": "泽风", "description": "栋桡，利有攸往，亨"},
    {"number": 29, "name": "坎", "pinyin": "kǎn", "meaning": "水", "description": "有孚，维心亨，行有尚"},
    {"number": 30, "name": "离", "pinyin": "lí", "meaning": "火", "description": "利贞，亨。畜牝牛，吉"},
    {"number": 31, "name": "咸", "pinyin": "xián", "meaning": "泽山", "description": "亨，利贞，取女吉"},
    {"number": 32, "name": "恒", "pinyin": "héng", "meaning": "雷风", "description": "亨，无咎，利贞，利有攸往"},
    {"number": 33, "name": "遁", "pinyin": "dùn", "meaning": "天山", "description": "亨，小利贞"},
    {"number": 34, "name": "大壮", "pinyin": "dà zhuàng", "meaning": "雷天", "description": "利贞"},
    {"number": 35, "name": "晋", "pinyin": "jìn", "meaning": "火地", "description": "康侯用锡马蕃庶，昼日三接"},
    {"number": 36, "name": "明夷", "pinyin": "míng yí", "meaning": "地火", "description": "利艰贞"},
    {"number": 37, "name": "家人", "pinyin": "jiā rén", "meaning": "风火", "description": "利女贞"},
    {"number": 38, "name": "睽", "pinyin": "kuí", "meaning": "火泽", "description": "小事吉"},
    {"number": 39, "name": "蹇", "pinyin": "jiǎn", "meaning": "水山", "description": "利西南，不利东北；利见大人，贞吉"},
    {"number": 40, "name": "解", "pinyin": "jiě", "meaning": "雷水", "description": "利西南，无所往，其来复吉"},
    {"number": 41, "name": "损", "pinyin": "sǔn", "meaning": "山泽", "description": "有孚，元吉，无咎，可贞，利有攸往"},
    {"number": 42, "name": "益", "pinyin": "yì", "meaning": "风雷", "description": "利有攸往，利涉大川"},
    {"number": 43, "name": "夬", "pinyin": "guài", "meaning": "泽天", "description": "扬于王庭，孚号，有厉，告自邑"},
    {"number": 44, "name": "姤", "pinyin": "gòu", "meaning": "天风", "description": "女壮，勿用取女"},
    {"number": 45, "name": "萃", "pinyin": "cuì", "meaning": "泽地", "description": "亨。王假有庙，利见大人，亨，利贞"},
    {"number": 46, "name": "升", "pinyin": "shēng", "meaning": "地风", "description": "元亨，用见大人，勿恤，南征吉"},
    {"number": 47, "name": "困", "pinyin": "kùn", "meaning": "泽水", "description": "亨，贞，大人吉，无咎"},
    {"number": 48, "name": "井", "pinyin": "jǐng", "meaning": "水风", "description": "改邑不改井，无丧无得"},
    {"number": 49, "name": "革", "pinyin": "gé", "meaning": "泽火", "description": "己日乃孚，元亨，利贞，悔亡"},
    {"number": 50, "name": "鼎", "pinyin": "dǐng", "meaning": "火风", "description": "元吉，亨"},
    {"number": 51, "name": "震", "pinyin": "zhèn", "meaning": "雷", "description": "亨。震来虩虩，笑言哑哑"},
    {"number": 52, "name": "艮", "pinyin": "gèn", "meaning": "山", "description": "艮其背，不获其身，行其庭，不见其人"},
    {"number": 53, "name": "渐", "pinyin": "jiàn", "meaning": "风山", "description": "女归吉，利贞"},
    {"number": 54, "name": "归妹", "pinyin": "guī mèi", "meaning": "雷泽", "description": "征凶，无攸利"},
    {"number": 55, "name": "丰", "pinyin": "fēng", "meaning": "雷火", "description": "亨，王假之，勿忧，宜日中"},
    {"number": 56, "name": "旅", "pinyin": "lǚ", "meaning": "火山", "description": "小亨，旅贞吉"},
    {"number": 57, "name": "巽", "pinyin": "xùn", "meaning": "风", "description": "小亨，利有攸往，利见大人"},
    {"number": 58, "name": "兑", "pinyin": "duì", "meaning": "泽", "description": "亨，利贞"},
    {"number": 59, "name": "涣", "pinyin": "huàn", "meaning": "风水", "description": "亨。王假有庙，利涉大川，利贞"},
    {"number": 60, "name": "节", "pinyin": "jié", "meaning": "水泽", "description": "亨。苦节不可贞"},
    {"number": 61, "name": "中孚", "pinyin": "zhōng fú", "meaning": "风泽", "description": "豚鱼吉，利涉大川，利贞"},
    {"number": 62, "name": "小过", "pinyin": "xiǎo guò", "meaning": "雷山", "description": "亨，利贞，可小事，不可大事"},
    {"number": 63, "name": "既济", "pinyin": "jì jì", "meaning": "水火", "description": "亨，小利贞，初吉终乱"},
    {"number": 64, "name": "未济", "pinyin": "wèi jì", "meaning": "火水", "description": "亨。小狐汔济，濡其尾，无攸利"},
]


class YiGuaService:
    """一事一卦服务"""
    
    @staticmethod
    def _generate_gua_number(question: str, timestamp: Optional[datetime] = None) -> int:
        """
        根据问题和时间生成卦数（1-64）
        使用确定性算法，相同输入产生相同输出
        
        Args:
            question: 用户问题
            timestamp: 时间戳（可选，用于增加随机性）
            
        Returns:
            int: 卦数（1-64）
        """
        # 使用问题的哈希值作为种子
        seed = hash(question)
        if timestamp:
            # 如果提供时间戳，加入时间因素
            seed += int(timestamp.timestamp())
        
        # 确保是正数
        seed = abs(seed)
        
        # 生成 1-64 的卦数
        gua_number = (seed % 64) + 1
        return gua_number
    
    @staticmethod
    def _get_gua_info(gua_number: int) -> Dict[str, Any]:
        """获取卦的信息"""
        if 1 <= gua_number <= 64:
            return YI_JING_64_GUA[gua_number - 1]
        return None
    
    @staticmethod
    def _generate_interpretation(gua_info: Dict[str, Any], question: str) -> str:
        """
        生成卦的解读（简化版，实际可以使用 LLM 生成更详细的解读）
        
        Args:
            gua_info: 卦的信息
            question: 用户问题
            
        Returns:
            str: 解读文本
        """
        lines = []
        lines.append(f"【卦象】{gua_info['name']}卦（{gua_info['pinyin']}）")
        lines.append(f"【卦数】第{gua_info['number']}卦")
        lines.append(f"【卦象含义】{gua_info['meaning']}")
        lines.append(f"【卦辞】{gua_info['description']}")
        lines.append("")
        lines.append("【解读】")
        lines.append(f"根据您的问题「{question}」，抽得{gua_info['name']}卦。")
        lines.append(f"此卦象为{gua_info['meaning']}，卦辞为「{gua_info['description']}」。")
        lines.append("")
        lines.append("【建议】")
        
        # 根据卦的吉凶给出建议（简化版）
        if gua_info['number'] in [1, 2, 11, 15, 19, 24, 25, 26, 27, 30, 32, 35, 42, 45, 46, 50, 55, 57, 58, 59, 61]:
            lines.append("此卦较为吉利，建议积极行动，把握时机。")
        elif gua_info['number'] in [6, 12, 23, 29, 36, 39, 47, 54, 60, 64]:
            lines.append("此卦需要谨慎，建议三思而后行，避免冲动。")
        else:
            lines.append("此卦中性，建议保持平衡，顺势而为。")
        
        lines.append("")
        lines.append("【注意事项】")
        lines.append("以上解读仅供参考，具体决策还需结合实际情况。")
        lines.append("占卜结果不应作为唯一依据，理性思考更为重要。")
        
        return "\n".join(lines)
    
    @staticmethod
    def divinate(question: str, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """
        占卜（一事一卦）
        
        Args:
            question: 用户问题
            timestamp: 时间戳（可选）
            
        Returns:
            dict: 包含卦的信息和解读
        """
        if not question or not question.strip():
            return {
                "success": False,
                "error": "问题不能为空",
                "gua": None,
                "interpretation": None
            }
        
        try:
            # 生成卦数
            gua_number = YiGuaService._generate_gua_number(question, timestamp)
            
            # 获取卦的信息
            gua_info = YiGuaService._get_gua_info(gua_number)
            if not gua_info:
                return {
                    "success": False,
                    "error": "获取卦信息失败",
                    "gua": None,
                    "interpretation": None
                }
            
            # 生成解读
            interpretation = YiGuaService._generate_interpretation(gua_info, question)
            
            return {
                "success": True,
                "question": question,
                "gua": {
                    "number": gua_info["number"],
                    "name": gua_info["name"],
                    "pinyin": gua_info["pinyin"],
                    "meaning": gua_info["meaning"],
                    "description": gua_info["description"]
                },
                "interpretation": interpretation,
                "timestamp": (timestamp or datetime.now()).isoformat()
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"占卜异常: {str(e)}\n{traceback.format_exc()}",
                "gua": None,
                "interpretation": None
            }
    
    @staticmethod
    def get_all_gua_list() -> Dict[str, Any]:
        """获取所有六十四卦列表"""
        return {
            "success": True,
            "total": 64,
            "gua_list": YI_JING_64_GUA
        }

