#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移手相/面相规则到数据库。
执行前会检查表是否存在，执行后验证数据量。
从 services/fortune_rule/rule_engine 读取硬编码规则，写入 fortune_rules 表。
运行方式：从项目根目录执行 python scripts/migration/migrate_fortune_rules_to_db.py
"""

import json
import os
import sys
import logging
from typing import Dict, Any, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TABLE_NAME = "fortune_rules"
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `fortune_rules` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
    `rule_type` VARCHAR(20) NOT NULL COMMENT 'hand/face',
    `category` VARCHAR(80) NOT NULL COMMENT 'hand_shape/life_line/san_ting等',
    `content` JSON NOT NULL COMMENT '规则内容',
    `enabled` TINYINT(1) DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_type_category` (`rule_type`, `category`),
    KEY `idx_rule_type` (`rule_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='手相面相规则（从硬编码迁移）';
"""


def load_hardcoded_rules() -> Dict[str, Dict[str, Any]]:
    """从 rule_engine 加载硬编码规则。"""
    from services.fortune_rule.rule_engine import get_hand_rules_static, get_face_rules_static
    hand = get_hand_rules_static()
    face = get_face_rules_static()
    return {"hand": hand, "face": face}


def migrate():
    """创建表并插入规则。"""
    from server.db.mysql_connector import MySQLConnector
    db = MySQLConnector()
    logger.info("创建表 %s（如不存在）", TABLE_NAME)
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
            conn.commit()
    rules = load_hardcoded_rules()
    inserted = 0
    for rule_type, categories_dict in rules.items():
        if not isinstance(categories_dict, dict):
            continue
        for category, content in categories_dict.items():
            if not category or content is None:
                continue
            content_json = json.dumps(content, ensure_ascii=False)
            try:
                db.execute_update(
                    """
                    INSERT INTO {} (rule_type, category, content, enabled)
                    VALUES (%s, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE content = VALUES(content), updated_at = CURRENT_TIMESTAMP
                    """.format(TABLE_NAME),
                    (rule_type, category, content_json),
                )
                inserted += 1
            except Exception as e:
                logger.warning("插入 %s/%s 失败: %s", rule_type, category, e)
    logger.info("迁移完成，插入/更新 %s 条记录", inserted)
    # 验证
    rows = db.execute_query(
        "SELECT rule_type, COUNT(*) AS cnt FROM {} GROUP BY rule_type".format(TABLE_NAME),
        None,
    )
    for row in rows:
        logger.info("  %s: %s 条", row.get("rule_type"), row.get("cnt"))
    return inserted


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        logger.exception("迁移失败: %s", e)
        sys.exit(1)
