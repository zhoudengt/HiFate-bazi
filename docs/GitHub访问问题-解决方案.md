# GitHub 访问问题 - 完整解决方案

## 🔍 问题分析

### 可能的原因：

1. **网络限制**：国内服务器访问 GitHub 可能被限制
2. **IP 封禁**：频繁请求导致 IP 被 GitHub 临时封禁
3. **DNS 问题**：DNS 解析失败
4. **防火墙**：服务器防火墙阻止了连接
5. **GitHub 服务问题**：GitHub 服务暂时不可用

---

## ✅ 解决方案

### 方案 1：使用 GitHub 镜像（推荐，最简单）

#### 镜像列表：

```bash
# 镜像 1：ghproxy（推荐）
git clone https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git .

# 镜像 2：cnpmjs
git clone https://github.com.cnpmjs.org/zhoudengt/HiFate-bazi.git .

# 镜像 3：fastgit
git clone https://hub.fastgit.xyz/zhoudengt/HiFate-bazi.git .

# 镜像 4：gitclone
git clone https://gitclone.com/github.com/zhoudengt/HiFate-bazi.git .
```

#### 如果已经克隆过，切换远程地址：

```bash
# 进入项目目录
cd /opt/HiFate-bazi

# 切换到镜像地址
git remote set-url origin https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git

# 验证
git remote -v

# 重新拉取
git pull origin master
```

---

### 方案 2：直接下载 ZIP 包（不需要 git）

```bash
# 在服务器上执行

# 1. 进入项目目录
cd /opt
rm -rf HiFate-bazi  # 如果已存在，先删除
mkdir -p HiFate-bazi
cd HiFate-bazi

# 2. 下载 ZIP 包（使用镜像）
wget https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi/archive/refs/heads/master.zip

# 如果没有 wget，使用 curl
# curl -L -o master.zip https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi/archive/refs/heads/master.zip

# 3. 解压
unzip master.zip

# 4. 移动到正确位置
mv HiFate-bazi-master/* . 2>/dev/null || true
mv HiFate-bazi-master/.[^.]* . 2>/dev/null || true
rm -rf HiFate-bazi-master master.zip

# 5. 验证
ls -la
ls -la scripts/deploy_remote.sh
```

---

### 方案 3：配置代理（如果有代理服务器）

```bash
# 设置 HTTP 代理
export http_proxy=http://proxy-server:port
export https_proxy=http://proxy-server:port

# 设置 Git 代理
git config --global http.proxy http://proxy-server:port
git config --global https.proxy http://proxy-server:port

# 然后执行 git clone
git clone https://github.com/zhoudengt/HiFate-bazi.git .

# 使用完后取消代理
unset http_proxy https_proxy
git config --global --unset http.proxy
git config --global --unset https.proxy
```

---

### 方案 4：修改 DNS（解决 DNS 解析问题）

```bash
# 编辑 hosts 文件
vim /etc/hosts

# 添加以下内容
140.82.112.3 github.com
140.82.112.4 github.com
185.199.108.153 assets-cdn.github.com
199.232.69.194 github.global.ssl.fastly.net

# 保存后测试
ping github.com
```

---

### 方案 5：使用 SSH 方式（如果配置了 SSH 密钥）

```bash
# 如果之前配置过 SSH 密钥，可以尝试 SSH 方式
git clone git@github.com:zhoudengt/HiFate-bazi.git .

# 如果 SSH 也失败，检查 SSH 连接
ssh -T git@github.com
```

---

## 🚀 推荐操作（你的情况）

### 在服务器上执行：

```bash
# 方案 A：使用镜像重新克隆（推荐）

cd /opt
rm -rf HiFate-bazi
mkdir -p HiFate-bazi
cd HiFate-bazi

# 使用镜像克隆
git clone https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git .

# 验证
ls -la scripts/deploy_remote.sh

# 执行部署
chmod +x scripts/deploy_remote.sh
./scripts/deploy_remote.sh
```

