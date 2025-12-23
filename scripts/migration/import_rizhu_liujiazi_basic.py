#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入基础六十甲子数据到数据库（临时方案）

由于没有Excel文件，使用标准的60甲子数据创建基础记录。
注意：这些是基础数据，解析内容需要后续补充。

使用方法：
  python scripts/migration/import_rizhu_liujiazi_basic.py
"""

import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection

# 六十甲子标准数据（天干地支组合）
TIAN_GAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
DI_ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

# 生成60甲子
def generate_60_jiazi():
    """生成60甲子列表"""
    jiazi_list = []
    gan_idx = 0
    zhi_idx = 0
    
    for i in range(60):
        gan = TIAN_GAN[gan_idx]
        zhi = DI_ZHI[zhi_idx]
        rizhu = f"{gan}{zhi}"
        jiazi_list.append({
            'id': i + 1,
            'rizhu': rizhu,
            'analysis': f"日柱 {rizhu} 的解析内容待补充。\n\n这是基础数据，完整的解析内容需要从Excel文件导入。"
        })
        
        gan_idx = (gan_idx + 1) % 10
        zhi_idx = (zhi_idx + 1) % 12
    
    return jiazi_list


def import_basic_data():
    """导入基础数据"""
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            print("❌ 无法连接数据库")
            return
        
        jiazi_list = generate_60_jiazi()
        
        print(f"\n📊 准备导入 {len(jiazi_list)} 条基础数据...")
        
        inserted = 0
        updated = 0
        
        with conn.cursor() as cursor:
            for item in jiazi_list:
                # 检查是否存在
                cursor.execute(
                    "SELECT id FROM rizhu_liujiazi WHERE id = %s OR rizhu = %s",
                    (item['id'], item['rizhu'])
                )
                existing = cursor.fetchone()
                
                if existing:
                    # 更新
                    cursor.execute("""
                        UPDATE rizhu_liujiazi SET
                            rizhu = %s,
                            analysis = %s,
                            enabled = TRUE
                        WHERE id = %s
                    """, (item['rizhu'], item['analysis'], item['id']))
                    updated += 1
                    print(f"  ✓ 更新: ID={item['id']}, 日柱={item['rizhu']}")
                else:
                    # 插入
                    cursor.execute("""
                        INSERT INTO rizhu_liujiazi (id, rizhu, analysis, enabled)
                        VALUES (%s, %s, %s, TRUE)
                    """, (item['id'], item['rizhu'], item['analysis']))
                    inserted += 1
                    print(f"  ✓ 插入: ID={item['id']}, 日柱={item['rizhu']}")
        
        conn.commit()
        
        print(f"\n✅ 导入完成:")
        print(f"   新增: {inserted} 条")
        print(f"   更新: {updated} 条")
        print(f"   总计: {inserted + updated} 条")
        print(f"\n⚠️  注意: 这是基础数据，解析内容需要从Excel文件补充。")
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn:
            return_mysql_connection(conn)


if __name__ == '__main__':
    print("=" * 60)
    print("导入基础六十甲子数据")
    print("=" * 60)
    import_basic_data()

