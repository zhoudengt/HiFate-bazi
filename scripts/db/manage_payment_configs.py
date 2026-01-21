#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付配置管理工具
用于添加、更新、查看支付配置
"""

import sys
import os
import argparse
from typing import Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
from services.payment_service.payment_config_loader import get_payment_environment, reload_payment_config


def add_config(
    provider: str,
    config_key: str,
    config_value: str,
    environment: str = 'production',
    description: Optional[str] = None,
    config_type: str = 'string'
):
    """添加或更新支付配置"""
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO payment_configs 
                (provider, config_key, config_value, config_type, environment, description, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                    config_value = VALUES(config_value),
                    description = VALUES(description),
                    updated_at = CURRENT_TIMESTAMP
            """
            cursor.execute(sql, (
                provider,
                config_key,
                config_value,
                config_type,
                environment,
                description or f"{provider}.{config_key}配置"
            ))
            conn.commit()
            print(f"✅ 配置已添加/更新: {provider}.{config_key} ({environment})")
    except Exception as e:
        print(f"❌ 添加配置失败: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            return_mysql_connection(conn)


def get_active_environment(provider: str):
    """获取指定支付方式的当前激活环境"""
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            sql = """
                SELECT DISTINCT environment
                FROM payment_configs 
                WHERE provider = %s 
                  AND merchant_id IS NULL
                  AND is_active = 1
                LIMIT 1
            """
            cursor.execute(sql, (provider,))
            result = cursor.fetchone()
            
            if result:
                env = result.get('environment')
                print(f"\n✅ {provider} 当前激活环境: {env}")
                return env
            else:
                print(f"\n⚠️  {provider} 没有找到激活的配置")
                return None
    except Exception as e:
        print(f"❌ 获取环境失败: {e}")
        raise
    finally:
        if conn:
            return_mysql_connection(conn)


def set_active_environment(provider: str, environment: str):
    """设置指定支付方式的激活环境"""
    valid_environments = ['production', 'sandbox', 'test']
    if environment not in valid_environments:
        print(f"❌ 无效的环境值: {environment}")
        print(f"   有效值: {', '.join(valid_environments)}")
        return
    
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            # 1. 先将该支付方式的所有环境的 is_active 设为 0
            sql1 = """
                UPDATE payment_configs 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE provider = %s 
                  AND merchant_id IS NULL
            """
            cursor.execute(sql1, (provider,))
            affected_rows1 = cursor.rowcount
            
            # 2. 将目标环境的 is_active 设为 1
            sql2 = """
                UPDATE payment_configs 
                SET is_active = 1, updated_at = CURRENT_TIMESTAMP
                WHERE provider = %s 
                  AND environment = %s
                  AND merchant_id IS NULL
            """
            cursor.execute(sql2, (provider, environment))
            affected_rows2 = cursor.rowcount
            
            conn.commit()
            
            print(f"✅ {provider} 环境已切换到: {environment}")
            print(f"   - 已停用 {affected_rows1} 条配置")
            print(f"   - 已激活 {affected_rows2} 条配置")
            
            # 清除缓存
            reload_payment_config(provider, None, None)
            print(f"✅ 配置缓存已清除，热更新已触发")
            
            print(f"\n⚠️  注意: 请确保 {provider} 的 {environment} 环境配置已完整设置")
    except Exception as e:
        print(f"❌ 设置环境失败: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            return_mysql_connection(conn)


def list_configs(provider: Optional[str] = None, environment: Optional[str] = None):
    """列出支付配置"""
    conn = None
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cursor:
            if provider and environment:
                sql = """
                    SELECT config_key, config_value, config_type, description, is_active
                    FROM payment_configs
                    WHERE provider = %s AND environment = %s
                    ORDER BY config_key
                """
                cursor.execute(sql, (provider, environment))
            elif provider:
                sql = """
                    SELECT environment, config_key, config_value, config_type, description, is_active
                    FROM payment_configs
                    WHERE provider = %s
                    ORDER BY environment, config_key
                """
                cursor.execute(sql, (provider,))
            else:
                sql = """
                    SELECT provider, environment, config_key, 
                           LEFT(config_value, 30) as config_value_preview, 
                           config_type, description, is_active
                    FROM payment_configs
                    ORDER BY provider, environment, config_key
                """
                cursor.execute(sql)
            
            results = cursor.fetchall()
            
            if not results:
                print("📭 没有找到配置")
                return
            
            print("\n" + "=" * 80)
            print("支付配置列表")
            print("=" * 80)
            
            for result in results:
                if provider and environment:
                    # 单个渠道单个环境
                    key = result.get('config_key')
                    value = result.get('config_value')
                    value_preview = value[:30] + "..." if value and len(value) > 30 else value
                    active = "✅" if result.get('is_active') else "❌"
                    print(f"{active} {key}: {value_preview}")
                elif provider:
                    # 单个渠道所有环境
                    env = result.get('environment')
                    key = result.get('config_key')
                    value = result.get('config_value')
                    value_preview = value[:30] + "..." if value and len(value) > 30 else value
                    active = "✅" if result.get('is_active') else "❌"
                    print(f"{active} [{env}] {key}: {value_preview}")
                else:
                    # 所有配置
                    prov = result.get('provider')
                    env = result.get('environment')
                    key = result.get('config_key')
                    value_preview = result.get('config_value_preview', '')
                    active = "✅" if result.get('is_active') else "❌"
                    print(f"{active} [{prov}] [{env}] {key}: {value_preview}")
            
            print("=" * 80)
            print(f"共 {len(results)} 条配置")
            
    except Exception as e:
        print(f"❌ 查询配置失败: {e}")
        raise
    finally:
        if conn:
            return_mysql_connection(conn)


def main():
    parser = argparse.ArgumentParser(description='支付配置管理工具')
    subparsers = parser.add_subparsers(dest='command', help='操作命令')
    
    # 添加配置
    add_parser = subparsers.add_parser('add', help='添加或更新配置')
    add_parser.add_argument('provider', help='支付渠道（stripe/paypal/alipay/wechat/linepay/newebpay/shared）')
    add_parser.add_argument('config_key', help='配置键（如：channel_id, merchant_id等）')
    add_parser.add_argument('config_value', help='配置值')
    add_parser.add_argument('--environment', default='production', help='环境（production/sandbox/test）')
    add_parser.add_argument('--description', help='配置描述')
    add_parser.add_argument('--type', default='string', help='配置类型（string/int/bool）')
    
    # 列出配置
    list_parser = subparsers.add_parser('list', help='列出配置')
    list_parser.add_argument('--provider', help='支付渠道（可选）')
    list_parser.add_argument('--environment', help='环境（可选）')
    
    # 获取激活环境
    get_env_parser = subparsers.add_parser('get-active-environment', help='获取指定支付方式的当前激活环境')
    get_env_parser.add_argument('provider', help='支付渠道（stripe/paypal/alipay/wechat/linepay/newebpay）')
    
    # 设置激活环境
    set_env_parser = subparsers.add_parser('set-active-environment', help='设置指定支付方式的激活环境')
    set_env_parser.add_argument('provider', help='支付渠道（stripe/paypal/alipay/wechat/linepay/newebpay）')
    set_env_parser.add_argument('environment', choices=['production', 'sandbox', 'test'], help='环境值')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'add':
            add_config(
                args.provider,
                args.config_key,
                args.config_value,
                args.environment,
                args.description,
                args.type
            )
        elif args.command == 'list':
            list_configs(args.provider, args.environment)
        elif args.command == 'get-active-environment':
            get_active_environment(args.provider)
        elif args.command == 'set-active-environment':
            set_active_environment(args.provider, args.environment)
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
