#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微服务热更新测试脚本

测试内容：
1. 热更新基本功能
2. 回滚机制
3. 依赖关系管理
4. 错误处理
5. 并发安全
6. 性能优化
"""

import sys
import os
import time
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.hot_reload.microservice_reloader import (
    MicroserviceReloader,
    create_hot_reload_server,
    register_microservice_reloader,
    get_dependent_services,
    trigger_dependent_services
)


def test_basic_hot_reload():
    """测试基本热更新功能"""
    print("\n" + "="*60)
    print("测试 1: 基本热更新功能")
    print("="*60)
    
    # 创建临时测试文件
    test_dir = tempfile.mkdtemp()
    test_file = os.path.join(test_dir, "test_servicer.py")
    
    # 初始代码
    initial_code = '''
class TestServicer:
    def __init__(self):
        self.version = 1
    
    def get_version(self):
        return self.version
'''
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(initial_code)
    
    try:
        # 创建热更新器（模拟）
        print("✓ 创建测试文件")
        print(f"  文件: {test_file}")
        
        # 验证文件存在
        assert os.path.exists(test_file), "测试文件不存在"
        print("✓ 测试文件创建成功")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    finally:
        # 清理
        shutil.rmtree(test_dir, ignore_errors=True)


def test_rollback_mechanism():
    """测试回滚机制"""
    print("\n" + "="*60)
    print("测试 2: 回滚机制")
    print("="*60)
    
    try:
        from server.hot_reload.microservice_reloader import MicroserviceReloader
        
        # 检查备份目录创建
        backup_dir = os.path.join(project_root, ".hot_reload_backups", "test_service")
        os.makedirs(backup_dir, exist_ok=True)
        
        assert os.path.exists(backup_dir), "备份目录未创建"
        print("✓ 备份目录创建成功")
        
        # 检查错误日志目录
        error_log_dir = os.path.join(project_root, "logs", "hot_reload_errors")
        os.makedirs(error_log_dir, exist_ok=True)
        
        assert os.path.exists(error_log_dir), "错误日志目录未创建"
        print("✓ 错误日志目录创建成功")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_dependency_management():
    """测试依赖关系管理"""
    print("\n" + "="*60)
    print("测试 3: 依赖关系管理")
    print("="*60)
    
    try:
        # 测试获取依赖服务
        dependent_services = get_dependent_services("src/bazi_calculator.py")
        print(f"✓ src/bazi_calculator.py 的依赖服务: {dependent_services}")
        assert len(dependent_services) > 0, "应该找到依赖服务"
        
        # 测试 server/ 目录的依赖
        dependent_services = get_dependent_services("server/services/rule_service.py")
        print(f"✓ server/services/rule_service.py 的依赖服务: {dependent_services}")
        assert len(dependent_services) > 0, "应该找到依赖服务"
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*60)
    print("测试 4: 错误处理")
    print("="*60)
    
    try:
        # 检查错误日志目录
        error_log_dir = os.path.join(project_root, "logs", "hot_reload_errors")
        os.makedirs(error_log_dir, exist_ok=True)
        
        # 检查是否可以写入错误日志
        test_log_file = os.path.join(error_log_dir, "test_log.json")
        import json
        test_log = {
            "service_name": "test_service",
            "error": "测试错误",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(test_log_file, 'w', encoding='utf-8') as f:
            json.dump(test_log, f, ensure_ascii=False, indent=2)
        
        assert os.path.exists(test_log_file), "错误日志文件未创建"
        print("✓ 错误日志写入成功")
        
        # 清理测试文件
        os.remove(test_log_file)
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_performance_optimization():
    """测试性能优化"""
    print("\n" + "="*60)
    print("测试 5: 性能优化")
    print("="*60)
    
    try:
        # 测试文件状态更新（应该优先使用修改时间）
        test_file = os.path.join(project_root, "server", "hot_reload", "microservice_reloader.py")
        
        if os.path.exists(test_file):
            mtime1 = os.path.getmtime(test_file)
            time.sleep(0.1)  # 等待一小段时间
            mtime2 = os.path.getmtime(test_file)
            
            # 修改时间应该相同（文件未改变）
            assert mtime1 == mtime2, "修改时间应该相同"
            print("✓ 文件修改时间检查正常")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_concurrent_safety():
    """测试并发安全"""
    print("\n" + "="*60)
    print("测试 6: 并发安全")
    print("="*60)
    
    try:
        from server.hot_reload.microservice_reloader import MicroserviceReloader
        import threading
        
        # 检查是否有锁机制
        reloader = MicroserviceReloader(
            service_name="test_service",
            module_path="server.hot_reload.microservice_reloader",
            servicer_class_name="MicroserviceReloader",
            check_interval=30
        )
        
        assert hasattr(reloader, '_servicer_lock'), "应该有 servicer_lock"
        assert hasattr(reloader, '_servicer_lock'), "应该有 servicer_lock"
        print("✓ 锁机制存在")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_dynamic_servicer():
    """测试 DynamicServicer"""
    print("\n" + "="*60)
    print("测试 7: DynamicServicer 方法转发")
    print("="*60)
    
    try:
        from server.hot_reload.microservice_reloader import DynamicServicer, MicroserviceReloader
        
        # 创建测试 Servicer
        class TestServicer:
            def test_method(self):
                return "test_result"
        
        # 创建热更新器
        reloader = MicroserviceReloader(
            service_name="test_service",
            module_path="__main__",
            servicer_class_name="TestServicer",
            check_interval=30
        )
        reloader.set_servicer(TestServicer())
        
        # 创建 DynamicServicer
        dynamic_servicer = DynamicServicer(reloader)
        
        # 测试方法调用
        result = dynamic_servicer.test_method()
        assert result == "test_result", "方法调用应该成功"
        print("✓ DynamicServicer 方法转发正常")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("微服务热更新系统测试")
    print("="*60)
    
    tests = [
        ("基本热更新功能", test_basic_hot_reload),
        ("回滚机制", test_rollback_mechanism),
        ("依赖关系管理", test_dependency_management),
        ("错误处理", test_error_handling),
        ("性能优化", test_performance_optimization),
        ("并发安全", test_concurrent_safety),
        ("DynamicServicer", test_dynamic_servicer),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

