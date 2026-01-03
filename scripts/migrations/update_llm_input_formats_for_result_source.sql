-- =====================================================
-- 更新 llm_input_formats 表，支持 source: "result" 类型
-- 允许从计算结果直接组装 input_data（不依赖 Redis）
-- =====================================================

-- 1. 更新事业财富分析格式定义
UPDATE llm_input_formats 
SET structure = JSON_OBJECT(
    'fields', JSON_OBJECT(
        'mingpan_shiye_caifu_zonglun', JSON_OBJECT(
            'source', 'result',
            'data_source', 'bazi_data',
            'fields', JSON_ARRAY('bazi_pillars', 'day_pillar', 'element_counts', 'ten_gods')
        ),
        'shiye_xing_gong', JSON_OBJECT(
            'source', 'result',
            'data_source', 'detail_result',
            'fields', JSON_ARRAY('ten_gods', 'ten_gods_stats', 'deities')
        ),
        'caifu_xing_gong', JSON_OBJECT(
            'source', 'result',
            'data_source', 'detail_result',
            'fields', JSON_ARRAY('ten_gods', 'deities')
        ),
        'shiye_yunshi', JSON_OBJECT(
            'source', 'composite',
            'composite', JSON_OBJECT(
                'current_dayun', JSON_OBJECT('data_source', 'detail_result', 'field', 'current_dayun'),
                'key_dayuns', JSON_OBJECT('data_source', 'kwargs', 'field', 'dayun_sequence')
            )
        ),
        'caifu_yunshi', JSON_OBJECT(
            'source', 'composite',
            'composite', JSON_OBJECT(
                'current_dayun', JSON_OBJECT('data_source', 'detail_result', 'field', 'current_dayun'),
                'key_dayuns', JSON_OBJECT('data_source', 'kwargs', 'field', 'dayun_sequence')
            )
        ),
        'tiyun_jianyi', JSON_OBJECT(
            'source', 'result',
            'data_source', 'wangshuai_result',
            'fields', JSON_ARRAY('xi_ji_elements', 'xi_shen_elements', 'ji_shen_elements')
        )
    )
),
updated_at = NOW()
WHERE format_name = 'career_wealth_analysis';

-- 2. 更新子女学习分析格式定义
UPDATE llm_input_formats 
SET structure = JSON_OBJECT(
    'fields', JSON_OBJECT(
        'mingpan_zinv_zonglun', JSON_OBJECT(
            'source', 'result',
            'data_source', 'bazi_data',
            'fields', JSON_ARRAY('bazi_pillars', 'day_pillar', 'element_counts', 'ten_gods')
        ),
        'zinvxing_zinvgong', JSON_OBJECT(
            'source', 'result',
            'data_source', 'detail_result',
            'fields', JSON_ARRAY('ten_gods', 'deities')
        ),
        'shengyu_shiji', JSON_OBJECT(
            'source', 'composite',
            'composite', JSON_OBJECT(
                'current_dayun', JSON_OBJECT('data_source', 'detail_result', 'field', 'current_dayun'),
                'key_dayuns', JSON_OBJECT('data_source', 'kwargs', 'field', 'dayun_sequence')
            )
        ),
        'yangyu_jianyi', JSON_OBJECT(
            'source', 'result',
            'data_source', 'wangshuai_result',
            'fields', JSON_ARRAY('xi_ji_elements', 'xi_shen_elements', 'ji_shen_elements')
        ),
        'children_rules', JSON_OBJECT(
            'source', 'result',
            'data_source', 'rule_result',
            'field', 'matched_rules',
            'optional', true
        )
    )
),
updated_at = NOW()
WHERE format_name = 'children_study_analysis';

-- 3. 更新身体健康分析格式定义
UPDATE llm_input_formats 
SET structure = JSON_OBJECT(
    'fields', JSON_OBJECT(
        'mingpan_jiankang_zonglun', JSON_OBJECT(
            'source', 'result',
            'data_source', 'bazi_data',
            'fields', JSON_ARRAY('bazi_pillars', 'day_pillar', 'element_counts', 'ten_gods')
        ),
        'wuxing_pingheng', JSON_OBJECT(
            'source', 'result',
            'data_source', 'kwargs',
            'field', 'health_result'
        ),
        'zangfu_tiaoyang', JSON_OBJECT(
            'source', 'result',
            'data_source', 'kwargs',
            'field', 'health_result'
        ),
        'jiankang_yunshi', JSON_OBJECT(
            'source', 'composite',
            'composite', JSON_OBJECT(
                'current_dayun', JSON_OBJECT('data_source', 'detail_result', 'field', 'current_dayun'),
                'key_dayuns', JSON_OBJECT('data_source', 'kwargs', 'field', 'dayun_sequence'),
                'special_liunians', JSON_OBJECT('data_source', 'kwargs', 'field', 'special_liunians')
            )
        ),
        'jianyi_fangxiang', JSON_OBJECT(
            'source', 'result',
            'data_source', 'wangshuai_result',
            'fields', JSON_ARRAY('xi_ji_elements', 'xi_shen_elements', 'ji_shen_elements')
        )
    )
),
updated_at = NOW()
WHERE format_name = 'health_analysis';

