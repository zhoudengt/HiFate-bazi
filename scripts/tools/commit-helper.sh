#!/bin/bash

# HiFate-bazi 提交助手脚本
# 使用方式：./scripts/commit-helper.sh

set -e

echo "=========================================="
echo "📝 HiFate-bazi 提交助手"
echo "=========================================="

# 1. 运行提交前检查
echo ""
echo "🔍 运行提交前检查..."
./scripts/pre-commit-check.sh
if [ $? -ne 0 ]; then
    echo "❌ 检查未通过，请修复后再试"
    exit 1
fi

# 2. 选择提交类型
echo ""
echo "📌 选择提交类型："
echo "  1) [新增] 新功能"
echo "  2) [修复] Bug修复"
echo "  3) [优化] 性能优化"
echo "  4) [重构] 代码重构"
echo "  5) [文档] 文档更新"
echo "  6) [测试] 测试相关"
echo "  7) [配置] 配置修改"
echo ""
read -p "请选择 (1-7): " type_choice

case $type_choice in
    1) COMMIT_TYPE="[新增]" ;;
    2) COMMIT_TYPE="[修复]" ;;
    3) COMMIT_TYPE="[优化]" ;;
    4) COMMIT_TYPE="[重构]" ;;
    5) COMMIT_TYPE="[文档]" ;;
    6) COMMIT_TYPE="[测试]" ;;
    7) COMMIT_TYPE="[配置]" ;;
    *) echo "❌ 无效选择"; exit 1 ;;
esac

# 3. 输入提交描述
echo ""
read -p "📝 简短描述（不超过50字）: " description

if [ -z "$description" ]; then
    echo "❌ 描述不能为空"
    exit 1
fi

# 4. 列出修改的文件
echo ""
echo "📂 修改的文件："
CHANGED_FILES=$(git diff --cached --name-only)
echo "$CHANGED_FILES" | sed 's/^/  - /'

# 5. 输入详细说明
echo ""
read -p "📋 是否添加详细说明？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "请输入详细说明（输入 'END' 结束）："
    DETAIL=""
    while IFS= read -r line; do
        if [ "$line" = "END" ]; then
            break
        fi
        DETAIL="$DETAIL$line"$'\n'
    done
fi

# 6. 输入测试情况
echo ""
read -p "🧪 是否已测试？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    TEST_STATUS="已通过本地测试"
else
    TEST_STATUS="待测试"
fi

# 7. 生成提交信息
COMMIT_MSG="$COMMIT_TYPE $description"

if [ -n "$DETAIL" ] || [ -n "$CHANGED_FILES" ]; then
    COMMIT_MSG="$COMMIT_MSG

"
fi

if [ -n "$CHANGED_FILES" ]; then
    COMMIT_MSG="$COMMIT_MSG- 修改文件："$'\n'
    while IFS= read -r file; do
        COMMIT_MSG="$COMMIT_MSG  - $file"$'\n'
    done <<< "$CHANGED_FILES"
fi

if [ -n "$DETAIL" ]; then
    COMMIT_MSG="$COMMIT_MSG- 详细说明：$DETAIL"
fi

COMMIT_MSG="$COMMIT_MSG- 测试情况：$TEST_STATUS"

# 8. 显示提交信息预览
echo ""
echo "=========================================="
echo "📋 提交信息预览："
echo "=========================================="
echo "$COMMIT_MSG"
echo "=========================================="

# 9. 确认提交
echo ""
read -p "✅ 确认提交？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消提交"
    exit 1
fi

# 10. 执行提交
git commit -m "$COMMIT_MSG"

echo ""
echo "✅ 提交成功！"

# 11. 询问是否推送
CURRENT_BRANCH=$(git branch --show-current)
echo ""
read -p "🚀 是否推送到远程？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git push origin $CURRENT_BRANCH
    echo "✅ 已推送到 origin/$CURRENT_BRANCH"
    
    # 如果是 develop 或 master，提示自动部署
    if [ "$CURRENT_BRANCH" = "develop" ]; then
        echo ""
        echo "🚀 推送到 develop 分支，将自动部署到开发环境"
        echo "   查看部署进度：https://github.com/zhoudengt/HiFate-bazi/actions"
    elif [ "$CURRENT_BRANCH" = "master" ]; then
        echo ""
        echo "🚀 推送到 master 分支，将自动部署到生产环境"
        echo "   查看部署进度：https://github.com/zhoudengt/HiFate-bazi/actions"
    fi
else
    echo "ℹ️  提交已保存在本地，使用以下命令推送："
    echo "   git push origin $CURRENT_BRANCH"
fi

echo ""
echo "🎉 完成！"

