# -*- coding: utf-8 -*-
"""
面相规则V2导入脚本
从JSON文件导入规则到数据库
"""

import json
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pymysql
from server.config.mysql_config import MYSQL_CONFIG


class FaceRuleImporter:
    def __init__(self):
        self.connection = None
        self.cursor = None
        
    def connect_db(self):
        """连接数据库"""
        try:
            self.connection = pymysql.connect(
                host=MYSQL_CONFIG['host'],
                port=MYSQL_CONFIG['port'],
                user=MYSQL_CONFIG['user'],
                password=MYSQL_CONFIG['password'],
                database=MYSQL_CONFIG['database'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self.cursor = self.connection.cursor()
            print("✓ 数据库连接成功")
        except Exception as e:
            print(f"❌ 数据库连接失败：{e}")
            sys.exit(1)
    
    def close_db(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
    
    def load_json_rules(self, json_file):
        """加载JSON规则文件"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✓ 加载规则文件：{json_file}")
            return data
        except Exception as e:
            print(f"❌ 加载文件失败 {json_file}: {e}")
            return None
    
    def import_rules(self, rules_data, rule_category):
        """导入规则到数据库"""
        imported_count = 0
        
        # 获取规则列表
        rules_list = None
        for key in rules_data.keys():
            if isinstance(rules_data[key], list):
                rules_list = rules_data[key]
                break
        
        if not rules_list:
            print(f"⚠️  未找到规则列表")
            return 0
        
        for rule in rules_list:
            try:
                # 提取规则信息
                rule_type = rule.get('rule_type', '')
                position = rule.get('position', '')
                position_code = rule.get('position_code', '')
                conditions = json.dumps(rule.get('conditions', {}), ensure_ascii=False)
                priority = rule.get('priority', 50)
                
                # 处理多个断语
                interpretations = rule.get('interpretations', [])
                for interp in interpretations:
                    interpretation_text = interp.get('interpretation', '')
                    category = interp.get('category', rule_category)
                    feature = interp.get('feature', '')
                    
                    # 构建完整条件（包含特征）
                    full_conditions = rule.get('conditions', {}).copy()
                    if feature:
                        full_conditions['feature'] = feature
                    conditions_json = json.dumps(full_conditions, ensure_ascii=False)
                    
                    # 插入数据库
                    sql = """
                        INSERT INTO face_rules_v2 
                        (rule_type, position, position_code, conditions, 
                         interpretation, category, priority, enabled)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                    """
                    
                    self.cursor.execute(sql, (
                        rule_type, position, position_code, conditions_json,
                        interpretation_text, category, priority
                    ))
                    imported_count += 1
            
            except Exception as e:
                print(f"⚠️  导入规则失败：{e}")
                print(f"   规则：{rule.get('position', 'unknown')}")
                continue
        
        self.connection.commit()
        return imported_count
    
    def run(self, data_dir):
        """执行导入"""
        print("="*50)
        print("面相规则V2 数据导入")
        print("="*50)
        
        self.connect_db()
        
        # 定义规则文件和类别
        rule_files = [
            ('gongwei_rules.json', '十三宫位'),
            ('liuqin_rules.json', '六亲'),
            ('shishen_rules.json', '十神'),
            ('feature_rules.json', '特征'),
            ('liunian_rules.json', '流年')
        ]
        
        total_imported = 0
        
        for filename, category in rule_files:
            file_path = os.path.join(data_dir, filename)
            
            if not os.path.exists(file_path):
                print(f"⚠️  文件不存在：{file_path}")
                continue
            
            print(f"\n导入 {category} 规则...")
            rules_data = self.load_json_rules(file_path)
            
            if rules_data:
                count = self.import_rules(rules_data, category)
                print(f"✓ 成功导入 {count} 条规则")
                total_imported += count
        
        print(f"\n{'='*50}")
        print(f"✅ 导入完成！共导入 {total_imported} 条规则")
        print(f"{'='*50}")
        
        self.close_db()


def main():
    # 数据目录
    data_dir = os.path.join(project_root, 'data', 'face_rules_v2')
    
    if not os.path.exists(data_dir):
        print(f"❌ 数据目录不存在：{data_dir}")
        sys.exit(1)
    
    importer = FaceRuleImporter()
    importer.run(data_dir)


if __name__ == '__main__':
    main()