-- 4. 更新总评分析格式定义
UPDATE llm_input_formats 
SET structure = JSON_OBJECT(
    'fields', JSON_OBJECT(
        'mingpan_hexin_geju', JSON_OBJECT(
            'source', 'result',
            'data_source', 'bazi_data',
            'fields', JSON_ARRAY('bazi_pillars', 'day_pillar', 'element_counts', 'ten_gods', 'ten_gods_stats')
        ),
        'xingge_tezheng', JSON_OBJECT(
            'source', 'composite',
            'composite', JSON_OBJECT(
                'personality_result', JSON_OBJECT('data_source', 'kwargs', 'field', 'personality_result'),
                'rizhu_result', JSON_OBJECT('data_source', 'kwargs', 'field', 'rizhu_result')
            )
        ),
        'guanjian_dayun', JSON_OBJECT(
            'source', 'composite',
            'composite', JSON_OBJECT(
                'current_dayun', JSON_OBJECT('data_source', 'detail_result', 'field', 'current_dayun'),
                'key_dayuns', JSON_OBJECT('data_source', 'kwargs', 'field', 'dayun_sequence'),
                'special_liunians', JSON_OBJECT('data_source', 'kwargs', 'field', 'special_liunians')
            )
        ),
        'zhongsheng_tidian', JSON_OBJECT(
            'source', 'result',
            'data_source', 'wangshuai_result',
            'fields', JSON_ARRAY('xi_ji_elements', 'xi_shen_elements', 'ji_shen_elements')
        ),
        'jiankang_tiaoyang', JSON_OBJECT(
            'source', 'result',
            'data_source', 'kwargs',
            'field', 'health_result'
        ),
        'zonghe_pingjia', JSON_OBJECT(
            'source', 'result',
            'data_source', 'rule_result',
            'field', 'matched_rules',
            'optional', true
        )
    )
),
updated_at = NOW()
WHERE format_name = 'general_review_analysis';

-- 5. 更新感情婚姻分析格式定义（优化，支持 source: result）
UPDATE llm_input_formats 
SET structure = JSON_OBJECT(
    'fields', JSON_OBJECT(
        'mingpan_zonglun', JSON_OBJECT(
            'source', 'result',
            'data_source', 'bazi_data',
            'fields', JSON_ARRAY('bazi_pillars', 'ten_gods', 'day_pillar', 'element_counts')
        ),
        'peiou_tezheng', JSON_OBJECT(
            'source', 'result',
            'data_source', 'detail_result',
            'fields', JSON_ARRAY('ten_gods', 'deities')
        ),
        'ganqing_zoushi', JSON_OBJECT(
            'source', 'composite',
            'composite', JSON_OBJECT(
                'current_dayun', JSON_OBJECT('data_source', 'detail_result', 'field', 'current_dayun'),
                'key_dayuns', JSON_OBJECT('data_source', 'kwargs', 'field', 'dayun_sequence')
            )
        ),
        'shensha_dianjing', JSON_OBJECT(
            'source', 'result',
            'data_source', 'detail_result',
            'field', 'deities'
        ),
        'jianyi_fangxiang', JSON_OBJECT(
            'source', 'result',
            'data_source', 'wangshuai_result',
            'fields', JSON_ARRAY('xi_ji_elements', 'xi_shen_elements', 'ji_shen_elements')
        )
    )
),
updated_at = NOW()
WHERE format_name = 'marriage_analysis';

-- 6. 更新 QA 问答格式定义
UPDATE llm_input_formats 
SET structure = JSON_OBJECT(
    'fields', JSON_OBJECT(
        'user_question', JSON_OBJECT(
            'source', 'result',
            'data_source', 'kwargs',
            'field', 'user_question'
        ),
        'bazi_data', JSON_OBJECT(
            'source', 'result',
            'data_source', 'bazi_data',
            'fields', JSON_ARRAY('bazi_pillars', 'day_pillar', 'element_counts', 'ten_gods')
        ),
        'wangshuai', JSON_OBJECT(
            'source', 'result',
            'data_source', 'wangshuai_result',
            'fields', JSON_ARRAY('xi_ji_elements', 'xi_shen_elements', 'ji_shen_elements')
        ),
        'dayun_sequence', JSON_OBJECT(
            'source', 'result',
            'data_source', 'detail_result',
            'field', 'dayun_sequence'
        ),
        'liunian_sequence', JSON_OBJECT(
            'source', 'result',
            'data_source', 'detail_result',
            'field', 'liunian_sequence'
        ),
        'matched_rules', JSON_OBJECT(
            'source', 'result',
            'data_source', 'rule_result',
            'field', 'matched_rules',
            'optional', true
        ),
        'intent', JSON_OBJECT(
            'source', 'result',
            'data_source', 'kwargs',
            'field', 'intent'
        ),
        'conversation_context', JSON_OBJECT(
            'source', 'result',
            'data_source', 'kwargs',
            'field', 'conversation_context'
        )
    )
),
updated_at = NOW()
WHERE format_name = 'qa_conversation';

-- 验证更新
SELECT format_name, is_active, updated_at, 
       JSON_EXTRACT(structure, '$.fields') IS NOT NULL AS has_fields
FROM llm_input_formats 
WHERE format_name IN (
    'career_wealth_analysis', 
    'children_study_analysis', 
    'health_analysis', 
    'general_review_analysis', 
    'marriage_analysis',
    'qa_conversation'
);

