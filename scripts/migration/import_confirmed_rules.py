#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入已确认的25条规则到数据库
根据用户确认的条件修改

执行方式: MYSQL_DATABASE=hifate_bazi python3 scripts/migration/import_confirmed_rules.py
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


# 需要删除的规则（3条）
RULES_TO_DELETE = ["FORMULA_事业_80022", "FORMULA_事业_80023", "FORMULA_事业_80033"]

# 需要导入的规则（22条）
RULES_TO_IMPORT = [
    # 20127 - 财富
    {
        "rule_code": "FORMULA_财富_20127",
        "rule_name": "财富规则-20127",
        "rule_type": "formula_wealth",
        "rule_category": "财富",
        "priority": 100,
        "conditions": {
            "all": [
                {"branches_count": {"names": ["辰", "戌", "丑", "未"], "min": 2, "max": 2}},
                {"not": {"all": [
                    {"branches_count": {"names": ["辰"], "min": 1}},
                    {"branches_count": {"names": ["戌"], "min": 1}}
                ]}},
                {"not": {"all": [
                    {"branches_count": {"names": ["丑"], "min": 1}},
                    {"branches_count": {"names": ["未"], "min": 1}}
                ]}}
            ]
        },
        "content": {"type": "text", "text": "人生跌宕起伏，时而财源广进，时而穷困潦倒，犹如过山车，人生的各方面考验都比较多。"},
        "description": "四柱有辰、戌、丑、未其中两个，但是辰和戌不能同时出现或丑和未不能同时出现"
    },
    
    # 80002 - 事业
    {
        "rule_code": "FORMULA_事业_80002",
        "rule_name": "事业规则-80002",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"ten_gods_main": {"names": ["食神", "伤官"], "min": 2}},
                {"ten_gods_main_chong_count": {"min": 2}}
            ]
        },
        "content": {"type": "text", "text": "宜后求利先求名。"},
        "description": "四柱主星食神和伤官，被其他柱主星形成2次以上冲的关系"
    },
    
    # 80030 - 事业
    {
        "rule_code": "FORMULA_事业_80030",
        "rule_name": "事业规则-80030",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"branch_sanxing": True},
                {"deities_in_any_pillar": "天乙贵人"}
            ]
        },
        "content": {"type": "text", "text": "任职法刑干警卫。"},
        "description": "十二地支有三刑关系，同时神煞又带天乙贵人"
    },
    
    # 80015 - 事业
    {
        "rule_code": "FORMULA_事业_80015",
        "rule_name": "事业规则-80015",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"gender": "female"},
                {"star_fortune_in_day": "帝旺"},
                {"any": [
                    {"main_star_in_day": "七杀"},
                    {"ten_gods_sub": {"names": ["七杀"], "pillars": ["day"], "min": 1}}
                ]}
            ]
        },
        "content": {"type": "text", "text": "女中王。"},
        "description": "日支坐帝旺，日柱同时有七杀"
    },
    
    # 80018 - 事业
    {
        "rule_code": "FORMULA_事业_80018",
        "rule_name": "事业规则-80018",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"any": [
                    {"star_fortune_in_hour": ["死", "绝"]},
                    {"star_fortune_in_day": ["死", "绝"]}
                ]}
            ]
        },
        "content": {"type": "text", "text": "老无成就事业败。"},
        "description": "时支和日支十二长生为死或绝"
    },
    
    # 80019 - 事业
    {
        "rule_code": "FORMULA_事业_80019",
        "rule_name": "事业规则-80019",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "star_fortune_in_day": "绝"
        },
        "content": {"type": "text", "text": "成就之时随即败。"},
        "description": "日支坐绝地（流年条件暂不支持）"
    },
    
    # 80020 - 事业
    {
        "rule_code": "FORMULA_事业_80020",
        "rule_name": "事业规则-80020",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "star_fortune_in_day": "墓"
        },
        "content": {"type": "text", "text": "四柱自坐墓库之人，做事需时刻敲打自己，打起精神。"},
        "description": "日柱的十二长生自坐是墓库"
    },
    
    # 80021 - 事业
    {
        "rule_code": "FORMULA_事业_80021",
        "rule_name": "事业规则-80021",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "star_fortune_in_day": "墓"
        },
        "content": {"type": "text", "text": "墓库之人能守财，但容易固执保守。"},
        "description": "日柱的十二长生自坐是墓库"
    },
    
    # 80014 - 事业 (喜用神)
    {
        "rule_code": "FORMULA_事业_80014",
        "rule_name": "事业规则-80014",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"wangshuai": ["身弱"]},
                {"xishen": "比肩"}
            ]
        },
        "content": {"type": "text", "text": "才能高人一倍多。只是大器晚成就，事业晚年结硕果。"},
        "description": "身弱之人，十神中比肩为喜用"
    },
    
    # 80029 - 事业 (喜用神)
    {
        "rule_code": "FORMULA_事业_80029",
        "rule_name": "事业规则-80029",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"ten_gods_total": {"names": ["食神", "伤官"], "min": 2}},
                {"xishen_in": ["食神", "伤官"]}
            ]
        },
        "content": {"type": "text", "text": "艺术专长有科名。"},
        "description": "十神出现多个食神或伤官，同时又为喜用神"
    },
    
    # 80027 - 事业
    {
        "rule_code": "FORMULA_事业_80027",
        "rule_name": "事业规则-80027",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"deities_in_year": "文昌贵人"},
                {"deities_in_month": "文昌贵人"}
            ]
        },
        "content": {"type": "text", "text": "文教部门缘分广。"},
        "description": "年支月支都有神煞文昌贵人"
    },
    
    # 80028 - 事业
    {
        "rule_code": "FORMULA_事业_80028",
        "rule_name": "事业规则-80028",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "deities_same_pillar": ["天乙贵人", "亡神"]
        },
        "content": {"type": "text", "text": "必与文教有缘分。"},
        "description": "同一柱同时存在天乙贵人和亡神"
    },
    
    # 80039 - 事业
    {
        "rule_code": "FORMULA_事业_80039",
        "rule_name": "事业规则-80039",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "deities_same_pillar": ["华盖", "空亡"]
        },
        "content": {"type": "text", "text": "为道僧，秉性孤僻喜清静。"},
        "description": "华盖与空亡在同柱出现"
    },
    
    # 80043 - 事业
    {
        "rule_code": "FORMULA_事业_80043",
        "rule_name": "事业规则-80043",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "any": [
                {"deities_in_day": "华盖"},
                {"deities_in_hour": "华盖"}
            ]
        },
        "content": {"type": "text", "text": "挟持一技走江湖。"},
        "description": "日柱有神煞华盖或时柱有神煞华盖"
    },
    
    # 80052 - 事业
    {
        "rule_code": "FORMULA_事业_80052",
        "rule_name": "事业规则-80052",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"branches_count": {"names": ["子"], "min": 3}},
                {"deities_in_any_pillar": "空亡"}
            ]
        },
        "content": {"type": "text", "text": "宜入佛门僧人当。"},
        "description": "地支出现3个以上子（包含3个），同柱出现空亡"
    },
    
    # 80053 - 事业
    {
        "rule_code": "FORMULA_事业_80053",
        "rule_name": "事业规则-80053",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "deities_same_pillar": ["天乙贵人", "空亡"]
        },
        "content": {"type": "text", "text": "必进寺院入佛堂。"},
        "description": "天乙贵人和空亡出现在同一柱上"
    },
    
    # 80034 - 事业
    {
        "rule_code": "FORMULA_事业_80034",
        "rule_name": "事业规则-80034",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"ten_gods_main": {"names": ["食神"], "min": 1}},
                {"ten_gods_sub": {"names": ["比肩", "劫财", "七杀"], "min": 1}}
            ]
        },
        "content": {"type": "text", "text": "钳工扒手顺牵羊。"},
        "description": "主星是食神，且副星有比劫或七杀"
    },
    
    # 80037 - 事业
    {
        "rule_code": "FORMULA_事业_80037",
        "rule_name": "事业规则-80037",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"deities_same_pillar": ["华盖", "空亡"]},
                {"pillar_branch_xing_chong": True}
            ]
        },
        "content": {"type": "text", "text": "怀一绝技江湖中。"},
        "description": "华盖、空亡同柱，且该柱地支被刑冲"
    },
    
    # 80054 - 事业
    {
        "rule_code": "FORMULA_事业_80054",
        "rule_name": "事业规则-80054",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"stem_wuhe_pairs": {"min": 1}},
                {"deities_in_any_pillar": "空亡"}
            ]
        },
        "content": {"type": "text", "text": "不为道士则为僧。"},
        "description": "天干至少有一对五合，同时地支神煞又出现空亡"
    },
    
    # 80055 - 事业
    {
        "rule_code": "FORMULA_事业_80055",
        "rule_name": "事业规则-80055",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "all": [
                {"ten_gods_main": {"names": ["食神", "伤官"], "eq": 0}},
                {"deities_in_any_pillar": "空亡"}
            ]
        },
        "content": {"type": "text", "text": "江湖术士走四方。苦学深钻劳心神，小有名气八方扬。"},
        "description": "天干主星没有食神或伤官，同时地支神煞出现空亡"
    },
    
    # 80045 - 事业
    {
        "rule_code": "FORMULA_事业_80045",
        "rule_name": "事业规则-80045",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "branches_count": {"names": ["子", "午", "卯", "酉", "寅", "申", "亥", "辰", "巳", "戌"], "min": 3}
        },
        "content": {"type": "text", "text": "不论文化大与小，研究易经是奇才。"},
        "description": "子、午、卯、酉、寅、申、亥、辰、巳、戌出现任意三个"
    },
    
    # 80046 - 事业
    {
        "rule_code": "FORMULA_事业_80046",
        "rule_name": "事业规则-80046",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "stems_branches_count": {"names": ["壬", "癸", "亥", "子", "丑", "寅"], "min": 3}
        },
        "content": {"type": "text", "text": "一代名流多漂泊，宗教五术有缘分。"},
        "description": "壬、癸、亥、子、丑、寅柱见三个以上"
    },
    
    # 80047 - 事业
    {
        "rule_code": "FORMULA_事业_80047",
        "rule_name": "事业规则-80047",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "branches_count": {"names": ["辰", "戌", "巳", "亥"], "min": 1}
        },
        "content": {"type": "text", "text": "信奉教门好学玄。"},
        "description": "辰、戌、巳、亥见一个以上"
    },
    
    # 80050 - 事业 (胎元身宫命宫 - 需要规则引擎扩展支持)
    {
        "rule_code": "FORMULA_事业_80050",
        "rule_name": "事业规则-80050",
        "rule_type": "formula_career",
        "rule_category": "事业",
        "priority": 100,
        "conditions": {
            "taiyuan_shengong_minggong": {
                "taiyuan": "癸丑",
                "minggong": "甲寅"
            }
        },
        "content": {"type": "text", "text": "必送寺庙入佛门。"},
        "description": "癸丑、甲寅胎命身（需要规则引擎扩展支持）"
    },
]


