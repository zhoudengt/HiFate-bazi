#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复规则 70067-70088 的条件格式

问题：这些规则的条件类型是"天干地支"，应该统计天干+地支的总数
但导入时使用了 stems_count（只统计天干），应该改为 stems_branches_count

修复范围：仅修复 FORMULA_70067 到 FORMULA_70088 这22条规则
不影响其他规则

使用方法：
  python scripts/migration/fix_rules_70067_70088.py --dry-run  # 预览
  python scripts/migration/fix_rules_70067_70088.py            # 正式修复
"""

import sys
import os
import json
import argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
from pymysql.cursors import DictCursor

# 规则修复映射表（根据图片描述，只修复这22条规则）
# 注意：规则编码格式是 FORMULA_身体_70067
RULE_FIXES = {
    'FORMULA_身体_70067': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['甲', '乙'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中甲和乙数量3个以上（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70068': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['甲', '乙'],
                        'max': 0
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中甲和乙数量0个以下（包含0个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70069': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['甲', '乙'],
                        'max': 1
                    }
                },
                {
                    'element_total': {
                        'names': ['水'],
                        'min': 3
                    }
                },
                {
                    'element_total': {
                        'names': ['土'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中甲和乙数量1个以下（包含1个），且对应五行属性水大于2个（包含2个），并且对应五行属性土大于2个（包含2个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70070': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['甲'],
                        'max': 1
                    }
                },
                {
                    'element_total': {
                        'names': ['火'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中甲数量1个以下（包含1个），且对应五行属性火大于3个（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70071': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['乙'],
                        'max': 1
                    }
                },
                {
                    'element_total': {
                        'names': ['火'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中乙数量1个以下（包含1个），且对应五行属性火大于3个（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70072': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['丁'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中丁数量3个以上（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70073': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['丁'],
                        'max': 0
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中丁数量0个以下（包含0个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70074': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['戊'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中戊数量3个以上（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70075': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['戊'],
                        'max': 0
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中戊数量0个以下（包含0个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70076': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['戊'],
                        'max': 1
                    }
                },
                {
                    'element_total': {
                        'names': ['金'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中戊数量1个以下（包含1个），且对应五行属性金大于3个（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70077': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['辛'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中辛数量3个以上（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70078': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['辛'],
                        'max': 0
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中辛数量0个以下（包含0个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70079': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['壬'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中壬数量3个以上（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70080': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['壬'],
                        'max': 0
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中壬数量0个以下（包含0个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70081': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['丙'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中丙数量3个以上（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70082': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['丙'],
                        'max': 0
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中丙数量0个以下（包含0个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70083': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['庚'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中庚数量3个以上（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70084': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['庚'],
                        'max': 0
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中庚数量0个以下（包含0个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70085': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['戊', '己'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中戊和己数量3个以上（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70086': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['戊', '己'],
                        'max': 0
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中戊和己数量0个以下（包含0个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70087': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['甲'],
                        'min': 3
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中甲数量3个以上（包含3个）',
            '性别': '无论男女'
        }
    },
    'FORMULA_身体_70088': {
        'conditions': {
            'all': [
                {
                    'stems_branches_count': {
                        'names': ['甲'],
                        'max': 0
                    }
                }
            ]
        },
        'description': {
            '筛选条件1': '天干地支',
            '筛选条件2': '天干地支中甲数量0个以下（包含0个）',
            '性别': '无论男女'
        }
    }
}

def fix_rules(dry_run=False):
    """修复规则条件"""
    conn = get_mysql_connection()
    try:
        with conn.cursor(DictCursor) as cursor:
            # 先检查这些规则是否存在
            rule_codes = list(RULE_FIXES.keys())
            placeholders = ','.join(['%s'] * len(rule_codes))
            cursor.execute(f"""
                SELECT rule_code, rule_name, conditions 
                FROM bazi_rules 
                WHERE rule_code IN ({placeholders})
                ORDER BY rule_code
            """, rule_codes)
            
            existing_rules = cursor.fetchall()
            print(f"找到 {len(existing_rules)} 条规则需要修复\n")
            
            if dry_run:
                print("=== DRY RUN 模式，不会修改数据库 ===\n")
            
            updated_count = 0
            not_found = []
            
            for rule_code, fix_data in RULE_FIXES.items():
                # 检查规则是否存在
                rule_exists = any(r.get('rule_code') == rule_code for r in existing_rules)
                
                if not rule_exists:
                    not_found.append(rule_code)
                    print(f"⚠️  规则不存在: {rule_code}")
                    continue
                
                conditions_json = json.dumps(fix_data['conditions'], ensure_ascii=False)
                description_json = json.dumps(fix_data.get('description', {}), ensure_ascii=False) if fix_data.get('description') else None
                
                if dry_run:
                    print(f"将修复规则: {rule_code}")
                    print(f"  新条件: {conditions_json[:200]}...")
                    if description_json:
                        print(f"  新描述: {description_json[:200]}...")
                else:
                    # 更新规则条件和描述
                    if description_json:
                        cursor.execute("""
                            UPDATE bazi_rules 
                            SET conditions = %s,
                                description = %s,
                                updated_at = NOW()
                            WHERE rule_code = %s
                        """, (conditions_json, description_json, rule_code))
                    else:
                    cursor.execute("""
                        UPDATE bazi_rules 
                        SET conditions = %s,
                            updated_at = NOW()
                        WHERE rule_code = %s
                    """, (conditions_json, rule_code))
                    
                    print(f"✅ 修复规则: {rule_code}")
                    updated_count += 1
            
            if not dry_run:
                conn.commit()
                print(f"\n✅ 共修复 {updated_count} 条规则")
            else:
                print(f"\n预览：将修复 {len(RULE_FIXES) - len(not_found)} 条规则")
            
            if not_found:
                print(f"\n⚠️  以下规则不存在: {', '.join(not_found)}")
                
    except Exception as e:
        if not dry_run:
            conn.rollback()
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        return_mysql_connection(conn)

def main():
    parser = argparse.ArgumentParser(description='修复规则 70067-70088 的条件格式')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不修改数据库')
    args = parser.parse_args()
    
    print("=" * 60)
    print("修复规则 70067-70088 的条件格式和描述")
    print("=" * 60)
    print(f"修复范围: FORMULA_身体_70067 到 FORMULA_身体_70088 (共 {len(RULE_FIXES)} 条规则)")
    print(f"修复内容:")
    print(f"  1. 修正条件值（70070/70071的火条件: min:4→min:3, 70076的金条件: min:4→min:3）")
    print(f"  2. 更新描述字段（'八字中' → '天干地支中'）")
    print(f"影响范围: 仅这22条规则，不影响其他规则")
    print("=" * 60)
    print()
    
    fix_rules(dry_run=args.dry_run)
    
    if not args.dry_run:
        print("\n✅ 修复完成！")
        print("⚠️  注意：修复后需要重启服务或清理规则缓存才能生效")

if __name__ == '__main__':
    main()

