#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五行行业数据导入脚本
将用户提供的行业数据导入到 wuxing_industries 表

使用方法：
  python scripts/migration/import_wuxing_industries.py --dry-run  # 预览
  python scripts/migration/import_wuxing_industries.py            # 正式导入
"""

import sys
import os
import argparse
import json
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

# 用户提供的行业数据
INDUSTRY_DATA = {
    '金': {
        'description': '适合逻辑清晰、决断力强的人',
        'categories': [
            {
                'name': '金融财务类',
                'industries': ['银行', '证券', '保险', '投资', '会计', '精算', '审计']
            },
            {
                'name': '法律政法类',
                'industries': ['律师', '法官', '检察官', '警察', '安全顾问']
            },
            {
                'name': '机械技术类',
                'industries': ['机械制造', '精密仪器', '电子设备', '汽车工业', '航空航天']
            },
            {
                'name': '医疗健康类',
                'industries': ['外科医生', '牙医', '医疗器械', '整形美容']
            },
            {
                'name': '商业管理类',
                'industries': ['企业管理', '质量管理', '战略规划', '市场监管']
            }
        ]
    },
    '木': {
        'description': '适合创造力强、善于培育的人',
        'categories': [
            {
                'name': '文化教育类',
                'industries': ['教师', '出版', '写作', '教育培训', '学术研究', '图书馆']
            },
            {
                'name': '设计创意类',
                'industries': ['服装设计', '室内设计', '园林设计', '广告创意']
            },
            {
                'name': '农林环保类',
                'industries': ['林业', '园艺', '生态修复', '可持续能源', '有机农业']
            },
            {
                'name': '医疗保健类',
                'industries': ['中医', '中药', '养生', '心理咨询', '康复治疗']
            },
            {
                'name': '慈善公益类',
                'industries': ['NGO 组织', '社会服务', '志愿者管理']
            }
        ]
    },
    '水': {
        'description': '适合思维敏捷、适应力强的人',
        'categories': [
            {
                'name': '物流运输类',
                'industries': ['物流', '航运', '快递', '供应链管理', '港口运营']
            },
            {
                'name': '贸易商务类',
                'industries': ['国际贸易', '跨境电商', '采购', '销售', '市场开发']
            },
            {
                'name': '媒体传播类',
                'industries': ['记者', '主持人', '新媒体运营', '广告策划']
            },
            {
                'name': '旅游服务类',
                'industries': ['导游', '酒店', '旅行社', '度假村管理']
            },
            {
                'name': '咨询研究类',
                'industries': ['顾问', '市场调研', '数据分析', '智库机构']
            },
            {
                'name': '技术研发类',
                'industries': ['IT 开发', '软件设计', '系统集成']
            }
        ]
    },
    '火': {
        'description': '适合热情洋溢、表达能力强的人',
        'categories': [
            {
                'name': '娱乐传媒类',
                'industries': ['影视制作', '演艺', '音乐', '直播', '自媒体', '内容创作']
            },
            {
                'name': '能源电力类',
                'industries': ['电力', '新能源', '照明', '燃气', '热能工程']
            },
            {
                'name': '餐饮烹饪类',
                'industries': ['厨师', '餐厅经营', '烘焙', '食品加工']
            },
            {
                'name': '美容美妆类',
                'industries': ['美发', '化妆', '美甲', '形象设计', 'SPA']
            },
            {
                'name': '教育培训类',
                'industries': ['演讲培训', '营销培训', '主持人培训']
            },
            {
                'name': '心理医疗类',
                'industries': ['心理咨询', '婚姻辅导', '情感治疗']
            }
        ]
    },
    '土': {
        'description': '适合踏实稳重、责任感强的人',
        'categories': [
            {
                'name': '房地产建筑类',
                'industries': ['房地产开发', '建筑工程', '物业管理', '室内装修']
            },
            {
                'name': '农业资源类',
                'industries': ['农业', '畜牧业', '林业资源开发', '土地评估']
            },
            {
                'name': '矿产建材类',
                'industries': ['矿产开发', '石材加工', '水泥', '砖瓦制造']
            },
            {
                'name': '仓储物流类',
                'industries': ['仓库管理', '物流基础设施', '供应链支撑']
            },
            {
                'name': '人力资源类',
                'industries': ['HR', '招聘', '培训', '组织发展', '企业文化']
            },
            {
                'name': '金融地产类',
                'industries': ['不动产投资', '资产评估', '抵押担保']
            }
        ]
    }
}


def generate_insert_statements(dry_run: bool = False) -> List[Dict[str, Any]]:
    """
    生成插入语句数据
    
    Returns:
        List[Dict]: 插入数据列表
    """
    insert_data = []
    priority_base = 100
    
    for element, element_data in INDUSTRY_DATA.items():
        description = element_data['description']
        categories = element_data['categories']
        
        category_priority = 0
        for category_info in categories:
            category_name = category_info['name']
            industries = category_info['industries']
            
            industry_priority = 0
            for industry_name in industries:
                insert_data.append({
                    'element': element,
                    'category': category_name,
                    'industry_name': industry_name,
                    'description': description,
                    'priority': priority_base + category_priority * 10 + industry_priority,
                    'enabled': 1
                })
                industry_priority += 1
            
            category_priority += 1
    
    return insert_data


def import_industries(dry_run: bool = False) -> tuple[int, int]:
    """
    导入行业数据到数据库
    
    Args:
        dry_run: 是否为预览模式
        
    Returns:
        (inserted_count, updated_count): 插入和更新的数量
    """
    insert_data = generate_insert_statements(dry_run)
    
    if dry_run:
        print("=== DRY RUN 模式，不会修改数据库 ===\n")
        print(f"将导入 {len(insert_data)} 条行业数据：\n")
        
        # 按五行分组显示
        for element in ['金', '木', '水', '火', '土']:
            element_data = [d for d in insert_data if d['element'] == element]
            if element_data:
                print(f"\n【{element}行职业】({len(element_data)}条)")
                current_category = None
                for data in element_data:
                    if data['category'] != current_category:
                        current_category = data['category']
                        print(f"  {current_category}:")
                    print(f"    - {data['industry_name']}")
        
        return 0, 0
    
    conn = get_mysql_connection()
    inserted = 0
    updated = 0
    
    try:
        with conn.cursor() as cursor:
            for data in insert_data:
                # 检查是否已存在（根据 element + category + industry_name）
                cursor.execute("""
                    SELECT id FROM wuxing_industries 
                    WHERE element = %s AND category = %s AND industry_name = %s
                """, (data['element'], data['category'], data['industry_name']))
                
                existing = cursor.fetchone()
                
                if existing:
                    # 更新
                    cursor.execute("""
                        UPDATE wuxing_industries SET
                            description = %s,
                            priority = %s,
                            enabled = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (
                        data['description'],
                        data['priority'],
                        data['enabled'],
                        existing['id']
                    ))
                    updated += 1
                else:
                    # 插入
                    cursor.execute("""
                        INSERT INTO wuxing_industries 
                        (element, category, industry_name, description, priority, enabled)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        data['element'],
                        data['category'],
                        data['industry_name'],
                        data['description'],
                        data['priority'],
                        data['enabled']
                    ))
                    inserted += 1
        
        conn.commit()
        print(f"✅ 导入完成：新增 {inserted} 条，更新 {updated} 条")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        return_mysql_connection(conn)
    
    return inserted, updated


def main():
    parser = argparse.ArgumentParser(description='导入五行行业数据')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不修改数据库')
    args = parser.parse_args()
    
    print("=" * 80)
    print("五行行业数据导入脚本")
    print("=" * 80)
    print()
    
    inserted, updated = import_industries(dry_run=args.dry_run)
    
    if not args.dry_run:
        print(f"\n导入结果：")
        print(f"  - 新增: {inserted} 条")
        print(f"  - 更新: {updated} 条")
        print(f"  - 总计: {inserted + updated} 条")


if __name__ == '__main__':
    main()

