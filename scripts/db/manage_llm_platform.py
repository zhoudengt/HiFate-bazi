#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 平台配置管理脚本

用于查看和设置各场景使用的 LLM 平台（Coze 或百炼）。

使用方法：
  查看配置:  python scripts/db/manage_llm_platform.py --list
  设置全局:  python scripts/db/manage_llm_platform.py --set-global bailian
  设置场景:  python scripts/db/manage_llm_platform.py --set-scene wuxing_proportion bailian
  批量设置:  python scripts/db/manage_llm_platform.py --set-all bailian
"""

import os
import sys
import argparse
import logging

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    # 如果没有 python-dotenv，手动加载 .env
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# 所有支持的场景列表
SUPPORTED_SCENES = [
    "wuxing_proportion",      # 五行占比
    "xishen_jishen",          # 喜神忌神
    "marriage",               # 婚姻分析
    "career_wealth",          # 事业财运
    "health_analysis",        # 健康分析
    "annual_report",          # 年度报告
    "general_review",         # 综合评述
    "qa_analysis",            # 问答分析
    "formula_analysis",       # 格局分析
    "dayun_analysis",         # 大运分析
]


def get_db_connection():
    """获取数据库连接"""
    from shared.config.database import get_mysql_connection
    return get_mysql_connection()


def list_configs():
    """列出所有 LLM 平台配置"""
    conn = get_db_connection()
    if not conn:
        logger.error("❌ 无法连接数据库")
        return
    
    try:
        cursor = conn.cursor()
        
        print("\n" + "=" * 60)
        print("LLM 平台配置状态")
        print("=" * 60)
        
        # 1. 查询全局配置
        cursor.execute("SELECT config_value FROM service_configs WHERE config_key = 'LLM_PLATFORM'")
        result = cursor.fetchone()
        global_platform = result['config_value'] if result else "未设置（默认：coze）"
        print(f"\n📌 全局配置 (LLM_PLATFORM): {global_platform}")
        
        # 2. 查询各场景配置
        print(f"\n📋 场景级配置:")
        print("-" * 60)
        print(f"{'场景':<25} {'配置键':<35} {'平台':<10}")
        print("-" * 60)
        
        for scene in SUPPORTED_SCENES:
            config_key = f"{scene.upper()}_LLM_PLATFORM"
            cursor.execute(
                "SELECT config_value FROM service_configs WHERE config_key = %s",
                (config_key,)
            )
            result = cursor.fetchone()
            platform = result['config_value'] if result else "未设置"
            effective = platform if result else f"继承全局({global_platform.split('（')[0]})"
            print(f"{scene:<25} {config_key:<35} {effective:<10}")
        
        # 3. 查询百炼相关配置
        print(f"\n🔑 百炼平台配置:")
        print("-" * 60)
        
        bailian_keys = [
            "BAILIAN_API_KEY",
            "BAILIAN_WUXING_APP_ID",
            "BAILIAN_XISHEN_JISHEN_APP_ID",
            "BAILIAN_MARRIAGE_APP_ID",
            "BAILIAN_CAREER_WEALTH_APP_ID",
            "BAILIAN_HEALTH_APP_ID",
            "BAILIAN_ANNUAL_REPORT_APP_ID",
            "BAILIAN_GENERAL_REVIEW_APP_ID",
            "BAILIAN_QA_APP_ID",
        ]
        
        for key in bailian_keys:
            cursor.execute(
                "SELECT config_value FROM service_configs WHERE config_key = %s",
                (key,)
            )
            result = cursor.fetchone()
            if result:
                value = result['config_value']
                # 隐藏敏感信息
                if 'KEY' in key or 'TOKEN' in key:
                    display_value = value[:8] + "..." if len(value) > 8 else "***"
                else:
                    display_value = value
                print(f"  ✓ {key}: {display_value}")
            else:
                print(f"  ✗ {key}: 未设置")
        
        print("\n" + "=" * 60)
        print("提示：使用 --set-global 或 --set-scene 来修改配置")
        print("=" * 60 + "\n")
        
    finally:
        cursor.close()
        conn.close()


def set_config(key: str, value: str):
    """设置配置"""
    conn = get_db_connection()
    if not conn:
        logger.error("❌ 无法连接数据库")
        return False
    
    try:
        cursor = conn.cursor()
        
        # 使用 INSERT ... ON DUPLICATE KEY UPDATE
        cursor.execute("""
            INSERT INTO service_configs (config_key, config_value, description, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE 
                config_value = VALUES(config_value),
                updated_at = NOW()
        """, (key, value, f"LLM 平台配置 - {key}"))
        
        conn.commit()
        logger.info(f"✓ 已设置 {key} = {value}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 设置失败: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def set_global_platform(platform: str):
    """设置全局 LLM 平台"""
    if platform not in ("coze", "bailian"):
        logger.error(f"❌ 无效的平台: {platform}，必须是 'coze' 或 'bailian'")
        return False
    
    return set_config("LLM_PLATFORM", platform)


def set_scene_platform(scene: str, platform: str):
    """设置场景级 LLM 平台"""
    if platform not in ("coze", "bailian"):
        logger.error(f"❌ 无效的平台: {platform}，必须是 'coze' 或 'bailian'")
        return False
    
    if scene not in SUPPORTED_SCENES:
        logger.warning(f"⚠️ 未知场景: {scene}，继续设置...")
    
    config_key = f"{scene.upper()}_LLM_PLATFORM"
    return set_config(config_key, platform)


def set_all_scenes(platform: str):
    """批量设置所有场景使用的平台"""
    if platform not in ("coze", "bailian"):
        logger.error(f"❌ 无效的平台: {platform}，必须是 'coze' 或 'bailian'")
        return False
    
    # 设置全局配置
    success = set_global_platform(platform)
    
    # 设置所有场景配置
    for scene in SUPPORTED_SCENES:
        success = set_scene_platform(scene, platform) and success
    
    if success:
        logger.info(f"\n✅ 已将所有场景设置为使用 {platform} 平台")
    
    return success


def main():
    parser = argparse.ArgumentParser(description="LLM 平台配置管理")
    parser.add_argument("--list", action="store_true", help="列出所有配置")
    parser.add_argument("--set-global", metavar="PLATFORM", help="设置全局平台 (coze/bailian)")
    parser.add_argument("--set-scene", nargs=2, metavar=("SCENE", "PLATFORM"), help="设置场景平台")
    parser.add_argument("--set-all", metavar="PLATFORM", help="批量设置所有场景使用的平台")
    
    args = parser.parse_args()
    
    if args.list:
        list_configs()
    elif args.set_global:
        set_global_platform(args.set_global)
        print("\n提示：配置已更新，热更新后生效。")
    elif args.set_scene:
        scene, platform = args.set_scene
        set_scene_platform(scene, platform)
        print("\n提示：配置已更新，热更新后生效。")
    elif args.set_all:
        set_all_scenes(args.set_all)
        print("\n提示：配置已更新，热更新后生效。")
    else:
        # 默认显示配置列表
        list_configs()


if __name__ == "__main__":
    main()
