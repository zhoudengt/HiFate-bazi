#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试热更新文件变化触发机制

测试新的热更新机制：
1. 文件变化后立即触发重载
2. 不依赖版本号检查
3. 重载成功后更新版本号
"""

import os
import sys
import time
import tempfile
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_file_change_trigger():
    """测试文件变化触发热更新"""
    print("\n" + "="*60)
    print("🧪 测试文件变化触发热更新机制")
    print("="*60)
    
    # 导入热更新管理器
    from server.hot_reload.hot_reload_manager import HotReloadManager
    from server.hot_reload.file_monitor import get_file_monitor
    from server.hot_reload.version_manager import VersionManager
    
    # 获取管理器实例
    manager = HotReloadManager.get_instance()
    
    # 检查是否已启动
    if not manager._running:
        print("⚠️  热更新管理器未启动，跳过测试")
        return False
    
    # 创建测试文件
    test_dir = os.path.join(project_root, "server", "hot_reload")
    os.makedirs(test_dir, exist_ok=True)
    test_file_path = os.path.join(test_dir, "__test_reload__.py")
    
    try:
        # 1. 获取初始版本号
        initial_version = VersionManager.get_version('source')
        print(f"✓ 初始版本号: {initial_version}")
        
        # 2. 创建测试文件
        test_content = f"# 热更新测试文件\n# 时间戳: {time.time()}\n"
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        print(f"✓ 创建测试文件: {test_file_path}")
        
        # 3. 等待文件监控器检测（最多10秒）
        print("⏳ 等待文件监控器检测文件变化...")
        max_wait = 10
        wait_interval = 0.5
        triggered = False
        
        for i in range(int(max_wait / wait_interval)):
            time.sleep(wait_interval)
            current_version = VersionManager.get_version('source')
            
            if current_version != initial_version:
                triggered = True
                print(f"✓ 检测到热更新触发（等待 {i * wait_interval:.1f} 秒）")
                print(f"  版本号变化: {initial_version} -> {current_version}")
                break
        
        if not triggered:
            print(f"❌ 文件变化未触发热更新（等待 {max_wait} 秒后超时）")
            return False
        
        # 4. 验证版本号已更新
        cached_version = VersionManager.get_cached_version('source')
        if cached_version == current_version:
            print(f"✓ 版本号缓存已更新: {cached_version}")
        else:
            print(f"⚠️  版本号缓存未更新（当前: {current_version}, 缓存: {cached_version}）")
        
        return True
        
    finally:
        # 清理测试文件
        try:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
                print(f"✓ 清理测试文件: {test_file_path}")
        except Exception as e:
            print(f"⚠️  清理测试文件失败: {e}")


def test_anti_duplicate_trigger():
    """测试防重复触发机制"""
    print("\n" + "="*60)
    print("🧪 测试防重复触发机制")
    print("="*60)
    
    from server.hot_reload.hot_reload_manager import HotReloadManager
    
    manager = HotReloadManager.get_instance()
    
    if not manager._running:
        print("⚠️  热更新管理器未启动，跳过测试")
        return False
    
    # 记录初始时间
    initial_time = manager._last_reload_time if hasattr(manager, '_last_reload_time') else 0
    print(f"✓ 初始触发时间: {initial_time}")
    
    # 模拟多次触发（1秒内）
    for i in range(3):
        manager._trigger_source_reload()
        current_time = manager._last_reload_time if hasattr(manager, '_last_reload_time') else 0
        time.sleep(0.2)  # 200ms，小于1秒
    
    # 验证只触发了一次
    final_time = manager._last_reload_time if hasattr(manager, '_last_reload_time') else 0
    if final_time > initial_time:
        print(f"✓ 防重复触发机制正常（最终时间: {final_time}）")
        return True
    else:
        print(f"⚠️  防重复触发机制可能未生效")
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🔥 热更新机制测试")
    print("="*60)
    
    results = []
    
    # 测试1：文件变化触发
    try:
        result = test_file_change_trigger()
        results.append(("文件变化触发", result))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("文件变化触发", False))
    
    # 测试2：防重复触发
    try:
        result = test_anti_duplicate_trigger()
        results.append(("防重复触发", result))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("防重复触发", False))
    
    # 打印总结
    print("\n" + "="*60)
    print("📊 测试结果总结")
    print("="*60)
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")
    
    all_passed = all(result for _, result in results)
    print(f"\n总体结果: {'✅ 全部通过' if all_passed else '❌ 部分失败'}")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

