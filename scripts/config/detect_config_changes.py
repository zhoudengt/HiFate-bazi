#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置变更检测脚本
对比本地和生产环境变量文件，检测配置变更

使用方法：
    python3 scripts/config/detect_config_changes.py
"""

import sys
import os
import json
import argparse
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class ConfigComparator:
    """配置比较器"""
    
    def __init__(self, local_env_path: str, production_host: str, production_env_path: str, ssh_password: Optional[str] = None):
        """
        初始化配置比较器
        
        Args:
            local_env_path: 本地环境变量文件路径
            production_host: 生产环境主机地址
            production_env_path: 生产环境变量文件路径
            ssh_password: SSH密码（可选）
        """
        self.local_env_path = local_env_path
        self.production_host = production_host
        self.production_env_path = production_env_path
        self.ssh_password = ssh_password
    
    def parse_env_file(self, content: str) -> Dict[str, str]:
        """
        解析环境变量文件内容
        
        Returns:
            配置项字典 {key: value}
        """
        config = {}
        for line in content.split('\n'):
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            
            # 解析 KEY=VALUE 格式
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # 移除引号（如果有）
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                config[key] = value
        
        return config
    
    def read_local_config(self) -> Dict[str, str]:
        """读取本地配置"""
        if not os.path.exists(self.local_env_path):
            # 如果本地.env不存在，尝试读取env.template
            template_path = os.path.join(os.path.dirname(self.local_env_path), 'env.template')
            if os.path.exists(template_path):
                self.local_env_path = template_path
            else:
                print(f"⚠️  警告：本地配置文件不存在: {self.local_env_path}")
                return {}
        
        with open(self.local_env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.parse_env_file(content)
    
    def read_production_config(self) -> Dict[str, str]:
        """读取生产环境配置（通过SSH）"""
        try:
            # 构建SSH命令
            ssh_cmd = f"cat {self.production_env_path}"
            
            # 如果有密码，使用sshpass
            if self.ssh_password:
                if subprocess.run(['which', 'sshpass'], capture_output=True).returncode == 0:
                    cmd = ['sshpass', '-p', self.ssh_password, 'ssh', '-o', 'StrictHostKeyChecking=no', 
                           '-o', 'ConnectTimeout=10', f'root@{self.production_host}', ssh_cmd]
                else:
                    # 如果没有sshpass，尝试使用expect（如果可用）
                    if subprocess.run(['which', 'expect'], capture_output=True).returncode == 0:
                        expect_script = f'''
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{self.production_host} "{ssh_cmd}"
expect {{
    "password:" {{
        send "{self.ssh_password}\\r"
        exp_continue
    }}
    eof
}}
'''
                        cmd = ['expect', '-c', expect_script]
                    else:
                        # 如果没有sshpass和expect，直接使用ssh（可能需要密钥认证）
                        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10', 
                               f'root@{self.production_host}', ssh_cmd]
            else:
                cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10', 
                       f'root@{self.production_host}', ssh_cmd]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"⚠️  警告：无法读取生产环境配置: {result.stderr}")
                return {}
            
            return self.parse_env_file(result.stdout)
        
        except subprocess.TimeoutExpired:
            print(f"⚠️  警告：读取生产环境配置超时")
            return {}
        except Exception as e:
            print(f"⚠️  警告：读取生产环境配置失败: {e}")
            return {}
    
    def detect_changes(self) -> Dict:
        """
        检测配置变更
        
        Returns:
            {
                'new_configs': [...],      # 新增配置项
                'modified_configs': [...], # 修改的配置项
                'removed_configs': [...]   # 删除的配置项（生产有但本地没有）
            }
        """
        local_config = self.read_local_config()
        prod_config = self.read_production_config()
        
        changes = {
            'new_configs': [],
            'modified_configs': [],
            'removed_configs': []
        }
        
        local_keys = set(local_config.keys())
        prod_keys = set(prod_config.keys())
        
        # 检测新增配置
        new_keys = local_keys - prod_keys
        for key in new_keys:
            changes['new_configs'].append({
                'key': key,
                'local_value': local_config[key],
                'production_value': None
            })
        
        # 检测修改的配置（排除密码和密钥，只显示部分内容）
        common_keys = local_keys & prod_keys
        for key in common_keys:
            local_value = local_config[key]
            prod_value = prod_config[key]
            
            if local_value != prod_value:
                # 敏感信息只显示部分
                if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']):
                    local_display = local_value[:10] + "..." if len(local_value) > 10 else "***"
                    prod_display = prod_value[:10] + "..." if len(prod_value) > 10 else "***"
                else:
                    local_display = local_value
                    prod_display = prod_value
                
                changes['modified_configs'].append({
                    'key': key,
                    'local_value': local_value,
                    'production_value': prod_value,
                    'local_display': local_display,
                    'production_display': prod_display
                })
        
        # 检测删除的配置（生产有但本地没有）
        removed_keys = prod_keys - local_keys
        for key in removed_keys:
            changes['removed_configs'].append({
                'key': key,
                'local_value': None,
                'production_value': prod_config[key]
            })
        
        return changes
    
    def generate_sync_report(self, changes: Dict) -> str:
        """生成配置同步报告"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("配置变更报告")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        if changes['new_configs']:
            report_lines.append(f"📋 新增配置项 ({len(changes['new_configs'])} 个):")
            for config in changes['new_configs']:
                value_display = config['local_value']
                if any(sensitive in config['key'].lower() for sensitive in ['password', 'secret', 'key', 'token']):
                    value_display = value_display[:10] + "..." if len(value_display) > 10 else "***"
                report_lines.append(f"  + {config['key']} = {value_display}")
            report_lines.append("")
        else:
            report_lines.append("✅ 无新增配置项")
            report_lines.append("")
        
        if changes['modified_configs']:
            report_lines.append(f"📝 修改的配置项 ({len(changes['modified_configs'])} 个):")
            for config in changes['modified_configs']:
                report_lines.append(f"  ~ {config['key']}")
                report_lines.append(f"    本地: {config['local_display']}")
                report_lines.append(f"    生产: {config['production_display']}")
            report_lines.append("")
        else:
            report_lines.append("✅ 无修改的配置项")
            report_lines.append("")
        
        if changes['removed_configs']:
            report_lines.append(f"🗑️  删除的配置项 ({len(changes['removed_configs'])} 个，生产有但本地没有):")
            for config in changes['removed_configs']:
                report_lines.append(f"  - {config['key']}")
            report_lines.append("")
        else:
            report_lines.append("✅ 无删除的配置项")
            report_lines.append("")
        
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description='配置变更检测脚本')
    parser.add_argument('--local-env', default='.env', help='本地环境变量文件路径（默认: .env）')
    parser.add_argument('--prod-host', default='8.210.52.217', help='生产环境主机地址（默认: 8.210.52.217）')
    parser.add_argument('--prod-env', default='/opt/HiFate-bazi/.env', help='生产环境变量文件路径（默认: /opt/HiFate-bazi/.env）')
    parser.add_argument('--ssh-password', help='SSH密码（可选，也可以从环境变量SSH_PASSWORD读取）')
    parser.add_argument('--output', help='输出报告文件路径（可选）')
    args = parser.parse_args()
    
    # 获取SSH密码
    ssh_password = args.ssh_password or os.getenv('SSH_PASSWORD')
    
    # 创建比较器
    comparator = ConfigComparator(
        local_env_path=args.local_env,
        production_host=args.prod_host,
        production_env_path=args.prod_env,
        ssh_password=ssh_password
    )
    
    try:
        # 检测配置变更
        print("\n🔍 检测配置变更...")
        changes = comparator.detect_changes()
        
        # 生成报告
        report = comparator.generate_sync_report(changes)
        print("\n" + report)
        
        # 如果有变更，显示提示
        has_changes = any([
            changes['new_configs'],
            changes['modified_configs'],
            changes['removed_configs']
        ])
        
        if has_changes:
            print("\n⚠️  发现配置变更，请使用以下命令同步配置到生产环境：")
            print("   bash scripts/config/sync_production_config.sh")
        else:
            print("\n✅ 无配置变更")
        
        # 保存报告到文件（如果指定）
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n✅ 报告已保存到: {args.output}")
        
        # 如果有变更，返回非零退出码
        return 0 if not has_changes else 0  # 返回0表示成功，但提示有变更
    
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

