#!/bin/bash

# 🚀 为xiechitian账户设置GitHub仓库的自动化脚本
# Automated script to setup GitHub repository for xiechitian account

echo "🚀 开始为xiechitian账户设置GitHub仓库..."
echo "=================================================="

# 检查Git配置
echo "🔍 检查当前Git配置..."
echo "当前Git用户: $(git config user.name)"
echo "当前Git邮箱: $(git config user.email)"
echo ""

# 配置Git用户信息
echo "🔧 配置Git用户信息为xiechitian..."
git config user.name "xiechitian"
git config user.email "xiechitian@example.com"
echo "✅ Git用户信息已配置"
echo ""

# 检查当前分支
echo "🌿 检查当前分支..."
current_branch=$(git branch --show-current)
echo "当前分支: $current_branch"

if [ "$current_branch" != "xiechitian-main" ]; then
    echo "🔄 切换到xiechitian-main分支..."
    git checkout xiechitian-main
else
    echo "✅ 已在xiechitian-main分支上"
fi
echo ""

# 检查远程仓库
echo "🌐 检查远程仓库配置..."
if git remote get-url xiechitian >/dev/null 2>&1; then
    echo "✅ xiechitian远程仓库已配置: $(git remote get-url xiechitian)"
else
    echo "❌ xiechitian远程仓库未配置"
    echo ""
    echo "请先在GitHub上创建仓库，然后运行以下命令："
    echo "git remote add xiechitian https://github.com/xiechitian/data-copy-tool.git"
    echo ""
    exit 1
fi
echo ""

# 显示推送命令
echo "📤 准备推送代码到xiechitian仓库..."
echo "使用以下命令推送代码："
echo ""
echo "git push -u xiechitian xiechitian-main"
echo ""
echo "如果遇到身份验证问题，请："
echo "1. 确保GitHub仓库已创建"
echo "2. 准备好xiechitian的GitHub用户名"
echo "3. 准备好Personal Access Token"
echo ""

# 检查是否有未提交的更改
echo "📝 检查是否有未提交的更改..."
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  发现未提交的更改："
    git status --short
    echo ""
    echo "建议先提交这些更改："
    echo "git add ."
    echo "git commit -m 'Update project files'"
    echo ""
else
    echo "✅ 没有未提交的更改"
fi
echo ""

# 显示当前状态
echo "📊 当前仓库状态："
echo "分支: $(git branch --show-current)"
echo "远程仓库:"
git remote -v
echo ""
echo "提交历史 (最近5条):"
git log --oneline -5
echo ""

echo "🎯 下一步操作："
echo "1. 在GitHub上创建名为 'data-copy-tool' 的仓库"
echo "2. 运行推送命令: git push -u xiechitian xiechitian-main"
echo "3. 输入GitHub用户名和Personal Access Token"
echo ""
echo "🚀 准备就绪！现在可以推送代码到xiechitian的GitHub仓库了！"
