# GitHub 连接问题 - 解决方案

## 🔍 问题说明

### 错误信息：
```
Failed to connect to github.com port 443 after 35766 ms: Couldn't connect to server
```

### 原因：
- **服务器无法访问 GitHub**（网络问题）
- 可能的原因：
  1. 服务器在国内，访问 GitHub 慢或被限制
  2. 防火墙阻止了 443 端口
  3. 网络配置问题

---

## ❓ 为什么需要连接 GitHub？

**简单解释**：
- 你的代码存储在 **GitHub**（代码仓库）
- `git pull` 需要从 GitHub **下载**最新代码
- 就像从网盘下载文件，需要连接到网盘服务器

**流程**：
```
服务器 → 连接 GitHub → 下载代码 → 更新本地代码
```

---

## ✅ 解决方案

### 方案 1：使用 GitHub 镜像（推荐，最简单）

```bash
# 在服务器上执行
cd /opt/HiFate-bazi/HiFate-bazi

# 切换到 GitHub 镜像
git remote set-url origin https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git

# 重新拉取
git pull origin master
```

### 方案 2：使用其他镜像

```bash
# 镜像 1：ghproxy
git remote set-url origin https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git

# 镜像 2：cnpmjs
git remote set-url origin https://github.com.cnpmjs.org/zhoudengt/HiFate-bazi.git

# 镜像 3：fastgit
git remote set-url origin https://hub.fastgit.xyz/zhoudengt/HiFate-bazi.git

# 然后执行
git pull origin master
```

### 方案 3：直接下载代码包（不需要 git）

```bash
# 在服务器上执行
cd /opt/HiFate-bazi

# 下载代码 ZIP 包
wget https://github.com/zhoudengt/HiFate-bazi/archive/refs/heads/master.zip

# 解压
unzip master.zip

# 移动到正确位置
mv HiFate-bazi-master/* HiFate-bazi/ 2>/dev/null || true
mv HiFate-bazi-master/.* HiFate-bazi/ 2>/dev/null || true
rm -rf HiFate-bazi-master master.zip

cd HiFate-bazi
```

### 方案 4：配置代理（如果有代理服务器）

```bash
# 设置 HTTP 代理
export http_proxy=http://proxy-server:port
export https_proxy=http://proxy-server:port

# 然后执行 git pull
git pull origin master
```

---

## 🚀 快速解决方案（推荐）

### 在服务器上执行：

```bash
# 1. 进入项目目录
cd /opt/HiFate-bazi/HiFate-bazi

# 2. 切换到 GitHub 镜像（国内加速）
git remote set-url origin https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git

# 3. 验证远程地址
git remote -v

# 4. 重新拉取
git pull origin master

# 5. 如果还是慢，尝试其他镜像
# git remote set-url origin https://github.com.cnpmjs.org/zhoudengt/HiFate-bazi.git
```

---

## 📦 如果镜像也不行：直接下载代码包

```bash
# 在服务器上执行
cd /opt/HiFate-bazi

# 备份现有配置（如果有）
if [ -f HiFate-bazi/.env ]; then
    cp HiFate-bazi/.env /tmp/.env.backup
fi

# 下载代码 ZIP 包（使用镜像）
wget https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi/archive/refs/heads/master.zip

# 如果没有 wget，使用 curl
# curl -L -o master.zip https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi/archive/refs/heads/master.zip

# 解压
unzip master.zip

# 合并到项目目录
cd HiFate-bazi-master
cp -r * ../HiFate-bazi/ 2>/dev/null || true
cp -r .* ../HiFate-bazi/ 2>/dev/null || true
cd ..
rm -rf HiFate-bazi-master master.zip

# 恢复配置
if [ -f /tmp/.env.backup ]; then
    cp /tmp/.env.backup HiFate-bazi/.env
    chmod 600 HiFate-bazi/.env
fi

cd HiFate-bazi
```

---

## 🔧 检查网络连接

```bash
# 测试 GitHub 连接
ping -c 3 github.com

# 测试 HTTPS 连接
curl -I https://github.com

# 如果都失败，说明网络无法访问 GitHub
```

---

## 💡 推荐操作（你的情况）

### 在服务器上执行：

```bash
# 1. 进入项目目录
cd /opt/HiFate-bazi/HiFate-bazi

# 2. 切换到 GitHub 镜像（国内加速）
git remote set-url origin https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git

# 3. 重新拉取（应该会快很多）
git pull origin master

# 4. 如果还是慢，等待完成（可能需要 1-2 分钟）

# 5. 拉取成功后，执行部署
chmod +x scripts/deploy_remote.sh
./scripts/deploy_remote.sh
```

---

## 📝 总结

### 问题：
- 服务器无法连接 GitHub（网络问题）

### 解决：
1. **使用镜像**：`git remote set-url origin https://ghproxy.com/...`
2. **直接下载 ZIP**：不需要 git，直接下载代码包
3. **配置代理**：如果有代理服务器

### 推荐：
- **使用 GitHub 镜像**（最简单，最快）

---

## ⚠️ 注意事项

1. **镜像可能不稳定**：如果某个镜像失败，尝试其他镜像
2. **ZIP 下载**：如果 git 完全不行，直接下载 ZIP 包
3. **网络问题**：这是服务器网络问题，不是代码问题

