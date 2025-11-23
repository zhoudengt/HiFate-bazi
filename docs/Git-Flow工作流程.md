# Git Flow 工作流程 - HiFate-bazi 项目

> 完整的分支管理和代码发布流程

## 🌳 分支架构

```
master (生产环境) ───────────────────────────────> 线上服务器
  ↑                                                production
  │ merge (经过充分测试)
  │
develop (开发环境) ──────────────────────────────> 开发服务器  
  ↑                                                staging
  │ merge (功能完成后)
  │
feature/* (功能分支) ─────────────────────────────> 本地开发
  ↑                                                localhost
  │ create (开始新功能)
  │
develop
```

---

## 📋 分支说明

| 分支 | 用途 | 生命周期 | 部署环境 | 保护规则 |
|------|------|----------|----------|----------|
| **master** | 生产环境 | 永久 | 生产服务器 | 🔒 只接受 PR，禁止直接 push |
| **develop** | 开发主分支 | 永久 | 开发服务器 | 🔒 建议 PR，可直接 push |
| **feature/** | 功能开发 | 临时 | 本地 | ✅ 自由开发 |
| **hotfix/** | 紧急修复 | 临时 | 本地 | ⚠️ 可直接合并到 master |

---

## 🔄 完整工作流程

### 场景 1：开发新功能

#### 步骤 1：创建功能分支

```bash
# 1. 确保 develop 是最新的
git checkout develop
git pull origin develop

# 2. 创建功能分支
git checkout -b feature/用户注册功能

# 命名规范：
# feature/简短描述
# 例如：
# feature/add-payment
# feature/fix-login-bug
# feature/optimize-rule-engine
```

#### 步骤 2：本地开发

```bash
# 1. 修改代码
vim server/api/v1/auth.py

# 2. 本地测试（必须！）
./start_all_services.sh
# 访问 http://localhost:8001 测试功能

# 3. 确保功能正常后再提交
```

#### 步骤 3：提交到功能分支

```bash
# 1. 查看修改
git status
git diff

# 2. 添加文件
git add server/api/v1/auth.py
git add frontend/js/auth.js

# 3. 提交
git commit -m "[新增] 用户注册功能

- 新增文件：server/api/v1/auth.py
- 修改文件：frontend/js/auth.js
- 功能说明：实现用户注册、登录接口
- 测试情况：本地测试通过"

# 4. 推送到远程
git push origin feature/用户注册功能
```

#### 步骤 4：合并到 develop

```bash
# 方式A：命令行合并（快速）
git checkout develop
git pull origin develop
git merge feature/用户注册功能
git push origin develop

# 方式B：GitHub Pull Request（推荐，适合团队）
# 1. 访问 https://github.com/zhoudengt/HiFate-bazi
# 2. 点击 "Compare & pull request"
# 3. Base: develop ← Compare: feature/用户注册功能
# 4. 填写 PR 描述
# 5. 点击 "Create pull request"
# 6. 审查后点击 "Merge pull request"
```

#### 步骤 5：开发环境测试

```bash
# develop 合并后，GitHub Actions 自动部署到开发服务器
# 访问开发环境测试：http://dev.hifate.com

# 如果发现问题：
# 1. 切回功能分支修复
git checkout feature/用户注册功能
# 2. 修复后重新合并
```

#### 步骤 6：发布到生产

```bash
# 开发环境测试通过后

# 1. 切换到 master
git checkout master
git pull origin master

# 2. 合并 develop
git merge develop

# 3. 推送（触发生产部署）
git push origin master

# GitHub Actions 自动部署到生产服务器
```

#### 步骤 7：清理功能分支（可选）

```bash
# 本地删除
git branch -d feature/用户注册功能

# 远程删除
git push origin --delete feature/用户注册功能
```

---

### 场景 2：紧急修复（Hotfix）

生产环境发现严重Bug，需要紧急修复：

```bash
# 1. 从 master 创建 hotfix 分支
git checkout master
git pull origin master
git checkout -b hotfix/修复登录bug

# 2. 修复bug
vim server/api/v1/auth.py

# 3. 本地测试
./start_all_services.sh
# 确保bug已修复

# 4. 提交
git add server/api/v1/auth.py
git commit -m "[修复] 紧急修复登录失败问题

- 修改文件：server/api/v1/auth.py
- 问题：Token验证逻辑错误
- 解决：修正验证算法
- 测试：本地测试通过"

# 5. 合并到 master（紧急发布）
git checkout master
git merge hotfix/修复登录bug
git push origin master

# 6. 同时合并到 develop（保持同步）
git checkout develop
git merge hotfix/修复登录bug
git push origin develop

# 7. 删除 hotfix 分支
git branch -d hotfix/修复登录bug
```

---

### 场景 3：多人协作

#### 开发者 A 和 B 同时开发不同功能

**开发者 A**：
```bash
git checkout -b feature/支付功能 develop
# 开发支付功能...
git push origin feature/支付功能
```

**开发者 B**：
```bash
git checkout -b feature/订单管理 develop
# 开发订单管理...
git push origin feature/订单管理
```

**合并顺序**：
1. A 先完成，合并到 develop
2. B 在合并前，先同步 develop 的更新
```bash
git checkout feature/订单管理
git fetch origin
git rebase origin/develop  # 或 git merge origin/develop
# 解决冲突（如有）
git push origin feature/订单管理
```
3. B 再合并到 develop

---

## 🎯 最佳实践

### ✅ 推荐做法

1. **小步提交**
   ```bash
   # 每完成一个小功能就提交
   git commit -m "[新增] 添加用户注册表单"
   git commit -m "[新增] 实现注册API"
   git commit -m "[测试] 添加注册功能测试"
   ```

2. **功能分支保持短生命周期**
   ```
   创建 → 开发 → 测试 → 合并 → 删除
   建议：1-3天内完成
   ```

3. **频繁同步 develop**
   ```bash
   # 每天早上
   git checkout develop
   git pull origin develop
   git checkout feature/my-feature
   git merge develop  # 合并最新代码
   ```

4. **提交前必须本地测试**
   ```bash
   # 启动服务
   ./start_all_services.sh
   
   # 测试功能
   # 访问前端页面验证
   
   # 检查日志无错误
   tail -f logs/server.log
   ```

5. **使用描述性的分支名**
   ```bash
   # ✅ 好的命名
   feature/user-authentication
   feature/add-wechat-payment
   hotfix/fix-rule-matching-bug
   
   # ❌ 不好的命名
   feature/test
   feature/fix
   feature/update
   ```

### ❌ 避免的做法

1. **不要直接在 master 开发**
   ```bash
   # ❌ 错误
   git checkout master
   vim some_file.py
   git commit ...
   
   # ✅ 正确
   git checkout develop
   git checkout -b feature/new-feature
   ```

2. **不要长期不合并功能分支**
   ```
   ❌ 功能分支开发2周还没合并
   ✅ 功能分支1-3天内合并
   ```

3. **不要跳过本地测试**
   ```bash
   # ❌ 错误：未测试直接提交
   git add .
   git commit -m "修改"
   git push
   
   # ✅ 正确：测试后再提交
   ./start_all_services.sh
   # 测试功能...
   git add .
   git commit -m "[新增] 功能描述（已测试）"
   ```

4. **不要在功能分支上修改无关代码**
   ```bash
   # ❌ 错误：在 feature/支付功能 中修改登录逻辑
   # ✅ 正确：只修改支付相关代码
   ```

---

## 📊 分支生命周期示例

### 完整的功能开发周期

```
Day 1 09:00 - 创建功能分支
  git checkout -b feature/短信验证码
  
Day 1 10:00-12:00 - 开发
  vim server/services/sms_service.py
  git commit -m "[新增] 短信服务基础功能"
  
Day 1 14:00-17:00 - 继续开发
  vim server/api/v1/sms.py
  git commit -m "[新增] 短信验证码API"
  
Day 1 17:30 - 本地测试
  ./start_all_services.sh
  # 测试通过
  
Day 1 18:00 - 推送功能分支
  git push origin feature/短信验证码
  
Day 2 09:00 - 合并到 develop
  git checkout develop
  git merge feature/短信验证码
  git push origin develop
  # 自动部署到开发环境
  
Day 2 10:00 - 开发环境测试
  访问 http://dev.hifate.com 测试
  # 测试通过
  
Day 2 14:00 - 发布到生产
  git checkout master
  git merge develop
  git push origin master
  # 自动部署到生产环境
  
Day 2 14:10 - 清理分支
  git branch -d feature/短信验证码
  git push origin --delete feature/短信验证码
```

---

## 🔍 常用 Git 命令

### 查看状态

```bash
# 查看当前分支和修改
git status

# 查看分支列表
git branch -a

# 查看提交历史
git log --oneline -10
git log --graph --all

# 查看某个文件的修改历史
git log --follow server/main.py
```

### 分支操作

```bash
# 创建并切换分支
git checkout -b feature/new-feature

# 切换分支
git checkout develop

# 删除本地分支
git branch -d feature/old-feature

# 删除远程分支
git push origin --delete feature/old-feature

# 重命名分支
git branch -m old-name new-name
```

### 同步更新

```bash
# 拉取远程更新
git pull origin develop

# 获取所有远程分支
git fetch origin

# 查看远程分支
git remote -v

# 合并分支
git merge feature/branch-name

# 变基（保持提交历史整洁）
git rebase develop
```

### 撤销操作

```bash
# 撤销工作区修改
git checkout -- file.py

# 撤销暂存区
git reset HEAD file.py

# 撤销最后一次提交（保留修改）
git reset --soft HEAD^

# 撤销最后一次提交（丢弃修改）
git reset --hard HEAD^
```

---

## 🚨 冲突解决

### 发生冲突时

```bash
# 1. 尝试合并
git merge develop
# 提示：CONFLICT (content): Merge conflict in server/main.py

# 2. 查看冲突文件
git status

# 3. 打开冲突文件
vim server/main.py

# 4. 解决冲突（编辑文件，选择保留哪部分代码）
<<<<<<< HEAD
# 你的代码
=======
# develop 分支的代码
>>>>>>> develop

# 5. 标记为已解决
git add server/main.py

# 6. 完成合并
git commit -m "[合并] 解决与 develop 的冲突"

# 7. 推送
git push origin feature/my-feature
```

---

## 📋 检查清单

### 创建功能分支前

- [ ] 已更新 develop 到最新
- [ ] 分支名称描述清晰
- [ ] 明确功能范围

### 提交代码前

- [ ] 本地测试通过
- [ ] 代码符合规范
- [ ] 提交信息清晰
- [ ] 只提交相关文件

### 合并到 develop 前

- [ ] 功能完整
- [ ] 本地测试通过
- [ ] 已同步最新 develop
- [ ] 无冲突

### 发布到 master 前

- [ ] 开发环境测试通过
- [ ] 无已知bug
- [ ] 已备份数据库（如需要）
- [ ] 通知团队发布

---

## 🎉 完整示例

一个真实的功能开发流程：

```bash
# ========== Day 1: 开始开发 ==========

# 1. 创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/add-wechat-payment

# 2. 开发微信支付功能
vim server/services/wechat_payment.py
vim server/api/v1/payment.py
vim frontend/js/payment.js

# 3. 本地测试
./start_all_services.sh
# 测试微信支付流程...

# 4. 提交
git add server/services/wechat_payment.py server/api/v1/payment.py frontend/js/payment.js
git commit -m "[新增] 微信支付功能

- 新增文件：server/services/wechat_payment.py
- 修改文件：server/api/v1/payment.py, frontend/js/payment.js
- 功能说明：实现微信扫码支付
- 测试情况：本地测试通过，支付流程正常"

git push origin feature/add-wechat-payment

# ========== Day 2: 合并和发布 ==========

# 5. 合并到 develop
git checkout develop
git pull origin develop
git merge feature/add-wechat-payment
git push origin develop
# GitHub Actions 自动部署到开发环境

# 6. 开发环境测试（30分钟后）
# 访问 http://dev.hifate.com 测试微信支付
# 测试通过！

# 7. 发布到生产
git checkout master
git pull origin master
git merge develop
git push origin master
# GitHub Actions 自动部署到生产环境

# 8. 清理分支
git branch -d feature/add-wechat-payment
git push origin --delete feature/add-wechat-payment

# 完成！🎉
```

---

## 📞 获取帮助

**遇到问题时**：

1. 查看 Git 状态
   ```bash
   git status
   ```

2. 查看提交历史
   ```bash
   git log --oneline -10
   ```

3. 咨询 AI 助手
   ```
   "我在合并分支时遇到冲突，怎么解决？"
   "如何撤销最后一次提交？"
   "如何查看某个文件的修改历史？"
   ```

---

**掌握 Git Flow，让代码管理井井有条！** ✨

