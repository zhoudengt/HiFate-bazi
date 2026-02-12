#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
测试 MySQL 和 MongoDB 连接到生产 Node1 Docker 数据库
"""

import sys

def test_mysql_connection():
    """测试 MySQL 连接"""
    print("=" * 60)
    print("测试 MySQL 连接...")
    print("=" * 60)
    
    try:
        import pymysql
        print("✅ pymysql 模块已安装")
    except ImportError:
        print("❌ pymysql 模块未安装，请运行: pip install pymysql")
        return False
    
    try:
        conn = pymysql.connect(
            host='8.210.52.217',
            port=3306,
            user='root',
            password=os.getenv("MYSQL_PASSWORD", ""),
            database='hifate_bazi',
            connect_timeout=10
        )
        print("✅ MySQL 连接成功")
        
        # 测试查询
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print(f"   当前数据库: {db_name}")
            
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"   数据库表数量: {len(tables)}")
            if tables:
                print(f"   示例表: {tables[0][0]}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ MySQL 连接失败: {e}")
        return False


def test_mongodb_connection():
    """测试 MongoDB 连接"""
    print("\n" + "=" * 60)
    print("测试 MongoDB 连接...")
    print("=" * 60)
    
    try:
        from pymongo import MongoClient
        print("✅ pymongo 模块已安装")
    except ImportError:
        print("❌ pymongo 模块未安装，请运行: pip install pymongo")
        return False
    
    try:
        client = MongoClient(
            'mongodb://8.210.52.217:27017/',
            serverSelectionTimeoutMS=10000
        )
        
        # 测试连接
        client.admin.command('ping')
        print("✅ MongoDB 连接成功")
        
        # 测试数据库
        db = client['bazi_feedback']
        collections = db.list_collection_names()
        print(f"   当前数据库: bazi_feedback")
        print(f"   集合数量: {len(collections)}")
        if collections:
            print(f"   示例集合: {collections[0]}")
        
        client.close()
        return True
    except Exception as e:
        print(f"❌ MongoDB 连接失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("数据库连接测试脚本")
    print("=" * 60)
    print("\n测试连接到生产 Node1 Docker 数据库...")
    print()
    
    mysql_ok = test_mysql_connection()
    mongodb_ok = test_mongodb_connection()
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"MySQL 连接:   {'✅ 成功' if mysql_ok else '❌ 失败'}")
    print(f"MongoDB 连接: {'✅ 成功' if mongodb_ok else '❌ 失败'}")
    print()
    
    if mysql_ok and mongodb_ok:
        print("🎉 所有数据库连接测试通过！")
        print("   现在可以在 DBeaver 中使用这些连接信息配置连接了。")
        return 0
    else:
        print("⚠️  部分数据库连接测试失败，请检查：")
        if not mysql_ok:
            print("   - MySQL 连接失败，请检查网络和防火墙设置")
        if not mongodb_ok:
            print("   - MongoDB 连接失败，请检查网络和防火墙设置")
        return 1


if __name__ == "__main__":
    sys.exit(main())
