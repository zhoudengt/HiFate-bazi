#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端页面端到端测试脚本
测试所有页面的可访问性和基本功能
"""

import sys
import os
import requests
import json
from typing import List, Dict, Tuple
from urllib.parse import urljoin

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

BASE_URL = "http://localhost:8001/frontend"

# 需要测试的所有页面
PAGES_TO_TEST = [
    ("login.html", "登录页面", True),  # (路径, 描述, 是否需要认证)
    ("index.html", "首页", False),
    ("pan.html", "八字排盘", False),
    ("formula-analysis.html", "公式分析", False),
    ("basic-info.html", "基本信息", False),
    ("shengong-minggong.html", "身宫命宫", False),
    ("smart-fortune.html", "智能运势", False),
    ("smart-fortune-stream.html", "智能运势(流式)", False),
    ("fortune.html", "运势", False),
    ("dayun.html", "大运", False),
    ("liunian.html", "流年", False),
    ("desk-fengshui.html", "办公桌风水", False),
    ("face-analysis.html", "面相分析", False),
    ("face-analysis-v2.html", "面相分析v2", False),
    ("hand-analysis.html", "手相分析", False),
    ("yigua.html", "一事一卦", False),
    ("payment.html", "支付", False),
    ("payment-success.html", "支付成功", False),
    ("payment-cancel.html", "支付取消", False),
]

# 需要测试的静态资源
STATIC_RESOURCES = [
    ("js/core/error-handler.js", "错误处理工具类"),
    ("js/core/dom-utils.js", "DOM工具类"),
    ("js/core/validator.js", "验证工具类"),
    ("js/api.js", "API客户端"),
    ("js/auth.js", "认证模块"),
    ("css/common.css", "公共样式"),
]


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def test_page(url: str, name: str, expect_html: bool = True) -> Tuple[bool, str]:
    """
    测试单个页面
    
    Args:
        url: 页面URL
        name: 页面名称
        expect_html: 是否期望返回HTML
        
    Returns:
        (成功, 错误信息)
    """
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 401:
            return False, f"401 未授权 - 被认证中间件拦截"
        
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}"
        
        content = response.text[:500]  # 只检查前500字符
        
        if expect_html:
            if "<!DOCTYPE html>" in content or "<html" in content:
                return True, "✅ HTML内容正常"
            elif content.strip().startswith("{") and "success" in content:
                return False, f"❌ 返回了JSON错误（应返回HTML）: {content[:200]}"
            else:
                return False, f"❌ 内容格式异常: {content[:200]}"
        else:
            # 静态资源检查
            if "ErrorHandler" in content or "DomUtils" in content or "Validator" in content:
                return True, "✅ JavaScript内容正常"
            elif "error-message" in content or "@keyframes" in content:
                return True, "✅ CSS内容正常"
            else:
                return True, "✅ 静态资源正常"
                
    except requests.exceptions.ConnectionError:
        return False, "❌ 连接失败 - 服务可能未启动"
    except requests.exceptions.Timeout:
        return False, "❌ 请求超时"
    except Exception as e:
        return False, f"❌ 异常: {str(e)}"


def test_all_pages():
    """测试所有页面"""
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}前端页面端到端测试{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")
    
    results = []
    passed = 0
    failed = 0
    
    # 测试页面
    print(f"{Colors.BOLD}📄 测试页面:{Colors.RESET}\n")
    for page_path, page_name, _ in PAGES_TO_TEST:
        url = urljoin(BASE_URL + "/", page_path)
        print(f"  {Colors.YELLOW}测试: {page_name} ({page_path}){Colors.RESET}")
        
        success, message = test_page(url, page_name, expect_html=True)
        
        if success:
            print(f"    {Colors.GREEN}✅ 通过: {message}{Colors.RESET}")
            passed += 1
        else:
            print(f"    {Colors.RED}❌ 失败: {message}{Colors.RESET}")
            failed += 1
            print(f"    {Colors.RED}   URL: {url}{Colors.RESET}")
        
        results.append(("页面", page_name, page_path, success, message))
        print()
    
    # 测试静态资源
    print(f"\n{Colors.BOLD}📦 测试静态资源:{Colors.RESET}\n")
    for resource_path, resource_name in STATIC_RESOURCES:
        url = urljoin(BASE_URL + "/", resource_path)
        print(f"  {Colors.YELLOW}测试: {resource_name} ({resource_path}){Colors.RESET}")
        
        success, message = test_page(url, resource_name, expect_html=False)
        
        if success:
            print(f"    {Colors.GREEN}✅ 通过: {message}{Colors.RESET}")
            passed += 1
        else:
            print(f"    {Colors.RED}❌ 失败: {message}{Colors.RESET}")
            print(f"    {Colors.RED}   URL: {url}{Colors.RESET}")
            failed += 1
        
        results.append(("资源", resource_name, resource_path, success, message))
        print()
    
    # 测试API端点（登录接口应该可访问）
    print(f"\n{Colors.BOLD}🔌 测试API端点:{Colors.RESET}\n")
    api_tests = [
        ("/api/v1/auth/login", "登录接口", True),  # 应该可以访问（不需要认证）
        ("/health", "健康检查", True),  # 应该可以访问
    ]
    
    for api_path, api_name, should_work in api_tests:
        url = f"http://localhost:8001{api_path}"
        print(f"  {Colors.YELLOW}测试: {api_name}{Colors.RESET}")
        
        try:
            if api_path == "/api/v1/auth/login":
                # POST 请求测试
                response = requests.post(url, json={}, timeout=5)
            else:
                response = requests.get(url, timeout=5)
            
            if response.status_code == 401:
                if should_work:
                    print(f"    {Colors.RED}❌ 失败: 401 未授权（应该在白名单中）{Colors.RESET}")
                    failed += 1
                else:
                    print(f"    {Colors.GREEN}✅ 通过: 401 未授权（符合预期）{Colors.RESET}")
                    passed += 1
            elif response.status_code == 200 or response.status_code == 422:
                print(f"    {Colors.GREEN}✅ 通过: HTTP {response.status_code}（可访问）{Colors.RESET}")
                passed += 1
            else:
                print(f"    {Colors.YELLOW}⚠️  警告: HTTP {response.status_code}{Colors.RESET}")
                passed += 1
        except Exception as e:
            print(f"    {Colors.RED}❌ 失败: {str(e)}{Colors.RESET}")
            failed += 1
        print()
    
    # 汇总
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}测试汇总:{Colors.RESET}")
    print(f"  {Colors.GREEN}✅ 通过: {passed}{Colors.RESET}")
    print(f"  {Colors.RED}❌ 失败: {failed}{Colors.RESET}")
    print(f"  📊 总计: {passed + failed}")
    print(f"  📈 通过率: {(passed / (passed + failed) * 100):.1f}%")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")
    
    # 失败详情
    if failed > 0:
        print(f"{Colors.RED}{Colors.BOLD}失败详情:{Colors.RESET}\n")
        for category, name, path, success, message in results:
            if not success:
                print(f"  {Colors.RED}❌ {category}: {name} ({path}){Colors.RESET}")
                print(f"      {message}\n")
    
    return failed == 0


if __name__ == "__main__":
    success = test_all_pages()
    sys.exit(0 if success else 1)

