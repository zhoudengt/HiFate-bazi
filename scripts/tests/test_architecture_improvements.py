#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
架构改进测试脚本
验证统一配置、接口抽象、依赖注入的效果
"""

import sys
import os
from unittest.mock import Mock, MagicMock, patch

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def test_unified_config():
    """测试统一配置管理"""
    print("=" * 60)
    print("测试 1: 统一配置管理")
    print("=" * 60)
    
    from server.config.app_config import get_config, DatabaseConfig, RedisConfig, ServiceConfig
    
    # 测试配置加载
    config = get_config()
    print(f"✅ 配置加载成功")
    print(f"   - 环境: {config.env}")
    print(f"   - 数据库主机: {config.database.host}")
    print(f"   - 数据库端口: {config.database.port}")
    print(f"   - Redis 主机: {config.redis.host}")
    print(f"   - Redis 端口: {config.redis.port}")
    
    # 测试配置单例
    config2 = get_config()
    assert config is config2, "配置应该是单例"
    print(f"✅ 配置单例模式正常")
    
    # 测试从环境变量创建
    with patch.dict(os.environ, {
        'MYSQL_HOST': 'test_host',
        'MYSQL_PORT': '3307',
        'REDIS_HOST': 'test_redis'
    }):
        db_config = DatabaseConfig.from_env()
        assert db_config.host == 'test_host'
        assert db_config.port == 3307
        print(f"✅ 从环境变量创建配置正常")
    
    print()


def test_interface_abstraction():
    """测试接口抽象层"""
    print("=" * 60)
    print("测试 2: 接口抽象层")
    print("=" * 60)
    
    from server.interfaces.bazi_core_client_interface import IBaziCoreClient
    from server.interfaces.bazi_rule_client_interface import IBaziRuleClient
    from server.interfaces.bazi_calculator_interface import IBaziCalculator
    
    # 测试接口定义存在
    assert IBaziCoreClient is not None
    assert IBaziRuleClient is not None
    assert IBaziCalculator is not None
    print(f"✅ 接口定义存在")
    
    # 测试 Mock 实现接口
    mock_client = Mock(spec=IBaziCoreClient)
    mock_client.calculate_bazi.return_value = {
        'bazi_pillars': {
            'year': {'stem': '庚', 'branch': '午'},
            'month': {'stem': '己', 'branch': '丑'},
            'day': {'stem': '甲', 'branch': '子'},
            'hour': {'stem': '庚', 'branch': '午'}
        },
        'basic_info': {'solar_date': '1990-01-15', 'solar_time': '12:00', 'gender': 'male'},
        'details': {},
        'ten_gods_stats': {},
        'elements': {},
        'element_counts': {},
        'relationships': {}
    }
    
    # 验证 Mock 实现了接口
    assert isinstance(mock_client, IBaziCoreClient)
    result = mock_client.calculate_bazi("1990-01-15", "12:00", "male")
    assert result is not None
    print(f"✅ Mock 可以实现接口")
    print()


def test_dependency_injection():
    """测试依赖注入"""
    print("=" * 60)
    print("测试 3: 依赖注入")
    print("=" * 60)
    
    from server.services.bazi_service_v2 import BaziServiceV2
    from server.interfaces.bazi_core_client_interface import IBaziCoreClient
    
    # 创建 Mock 客户端
    mock_client = Mock(spec=IBaziCoreClient)
    mock_client.calculate_bazi.return_value = {
        'bazi_pillars': {
            'year': {'stem': '庚', 'branch': '午'},
            'month': {'stem': '己', 'branch': '丑'},
            'day': {'stem': '甲', 'branch': '子'},
            'hour': {'stem': '庚', 'branch': '午'}
        },
        'basic_info': {'solar_date': '1990-01-15', 'solar_time': '12:00', 'gender': 'male'},
        'details': {},
        'ten_gods_stats': {},
        'elements': {},
        'element_counts': {},
        'relationships': {}
    }
    
    # 通过依赖注入创建服务
    service = BaziServiceV2(core_client=mock_client)
    print(f"✅ 服务创建成功（依赖注入）")
    
    # 调用服务
    result = service.calculate_bazi_full("1990-01-15", "12:00", "male")
    assert result is not None
    assert "bazi" in result
    print(f"✅ 服务调用成功")
    
    # 验证 Mock 被调用
    assert mock_client.calculate_bazi.called
    print(f"✅ 依赖注入正常工作")
    print()


def test_service_without_client():
    """测试不使用远程客户端（本地计算）"""
    print("=" * 60)
    print("测试 4: 本地计算（无依赖注入）")
    print("=" * 60)
    
    from server.services.bazi_service_v2 import BaziServiceV2
    
    # 创建服务（不注入客户端）
    service = BaziServiceV2(core_client=None)
    print(f"✅ 服务创建成功（无远程客户端）")
    
    # 调用服务（应该使用本地计算）
    result = service.calculate_bazi_full("1990-01-15", "12:00", "male")
    assert result is not None
    assert "bazi" in result
    assert "rizhu" in result
    print(f"✅ 本地计算成功")
    print(f"   - 日柱: {result.get('rizhu')}")
    print()


def test_service_factory():
    """测试服务工厂"""
    print("=" * 60)
    print("测试 5: 服务工厂")
    print("=" * 60)
    
    from server.factories.service_factory import ServiceFactory
    
    # 使用工厂创建服务
    service = ServiceFactory.create_bazi_service()
    assert service is not None
    print(f"✅ 工厂创建服务成功")
    
    # 验证服务可以正常工作
    result = service.calculate_bazi_full("1990-01-15", "12:00", "male")
    assert result is not None
    print(f"✅ 工厂创建的服务正常工作")
    print()


def test_low_coupling():
    """测试低耦合度"""
    print("=" * 60)
    print("测试 6: 低耦合度（可替换实现）")
    print("=" * 60)
    
    from server.services.bazi_service_v2 import BaziServiceV2
    from server.interfaces.bazi_core_client_interface import IBaziCoreClient
    
    # 创建两个不同的 Mock 实现
    mock_client1 = Mock(spec=IBaziCoreClient)
    mock_client2 = Mock(spec=IBaziCoreClient)
    
    # 创建两个服务实例，使用不同的客户端
    service1 = BaziServiceV2(core_client=mock_client1)
    service2 = BaziServiceV2(core_client=mock_client2)
    
    # 验证它们可以独立工作
    assert service1 is not service2
    assert service1._core_client is mock_client1
    assert service2._core_client is mock_client2
    print(f"✅ 可以轻松替换实现（低耦合）")
    print()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("架构改进测试")
    print("=" * 60)
    print()
    
    try:
        test_unified_config()
        test_interface_abstraction()
        test_dependency_injection()
        test_service_without_client()
        test_service_factory()
        test_low_coupling()
        
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        print()
        print("改进效果：")
        print("  ✅ 统一配置管理 - 配置集中，易于管理")
        print("  ✅ 接口抽象层 - 可以轻松替换实现")
        print("  ✅ 依赖注入 - 降低耦合，易于测试")
        print()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

