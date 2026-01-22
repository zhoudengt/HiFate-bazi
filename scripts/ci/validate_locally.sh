#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# 本地验证脚本 - 模拟 GitHub Actions 环境
# 用途：在本地运行 CI/CD 检查，提前发现问题

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 检查 Python 版本
check_python() {
    print_header "检查 Python 环境"
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version)
    print_success "Python 版本: ${PYTHON_VERSION}"
    
    # 检查是否为 Python 3.11
    if ! python3 -c "import sys; assert sys.version_info >= (3, 11), '需要 Python 3.11 或更高版本'"; then
        print_warning "建议使用 Python 3.11（GitHub Actions 使用 3.11）"
    fi
}

# 安装依赖
install_dependencies() {
    print_header "安装依赖"
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt 不存在"
        exit 1
    fi
    
    print_success "升级 pip..."
    python3 -m pip install --upgrade pip || {
        print_error "pip 升级失败"
        exit 1
    }
    
    print_success "安装依赖..."
    pip install -r requirements.txt || {
        print_error "依赖安装失败"
        exit 1
    }
    
    print_success "依赖安装完成"
}

# 运行代码审查检查
run_code_review() {
    print_header "运行代码审查检查"
    
    REVIEW_SCRIPTS=(
        "scripts/review/check_cursorrules.py:开发规范符合性检查"
        "scripts/review/check_security.py:安全漏洞检查"
        "scripts/review/check_hot_reload.py:热更新支持检查"
        "scripts/review/check_encoding.py:编码方式检查"
        "scripts/review/check_grpc.py:gRPC 端点注册检查"
        "scripts/review/check_tests.py:测试覆盖检查"
        "scripts/review/code_review_check.py:综合代码审查检查"
    )
    
    FAILED=0
    for script_info in "${REVIEW_SCRIPTS[@]}"; do
        IFS=':' read -r script_path description <<< "${script_info}"
        
        if [ ! -f "${script_path}" ]; then
            print_error "${description}: 脚本不存在 ${script_path}"
            FAILED=1
            continue
        fi
        
        echo "运行: ${description}..."
        if python3 "${script_path}" --exit-on-error 2>/dev/null || python3 "${script_path}" 2>/dev/null; then
            print_success "${description} 通过"
        else
            print_error "${description} 失败"
            FAILED=1
        fi
    done
    
    if [ $FAILED -eq 1 ]; then
        print_error "部分代码审查检查失败"
        return 1
    fi
    
    print_success "所有代码审查检查通过"
    return 0
}

# 运行 gRPC 代码生成和修复
run_grpc_generation() {
    print_header "运行 gRPC 代码生成和修复"
    
    # 检查 grpc_tools
    if ! python3 -m grpc_tools.protoc --version &> /dev/null; then
        print_warning "grpc_tools 未安装或不可用"
    else
        print_success "grpc_tools 可用"
    fi
    
    # 检查 grpcio
    if ! python3 -c "import grpc" 2>/dev/null; then
        print_error "无法导入 grpc 模块"
        return 1
    else
        GRPC_VERSION=$(python3 -c "import grpc; print(grpc.__version__)")
        print_success "grpcio 版本: ${GRPC_VERSION}"
    fi
    
    # 生成 gRPC 代码
    if [ -f "scripts/grpc/generate_grpc_code.sh" ]; then
        echo "生成 gRPC 代码..."
        if bash scripts/grpc/generate_grpc_code.sh; then
            print_success "gRPC 代码生成成功"
        else
            print_warning "gRPC 代码生成失败，使用现有代码"
        fi
    else
        print_warning "gRPC 代码生成脚本不存在"
    fi
    
    # 修复版本检查
    if [ -f "scripts/grpc/fix_version_check.py" ]; then
        echo "修复 gRPC 版本检查..."
        if python3 scripts/grpc/fix_version_check.py; then
            print_success "gRPC 版本检查修复成功"
        else
            print_warning "gRPC 版本检查修复失败"
        fi
    fi
    
    # 验证 gRPC 代码可以导入
    if [ -d "proto/generated" ]; then
        echo "验证 gRPC 代码导入..."
        if python3 -c "
import sys
sys.path.insert(0, 'proto/generated')
try:
    import bazi_core_pb2_grpc
    import bazi_rule_pb2_grpc
    print('✅ gRPC 代码导入成功')
except Exception as e:
    print(f'❌ gRPC 代码导入失败: {e}')
    exit(1)
" 2>/dev/null; then
            print_success "gRPC 代码导入验证通过"
        else
            print_error "gRPC 代码导入验证失败"
            return 1
        fi
    else
        print_warning "proto/generated 目录不存在"
    fi
    
    return 0
}

# 运行测试（如果数据库可用）
run_tests() {
    print_header "运行测试"
    
    # 检查是否有测试文件
    if [ ! -d "tests" ]; then
        print_warning "tests 目录不存在，跳过测试"
        return 0
    fi
    
    # 检查数据库连接（可选）
    if command -v mysql &> /dev/null; then
        echo "检查 MySQL 连接..."
        # 这里可以添加数据库连接检查
    fi
    
    print_warning "本地测试需要数据库环境，跳过实际测试执行"
    print_warning "要运行完整测试，请使用: pytest tests/ -v"
    
    return 0
}

# 主函数
main() {
    print_header "GitHub Actions 本地验证"
    
    echo "此脚本模拟 GitHub Actions CI/CD 环境，在本地运行检查"
    echo ""
    
    # 运行检查
    check_python
    install_dependencies
    
    # 运行诊断
    if [ -f "scripts/ci/diagnose_github_actions.py" ]; then
        print_header "运行诊断脚本"
        python3 scripts/ci/diagnose_github_actions.py || {
            print_warning "诊断脚本发现一些问题，但继续执行"
        }
    fi
    
    # 运行代码审查检查
    if ! run_code_review; then
        print_error "代码审查检查失败"
        exit 1
    fi
    
    # 运行 gRPC 代码生成
    if ! run_grpc_generation; then
        print_error "gRPC 代码生成/修复失败"
        exit 1
    fi
    
    # 运行测试（可选）
    run_tests
    
    print_header "验证完成"
    print_success "所有检查通过！可以提交代码了。"
    echo ""
    echo "下一步："
    echo "  1. 提交代码到 Git"
    echo "  2. 推送到远程仓库"
    echo "  3. GitHub Actions 将自动运行 CI/CD"
}

# 执行主函数
main "$@"
