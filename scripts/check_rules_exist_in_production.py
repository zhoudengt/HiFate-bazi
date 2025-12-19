#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案执行：检查生产数据库中是否存在本地匹配的63条规则
"""

import sys
import os
import json
import requests
from typing import Dict, List, Set

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
import pymysql.cursors


def get_local_matched_rules() -> List[Dict]:
    """获取本地匹配的63条规则"""
    print("="*80)
    print("步骤 1: 获取本地匹配的63条规则")
    print("="*80)
    
    try:
        from server.services.bazi_service import BaziService
        from server.services.rule_service import RuleService
        
        # 计算八字
        bazi_result = BaziService.calculate_bazi_full(
            solar_date="1987-01-07",
            solar_time="09:00",
            gender="male"
        )
        bazi_data = bazi_result.get('bazi', {})
        
        # 构建规则匹配数据
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': bazi_data.get('element_counts', {}),
            'relationships': bazi_data.get('relationships', {})
        }
        
        # 匹配规则
        rule_types = ['wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents']
        matched_rules = RuleService.match_rules(rule_data, rule_types=rule_types, use_cache=False)
        
        # 只保留 FORMULA_ 前缀的规则
        formula_rules = [r for r in matched_rules if r.get('rule_id', '').startswith('FORMULA_')]
        
        print(f"\n✅ 本地匹配到 {len(formula_rules)} 条 FORMULA_ 规则")
        
        # 提取 rule_code 列表
        rule_codes = [r.get('rule_id', '') for r in formula_rules]
        
        print(f"\n规则列表（前10条）:")
        for i, code in enumerate(rule_codes[:10], 1):
            print(f"  {i}. {code}")
        if len(rule_codes) > 10:
            print(f"  ... 还有 {len(rule_codes) - 10} 条")
        
        return formula_rules, rule_codes
        
    except Exception as e:
        print(f"❌ 获取本地规则失败: {e}")
        import traceback
        traceback.print_exc()
        return [], []


def check_rules_in_production_db(rule_codes: List[str]) -> Dict:
    """检查生产数据库中是否存在这些规则"""
    print("\n" + "="*80)
    print("步骤 2: 检查生产数据库中是否存在这些规则")
    print("="*80)
    
    # 由于无法直接连接生产数据库，通过 API 间接检查
    print("\n📡 通过 API 检查生产环境...")
    
    # 测试生产环境 API
    test_case = {
        'solar_date': '1987-01-07',
        'solar_time': '09:00',
        'gender': 'male'
    }
    
    try:
        url = "http://8.210.52.217:8001/api/v1/bazi/formula-analysis"
        response = requests.post(url, json=test_case, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        prod_matched_rules = result.get('data', {}).get('matched_rules', {})
        prod_rule_details = result.get('data', {}).get('rule_details', {})
        
        # 提取生产环境匹配的 rule_code（从 rule_details 中）
        prod_rule_codes = set()
        for rule_id, details in prod_rule_details.items():
            # rule_id 是数字，需要转换为 FORMULA_ 格式
            # 从 details 中获取类型，然后构造 rule_code
            rule_type_cn = details.get('类型', '')
            rule_type_map = {
                '财富': 'wealth',
                '婚姻': 'marriage',
                '事业': 'career',
                '子女': 'children',
                '性格': 'character',
                '总评': 'summary',
                '身体': 'health',
                '桃花': 'peach_blossom',
                '十神命格': 'shishen',
                '父母': 'parents'
            }
            rule_type = rule_type_map.get(rule_type_cn, '')
            if rule_type:
                # 构造可能的 rule_code（需要从数据库查询确认）
                prod_rule_codes.add(f"FORMULA_{rule_type_cn}_{rule_id}")
        
        print(f"\n✅ 生产环境匹配到 {len(prod_rule_codes)} 条规则（通过 API）")
        
        # 对比
        local_codes_set = set(rule_codes)
        missing_codes = local_codes_set - prod_rule_codes
        
        print(f"\n📊 对比结果:")
        print(f"  本地规则数: {len(local_codes_set)}")
        print(f"  生产规则数: {len(prod_rule_codes)}")
        print(f"  缺失规则数: {len(missing_codes)}")
        
        if missing_codes:
            print(f"\n⚠️  发现 {len(missing_codes)} 条规则在生产环境中缺失")
            print(f"\n缺失规则示例（前10条）:")
            for i, code in enumerate(list(missing_codes)[:10], 1):
                print(f"  {i}. {code}")
            if len(missing_codes) > 10:
                print(f"  ... 还有 {len(missing_codes) - 10} 条")
            
            return {
                'exists': False,
                'missing_count': len(missing_codes),
                'missing_codes': list(missing_codes)
            }
        else:
            print(f"\n✅ 所有规则在生产环境中都存在")
            return {
                'exists': True,
                'missing_count': 0
            }
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return {'exists': None, 'error': str(e)}


def check_production_db_directly(rule_codes: List[str]) -> Dict:
    """直接检查生产数据库（如果可以通过 SSH）"""
    print("\n" + "="*80)
    print("步骤 2（备选）: 直接检查生产数据库")
    print("="*80)
    
    print("\n💡 需要通过 SSH 连接生产环境数据库")
    print("执行以下命令检查:")
    print(f"  ssh root@8.210.52.217")
    print(f"  cd /opt/HiFate-bazi")
    print(f"  docker exec hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi -e")
    codes_str = "','".join(rule_codes[:10])
    print(f"    \"SELECT rule_code FROM bazi_rules WHERE rule_code IN ('{codes_str}');\"")
    
    return {'method': 'ssh_required'}


def sync_missing_rules(missing_codes: List[str]):
    """同步缺失的规则到生产环境"""
    print("\n" + "="*80)
    print("步骤 3: 同步缺失的规则到生产环境")
    print("="*80)
    
    if not missing_codes:
        print("✅ 没有缺失的规则，跳过同步")
        return
    
    print(f"\n需要同步 {len(missing_codes)} 条规则")
    print(f"\n💡 执行同步:")
    print(f"  scp scripts/temp_rules_export.sql root@8.210.52.217:/tmp/rules_import.sql")
    print(f"  ssh root@8.210.52.217 'cd /opt/HiFate-bazi && docker exec -i hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi < /tmp/rules_import.sql'")


def compare_code_logic():
    """对比代码逻辑"""
    print("\n" + "="*80)
    print("步骤 4: 对比代码逻辑")
    print("="*80)
    
    key_files = [
        'server/api/v1/formula_analysis.py',
        'server/services/rule_service.py',
        'server/engines/rule_engine.py'
    ]
    
    print("\n检查关键代码文件:")
    for file_path in key_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            print(f"  ✅ {file_path}")
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查关键逻辑
                if 'RuleService.match_rules' in content:
                    print(f"    ✅ 使用 RuleService.match_rules")
                if 'FORMULA_' in content and 'startswith' in content:
                    print(f"    ✅ 筛选 FORMULA_ 前缀规则")
                if 'enabled = 1' in content or 'enabled = True' in content:
                    print(f"    ✅ 过滤 enabled 规则")
        else:
            print(f"  ❌ {file_path} - 文件不存在")
    
    print("\n✅ 代码逻辑检查完成")


def check_frontend():
    """检查前端展示"""
    print("\n" + "="*80)
    print("步骤 5: 检查前端展示")
    print("="*80)
    
    frontend_file = os.path.join(project_root, 'local_frontend/formula-analysis.html')
    
    if os.path.exists(frontend_file):
        print(f"\n✅ 前端文件存在: {frontend_file}")
        
        with open(frontend_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查关键字段
            key_fields = ['total_matched', 'wealth_count', 'career_count', 'health_count', 'summary_count']
            print(f"\n检查统计字段:")
            all_ok = True
            for field in key_fields:
                if field in content:
                    print(f"  ✅ {field}")
                else:
                    print(f"  ❌ {field} - 未找到")
                    all_ok = False
            
            # 检查 API 路径
            if '/bazi/formula-analysis' in content:
                print(f"\n✅ API 路径正确")
            else:
                print(f"\n⚠️  API 路径可能错误")
                all_ok = False
            
            if all_ok:
                print(f"\n✅ 前端展示逻辑正常")
            else:
                print(f"\n⚠️  前端展示可能有问题")
    else:
        print(f"\n❌ 前端文件不存在: {frontend_file}")


def main():
    """主函数 - 按照用户方案执行"""
    print("="*80)
    print("🔍 按照方案执行：检查规则是否存在，对比代码逻辑，检查前端")
    print("="*80)
    
    # 步骤 1: 获取本地匹配的63条规则
    local_rules, rule_codes = get_local_matched_rules()
    
    if not rule_codes:
        print("❌ 无法获取本地规则，退出")
        return
    
    # 步骤 2: 检查生产数据库中是否存在这些规则
    check_result = check_rules_in_production_db(rule_codes)
    
    if check_result.get('exists') is False:
        # 规则不存在，需要同步
        print(f"\n{'='*80}")
        print("🔴 结论: 生产数据库中缺少规则")
        print(f"{'='*80}")
        print(f"缺失 {check_result.get('missing_count', 0)} 条规则")
        
        # 步骤 3: 同步缺失的规则
        sync_missing_rules(check_result.get('missing_codes', []))
        
        print(f"\n💡 执行修复:")
        print(f"  scp scripts/temp_rules_export.sql root@8.210.52.217:/tmp/rules_import.sql")
        print(f"  ssh root@8.210.52.217 'cd /opt/HiFate-bazi && docker exec -i hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi < /tmp/rules_import.sql && curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check'")
        
    elif check_result.get('exists') is True:
        # 规则存在，对比代码逻辑
        print(f"\n{'='*80}")
        print("✅ 结论: 生产数据库中规则存在")
        print(f"{'='*80}")
        
        # 步骤 4: 对比代码逻辑
        compare_code_logic()
        
        # 步骤 5: 检查前端
        check_frontend()
        
        print(f"\n💡 如果规则存在但匹配数量不同，可能原因:")
        print(f"  1. 规则 enabled 状态不同")
        print(f"  2. 规则匹配逻辑有差异")
        print(f"  3. 缓存影响")
    else:
        print(f"\n⚠️  无法确定规则是否存在（API 检查失败）")
        print(f"💡 建议直接同步规则确保一致性")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  执行被中断")
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()

