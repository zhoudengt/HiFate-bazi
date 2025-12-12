#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码生成器

用法：
    python scripts/generate.py api --name=feature_name --desc="功能描述"
    python scripts/generate.py service --name=feature_name --desc="服务描述"
    python scripts/generate.py test --name=feature_name
    python scripts/generate.py all --name=feature_name --desc="功能描述"

示例：
    python scripts/generate.py all --name=calendar --desc="万年历查询功能"
    
生成文件：
    - server/api/v1/{name}_api.py
    - server/services/{name}_service.py
    - tests/unit/test_{name}.py
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# ==================== 模板定义 ====================

API_TEMPLATE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{description} API

创建时间：{create_time}
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from server.services.{name}_service import {class_name}Service

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 数据模型 ====================

class {class_name}Request(BaseModel):
    """{description}请求模型"""
    # TODO: 添加请求字段
    pass


class {class_name}Response(BaseModel):
    """{description}响应模型"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")


# ==================== API 路由 ====================

@router.post("/{path}/query", response_model={class_name}Response, summary="{description}查询")
async def query_{name}(request: {class_name}Request):
    """
    {description}
    
    Args:
        request: 请求参数
        
    Returns:
        {class_name}Response: 响应结果
    """
    try:
        service = {class_name}Service()
        result = service.query(request)
        return {class_name}Response(success=True, data=result)
    except Exception as e:
        logger.error(f"{description}处理失败: {{e}}", exc_info=True)
        return {class_name}Response(success=False, error=str(e))
'''

SERVICE_TEMPLATE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{description} 服务

创建时间：{create_time}
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class {class_name}Service:
    """{description}服务类"""
    
    def __init__(self):
        """初始化服务"""
        logger.info("{class_name}Service 初始化完成")
    
    def query(self, request) -> Dict[str, Any]:
        """
        查询处理
        
        Args:
            request: 请求参数
            
        Returns:
            处理结果字典
        """
        try:
            # TODO: 实现业务逻辑
            result = {{
                "message": "{description}处理成功"
            }}
            logger.info(f"{description}查询成功")
            return result
        except Exception as e:
            logger.error(f"{description}查询失败: {{e}}", exc_info=True)
            raise
'''

TEST_TEMPLATE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{description} 测试

创建时间：{create_time}
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# 导入被测模块
from server.services.{name}_service import {class_name}Service


class Test{class_name}Service:
    """{class_name}Service 测试类"""
    
    # ==================== 测试前置 ====================
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.service = {class_name}Service()
    
    def teardown_method(self):
        """每个测试方法后执行"""
        pass
    
    # ==================== 单元测试 ====================
    
    def test_query_success(self):
        """测试：正常查询"""
        # Given: 准备测试数据
        request = Mock()
        
        # When: 执行被测方法
        result = self.service.query(request)
        
        # Then: 验证结果
        assert result is not None
        assert "message" in result
    
    def test_query_with_invalid_request(self):
        """测试：无效请求"""
        # Given
        request = None
        
        # When & Then
        # TODO: 根据实际业务逻辑调整
        # with pytest.raises(ValueError):
        #     self.service.query(request)
        pass
    
    # ==================== 边界测试 ====================
    
    def test_query_boundary_case(self):
        """测试：边界情况"""
        # TODO: 添加边界测试
        pass
    
    # ==================== Mock 测试 ====================
    
    def test_query_with_mock(self):
        """测试：使用 Mock"""
        # TODO: 添加 Mock 测试
        pass


class Test{class_name}API:
    """{class_name} API 测试类"""
    
    @pytest.fixture(autouse=True)
    def setup(self, client):
        """测试前置"""
        self.client = client
    
    def test_api_query_success(self, client):
        """测试：API 正常调用"""
        # Given
        request_data = {{}}  # TODO: 填写请求数据
        
        # When
        response = client.post("/api/v1/{path}/query", json=request_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
'''

GRPC_REGISTER_TEMPLATE = '''
# ===== {description} API 注册 =====
# 在 server/api/grpc_gateway.py 中添加以下代码：

# 1. 在 import 部分添加：
from server.api.v1.{name}_api import {class_name}Request, query_{name}

# 2. 在 SUPPORTED_ENDPOINTS 注册后添加：
@_register("/{path}/query")
async def _handle_{name}_query(payload: Dict[str, Any]):
    request_model = {class_name}Request(**payload)
    return await query_{name}(request_model)
'''

MAIN_REGISTER_TEMPLATE = '''
# ===== {description} 路由注册 =====
# 在 server/main.py 中添加以下代码：

# 1. 在 import 部分添加：
from server.api.v1.{name}_api import router as {name}_router

# 2. 在路由注册部分添加：
app.include_router({name}_router, prefix="/api/v1", tags=["{description}"])
logger.info("✓ {description}路由已注册")
'''


# ==================== 生成函数 ====================

def to_class_name(name: str) -> str:
    """将下划线命名转换为类名（PascalCase）"""
    return ''.join(word.capitalize() for word in name.split('_'))


def generate_api(name: str, desc: str) -> str:
    """生成 API 文件"""
    file_path = PROJECT_ROOT / f"server/api/v1/{name}_api.py"
    
    if file_path.exists():
        print(f"⚠️  文件已存在，跳过: {file_path}")
        return str(file_path)
    
    content = API_TEMPLATE.format(
        name=name,
        class_name=to_class_name(name),
        description=desc,
        path=name.replace('_', '-'),
        create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')
    print(f"✅ 创建 API 文件: {file_path}")
    return str(file_path)


def generate_service(name: str, desc: str) -> str:
    """生成 Service 文件"""
    file_path = PROJECT_ROOT / f"server/services/{name}_service.py"
    
    if file_path.exists():
        print(f"⚠️  文件已存在，跳过: {file_path}")
        return str(file_path)
    
    content = SERVICE_TEMPLATE.format(
        name=name,
        class_name=to_class_name(name),
        description=desc,
        create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')
    print(f"✅ 创建 Service 文件: {file_path}")
    return str(file_path)


def generate_test(name: str, desc: str) -> str:
    """生成测试文件"""
    file_path = PROJECT_ROOT / f"tests/unit/test_{name}.py"
    
    if file_path.exists():
        print(f"⚠️  文件已存在，跳过: {file_path}")
        return str(file_path)
    
    content = TEST_TEMPLATE.format(
        name=name,
        class_name=to_class_name(name),
        description=desc,
        path=name.replace('_', '-'),
        create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')
    print(f"✅ 创建测试文件: {file_path}")
    return str(file_path)


def print_register_instructions(name: str, desc: str):
    """打印注册说明"""
    class_name = to_class_name(name)
    path = name.replace('_', '-')
    
    print("\n" + "=" * 60)
    print("📝 请手动完成以下注册步骤：")
    print("=" * 60)
    
    print(GRPC_REGISTER_TEMPLATE.format(
        name=name,
        class_name=class_name,
        description=desc,
        path=path
    ))
    
    print(MAIN_REGISTER_TEMPLATE.format(
        name=name,
        description=desc
    ))
    
    print("=" * 60)


def generate_all(name: str, desc: str):
    """生成所有文件"""
    print(f"\n🚀 开始生成 '{desc}' 功能代码...\n")
    
    generate_service(name, desc)
    generate_api(name, desc)
    generate_test(name, desc)
    
    print_register_instructions(name, desc)
    
    print("\n✅ 代码生成完成！")
    print("\n下一步操作：")
    print("1. 完成上述注册步骤")
    print("2. 实现业务逻辑")
    print("3. 运行测试: pytest tests/unit/test_{}.py -v".format(name))


# ==================== 主函数 ====================

def main():
    parser = argparse.ArgumentParser(
        description="HiFate-bazi 代码生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/generate.py api --name=calendar --desc="万年历查询"
  python scripts/generate.py service --name=calendar --desc="万年历服务"
  python scripts/generate.py test --name=calendar --desc="万年历测试"
  python scripts/generate.py all --name=calendar --desc="万年历功能"
        """
    )
    
    parser.add_argument(
        "type",
        choices=["api", "service", "test", "all"],
        help="生成类型：api/service/test/all"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="功能名称（小写+下划线，如 calendar_api）"
    )
    parser.add_argument(
        "--desc",
        default="",
        help="功能描述（中文，如 万年历查询）"
    )
    
    args = parser.parse_args()
    
    # 默认描述
    if not args.desc:
        args.desc = args.name.replace('_', ' ').title()
    
    # 生成代码
    if args.type == "api":
        generate_api(args.name, args.desc)
        print_register_instructions(args.name, args.desc)
    elif args.type == "service":
        generate_service(args.name, args.desc)
    elif args.type == "test":
        generate_test(args.name, args.desc)
    elif args.type == "all":
        generate_all(args.name, args.desc)


if __name__ == "__main__":
    main()
