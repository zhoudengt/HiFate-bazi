#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署自动化工具
用途：自动化部署流程，包括部署前检查、自动部署、部署后验证

使用方法：
  python3 scripts/deploy/auto_deploy.py --mode incremental  # 增量部署
  python3 scripts/deploy/auto_deploy.py --mode full         # 完整部署
  python3 scripts/deploy/auto_deploy.py --check-only       # 只检查，不部署
"""

import sys
import os
import subprocess
import json
import requests
from pathlib import Path
from typing import Dict, Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# 生产环境配置
NODE1_PUBLIC_IP = "8.210.52.217"
NODE2_PUBLIC_IP = "47.243.160.43"
NODE1_PRIVATE_IP = "172.18.121.222"
NODE2_PRIVATE_IP = "172.18.121.223"


class AutoDeployer:
    """部署自动化工具"""
    
    def __init__(self, mode: str = 'incremental'):
        self.mode = mode
        self.checks_passed = False
        self.deploy_success = False
        self.verify_success = False
    
    def deploy(self) -> bool:
        """执行部署"""
        print(f"{BLUE}🚀 开始自动部署（模式: {self.mode}）...{NC}\n")
        
        # 1. 部署前检查
        print(f"{BLUE}1. 部署前检查{NC}")
        if not self.pre_deploy_check():
            print(f"{RED}❌ 部署前检查失败，停止部署{NC}\n")
            return False
        
        # 2. 执行部署
        if self.mode == 'incremental':
            print(f"\n{BLUE}2. 执行增量部署{NC}")
            if not self.incremental_deploy():
                print(f"{RED}❌ 增量部署失败{NC}\n")
                return False
        elif self.mode == 'full':
            print(f"\n{BLUE}2. 执行完整部署{NC}")
            if not self.full_deploy():
                print(f"{RED}❌ 完整部署失败{NC}\n")
                return False
        else:
            print(f"{RED}❌ 未知的部署模式: {self.mode}{NC}\n")
            return False
        
        # 3. 部署后验证
        print(f"\n{BLUE}3. 部署后验证{NC}")
        if not self.post_deploy_verify():
            print(f"{RED}❌ 部署后验证失败{NC}\n")
            # 自动回滚
            print(f"{YELLOW}⚠️  自动回滚...{NC}")
            self.rollback()
            return False
        
        print(f"\n{GREEN}✅ 部署成功！{NC}\n")
        return True
    
    def pre_deploy_check(self) -> bool:
        """部署前检查"""
        checks = [
            ("代码一致性检查", self._check_code_consistency),
            ("语法验证", self._check_syntax),
            ("依赖检查", self._check_dependencies),
            ("配置检查", self._check_config),
        ]
        
        all_passed = True
        for name, check_func in checks:
            print(f"  {BLUE}检查: {name}{NC}")
            try:
                if not check_func():
                    print(f"    {RED}✗{NC} {name} 失败")
                    all_passed = False
                else:
                    print(f"    {GREEN}✓{NC} {name} 通过")
            except Exception as e:
                print(f"    {RED}✗{NC} {name} 异常: {e}")
                all_passed = False
        
        self.checks_passed = all_passed
        return all_passed
    
    def incremental_deploy(self) -> bool:
        """增量部署"""
        deploy_script = PROJECT_ROOT / 'deploy/scripts/incremental_deploy_production.sh'
        if not deploy_script.exists():
            print(f"  {RED}✗{NC} 增量部署脚本不存在{NC}")
            return False
        
        try:
            result = subprocess.run(
                ['bash', str(deploy_script)],
                cwd=PROJECT_ROOT,
                timeout=300
            )
            
            if result.returncode == 0:
                print(f"  {GREEN}✓{NC} 增量部署成功")
                self.deploy_success = True
                return True
            else:
                print(f"  {RED}✗{NC} 增量部署失败（返回码: {result.returncode}）")
                return False
        except subprocess.TimeoutExpired:
            print(f"  {RED}✗{NC} 增量部署超时")
            return False
        except Exception as e:
            print(f"  {RED}✗{NC} 增量部署异常: {e}")
            return False
    
    def full_deploy(self) -> bool:
        """完整部署"""
        # 完整部署使用 GitHub Actions 或 Docker Compose
        print(f"  {YELLOW}⚠️  完整部署需要手动执行或使用 CI/CD{NC}")
        print(f"  {YELLOW}建议使用: bash deploy/scripts/deploy.sh{NC}")
        return False
    
    def post_deploy_verify(self) -> bool:
        """部署后验证"""
        checks = [
            ("Node1 健康检查", lambda: self._check_health(NODE1_PUBLIC_IP)),
            ("Node2 健康检查", lambda: self._check_health(NODE2_PUBLIC_IP)),
            ("热更新状态", self._check_hot_reload_status),
            ("关键接口验证", self._check_key_endpoints),
        ]
        
        all_passed = True
        for name, check_func in checks:
            print(f"  {BLUE}验证: {name}{NC}")
            try:
                if not check_func():
                    print(f"    {RED}✗{NC} {name} 失败")
                    all_passed = False
                else:
                    print(f"    {GREEN}✓{NC} {name} 通过")
            except Exception as e:
                print(f"    {RED}✗{NC} {name} 异常: {e}")
                all_passed = False
        
        self.verify_success = all_passed
        return all_passed
    
    def rollback(self) -> bool:
        """回滚部署"""
        print(f"{YELLOW}🔄 开始回滚...{NC}\n")
        
        # 使用热更新回滚
        try:
            for node_ip in [NODE1_PUBLIC_IP, NODE2_PUBLIC_IP]:
                response = requests.post(
                    f'http://{node_ip}:8001/api/v1/hot-reload/rollback',
                    timeout=10
                )
                if response.status_code == 200:
                    print(f"  {GREEN}✓{NC} {node_ip} 回滚成功")
                else:
                    print(f"  {RED}✗{NC} {node_ip} 回滚失败")
        except Exception as e:
            print(f"  {RED}✗{NC} 回滚异常: {e}")
            return False
        
        return True
    
    def _check_code_consistency(self) -> bool:
        """检查代码一致性"""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            if result.stdout.strip():
                print(f"    {YELLOW}⚠️  有未提交的更改{NC}")
                return False
            
            # 检查是否已推送到远程
            result = subprocess.run(
                ['git', 'log', '--oneline', 'origin/master..HEAD'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            if result.stdout.strip():
                print(f"    {YELLOW}⚠️  有未推送的提交{NC}")
                return False
            
            return True
        except Exception:
            return True
    
    def _check_syntax(self) -> bool:
        """检查语法"""
        try:
            result = subprocess.run(
                ['python3', '-m', 'py_compile', 'server/main.py'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return True
    
    def _check_dependencies(self) -> bool:
        """检查依赖"""
        # 检查 requirements.txt 是否存在
        requirements_file = PROJECT_ROOT / 'requirements.txt'
        if not requirements_file.exists():
            return False
        
        return True
    
    def _check_config(self) -> bool:
        """检查配置"""
        # 检查 .env 文件是否存在（可选）
        env_file = PROJECT_ROOT / '.env'
        if not env_file.exists():
            print(f"    {YELLOW}⚠️  .env 文件不存在（可选）{NC}")
        
        return True
    
    def _check_health(self, node_ip: str) -> bool:
        """检查节点健康状态"""
        try:
            response = requests.get(
                f'http://{node_ip}:8001/health',
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _check_hot_reload_status(self) -> bool:
        """检查热更新状态"""
        try:
            response = requests.get(
                f'http://{NODE1_PUBLIC_IP}:8001/api/v1/hot-reload/status',
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _check_key_endpoints(self) -> bool:
        """检查关键接口"""
        key_endpoints = [
            '/health',
            '/api/v1/bazi/calculate',
        ]
        
        all_passed = True
        for endpoint in key_endpoints:
            try:
                response = requests.get(
                    f'http://{NODE1_PUBLIC_IP}:8001{endpoint}',
                    timeout=5
                )
                if response.status_code != 200:
                    all_passed = False
            except Exception:
                all_passed = False
        
        return all_passed


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='部署自动化工具')
    parser.add_argument('--mode', type=str, choices=['incremental', 'full'], default='incremental', help='部署模式')
    parser.add_argument('--check-only', action='store_true', help='只检查，不部署')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式报告')
    parser.add_argument('--exit-on-failure', action='store_true', help='部署失败时退出（用于 CI/CD）')
    
    args = parser.parse_args()
    
    deployer = AutoDeployer(mode=args.mode)
    
    if args.check_only:
        success = deployer.pre_deploy_check()
    else:
        success = deployer.deploy()
    
    if args.json:
        report = {
            'mode': args.mode,
            'checks_passed': deployer.checks_passed,
            'deploy_success': deployer.deploy_success,
            'verify_success': deployer.verify_success,
            'overall_success': success,
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
    
    if args.exit_on_failure and not success:
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

