#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本：将配置文件迁移到数据库
"""

import sys
import os
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.config.rizhu_gender_config import RIZHU_GENDER_CONFIG
from server.db.rule_content_dao import RuleContentDAO


def migrate_rizhu_gender_config():
    """将配置文件迁移到数据库"""
    print("=" * 60)
    print("开始迁移日柱性别配置到数据库...")
    print("=" * 60)
    
    total_count = len(RIZHU_GENDER_CONFIG)
    success_count = 0
    failed_count = 0
    
    print(f"\n待迁移记录数: {total_count}")
    print("\n开始迁移...")
    
    for idx, ((rizhu, gender), descriptions) in enumerate(RIZHU_GENDER_CONFIG.items(), 1):
        try:
            success = RuleContentDAO.save_rizhu_gender_content(rizhu, gender, descriptions)
            if success:
                success_count += 1
                if idx % 10 == 0:
                    print(f"  进度: {idx}/{total_count} ({idx*100//total_count}%)")
            else:
                failed_count += 1
                print(f"  ⚠ 迁移失败: {rizhu} {gender}")
        except Exception as e:
            failed_count += 1
            print(f"  ✗ 迁移失败: {rizhu} {gender} - {e}")
    
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print(f"总计: {total_count}")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    
    # 显示版本号
    try:
        content_version = RuleContentDAO.get_content_version()
        print(f"\n当前内容版本号: {content_version}")
    except Exception as e:
        print(f"\n⚠ 获取版本号失败: {e}")
    
    return success_count, failed_count


def verify_migration():
    """验证迁移结果"""
    print("\n" + "=" * 60)
    print("验证迁移结果...")
    print("=" * 60)
    
    # 检查几个示例
    test_cases = [
        ('甲子', 'male'),
        ('甲子', 'female'),
        ('乙丑', 'male'),
        ('乙丑', 'female'),
    ]
    
    all_ok = True
    for rizhu, gender in test_cases:
        descriptions = RuleContentDAO.get_rizhu_gender_content(rizhu, gender)
        if descriptions:
            print(f"  ✓ {rizhu} {gender}: {len(descriptions)} 条描述")
        else:
            print(f"  ✗ {rizhu} {gender}: 未找到数据")
            all_ok = False
    
    if all_ok:
        print("\n✓ 验证通过！")
    else:
        print("\n⚠ 验证失败，请检查数据")
    
    return all_ok


if __name__ == "__main__":
    try:
        # 执行迁移
        success_count, failed_count = migrate_rizhu_gender_config()
        
        # 验证迁移
        if success_count > 0:
            verify_migration()
        
        if failed_count == 0:
            print("\n✓ 所有数据迁移成功！")
            sys.exit(0)
        else:
            print(f"\n⚠ 有 {failed_count} 条数据迁移失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ 迁移过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)








































