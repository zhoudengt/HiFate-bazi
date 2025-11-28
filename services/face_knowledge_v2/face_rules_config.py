# -*- coding: utf-8 -*-
"""
面相规则配置 - 内置规则数据
注意：不再从外部 JSON 文件读取，所有规则数据固化在此文件中
"""

# 十三宫位规则
GONGWEI_RULES = [
    {
        "rule_type": "gongwei", "position": "天中", "position_code": "tianchong",
        "conditions": {"region": "forehead_top", "features": ["饱满", "平润", "光洁"]},
        "interpretations": [
            {"feature": "饱满明润", "interpretation": "早年得志，15-16岁学业顺利，智慧聪颖", "category": "事业"},
            {"feature": "凹陷暗沉", "interpretation": "早年不利，家境一般，需靠自己奋斗", "category": "事业"}
        ],
        "priority": 80
    },
    {
        "rule_type": "gongwei", "position": "天庭", "position_code": "tinting",
        "conditions": {"region": "forehead_upper", "features": ["宽阔", "饱满", "光泽"]},
        "interpretations": [
            {"feature": "宽阔饱满", "interpretation": "聪明智慧，17-18岁学业有成，家庭背景好", "category": "性格"},
            {"feature": "窄小凹陷", "interpretation": "少年辛苦，需后天努力，家境普通", "category": "性格"}
        ],
        "priority": 85
    },
    {
        "rule_type": "gongwei", "position": "司空", "position_code": "sikong",
        "conditions": {"region": "forehead_middle", "features": ["平满", "光润"]},
        "interpretations": [
            {"feature": "平满光润", "interpretation": "19-20岁运势佳，求学顺利，有贵人相助", "category": "事业"},
            {"feature": "有疤痕或凹陷", "interpretation": "此年运势波折，需谨慎行事", "category": "事业"}
        ],
        "priority": 75
    },
    {
        "rule_type": "gongwei", "position": "中正", "position_code": "zhongzheng",
        "conditions": {"region": "forehead_lower", "features": ["端正", "平满"]},
        "interpretations": [
            {"feature": "端正平满", "interpretation": "21-22岁事业起步顺利，为人正直", "category": "性格"}
        ],
        "priority": 75
    },
    {
        "rule_type": "gongwei", "position": "印堂", "position_code": "yintang",
        "conditions": {"region": "between_eyebrows", "features": ["开阔", "平满", "明润", "颜色"]},
        "interpretations": [
            {"feature": "开阔平满", "interpretation": "命宫开阔，28岁运势极佳，一生顺遂，心胸宽广", "category": "综合"},
            {"feature": "狭窄或有竖纹", "interpretation": "心胸较窄，易钻牛角尖，运势起伏", "category": "性格"},
            {"feature": "印堂发黑", "interpretation": "近期运势不佳，需注意健康和安全", "category": "健康"},
            {"feature": "印堂红润", "interpretation": "近期有喜事，运势上扬", "category": "财运"}
        ],
        "priority": 100
    },
    {
        "rule_type": "gongwei", "position": "山根", "position_code": "shangen",
        "conditions": {"region": "nose_bridge_root", "features": ["高低", "宽窄", "有无断节"]},
        "interpretations": [
            {"feature": "山根高起", "interpretation": "41岁运势佳，身体健康，事业稳固", "category": "健康"},
            {"feature": "山根低陷", "interpretation": "41岁需注意健康，运势有波折", "category": "健康"},
            {"feature": "山根有横纹", "interpretation": "中年易有变动，需谨慎理财", "category": "财运"}
        ],
        "priority": 80
    },
    {
        "rule_type": "gongwei", "position": "年上寿上", "position_code": "nianshang_shoushang",
        "conditions": {"region": "nose_bridge_middle", "features": ["挺直", "有无节"]},
        "interpretations": [
            {"feature": "挺直无节", "interpretation": "44-45岁运势平稳，身体健康", "category": "健康"},
            {"feature": "有节或弯曲", "interpretation": "中年运势波折，需注意健康", "category": "健康"}
        ],
        "priority": 70
    },
    {
        "rule_type": "gongwei", "position": "准头", "position_code": "zhuntou",
        "conditions": {"region": "nose_tip", "features": ["大小", "形状", "肉质", "颜色"]},
        "interpretations": [
            {"feature": "鼻头圆润有肉", "interpretation": "48-50岁财运极佳，一生财运亨通，善于聚财", "category": "财运"},
            {"feature": "鼻头尖薄", "interpretation": "财运平平，不易聚财，需节俭持家", "category": "财运"},
            {"feature": "鼻头有痣", "interpretation": "财运有波折，注意破财", "category": "财运"},
            {"feature": "鼻头红润", "interpretation": "近期财运佳，有进财机会", "category": "财运"}
        ],
        "priority": 95
    },
    {
        "rule_type": "gongwei", "position": "人中", "position_code": "renzhong",
        "conditions": {"region": "philtrum", "features": ["深浅", "长短", "宽窄"]},
        "interpretations": [
            {"feature": "人中深长", "interpretation": "51岁运势佳，子女孝顺，长寿健康", "category": "健康"},
            {"feature": "人中短浅", "interpretation": "子女缘薄，需注意生殖系统健康", "category": "健康"}
        ],
        "priority": 75
    },
    {
        "rule_type": "gongwei", "position": "水星", "position_code": "shuixing",
        "conditions": {"region": "mouth", "features": ["嘴型", "唇色", "大小"]},
        "interpretations": [
            {"feature": "嘴唇红润饱满", "interpretation": "60岁运势佳，口福好，晚年安康", "category": "健康"},
            {"feature": "嘴唇薄且色淡", "interpretation": "口才佳但情感波折，需注意脾胃", "category": "健康"}
        ],
        "priority": 70
    },
    {
        "rule_type": "gongwei", "position": "承浆", "position_code": "chengjiang",
        "conditions": {"region": "below_lower_lip", "features": ["饱满", "凹陷"]},
        "interpretations": [
            {"feature": "饱满有肉", "interpretation": "61岁运势平稳，子孙满堂", "category": "健康"}
        ],
        "priority": 65
    },
    {
        "rule_type": "gongwei", "position": "地阁", "position_code": "dige",
        "conditions": {"region": "chin", "features": ["饱满", "方圆", "双下巴"]},
        "interpretations": [
            {"feature": "地阁方圆饱满", "interpretation": "晚年运势极佳，福禄双全，子孙孝顺，有房有产", "category": "财运"},
            {"feature": "地阁尖削", "interpretation": "晚年孤独，需提前规划养老", "category": "财运"},
            {"feature": "双下巴", "interpretation": "晚年富贵，生活安逸", "category": "财运"}
        ],
        "priority": 85
    }
]

