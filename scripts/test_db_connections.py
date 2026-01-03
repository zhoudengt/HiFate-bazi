#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据库连接脚本
验证MySQL和MongoDB连接是否正常
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def test_mysql_connection():
    """测试MySQL连接"""
    print("🧪 测试MySQL连接...")
    try:
        from server.config.mysql_config import get_mysql_connection, return_mysql_connection, test_mysql_connection
        
        result = test_mysql_connection()
        if result:
            print("✅ MySQL连接成功")
            
            # 测试查询
            conn = get_mysql_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT DATABASE()")
                    db = cursor.fetchone()
                    print(f"   当前数据库: {db.get('DATABASE()') if db else 'N/A'}")
                    
                    cursor.execute("SELECT VERSION()")
                    version = cursor.fetchone()
                    print(f"   MySQL版本: {version.get('VERSION()') if version else 'N/A'}")
            finally:
                return_mysql_connection(conn)
            
            return True
        else:
            print("❌ MySQL连接失败")
            return False
    except Exception as e:
        print(f"❌ MySQL连接测试异常: {e}")
        return False

def test_mongodb_connection():
    """测试MongoDB连接"""
    print("\n🧪 测试MongoDB连接...")
    try:
        from services.prompt_optimizer.config import MONGO_HOST, MONGO_PORT, MONGO_DB, MONGO_USER, MONGO_PASSWORD
        
        try:
            from pymongo import MongoClient
            
            # 构建连接字符串
            if MONGO_USER and MONGO_PASSWORD:
                mongo_uri = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"
            else:
                mongo_uri = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"
            
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            
            # 测试连接
            client.admin.command('ping')
            
            # 获取数据库信息
            db = client[MONGO_DB]
            collections = db.list_collection_names()
            
            print(f"✅ MongoDB连接成功")
            print(f"   主机: {MONGO_HOST}:{MONGO_PORT}")
            print(f"   数据库: {MONGO_DB}")
            print(f"   集合数量: {len(collections)}")
            
            client.close()
            return True
        except ImportError:
            print("⚠️  pymongo模块未安装，跳过MongoDB连接测试")
            return None
    except Exception as e:
        print(f"❌ MongoDB连接测试异常: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("数据库连接测试")
    print("=" * 60)
    
    # 测试MySQL
    mysql_ok = test_mysql_connection()
    
    # 测试MongoDB
    mongo_ok = test_mongodb_connection()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"MySQL: {'✅ 连接成功' if mysql_ok else '❌ 连接失败'}")
    if mongo_ok is not None:
        print(f"MongoDB: {'✅ 连接成功' if mongo_ok else '❌ 连接失败'}")
    else:
        print(f"MongoDB: ⚠️  未测试（pymongo未安装）")
    
    if mysql_ok and (mongo_ok is None or mongo_ok):
        print("\n✅ 所有数据库连接正常")
        return 0
    else:
        print("\n❌ 部分数据库连接失败，请检查配置")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

