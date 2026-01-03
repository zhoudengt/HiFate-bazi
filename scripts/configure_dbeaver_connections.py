#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DBeaver 连接配置脚本
自动配置 MySQL 和 MongoDB 连接到生产 Node1 Docker 数据库
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime

# DBeaver 配置文件路径
DBEAVER_CONFIG_DIR = Path.home() / "Library" / "DBeaverData" / "workspace6" / "General" / ".dbeaver"
DATA_SOURCES_FILE = DBEAVER_CONFIG_DIR / "data-sources.json"

# MySQL 连接配置
MYSQL_CONFIG = {
    "provider": "mysql",
    "driver": "mysql",
    "name": "MySQL - Node1 Docker (生产)",
    "description": "生产环境 Node1 Docker MySQL 数据库",
    "save-password": True,
    "show-system-objects": False,
    "configuration": {
        "host": "8.210.52.217",
        "port": "3306",
        "database": "hifate_bazi",
        "url": "jdbc:mysql://8.210.52.217:3306/hifate_bazi",
        "type": "dev",
        "auth-model": "native",
        "user": "root",
        "password": "Yuanqizhan@163",
        "configurationType": "MANUAL",
        "closeIdleConnection": True,
        "properties": {
            "connectTimeout": "20000",
            "rewriteBatchedStatements": "true",
            "enabledTLSProtocols": "TLSv1.2",
            "characterEncoding": "utf8mb4"
        }
    }
}

# MongoDB 连接配置
MONGODB_CONFIG = {
    "provider": "mongodb",
    "driver": "mongo",
    "name": "MongoDB - Node1 Docker (生产)",
    "description": "生产环境 Node1 Docker MongoDB 数据库",
    "save-password": False,
    "show-system-objects": False,
    "configuration": {
        "host": "8.210.52.217",
        "port": "27017",
        "database": "bazi_feedback",
        "url": "mongodb://8.210.52.217:27017/bazi_feedback",
        "type": "dev",
        "authSource": "admin",
        "authMechanism": "SCRAM-SHA-1",
        "configurationType": "MANUAL",
        "closeIdleConnection": True,
        "properties": {
            "connectTimeout": "20000",
            "socketTimeout": "0"
        }
    }
}


def backup_config_file():
    """备份配置文件"""
    if DATA_SOURCES_FILE.exists():
        backup_file = DATA_SOURCES_FILE.with_suffix(f".json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(DATA_SOURCES_FILE, backup_file)
        print(f"✅ 已备份配置文件到: {backup_file}")
        return True
    return False


def load_config():
    """加载现有配置"""
    if DATA_SOURCES_FILE.exists():
        with open(DATA_SOURCES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 创建默认配置结构
        return {
            "folders": {},
            "connections": {},
            "connection-types": {
                "dev": {
                    "name": "开发",
                    "color": "255,255,255",
                    "description": "常规开发数据库",
                    "auto-commit": True,
                    "confirm-execute": False,
                    "confirm-data-change": False,
                    "smart-commit": False,
                    "smart-commit-recover": True,
                    "auto-close-transactions": True,
                    "close-transactions-period": 1800,
                    "auto-close-connections": True,
                    "close-connections-period": 14400
                }
            }
        }


def generate_connection_id(prefix, name):
    """生成连接 ID"""
    # 使用名称生成唯一 ID（简化版）
    import hashlib
    name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
    return f"{prefix}-{name_hash}"


def add_connection(config_data, connection_config, connection_id):
    """添加连接配置"""
    if "connections" not in config_data:
        config_data["connections"] = {}
    
    # 检查连接是否已存在
    existing_ids = [cid for cid in config_data["connections"].keys() 
                   if config_data["connections"][cid].get("name") == connection_config["name"]]
    
    if existing_ids:
        print(f"⚠️  连接 '{connection_config['name']}' 已存在，跳过添加")
        return False
    
    config_data["connections"][connection_id] = connection_config
    print(f"✅ 已添加连接: {connection_config['name']}")
    return True


def save_config(config_data):
    """保存配置"""
    DBEAVER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(DATA_SOURCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent='\t', ensure_ascii=False)
    
    print(f"✅ 配置文件已保存到: {DATA_SOURCES_FILE}")


def main():
    """主函数"""
    print("=" * 60)
    print("DBeaver 数据库连接配置脚本")
    print("=" * 60)
    print()
    
    # 备份配置文件
    backup_config_file()
    
    # 加载现有配置
    print("📖 加载现有配置...")
    config_data = load_config()
    
    # 生成连接 ID
    mysql_id = generate_connection_id("mysql", MYSQL_CONFIG["name"])
    mongodb_id = generate_connection_id("mongodb", MONGODB_CONFIG["name"])
    
    # 添加 MySQL 连接
    print(f"\n📝 配置 MySQL 连接...")
    add_connection(config_data, MYSQL_CONFIG, mysql_id)
    
    # 添加 MongoDB 连接
    print(f"\n📝 配置 MongoDB 连接...")
    add_connection(config_data, MONGODB_CONFIG, mongodb_id)
    
    # 保存配置
    print(f"\n💾 保存配置...")
    save_config(config_data)
    
    print()
    print("=" * 60)
    print("配置完成！")
    print("=" * 60)
    print()
    print("📌 下一步操作：")
    print("1. 在 DBeaver 中刷新数据库连接列表（右键点击连接 -> Refresh）")
    print("2. 或者重启 DBeaver 应用程序")
    print("3. 双击连接名称进行测试连接")
    print()
    print("⚠️  注意：如果连接测试失败，DBeaver 可能会提示下载相应的驱动，")
    print("   请按照提示下载并安装驱动。")
    print()


if __name__ == "__main__":
    main()