# 99特征点断语规则
FEATURE_RULES = [
    {
        "rule_type": "feature", "position": "眉毛", "position_code": "eyebrows",
        "conditions": {"features": ["眉型", "眉毛浓淡", "眉长", "眉尾"]},
        "interpretations": [
            {"feature": "眉毛浓黑顺长", "interpretation": "性格刚毅，有主见，兄弟运佳，事业心强", "category": "性格"},
            {"feature": "眉毛稀疏淡薄", "interpretation": "性格温和，但意志力较弱，需要鼓励", "category": "性格"},
            {"feature": "一字眉", "interpretation": "性格直爽，不拐弯抹角，讲义气", "category": "性格"},
            {"feature": "柳叶眉", "interpretation": "温柔贤淑，性格柔和，人缘好", "category": "性格"},
            {"feature": "剑眉", "interpretation": "英气逼人，有魄力，适合领导岗位", "category": "事业"},
            {"feature": "八字眉", "interpretation": "性格忧郁，容易想太多，需调整心态", "category": "性格"},
            {"feature": "眉尾上扬", "interpretation": "性格积极向上，有进取心", "category": "性格"},
            {"feature": "眉尾下垂", "interpretation": "性格较为消极，需要激励", "category": "性格"}
        ],
        "priority": 80
    },
    {
        "rule_type": "feature", "position": "眼睛", "position_code": "eyes",
        "conditions": {"features": ["眼型", "眼睛大小", "眼神", "眼距"]},
        "interpretations": [
            {"feature": "眼睛大而有神", "interpretation": "聪明伶俐，观察力强，有艺术天赋", "category": "性格"},
            {"feature": "眼睛小而精明", "interpretation": "心思细腻，谨慎小心，理财有道", "category": "性格"},
            {"feature": "丹凤眼", "interpretation": "智慧过人，有领导才能，桃花运旺", "category": "性格"},
            {"feature": "桃花眼", "interpretation": "异性缘好，魅力十足，但需慎重感情", "category": "婚姻"},
            {"feature": "眼距宽", "interpretation": "心胸开阔，性格大度，不计小事", "category": "性格"},
            {"feature": "眼距窄", "interpretation": "做事专注，但容易钻牛角尖", "category": "性格"},
            {"feature": "眼神清澈", "interpretation": "心地善良，为人正直，没有心机", "category": "性格"},
            {"feature": "眼神游移", "interpretation": "心思不定，需培养专注力", "category": "性格"}
        ],
        "priority": 85
    },
    {
        "rule_type": "feature", "position": "鼻子", "position_code": "nose",
        "conditions": {"features": ["鼻型", "鼻梁高低", "鼻头大小", "鼻翼"]},
        "interpretations": [
            {"feature": "鼻梁挺直", "interpretation": "性格正直，有原则，事业运佳", "category": "事业"},
            {"feature": "鼻梁塌陷", "interpretation": "性格随和，但缺乏主见，需培养自信", "category": "性格"},
            {"feature": "鹰钩鼻", "interpretation": "精明能干，善于计算，但需注意人际关系", "category": "性格"},
            {"feature": "狮子鼻", "interpretation": "财运亨通，有领导力，事业有成", "category": "财运"},
            {"feature": "鼻孔外露", "interpretation": "花钱大手大脚，不善理财，需节制", "category": "财运"}
        ],
        "priority": 90
    },
    {
        "rule_type": "feature", "position": "嘴巴", "position_code": "mouth",
        "conditions": {"features": ["嘴型", "唇厚薄", "嘴大小"]},
        "interpretations": [
            {"feature": "嘴大唇厚", "interpretation": "口福好，性格豪爽，交际能力强", "category": "性格"},
            {"feature": "樱桃小口", "interpretation": "说话谨慎，秀气端庄，但需加强表达", "category": "性格"},
            {"feature": "上唇厚", "interpretation": "重感情，对人真诚", "category": "性格"},
            {"feature": "下唇厚", "interpretation": "物欲较强，享受生活", "category": "性格"}
        ],
        "priority": 75
    },
    {
        "rule_type": "feature", "position": "耳朵", "position_code": "ears",
        "conditions": {"features": ["耳型", "耳垂", "耳位高低"]},
        "interpretations": [
            {"feature": "耳垂厚大", "interpretation": "福气深厚，晚年安康，有财运", "category": "财运"},
            {"feature": "耳位高于眉", "interpretation": "智慧聪颖，学习能力强", "category": "事业"},
            {"feature": "招风耳", "interpretation": "性格独立，有主见，但较固执", "category": "性格"}
        ],
        "priority": 70
    },
    {
        "rule_type": "feature", "position": "脸型", "position_code": "face_shape",
        "conditions": {"features": ["脸型分类"]},
        "interpretations": [
            {"feature": "国字脸", "interpretation": "性格稳重，有领导能力，事业运佳", "category": "事业"},
            {"feature": "瓜子脸", "interpretation": "聪明伶俐，有艺术气质，人缘好", "category": "性格"},
            {"feature": "圆脸", "interpretation": "性格随和，福气好，人际关系佳", "category": "性格"},
            {"feature": "长脸", "interpretation": "思虑周密，有耐心，适合研究工作", "category": "事业"},
            {"feature": "倒三角脸", "interpretation": "聪明但体力较弱，需注意健康", "category": "健康"}
        ],
        "priority": 80
    }
]

