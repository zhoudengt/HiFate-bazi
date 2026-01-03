#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大模型 input_data 结构定义
基于源代码手动定义所有接口的完整 input_data 结构
"""

# ==================== 结构化 input_data 接口定义 ====================

# 1. 八字命理-子女学习
CHILDREN_STUDY_INPUT_DATA = {
    'name': '八字命理-子女学习',
    'endpoint': '/api/v1/bazi/children-study/stream',
    'function': 'build_children_study_input_data',
    'file': 'server/api/v1/children_study_analysis.py',
    'type': 'structured',
    'fields': [
        # mingpan_zinv_zonglun
        {'path': 'mingpan_zinv_zonglun', 'type': 'dict', 'description': '命盘子女总论', 'source': 'build_children_study_input_data()'},
        {'path': 'mingpan_zinv_zonglun.day_master', 'type': 'dict', 'description': '日主信息', 'source': 'bazi_data.bazi_pillars.day'},
        {'path': 'mingpan_zinv_zonglun.day_master.stem', 'type': 'string', 'description': '日干', 'source': 'day_pillar.stem'},
        {'path': 'mingpan_zinv_zonglun.day_master.branch', 'type': 'string', 'description': '日支', 'source': 'day_pillar.branch'},
        {'path': 'mingpan_zinv_zonglun.day_master.element', 'type': 'string', 'description': '日主五行', 'source': 'day_pillar.element'},
        {'path': 'mingpan_zinv_zonglun.day_master.yin_yang', 'type': 'string', 'description': '阴阳', 'source': 'day_pillar.yin_yang'},
        {'path': 'mingpan_zinv_zonglun.bazi_pillars', 'type': 'dict', 'description': '四柱排盘', 'source': 'bazi_data.bazi_pillars'},
        {'path': 'mingpan_zinv_zonglun.elements', 'type': 'dict', 'description': '五行分布', 'source': 'bazi_data.element_counts'},
        {'path': 'mingpan_zinv_zonglun.wangshuai', 'type': 'string', 'description': '旺衰分析', 'source': 'wangshuai_result.wangshuai'},
        {'path': 'mingpan_zinv_zonglun.gender', 'type': 'string', 'description': '性别（关键！影响子女星判断）', 'source': 'request.gender'},
        
        # zinvxing_zinvgong
        {'path': 'zinvxing_zinvgong', 'type': 'dict', 'description': '子女星与子女宫', 'source': 'build_children_study_input_data()'},
        {'path': 'zinvxing_zinvgong.zinv_xing_type', 'type': 'string', 'description': '子女星类型（男命官杀/女命食伤）', 'source': 'determine_children_star_type(ten_gods_data, gender)'},
        {'path': 'zinvxing_zinvgong.hour_pillar', 'type': 'dict', 'description': '时柱（子女宫）', 'source': 'bazi_data.bazi_pillars.hour'},
        {'path': 'zinvxing_zinvgong.ten_gods', 'type': 'dict', 'description': '十神配置', 'source': 'detail_result.ten_gods'},
        {'path': 'zinvxing_zinvgong.deities', 'type': 'dict', 'description': '神煞分布', 'source': 'detail_result.deities'},
        
        # shengyu_shiji
        {'path': 'shengyu_shiji', 'type': 'dict', 'description': '生育时机', 'source': 'build_children_study_input_data()'},
        {'path': 'shengyu_shiji.zinv_xing_type', 'type': 'string', 'description': '子女星类型', 'source': 'determine_children_star_type(ten_gods_data, gender)'},
        {'path': 'shengyu_shiji.current_dayun', 'type': 'dict', 'description': '当前大运（包含流年数据）', 'source': 'identify_key_dayuns() -> current_dayun_info + dayun_liunians'},
        {'path': 'shengyu_shiji.current_dayun.step', 'type': 'string', 'description': '大运步数', 'source': 'current_dayun_info.step'},
        {'path': 'shengyu_shiji.current_dayun.stem', 'type': 'string', 'description': '大运天干', 'source': 'current_dayun_info.stem'},
        {'path': 'shengyu_shiji.current_dayun.branch', 'type': 'string', 'description': '大运地支', 'source': 'current_dayun_info.branch'},
        {'path': 'shengyu_shiji.current_dayun.age_display', 'type': 'string', 'description': '年龄显示', 'source': 'current_dayun_info.age_display'},
        {'path': 'shengyu_shiji.current_dayun.main_star', 'type': 'string', 'description': '大运主星', 'source': 'current_dayun_info.main_star'},
        {'path': 'shengyu_shiji.current_dayun.description', 'type': 'string', 'description': '大运描述', 'source': 'current_dayun_info.description'},
        {'path': 'shengyu_shiji.current_dayun.liunians', 'type': 'list', 'description': '流年列表（合并后的所有流年）', 'source': 'dayun_liunians[current_step]'},
        {'path': 'shengyu_shiji.key_dayuns', 'type': 'list', 'description': '关键节点大运列表', 'source': 'identify_key_dayuns() -> key_dayuns_list + dayun_liunians'},
        {'path': 'shengyu_shiji.key_dayuns[].step', 'type': 'string', 'description': '大运步数', 'source': 'key_dayun.step'},
        {'path': 'shengyu_shiji.key_dayuns[].stem', 'type': 'string', 'description': '大运天干', 'source': 'key_dayun.stem'},
        {'path': 'shengyu_shiji.key_dayuns[].branch', 'type': 'string', 'description': '大运地支', 'source': 'key_dayun.branch'},
        {'path': 'shengyu_shiji.key_dayuns[].age_display', 'type': 'string', 'description': '年龄显示', 'source': 'key_dayun.age_display'},
        {'path': 'shengyu_shiji.key_dayuns[].main_star', 'type': 'string', 'description': '大运主星', 'source': 'key_dayun.main_star'},
        {'path': 'shengyu_shiji.key_dayuns[].description', 'type': 'string', 'description': '大运描述', 'source': 'key_dayun.description'},
        {'path': 'shengyu_shiji.key_dayuns[].relation_type', 'type': 'string', 'description': '关系类型', 'source': 'key_dayun.relation_type'},
        {'path': 'shengyu_shiji.key_dayuns[].liunians', 'type': 'list', 'description': '流年列表', 'source': 'dayun_liunians[step]'},
        {'path': 'shengyu_shiji.all_dayuns', 'type': 'list', 'description': '所有大运列表（用于参考）', 'source': 'dayun_sequence (转换格式)'},
        {'path': 'shengyu_shiji.all_dayuns[].step', 'type': 'string', 'description': '大运步数', 'source': 'dayun.step'},
        {'path': 'shengyu_shiji.all_dayuns[].stem', 'type': 'string', 'description': '大运天干', 'source': 'dayun.stem'},
        {'path': 'shengyu_shiji.all_dayuns[].branch', 'type': 'string', 'description': '大运地支', 'source': 'dayun.branch'},
        {'path': 'shengyu_shiji.all_dayuns[].age_display', 'type': 'string', 'description': '年龄显示', 'source': 'dayun.age_display'},
        {'path': 'shengyu_shiji.all_dayuns[].main_star', 'type': 'string', 'description': '大运主星', 'source': 'dayun.main_star'},
        {'path': 'shengyu_shiji.all_dayuns[].description', 'type': 'string', 'description': '大运描述', 'source': 'dayun.description'},
        {'path': 'shengyu_shiji.ten_gods', 'type': 'dict', 'description': '十神配置', 'source': 'detail_result.ten_gods'},
        
        # yangyu_jianyi
        {'path': 'yangyu_jianyi', 'type': 'dict', 'description': '养育建议', 'source': 'build_children_study_input_data()'},
        {'path': 'yangyu_jianyi.ten_gods', 'type': 'dict', 'description': '十神配置', 'source': 'detail_result.ten_gods'},
        {'path': 'yangyu_jianyi.wangshuai', 'type': 'dict', 'description': '旺衰数据', 'source': 'wangshuai_result (完整对象)'},
        {'path': 'yangyu_jianyi.xi_ji', 'type': 'dict', 'description': '喜忌数据', 'source': 'wangshuai_result (提取xi_shen, ji_shen, xi_ji_elements)'},
        {'path': 'yangyu_jianyi.xi_ji.xi_shen', 'type': 'list', 'description': '喜神列表', 'source': 'wangshuai_result.xi_shen'},
        {'path': 'yangyu_jianyi.xi_ji.ji_shen', 'type': 'list', 'description': '忌神列表', 'source': 'wangshuai_result.ji_shen'},
        {'path': 'yangyu_jianyi.xi_ji.xi_ji_elements', 'type': 'dict', 'description': '喜忌五行', 'source': 'wangshuai_result.xi_ji_elements'},
        
        # children_rules (动态添加)
        {'path': 'children_rules', 'type': 'dict', 'description': '子女规则（动态添加）', 'source': 'RuleService.match_rules(rule_data, [\'children\'])'},
        {'path': 'children_rules.matched_rules', 'type': 'list', 'description': '匹配到的规则', 'source': 'RuleService.match_rules()'},
        {'path': 'children_rules.rules_count', 'type': 'int', 'description': '规则数量', 'source': 'len(children_rules)'},
        {'path': 'children_rules.rule_judgments', 'type': 'list', 'description': '规则判词列表', 'source': '从matched_rules中提取content.text'},
    ]
}

# 2. 八字命理-身体健康
HEALTH_INPUT_DATA = {
    'name': '八字命理-身体健康',
    'endpoint': '/api/v1/bazi/health/stream',
    'function': 'build_health_input_data',
    'file': 'server/api/v1/health_analysis.py',
    'type': 'structured',
    'fields': [
        # mingpan_tizhi_zonglun
        {'path': 'mingpan_tizhi_zonglun', 'type': 'dict', 'description': '命盘体质总论', 'source': 'build_health_input_data()'},
        {'path': 'mingpan_tizhi_zonglun.day_master', 'type': 'dict', 'description': '日主信息', 'source': 'bazi_data.bazi_pillars.day'},
        {'path': 'mingpan_tizhi_zonglun.day_master.stem', 'type': 'string', 'description': '日干', 'source': 'day_pillar.stem'},
        {'path': 'mingpan_tizhi_zonglun.day_master.branch', 'type': 'string', 'description': '日支', 'source': 'day_pillar.branch'},
        {'path': 'mingpan_tizhi_zonglun.day_master.element', 'type': 'string', 'description': '日主五行', 'source': 'day_pillar.element'},
        {'path': 'mingpan_tizhi_zonglun.day_master.yin_yang', 'type': 'string', 'description': '阴阳', 'source': 'day_pillar.yin_yang'},
        {'path': 'mingpan_tizhi_zonglun.bazi_pillars', 'type': 'dict', 'description': '四柱排盘', 'source': 'bazi_data.bazi_pillars'},
        {'path': 'mingpan_tizhi_zonglun.elements', 'type': 'dict', 'description': '五行分布', 'source': 'bazi_data.element_counts'},
        {'path': 'mingpan_tizhi_zonglun.wangshuai', 'type': 'string', 'description': '旺衰分析', 'source': 'wangshuai_result.wangshuai'},
        {'path': 'mingpan_tizhi_zonglun.yue_ling', 'type': 'string', 'description': '月令', 'source': 'month_pillar.branch + "月"'},
        {'path': 'mingpan_tizhi_zonglun.wuxing_balance', 'type': 'string', 'description': '全局五行平衡情况', 'source': 'health_result.wuxing_balance'},
        
        # wuxing_bingli
        {'path': 'wuxing_bingli', 'type': 'dict', 'description': '五行病理推演', 'source': 'build_health_input_data()'},
        {'path': 'wuxing_bingli.wuxing_shengke', 'type': 'dict', 'description': '五行生克关系', 'source': 'pathology_tendency.wuxing_relations'},
        {'path': 'wuxing_bingli.body_algorithm', 'type': 'dict', 'description': '身体算法（五脏对应）', 'source': 'health_result.body_algorithm'},
        {'path': 'wuxing_bingli.pathology_tendency', 'type': 'dict', 'description': '病理倾向', 'source': 'health_result.pathology_tendency'},
        
        # dayun_jiankang
        {'path': 'dayun_jiankang', 'type': 'dict', 'description': '大运流年健康警示', 'source': 'build_health_input_data()'},
        {'path': 'dayun_jiankang.current_dayun', 'type': 'dict', 'description': '当前大运（包含流年数据）', 'source': 'identify_key_dayuns() -> current_dayun_info + dayun_liunians'},
        {'path': 'dayun_jiankang.current_dayun.step', 'type': 'int/string', 'description': '大运步数', 'source': 'current_dayun_info.step'},
        {'path': 'dayun_jiankang.current_dayun.stem', 'type': 'string', 'description': '大运天干', 'source': 'current_dayun_info.stem'},
        {'path': 'dayun_jiankang.current_dayun.branch', 'type': 'string', 'description': '大运地支', 'source': 'current_dayun_info.branch'},
        {'path': 'dayun_jiankang.current_dayun.age_display', 'type': 'string', 'description': '年龄显示', 'source': 'current_dayun_info.age_display'},
        {'path': 'dayun_jiankang.current_dayun.year_start', 'type': 'int', 'description': '起始年份', 'source': 'current_dayun_info.year_start'},
        {'path': 'dayun_jiankang.current_dayun.year_end', 'type': 'int', 'description': '结束年份', 'source': 'current_dayun_info.year_end'},
        {'path': 'dayun_jiankang.current_dayun.liunians', 'type': 'dict', 'description': '流年数据（按类型分组）', 'source': 'dayun_liunians[current_step]'},
        {'path': 'dayun_jiankang.current_dayun.liunians.tiankedi_chong', 'type': 'list', 'description': '天克地冲流年', 'source': 'dayun_liunians[current_step].tiankedi_chong'},
        {'path': 'dayun_jiankang.current_dayun.liunians.tianhedi_he', 'type': 'list', 'description': '天合地合流年', 'source': 'dayun_liunians[current_step].tianhedi_he'},
        {'path': 'dayun_jiankang.current_dayun.liunians.suiyun_binglin', 'type': 'list', 'description': '岁运并临流年', 'source': 'dayun_liunians[current_step].suiyun_binglin'},
        {'path': 'dayun_jiankang.current_dayun.liunians.other', 'type': 'list', 'description': '其他特殊流年', 'source': 'dayun_liunians[current_step].other'},
        {'path': 'dayun_jiankang.key_dayuns', 'type': 'list', 'description': '关键节点大运列表', 'source': 'identify_key_dayuns() -> key_dayuns_list + dayun_liunians'},
        {'path': 'dayun_jiankang.key_dayuns[].step', 'type': 'int/string', 'description': '大运步数', 'source': 'key_dayun.step'},
        {'path': 'dayun_jiankang.key_dayuns[].stem', 'type': 'string', 'description': '大运天干', 'source': 'key_dayun.stem'},
        {'path': 'dayun_jiankang.key_dayuns[].branch', 'type': 'string', 'description': '大运地支', 'source': 'key_dayun.branch'},
        {'path': 'dayun_jiankang.key_dayuns[].age_display', 'type': 'string', 'description': '年龄显示', 'source': 'key_dayun.age_display'},
        {'path': 'dayun_jiankang.key_dayuns[].year_start', 'type': 'int', 'description': '起始年份', 'source': 'key_dayun.year_start'},
        {'path': 'dayun_jiankang.key_dayuns[].year_end', 'type': 'int', 'description': '结束年份', 'source': 'key_dayun.year_end'},
        {'path': 'dayun_jiankang.key_dayuns[].relation_type', 'type': 'string', 'description': '关系类型', 'source': 'key_dayun.relation_type'},
        {'path': 'dayun_jiankang.key_dayuns[].liunians', 'type': 'dict', 'description': '流年数据（按类型分组）', 'source': 'dayun_liunians[key_step]'},
        {'path': 'dayun_jiankang.all_dayuns', 'type': 'list', 'description': '所有大运列表（用于参考）', 'source': 'dayun_sequence (转换格式)'},
        {'path': 'dayun_jiankang.all_dayuns[].step', 'type': 'int/string', 'description': '大运步数', 'source': 'dayun.step'},
        {'path': 'dayun_jiankang.all_dayuns[].stem', 'type': 'string', 'description': '大运天干', 'source': 'dayun.stem'},
        {'path': 'dayun_jiankang.all_dayuns[].branch', 'type': 'string', 'description': '大运地支', 'source': 'dayun.branch'},
        {'path': 'dayun_jiankang.all_dayuns[].age_display', 'type': 'string', 'description': '年龄显示', 'source': 'dayun.age_display'},
        {'path': 'dayun_jiankang.all_dayuns[].year_start', 'type': 'int', 'description': '起始年份', 'source': 'dayun.year_start'},
        {'path': 'dayun_jiankang.all_dayuns[].year_end', 'type': 'int', 'description': '结束年份', 'source': 'dayun.year_end'},
        {'path': 'dayun_jiankang.ten_gods', 'type': 'dict', 'description': '十神配置', 'source': 'detail_result.ten_gods'},
        
        # tizhi_tiaoli
        {'path': 'tizhi_tiaoli', 'type': 'dict', 'description': '体质调理建议', 'source': 'build_health_input_data()'},
        {'path': 'tizhi_tiaoli.xi_ji', 'type': 'dict', 'description': '喜忌数据', 'source': 'wangshuai_result (提取xi_shen, ji_shen, xi_ji_elements)'},
        {'path': 'tizhi_tiaoli.xi_ji.xi_shen', 'type': 'list', 'description': '喜神列表', 'source': 'wangshuai_result.xi_shen'},
        {'path': 'tizhi_tiaoli.xi_ji.ji_shen', 'type': 'list', 'description': '忌神列表', 'source': 'wangshuai_result.ji_shen'},
        {'path': 'tizhi_tiaoli.xi_ji.xi_ji_elements', 'type': 'dict', 'description': '喜忌五行', 'source': 'wangshuai_result.xi_ji_elements'},
        {'path': 'tizhi_tiaoli.wuxing_tiaohe', 'type': 'dict', 'description': '五行调和方案', 'source': 'health_result.wuxing_tuning'},
        {'path': 'tizhi_tiaoli.zangfu_yanghu', 'type': 'dict', 'description': '脏腑养护建议', 'source': 'health_result.zangfu_care'},
    ]
}

# 所有接口列表
ALL_INTERFACES = [
    CHILDREN_STUDY_INPUT_DATA,
    HEALTH_INPUT_DATA,
    # 后续添加其他接口：事业财富、总评、婚姻、智能运势、五行占比、喜神忌神、LLM生成报告、Coze AI分析...
]