```bash
# 方案 B：直接下载 ZIP 包（如果 git 完全不行）

cd /opt
rm -rf HiFate-bazi
mkdir -p HiFate-bazi
cd HiFate-bazi

# 下载 ZIP
wget https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi/archive/refs/heads/master.zip

# 解压
unzip master.zip
mv HiFate-bazi-master/* .
mv HiFate-bazi-master/.[^.]* . 2>/dev/null || true
rm -rf HiFate-bazi-master master.zip

# 验证
ls -la scripts/deploy_remote.sh

# 执行部署
chmod +x scripts/deploy_remote.sh
./scripts/deploy_remote.sh
```

---

## 🔧 诊断步骤

### 1. 检查网络连接

```bash
# 测试 GitHub 连接
ping -c 3 github.com

# 测试 HTTPS 连接
curl -I https://github.com

# 如果都失败，说明网络无法访问 GitHub
```

### 2. 检查 DNS 解析

```bash
# 查看 DNS 解析
nslookup github.com

# 或使用 dig
dig github.com
```

### 3. 检查防火墙

```bash
# 检查防火墙状态（CentOS）
systemctl status firewalld

# 检查防火墙规则
iptables -L -n | grep 443
```

### 4. 检查 Git 配置

```bash
# 查看 Git 配置
git config --list

# 检查代理设置
git config --global --get http.proxy
git config --global --get https.proxy
```

---

## 📝 永久解决方案

### 修改 Git 全局配置（使用镜像）

```bash
# 设置全局镜像
git config --global url."https://ghproxy.com/https://github.com/".insteadOf "https://github.com/"

# 验证
git config --global --get-regexp url

# 之后所有 git clone 都会自动使用镜像
git clone https://github.com/zhoudengt/HiFate-bazi.git .
```

### 修改项目远程地址（已克隆的项目）

```bash
# 进入项目目录
cd /opt/HiFate-bazi

# 切换到镜像地址
git remote set-url origin https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi.git

# 验证
git remote -v

# 以后 git pull 都会使用镜像
git pull origin master
```

---

## 🎯 快速解决方案（复制粘贴）

### 如果 git clone 失败，直接下载 ZIP：

```bash
cd /opt && \
rm -rf HiFate-bazi && \
mkdir -p HiFate-bazi && \
cd HiFate-bazi && \
wget https://ghproxy.com/https://github.com/zhoudengt/HiFate-bazi/archive/refs/heads/master.zip && \
unzip master.zip && \
mv HiFate-bazi-master/* . && \
mv HiFate-bazi-master/.[^.]* . 2>/dev/null || true && \
rm -rf HiFate-bazi-master master.zip && \
chmod +x scripts/deploy_remote.sh && \
./scripts/deploy_remote.sh
```

---

## 📊 镜像对比

| 镜像 | 地址 | 稳定性 | 速度 |
|------|------|--------|------|
| ghproxy | `ghproxy.com` | ⭐⭐⭐⭐ | 快 |
| cnpmjs | `github.com.cnpmjs.org` | ⭐⭐⭐ | 中等 |
| fastgit | `hub.fastgit.xyz` | ⭐⭐ | 中等 |
| gitclone | `gitclone.com` | ⭐⭐⭐ | 中等 |

**推荐使用 ghproxy**，稳定性最好。

---

## ⚠️ 注意事项

1. **镜像可能不稳定**：如果某个镜像失败，尝试其他镜像
2. **ZIP 下载**：如果 git 完全不行，直接下载 ZIP 包
3. **数据持久化**：ZIP 下载不会保留 git 历史，但可以正常部署
4. **更新代码**：如果使用 ZIP，后续更新需要重新下载

---

## ✅ 总结

### 问题：
- GitHub 访问被限制或 IP 被封禁

### 解决方案（按优先级）：
1. **使用镜像**：`git clone https://ghproxy.com/https://github.com/...`
2. **下载 ZIP**：直接下载代码包，不需要 git
3. **配置代理**：如果有代理服务器
4. **修改 DNS**：解决 DNS 解析问题

### 推荐：
- **最快**：直接下载 ZIP 包
- **最稳定**：使用 ghproxy 镜像

---

**现在在服务器上执行方案 B（下载 ZIP），最快最稳定！**