# 六亲定位规则
LIUQIN_RULES = [
    {
        "rule_type": "liuqin", "position": "父母宫-父", "position_code": "father",
        "conditions": {"region": "left_forehead_upper", "features": ["气色", "饱满度", "纹路"]},
        "interpretations": [
            {"feature": "饱满明润", "interpretation": "父亲健康长寿，家境殷实，父子关系和睦", "category": "六亲"},
            {"feature": "凹陷或有痣疤", "interpretation": "与父亲缘薄，或父亲早年辛苦", "category": "六亲"}
        ],
        "priority": 70
    },
    {
        "rule_type": "liuqin", "position": "父母宫-母", "position_code": "mother",
        "conditions": {"region": "right_forehead_upper", "features": ["气色", "饱满度", "纹路"]},
        "interpretations": [
            {"feature": "饱满明润", "interpretation": "母亲健康长寿，母子关系深厚", "category": "六亲"},
            {"feature": "凹陷或有痣疤", "interpretation": "与母亲缘薄，或母亲早年辛苦", "category": "六亲"}
        ],
        "priority": 70
    },
    {
        "rule_type": "liuqin", "position": "兄弟宫", "position_code": "siblings",
        "conditions": {"region": "eyebrows", "features": ["眉毛浓淡", "眉型", "眉间距"]},
        "interpretations": [
            {"feature": "眉毛浓密顺长", "interpretation": "兄弟姐妹情深，互相帮助，手足和睦", "category": "六亲"},
            {"feature": "眉毛稀疏散乱", "interpretation": "兄弟缘薄，各自为政，少有往来", "category": "六亲"},
            {"feature": "眉间距宽", "interpretation": "兄弟宫宽阔，性格开朗，与兄弟相处融洽", "category": "性格"}
        ],
        "priority": 75
    },
    {
        "rule_type": "liuqin", "position": "夫妻宫", "position_code": "spouse",
        "conditions": {"region": "eye_corners", "features": ["鱼尾纹", "光泽", "色泽"]},
        "interpretations": [
            {"feature": "光洁饱满无纹", "interpretation": "婚姻美满，夫妻恩爱，感情稳定长久", "category": "婚姻"},
            {"feature": "鱼尾纹多且深", "interpretation": "婚姻有波折，或晚婚较好，需经营感情", "category": "婚姻"},
            {"feature": "有痣或疤", "interpretation": "感情路坎坷，易有桃花劫或感情纠纷", "category": "婚姻"},
            {"feature": "色泽暗淡", "interpretation": "夫妻关系冷淡，需加强沟通", "category": "婚姻"}
        ],
        "priority": 90
    },
    {
        "rule_type": "liuqin", "position": "子女宫", "position_code": "children",
        "conditions": {"region": "under_eyes", "features": ["卧蚕", "眼袋", "色泽"]},
        "interpretations": [
            {"feature": "卧蚕饱满", "interpretation": "子女运佳，儿孙满堂，子女孝顺有出息", "category": "六亲"},
            {"feature": "眼袋深重", "interpretation": "子女缘薄，或子女不听话，操心较多", "category": "六亲"},
            {"feature": "色泽明润", "interpretation": "子女健康聪明，有贵子相", "category": "六亲"},
            {"feature": "有痣或纹", "interpretation": "子女健康需注意，或生育有波折", "category": "健康"}
        ],
        "priority": 85
    },
    {
        "rule_type": "liuqin", "position": "奴仆宫", "position_code": "servants",
        "conditions": {"region": "lower_cheeks", "features": ["饱满度", "色泽"]},
        "interpretations": [
            {"feature": "饱满有肉", "interpretation": "下属得力，朋友真诚，人缘好，得人助", "category": "事业"},
            {"feature": "削瘦凹陷", "interpretation": "下属不力，朋友少，需亲力亲为", "category": "事业"}
        ],
        "priority": 65
    }
]

