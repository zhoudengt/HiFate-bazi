#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移配置数据到数据库
1. 创建数据库表
2. 迁移services.env数据到service_configs表
3. 创建input_data格式定义初始数据
"""

import sys
import os
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
# 使用print输出日志，避免logger接口问题


def create_tables():
    """创建数据库表"""
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            # 直接执行CREATE TABLE语句，不使用SQL文件
            # 1. 创建service_configs表
            create_service_configs_sql = """
            CREATE TABLE IF NOT EXISTS `service_configs` (
                `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
                `config_key` VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键（如：BAZI_CORE_SERVICE_URL）',
                `config_value` TEXT COMMENT '配置值',
                `config_type` VARCHAR(20) DEFAULT 'string' COMMENT '配置类型：string/int/bool/json',
                `description` TEXT COMMENT '配置描述',
                `category` VARCHAR(50) COMMENT '配置分类：grpc/coze/payment/frontend等',
                `environment` VARCHAR(20) DEFAULT 'production' COMMENT '环境：production/development/staging',
                `version` INT DEFAULT 1 COMMENT '版本号',
                `is_active` BOOLEAN DEFAULT 1 COMMENT '是否启用',
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX `idx_key` (`config_key`),
                INDEX `idx_category` (`category`),
                INDEX `idx_env` (`environment`),
                INDEX `idx_active` (`is_active`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='服务配置表'
            """
            cursor.execute(create_service_configs_sql)
            print("✓ 创建service_configs表")
            
            # 2. 创建llm_input_formats表
            create_llm_formats_sql = """
            CREATE TABLE IF NOT EXISTS `llm_input_formats` (
                `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '格式ID',
                `format_name` VARCHAR(100) NOT NULL UNIQUE COMMENT '格式名称（如：fortune_analysis_full）',
                `intent` VARCHAR(50) NOT NULL COMMENT '意图类型（如：wealth/health/career/marriage/general等）',
                `format_type` VARCHAR(50) DEFAULT 'full' COMMENT '格式类型：full/minimal/custom',
                `structure` JSON NOT NULL COMMENT '格式结构定义（JSON格式，定义需要哪些字段）',
                `description` TEXT COMMENT '格式描述',
                `version` VARCHAR(20) DEFAULT 'v1.0' COMMENT '版本号',
                `is_active` BOOLEAN DEFAULT 1 COMMENT '是否启用',
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX `idx_format_name` (`format_name`),
                INDEX `idx_intent` (`intent`),
                INDEX `idx_format_type` (`format_type`),
                INDEX `idx_active` (`is_active`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM输入数据格式定义表'
            """
            cursor.execute(create_llm_formats_sql)
            print("✓ 创建llm_input_formats表")
        
        conn.commit()
        print("✅ 数据库表创建成功")
        return True
    except Exception as e:
        print(f"❌ 创建数据库表失败: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            return_mysql_connection(conn)


def migrate_services_env():
    """迁移services.env数据到数据库"""
    services_env_path = project_root / 'config' / 'services.env'
    
    if not services_env_path.exists():
        print(f"❌ services.env文件不存在: {services_env_path}")
        return False
    
    # 解析services.env文件
    configs = []
    categories = {
        'BAZI_CORE_SERVICE_URL': 'grpc',
        'BAZI_FORTUNE_SERVICE_URL': 'grpc',
        'BAZI_ANALYZER_SERVICE_URL': 'grpc',
        'BAZI_RULE_SERVICE_URL': 'grpc',
        'FORTUNE_ANALYSIS_SERVICE_URL': 'grpc',
        'FORTUNE_RULE_SERVICE_URL': 'grpc',
        'PAYMENT_SERVICE_URL': 'grpc',
        'INTENT_SERVICE_URL': 'grpc',
        'PROMPT_OPTIMIZER_SERVICE_URL': 'grpc',
        'COZE_ACCESS_TOKEN': 'coze',
        'COZE_BOT_ID': 'coze',
        'INTENT_BOT_ID': 'coze',
        'FORTUNE_ANALYSIS_BOT_ID': 'coze',
        'DAILY_FORTUNE_ACTION_BOT_ID': 'coze',
        'XISHEN_JISHEN_BOT_ID': 'coze',
        'MARRIAGE_ANALYSIS_BOT_ID': 'coze',
        'CAREER_WEALTH_BOT_ID': 'coze',
        'CHILDREN_STUDY_BOT_ID': 'coze',
        'HEALTH_ANALYSIS_BOT_ID': 'coze',
        'GENERAL_REVIEW_BOT_ID': 'coze',
        'QA_ANALYSIS_BOT_ID': 'coze',
        'QA_QUESTION_GENERATOR_BOT_ID': 'coze',
        'PROMPT_VERSION': 'coze',
        'PROMPT_CACHE_TTL': 'coze',
        'STRIPE_SECRET_KEY': 'payment',
        'PAYPAL_CLIENT_ID': 'payment',
        'PAYPAL_CLIENT_SECRET': 'payment',
        'PAYPAL_MODE': 'payment',
        'FRONTEND_BASE_URL': 'frontend',
    }
    
    try:
        with open(services_env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 解析 export KEY="VALUE" 格式
                if line.startswith('export '):
                    line = line[7:].strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        # 判断类型
                        config_type = 'string'
                        if value.isdigit():
                            config_type = 'int'
                        elif value.lower() in ('true', 'false', '1', '0', 'yes', 'no'):
                            config_type = 'bool'
                        
                        configs.append({
                            'key': key,
                            'value': value,
                            'type': config_type,
                            'category': categories.get(key, 'other'),
                            'description': f'{key}配置'
                        })
        
        # 插入数据库
        conn = None
        try:
            conn = get_mysql_connection()
            with conn.cursor() as cursor:
                for config in configs:
                    # 检查是否已存在
                    check_sql = "SELECT id FROM service_configs WHERE config_key = %s"
                    cursor.execute(check_sql, (config['key'],))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # 更新
                        update_sql = """
                            UPDATE service_configs 
                            SET config_value = %s, config_type = %s, category = %s, description = %s, updated_at = NOW()
                            WHERE config_key = %s
                        """
                        cursor.execute(update_sql, (
                            config['value'],
                            config['type'],
                            config['category'],
                            config['description'],
                            config['key']
                        ))
                        print(f"✓ 更新配置: {config['key']}")
                    else:
                        # 插入
                        insert_sql = """
                            INSERT INTO service_configs (config_key, config_value, config_type, category, description, environment)
                            VALUES (%s, %s, %s, %s, %s, 'production')
                        """
                        cursor.execute(insert_sql, (
                            config['key'],
                            config['value'],
                            config['type'],
                            config['category'],
                            config['description']
                        ))
                        print(f"✓ 插入配置: {config['key']}")
            
            conn.commit()
            print(f"✅ 成功迁移 {len(configs)} 个配置到数据库")
            return True
        except Exception as e:
            print(f"❌ 迁移配置失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                return_mysql_connection(conn)
    
    except Exception as e:
        print(f"❌ 解析services.env失败: {e}")
        return False


def create_format_definitions():
    """创建input_data格式定义初始数据 - 为所有分析类型创建格式定义"""
    formats = [
        # 1. 通用格式（用于FortuneLLMClient）
        {
            'format_name': 'fortune_analysis_full',
            'intent': 'general',
            'format_type': 'full',
            'structure': {
                'fields': {
                    'intent': {'source': 'request_param', 'field': 'intent'},
                    'question': {'source': 'request_param', 'field': 'question'},
                    'bazi': {
                        'source': 'redis',
                        'key_template': 'bazi:{solar_date}:{solar_time}:{gender}',
                        'fields': ['pillars', 'day_stem']
                    },
                    'liunian': {
                        'source': 'redis',
                        'key_template': 'fortune:{solar_date}:{solar_time}:{gender}:liunian',
                        'fields': ['year', 'stem', 'branch', 'stem_element', 'branch_element', 'stem_shishen', 'branch_shishen', 'balance_summary', 'relation_summary']
                    },
                    'dayun': {
                        'source': 'redis',
                        'key_template': 'fortune:{solar_date}:{solar_time}:{gender}:dayun',
                        'fields': ['stem', 'branch']
                    },
                    'xi_ji': {
                        'source': 'redis',
                        'key_template': 'fortune:{solar_date}:{solar_time}:{gender}:xi_ji',
                        'fields': ['xi_shen', 'ji_shen'],
                        'transform': {'xi_shen': 'slice:0:5', 'ji_shen': 'slice:0:5'}
                    },
                    'wangshuai': {
                        'source': 'redis',
                        'key_template': 'fortune:{solar_date}:{solar_time}:{gender}:wangshuai'
                    },
                    'matched_rules': {
                        'source': 'redis',
                        'key_template': 'rules:{solar_date}:{solar_time}:{gender}:{intent}',
                        'fields': ['rules_by_intent', 'rules_count'],
                        'optional': True
                    },
                    'language_style': {
                        'source': 'static',
                        'value': '通俗易懂，避免专业术语，面向普通用户。用日常语言解释命理概念，如"正官"可以说成"稳定的工作机会"，"七杀"可以说成"挑战和压力"。'
                    },
                    'category': {
                        'source': 'request_param',
                        'field': 'category',
                        'optional': True
                    }
                }
            },
            'description': '完整格式：包含所有字段的input_data格式（用于FortuneLLMClient）'
        },
        {
            'format_name': 'fortune_analysis_minimal',
            'intent': 'general',
            'format_type': 'minimal',
            'structure': {
                'fields': {
                    'intent': {'source': 'request_param', 'field': 'intent'},
                    'question': {'source': 'request_param', 'field': 'question'},
                    'category': {'source': 'request_param', 'field': 'category', 'optional': True},
                    'bazi': {
                        'source': 'redis',
                        'key_template': 'bazi:{solar_date}:{solar_time}:{gender}',
                        'fields': ['pillars', 'day_stem']
                    },
                    'language_style': {
                        'source': 'static',
                        'value': '通俗易懂，避免专业术语，面向普通用户。用日常语言解释命理概念，如"正官"可以说成"稳定的工作机会"，"七杀"可以说成"挑战和压力"。'
                    },
                    'note': {
                        'source': 'static',
                        'value': '八字详细信息已在第一次调用时提供，本次只基于用户问题和类别生成答案。请快速响应，在10秒内生成内容。'
                    }
                }
            },
            'description': '精简格式：只包含必要字段的input_data格式'
        },
        {
            'format_name': 'fortune_analysis_simple',
            'intent': 'general',
            'format_type': 'custom',
            'structure': {
                'fields': {
                    'question': {'source': 'request_param', 'field': 'question'},
                    'intent': {'source': 'request_param', 'field': 'intent'},
                    'confidence': {'source': 'request_param', 'field': 'confidence', 'optional': True},
                    'bazi_info': {
                        'source': 'redis',
                        'key_template': 'bazi:{solar_date}:{solar_time}:{gender}',
                        'fields': ['solar_date', 'solar_time', 'gender', 'pillars', 'day_stem', 'element_counts']
                    },
                    'fortune_context': {
                        'source': 'redis',
                        'key_template': 'fortune:{solar_date}:{solar_time}:{gender}:context',
                        'optional': True
                    }
                }
            },
            'description': '简单格式：用于FortuneAnalysisLLMClient'
        },
        # 2. 感情婚姻分析格式
        {
            'format_name': 'marriage_analysis',
            'intent': 'marriage',
            'format_type': 'full',
            'structure': {
                'fields': {
                    'mingpan_zonglun': {
                        'source': 'redis',
                        'key_template': 'marriage:{solar_date}:{solar_time}:{gender}:mingpan',
                        'fields': ['bazi_pillars', 'ten_gods', 'wangshuai', 'branch_relations', 'day_pillar']
                    },
                    'peiou_tezheng': {
                        'source': 'redis',
                        'key_template': 'marriage:{solar_date}:{solar_time}:{gender}:peiou',
                        'fields': ['ten_gods', 'deities', 'marriage_judgments', 'peach_blossom_judgments', 'matchmaking_judgments', 'zhengyuan_judgments']
                    },
                    'ganqing_zoushi': {
                        'source': 'redis',
                        'key_template': 'marriage:{solar_date}:{solar_time}:{gender}:ganqing',
                        'fields': ['current_dayun', 'key_dayuns', 'ten_gods']
                    },
                    'shensha_dianjing': {
                        'source': 'redis',
                        'key_template': 'marriage:{solar_date}:{solar_time}:{gender}:shensha',
                        'fields': ['deities']
                    },
                    'jianyi_fangxiang': {
                        'source': 'redis',
                        'key_template': 'marriage:{solar_date}:{solar_time}:{gender}:jianyi',
                        'fields': ['ten_gods', 'xi_ji', 'current_dayun', 'key_dayuns']
                    }
                }
            },
            'description': '感情婚姻分析格式：包含命盘总论、配偶特征、感情走势、神煞点睛、建议方向'
        },
        # 3. 事业财富分析格式
        {
            'format_name': 'career_wealth_analysis',
            'intent': 'career_wealth',
            'format_type': 'full',
            'structure': {
                'fields': {
                    'mingpan_shiye_caifu_zonglun': {
                        'source': 'redis',
                        'key_template': 'career_wealth:{solar_date}:{solar_time}:{gender}:mingpan',
                        'fields': ['day_master', 'bazi_pillars', 'wuxing_distribution', 'wangshuai', 'wangshuai_detail', 'yue_ling', 'yue_ling_shishen', 'gender', 'geju_type', 'geju_description', 'ten_gods']
                    },
                    'shiye_xing_gong': {
                        'source': 'redis',
                        'key_template': 'career_wealth:{solar_date}:{solar_time}:{gender}:shiye',
                        'fields': ['shiye_xing', 'month_pillar_analysis', 'ten_gods', 'ten_gods_stats', 'deities', 'career_judgments']
                    },
                    'caifu_xing_gong': {
                        'source': 'redis',
                        'key_template': 'career_wealth:{solar_date}:{solar_time}:{gender}:caifu',
                        'fields': ['caifu_xing', 'year_pillar_analysis', 'hour_pillar_analysis', 'shishang_shengcai', 'caiku', 'wealth_judgments']
                    },
                    'shiye_yunshi': {
                        'source': 'redis',
                        'key_template': 'career_wealth:{solar_date}:{solar_time}:{gender}:yunshi',
                        'fields': ['current_dayun', 'key_dayuns', 'ten_gods']
                    },
                    'caifu_yunshi': {
                        'source': 'redis',
                        'key_template': 'career_wealth:{solar_date}:{solar_time}:{gender}:caifu_yunshi',
                        'fields': ['current_dayun', 'key_dayuns', 'ten_gods']
                    },
                    'jianyi_fangxiang': {
                        'source': 'redis',
                        'key_template': 'career_wealth:{solar_date}:{solar_time}:{gender}:jianyi',
                        'fields': ['fangwei', 'hangye', 'xi_ji', 'current_dayun', 'key_dayuns']
                    }
                }
            },
            'description': '事业财富分析格式：包含命盘总论、事业星与事业宫、财富星与财富宫、事业运势、财富运势、建议方向'
        },
        # 4. 子女学习分析格式
        {
            'format_name': 'children_study_analysis',
            'intent': 'children_study',
            'format_type': 'full',
            'structure': {
                'fields': {
                    'mingpan_zinv_zonglun': {
                        'source': 'redis',
                        'key_template': 'children_study:{solar_date}:{solar_time}:{gender}:mingpan',
                        'fields': ['bazi_pillars', 'ten_gods', 'wangshuai', 'branch_relations', 'day_pillar']
                    },
                    'zinvxing_zinvgong': {
                        'source': 'redis',
                        'key_template': 'children_study:{solar_date}:{solar_time}:{gender}:zinvxing',
                        'fields': ['zinv_xing_type', 'zinv_xing_analysis', 'hour_pillar_analysis', 'ten_gods', 'deities', 'children_judgments']
                    },
                    'shengyu_shiji': {
                        'source': 'redis',
                        'key_template': 'children_study:{solar_date}:{solar_time}:{gender}:shengyu',
                        'fields': ['current_dayun', 'key_dayuns', 'all_dayuns', 'ten_gods']
                    },
                    'yangyu_jianyi': {
                        'source': 'redis',
                        'key_template': 'children_study:{solar_date}:{solar_time}:{gender}:yangyu',
                        'fields': ['ten_gods', 'xi_ji', 'current_dayun', 'key_dayuns']
                    },
                    'children_rules': {
                        'source': 'redis',
                        'key_template': 'children_study:{solar_date}:{solar_time}:{gender}:rules',
                        'fields': ['matched_rules', 'rules_count', 'rule_judgments'],
                        'optional': True
                    }
                }
            },
            'description': '子女学习分析格式：包含命盘总论、子女星与子女宫、生育时机、养育建议、子女规则'
        },
        # 5. 身体健康分析格式
        {
            'format_name': 'health_analysis',
            'intent': 'health',
            'format_type': 'full',
            'structure': {
                'fields': {
                    'mingpan_jiankang_zonglun': {
                        'source': 'redis',
                        'key_template': 'health:{solar_date}:{solar_time}:{gender}:mingpan',
                        'fields': ['bazi_pillars', 'day_pillar', 'wuxing_distribution', 'wangshuai', 'yue_ling', 'ten_gods', 'ten_gods_stats']
                    },
                    'wuxing_pingheng': {
                        'source': 'redis',
                        'key_template': 'health:{solar_date}:{solar_time}:{gender}:wuxing',
                        'fields': ['wuxing_balance', 'wuxing_relations', 'pathology_tendency']
                    },
                    'zangfu_tiaoyang': {
                        'source': 'redis',
                        'key_template': 'health:{solar_date}:{solar_time}:{gender}:zangfu',
                        'fields': ['body_algorithm', 'wuxing_tuning', 'zangfu_care']
                    },
                    'jiankang_yunshi': {
                        'source': 'redis',
                        'key_template': 'health:{solar_date}:{solar_time}:{gender}:yunshi',
                        'fields': ['current_dayun', 'key_dayuns', 'special_liunians', 'ten_gods']
                    },
                    'jianyi_fangxiang': {
                        'source': 'redis',
                        'key_template': 'health:{solar_date}:{solar_time}:{gender}:jianyi',
                        'fields': ['xi_ji', 'wuxing_tuning', 'zangfu_care', 'current_dayun', 'key_dayuns']
                    }
                }
            },
            'description': '身体健康分析格式：包含命盘总论、五行平衡、脏腑调养、健康运势、建议方向'
        },
        # 6. 总评分析格式
        {
            'format_name': 'general_review_analysis',
            'intent': 'general',
            'format_type': 'full',
            'structure': {
                'fields': {
                    'mingpan_hexin_geju': {
                        'source': 'redis',
                        'key_template': 'general_review:{solar_date}:{solar_time}:{gender}:mingpan',
                        'fields': ['bazi_pillars', 'day_pillar', 'wuxing_distribution', 'wangshuai', 'yue_ling', 'geju_type', 'geju_description', 'ten_gods', 'ten_gods_stats']
                    },
                    'xingge_tezheng': {
                        'source': 'redis',
                        'key_template': 'general_review:{solar_date}:{solar_time}:{gender}:xingge',
                        'fields': ['personality_traits', 'rizhu_analysis', 'character_judgments']
                    },
                    'guanjian_dayun': {
                        'source': 'redis',
                        'key_template': 'general_review:{solar_date}:{solar_time}:{gender}:dayun',
                        'fields': ['current_dayun', 'key_dayuns', 'special_liunians']
                    },
                    'zhongsheng_tidian': {
                        'source': 'redis',
                        'key_template': 'general_review:{solar_date}:{solar_time}:{gender}:zhongsheng',
                        'fields': ['xishen', 'jishen', 'xi_ji_elements']
                    },
                    'jiankang_tiaoyang': {
                        'source': 'redis',
                        'key_template': 'general_review:{solar_date}:{solar_time}:{gender}:jiankang',
                        'fields': ['wuxing_balance', 'pathology_tendency', 'wuxing_tuning', 'zangfu_care']
                    },
                    'zonghe_pingjia': {
                        'source': 'redis',
                        'key_template': 'general_review:{solar_date}:{solar_time}:{gender}:zonghe',
                        'fields': ['rizhu_rules', 'character_rules', 'summary_rules']
                    }
                }
            },
            'description': '总评分析格式：包含命盘核心格局、性格特征、关键大运、重生命点、健康调养、综合评价'
        },
        # 7. AI问答格式
        {
            'format_name': 'qa_conversation',
            'intent': 'qa',
            'format_type': 'custom',
            'structure': {
                'fields': {
                    'question': {'source': 'request_param', 'field': 'question'},
                    'session_id': {'source': 'request_param', 'field': 'session_id'},
                    'bazi_info': {
                        'source': 'redis',
                        'key_template': 'qa:{session_id}:bazi',
                        'fields': ['solar_date', 'solar_time', 'gender', 'pillars', 'day_stem']
                    },
                    'conversation_history': {
                        'source': 'redis',
                        'key_template': 'qa:{session_id}:history',
                        'optional': True
                    }
                }
            },
            'description': 'AI问答格式：包含问题、会话ID、八字信息、对话历史'
        }
    ]
    
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            for format_def in formats:
                # 检查是否已存在
                check_sql = "SELECT id FROM llm_input_formats WHERE format_name = %s"
                cursor.execute(check_sql, (format_def['format_name'],))
                existing = cursor.fetchone()
                
                structure_json = json.dumps(format_def['structure'], ensure_ascii=False)
                
                if existing:
                    # 更新
                    update_sql = """
                        UPDATE llm_input_formats 
                        SET intent = %s, format_type = %s, structure = %s, description = %s, updated_at = NOW()
                        WHERE format_name = %s
                    """
                    cursor.execute(update_sql, (
                        format_def['intent'],
                        format_def['format_type'],
                        structure_json,
                        format_def['description'],
                        format_def['format_name']
                    ))
                    print(f"✓ 更新格式定义: {format_def['format_name']}")
                else:
                    # 插入
                    insert_sql = """
                        INSERT INTO llm_input_formats (format_name, intent, format_type, structure, description, version)
                        VALUES (%s, %s, %s, %s, %s, 'v1.0')
                    """
                    cursor.execute(insert_sql, (
                        format_def['format_name'],
                        format_def['intent'],
                        format_def['format_type'],
                        structure_json,
                        format_def['description']
                    ))
                    print(f"✓ 插入格式定义: {format_def['format_name']}")
        
        conn.commit()
        print(f"✅ 成功创建 {len(formats)} 个格式定义")
        return True
    except Exception as e:
        print(f"❌ 创建格式定义失败: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            return_mysql_connection(conn)


def main():
    """主函数"""
    print("🚀 开始迁移配置数据到数据库...")
    
    # 1. 创建数据库表
    print("📋 步骤1: 创建数据库表...")
    if not create_tables():
        print("❌ 创建数据库表失败")
        return False
    
    # 2. 迁移services.env数据
    print("📋 步骤2: 迁移services.env数据...")
    if not migrate_services_env():
        print("❌ 迁移services.env数据失败")
        return False
    
    # 3. 创建格式定义初始数据
    print("📋 步骤3: 创建格式定义初始数据...")
    if not create_format_definitions():
        print("❌ 创建格式定义初始数据失败")
        return False
    
    print("✅ 所有配置数据迁移完成！")
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