def main():
    """执行规则导入"""
    print("=" * 60)
    print("导入已确认的规则到数据库")
    print("=" * 60)
    
    try:
        from server.config.mysql_config import get_mysql_connection
        conn = get_mysql_connection()
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return
    
    deleted_count = 0
    inserted_count = 0
    updated_count = 0
    
    try:
        with conn.cursor() as cur:
            # 1. 删除不需要的规则
            print(f"\n🗑️  删除不需要的规则...")
            for rule_code in RULES_TO_DELETE:
                cur.execute("DELETE FROM bazi_rules WHERE rule_code = %s", (rule_code,))
                if cur.rowcount > 0:
                    deleted_count += 1
                    print(f"  ✓ 删除: {rule_code}")
            
            # 2. 导入/更新规则
            print(f"\n📥 导入规则...")
            
            # 检查已存在的规则
            cur.execute("SELECT rule_code FROM bazi_rules WHERE rule_code LIKE 'FORMULA_%'")
            existing_codes = {row["rule_code"] for row in cur.fetchall()}
            
            for rule in RULES_TO_IMPORT:
                rule_code = rule["rule_code"]
                
                if rule_code in existing_codes:
                    # 更新
                    sql = """
                        UPDATE bazi_rules
                        SET rule_name = %s, rule_type = %s, rule_category = %s, priority = %s,
                            conditions = %s, content = %s, description = %s, enabled = %s
                        WHERE rule_code = %s
                    """
                    cur.execute(sql, (
                        rule["rule_name"],
                        rule["rule_type"],
                        rule["rule_category"],
                        rule["priority"],
                        json.dumps(rule["conditions"], ensure_ascii=False),
                        json.dumps(rule["content"], ensure_ascii=False),
                        rule["description"],
                        True,
                        rule_code
                    ))
                    updated_count += 1
                    print(f"  ✓ 更新: {rule_code}")
                else:
                    # 新增
                    sql = """
                        INSERT INTO bazi_rules 
                        (rule_code, rule_name, rule_type, rule_category, priority, conditions, content, description, enabled)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cur.execute(sql, (
                        rule_code,
                        rule["rule_name"],
                        rule["rule_type"],
                        rule["rule_category"],
                        rule["priority"],
                        json.dumps(rule["conditions"], ensure_ascii=False),
                        json.dumps(rule["content"], ensure_ascii=False),
                        rule["description"],
                        True
                    ))
                    inserted_count += 1
                    print(f"  ✓ 新增: {rule_code}")
            
            # 更新版本号
            cur.execute("UPDATE rule_version SET rule_version = rule_version + 1, content_version = content_version + 1")
            conn.commit()
            
    except Exception as e:
        conn.rollback()
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return
    finally:
        conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 导入完成!")
    print(f"  - 删除: {deleted_count} 条")
    print(f"  - 新增: {inserted_count} 条")
    print(f"  - 更新: {updated_count} 条")
    print("=" * 60)
    
    # 打印需要规则引擎扩展的条件类型
    print("\n⚠️ 以下条件类型可能需要规则引擎扩展支持:")
    print("  - deities_same_pillar: 同一柱存在多个神煞")
    print("  - branch_sanxing: 地支三刑关系")
    print("  - stem_wuhe_pairs: 天干五合对数量")
    print("  - ten_gods_main_chong_count: 主星被冲次数")
    print("  - xishen / xishen_in: 喜用神条件")
    print("  - taiyuan_shengong_minggong: 胎元身宫命宫")
    print("  - pillar_branch_xing_chong: 柱地支被刑冲")
    print("  - stems_branches_count: 天干地支混合计数")


if __name__ == "__main__":
    main()