# 十神定位规则
SHISHEN_RULES = [
    {
        "rule_type": "shishen", "position": "印堂-正官", "position_code": "zhengguan",
        "conditions": {"region": "yintang", "features": ["开阔度", "光泽", "颜色"]},
        "interpretations": [
            {"feature": "印堂开阔明润", "interpretation": "正官得位，事业有成，有权威，受人尊敬", "category": "事业"},
            {"feature": "印堂狭窄暗沉", "interpretation": "正官受制，事业发展受阻，需提升能力", "category": "事业"}
        ],
        "priority": 85
    },
    {
        "rule_type": "shishen", "position": "司空-偏官", "position_code": "pianguan",
        "conditions": {"region": "sikong", "features": ["饱满度", "气色"]},
        "interpretations": [
            {"feature": "饱满有力", "interpretation": "偏官(七杀)有力，性格果断，有魄力，适合创业", "category": "性格"}
        ],
        "priority": 70
    },
    {
        "rule_type": "shishen", "position": "准头-正财", "position_code": "zhengcai",
        "conditions": {"region": "nose_tip", "features": ["大小", "肉质", "色泽"]},
        "interpretations": [
            {"feature": "鼻头圆润丰厚", "interpretation": "正财旺盛，收入稳定，善于理财，财源广进", "category": "财运"},
            {"feature": "鼻头尖薄", "interpretation": "正财不足，需开拓财源，理财需谨慎", "category": "财运"}
        ],
        "priority": 95
    },
    {
        "rule_type": "shishen", "position": "鼻翼-偏财", "position_code": "piancai",
        "conditions": {"region": "nose_wings", "features": ["饱满度", "大小"]},
        "interpretations": [
            {"feature": "鼻翼饱满外张", "interpretation": "偏财运佳，有横财运，投资眼光好，适合做生意", "category": "财运"},
            {"feature": "鼻翼窄小内收", "interpretation": "偏财运弱，不宜投机，守财为上", "category": "财运"}
        ],
        "priority": 80
    },
    {
        "rule_type": "shishen", "position": "上唇-食神", "position_code": "shishen",
        "conditions": {"region": "upper_lip", "features": ["厚薄", "形状"]},
        "interpretations": [
            {"feature": "上唇饱满有型", "interpretation": "食神得位，口福好，享受生活，有口才，善表达", "category": "性格"}
        ],
        "priority": 70
    },
    {
        "rule_type": "shishen", "position": "下唇-伤官", "position_code": "shangguan",
        "conditions": {"region": "lower_lip", "features": ["厚薄", "形状"]},
        "interpretations": [
            {"feature": "下唇厚于上唇", "interpretation": "伤官旺，口才佳，创意足，但需注意言辞", "category": "性格"}
        ],
        "priority": 70
    },
    {
        "rule_type": "shishen", "position": "天庭-正印", "position_code": "zhengyin",
        "conditions": {"region": "tinting", "features": ["宽阔度", "饱满度"]},
        "interpretations": [
            {"feature": "天庭宽阔饱满", "interpretation": "正印得位，学识渊博，有文化修养，得长辈提携", "category": "事业"}
        ],
        "priority": 80
    },
    {
        "rule_type": "shishen", "position": "额角-偏印", "position_code": "pianyin",
        "conditions": {"region": "temples", "features": ["饱满度", "气色"]},
        "interpretations": [
            {"feature": "额角饱满", "interpretation": "偏印有力，有特殊技能，思维独特，适合技术工作", "category": "事业"}
        ],
        "priority": 70
    },
    {
        "rule_type": "shishen", "position": "颧骨-比肩", "position_code": "bijian",
        "conditions": {"region": "cheekbones", "features": ["高低", "大小"]},
        "interpretations": [
            {"feature": "颧骨高起有势", "interpretation": "比肩有力，朋友多，合作运佳，有领导能力", "category": "事业"},
            {"feature": "颧骨过高凸出", "interpretation": "比肩过旺，性格强势，需注意人际关系", "category": "性格"}
        ],
        "priority": 75
    },
    {
        "rule_type": "shishen", "position": "下颌-劫财", "position_code": "jiecai",
        "conditions": {"region": "jaw", "features": ["方圆", "大小"]},
        "interpretations": [
            {"feature": "下颌方正有力", "interpretation": "劫财有力，执行力强，但需防破财，理财要谨慎", "category": "财运"}
        ],
        "priority": 70
    }
]

