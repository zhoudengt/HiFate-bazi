#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户交互数据表迁移脚本
在Node1上执行，创建MySQL表和MongoDB索引
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
from server.config.database_config import MONGO_CONFIG
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_mysql():
    """迁移MySQL表结构"""
    logger.info("开始迁移MySQL表结构...")
    
    sql_file = os.path.join(project_root, 'server/db/migrations/create_user_interaction_tables.sql')
    
    if not os.path.exists(sql_file):
        logger.error(f"SQL文件不存在: {sql_file}")
        return False
    
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                # 执行SQL（支持多语句）
                for statement in sql_content.split(';'):
                    statement = statement.strip()
                    if statement:
                        cursor.execute(statement)
                conn.commit()
        logger.info("✓ MySQL表结构迁移成功")
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"✗ MySQL表结构迁移失败: {e}", exc_info=True)
        return False
    finally:
        if conn:
            return_mysql_connection(conn)


def migrate_mongodb():
    """创建MongoDB索引"""
    logger.info("开始创建MongoDB索引...")
    
    try:
        from pymongo import MongoClient
        
        client = MongoClient(
            MONGO_CONFIG['connection_string'],
            serverSelectionTimeoutMS=5000
        )
        db = client[MONGO_CONFIG['database']]
        collection = db['function_usage_details']
        
        # 创建索引
        collection.create_index('record_id', unique=True)
        collection.create_index('session_id')
        collection.create_index('user_id')
        collection.create_index('function_type')
        collection.create_index('created_at')
        
        logger.info("✓ MongoDB索引创建成功")
        return True
    except ImportError:
        logger.warning("pymongo不可用，跳过MongoDB索引创建")
        return True
    except Exception as e:
        logger.error(f"✗ MongoDB索引创建失败: {e}", exc_info=True)
        return False


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("用户交互数据表迁移脚本")
    logger.info("=" * 50)
    
    # 迁移MySQL
    mysql_success = migrate_mysql()
    
    # 迁移MongoDB
    mongo_success = migrate_mongodb()
    
    if mysql_success and mongo_success:
        logger.info("=" * 50)
        logger.info("✓ 所有迁移完成")
        logger.info("=" * 50)
        return 0
    else:
        logger.error("=" * 50)
        logger.error("✗ 迁移失败")
        logger.error("=" * 50)
        return 1


if __name__ == '__main__':
    sys.exit(main())