# 流年运势规则
LIUNIAN_RULES = [
    {"rule_type": "liunian", "age_range": "1-2", "position": "天轮地轮", "region": "ears",
     "interpretations": [{"feature": "耳朵饱满色润", "interpretation": "幼年健康，家境安定"}], "priority": 60},
    {"rule_type": "liunian", "age_range": "3-14", "position": "额头", "region": "forehead",
     "interpretations": [{"feature": "额头饱满无疤", "interpretation": "少年时期学业顺利，家庭和睦"}], "priority": 70},
    {"rule_type": "liunian", "age_range": "15-16", "position": "天中", "region": "tianchong",
     "interpretations": [{"feature": "色泽明润", "interpretation": "此年运势佳，学业进步"}], "priority": 75},
    {"rule_type": "liunian", "age_range": "28", "position": "印堂", "region": "yintang",
     "interpretations": [{"feature": "印堂开阔明润", "interpretation": "28岁运势极佳，事业爱情双丰收"}], "priority": 95},
    {"rule_type": "liunian", "age_range": "41", "position": "山根", "region": "shangen",
     "interpretations": [{"feature": "山根高起无断", "interpretation": "41岁运势平稳，身体健康"}], "priority": 80},
    {"rule_type": "liunian", "age_range": "48-50", "position": "准头", "region": "zhuntou",
     "interpretations": [{"feature": "鼻头丰隆有肉", "interpretation": "48-50岁财运极佳，事业高峰期"}], "priority": 90},
    {"rule_type": "liunian", "age_range": "51", "position": "人中", "region": "renzhong",
     "interpretations": [{"feature": "人中深长", "interpretation": "51岁运势佳，健康长寿"}], "priority": 75},
    {"rule_type": "liunian", "age_range": "60+", "position": "地阁", "region": "dige",
     "interpretations": [{"feature": "地阁饱满", "interpretation": "晚年运势好，福寿双全"}], "priority": 85}
]


def get_all_rules():
    """获取所有规则"""
    return {
        'gongwei_rules': GONGWEI_RULES,
        'feature_rules': FEATURE_RULES,
        'liuqin_rules': LIUQIN_RULES,
        'shishen_rules': SHISHEN_RULES,
        'liunian_rules': LIUNIAN_RULES
    }

