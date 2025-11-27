# HiFate-bazi Docker 部署 - 简明版

## 📍 三个概念要分清

1. **本地电脑**：你现在写代码的电脑（Mac/Windows）
2. **GitHub**：代码仓库（`https://github.com/zhoudengt/HiFate-bazi`）
3. **远程服务器**：要部署代码的服务器（Linux 服务器，有公网 IP）

---

## 🎯 部署流程

### 第一步：连接到远程服务器

```bash
# 这个命令是在你的本地电脑上执行的
# 用来连接到你要部署的服务器

ssh root@你的服务器IP
# 例如：ssh root@192.168.1.100
# 或者：ssh ubuntu@example.com
```

**说明**：
- `root` 或 `ubuntu` 是服务器的用户名
- `192.168.1.100` 或 `example.com` 是你的服务器 IP 地址或域名
- 这个命令是在**本地电脑**上执行的，用来登录到**远程服务器**

**如何获取服务器信息**：
- 服务器 IP：从云服务商（阿里云、腾讯云、AWS 等）控制台查看
- 用户名：通常是 `root`（CentOS）或 `ubuntu`（Ubuntu）

---

### 第二步：在服务器上克隆代码

```bash
# 现在你已经登录到服务器了
# 以下命令都在服务器上执行

# 1. 创建项目目录
cd /opt
sudo mkdir -p HiFate-bazi
sudo chown $USER:$USER HiFate-bazi
cd HiFate-bazi

# 2. 从 GitHub 克隆代码（使用 HTTPS，最简单）
git clone https://github.com/zhoudengt/HiFate-bazi.git .

# 3. 执行部署
chmod +x scripts/deploy_remote.sh
./scripts/deploy_remote.sh
```

---

## 🚀 完整示例

假设你的服务器信息是：
- IP：`123.456.789.0`
- 用户名：`root`

### 在本地电脑上执行：

```bash
# 1. 连接到服务器
ssh root@123.456.789.0

# 输入密码后，你就登录到服务器了
```

### 在服务器上执行（登录后）：

```bash
# 2. 创建目录并克隆代码
cd /opt
sudo mkdir -p HiFate-bazi
sudo chown $USER:$USER HiFate-bazi
cd HiFate-bazi
git clone https://github.com/zhoudengt/HiFate-bazi.git .

# 3. 配置环境变量
cp env.template .env
vim .env  # 编辑配置，修改密码和密钥
chmod 600 .env

# 4. 执行部署
chmod +x scripts/deploy_remote.sh
./scripts/deploy_remote.sh
```

---

## 📝 一键部署脚本（复制粘贴即可）

### 在服务器上执行（替换你的服务器信息）：

```bash
# 替换下面的信息：
# - 123.456.789.0 改为你的服务器 IP
# - root 改为你的服务器用户名

# 在本地电脑执行（连接服务器）
ssh root@123.456.789.0 << 'EOF'
# 以下命令在服务器上执行

cd /opt
sudo mkdir -p HiFate-bazi
sudo chown $USER:$USER HiFate-bazi
cd HiFate-bazi
git clone https://github.com/zhoudengt/HiFate-bazi.git .
chmod +x scripts/deploy_remote.sh
./scripts/deploy_remote.sh

EOF
```

---

## ❓ 常见问题

### Q1: 我没有服务器怎么办？

**A**: 需要先购买一台云服务器：
- 阿里云：https://www.aliyun.com
- 腾讯云：https://cloud.tencent.com
- AWS：https://aws.amazon.com
- 其他云服务商

### Q2: 我不知道服务器 IP 和用户名？

**A**: 
- **IP 地址**：在云服务商控制台的"实例列表"中查看
- **用户名**：
  - CentOS/RHEL：通常是 `root`
  - Ubuntu：通常是 `ubuntu`
  - 其他：查看云服务商文档

### Q3: SSH 连接失败怎么办？

**A**: 检查：
1. 服务器是否已启动
2. 防火墙是否开放 22 端口
3. IP 地址是否正确
4. 用户名是否正确

### Q4: 如何获取服务器密码？

**A**: 
- 云服务器：在控制台重置密码或查看初始密码
- 自建服务器：使用你设置的 root 密码

---

## 🎯 总结

1. **本地电脑** → 执行 `ssh root@服务器IP` → 连接到**远程服务器**
2. **远程服务器** → 执行 `git clone https://github.com/zhoudengt/HiFate-bazi.git` → 从 **GitHub** 拉取代码
3. **远程服务器** → 执行 `./scripts/deploy_remote.sh` → 部署应用

**关键点**：
- `ssh user@ip` 是连接服务器的命令，不是 GitHub 相关的
- GitHub 只是代码仓库，代码需要下载到服务器上才能运行
- 部署是在服务器上执行的，不是在本地电脑

---

## 📞 需要帮助？

如果还有不清楚的地方，请告诉我：
- 你的服务器 IP 是多少？
- 你的服务器用户名是什么？
- 你使用的是什么云服务商？

我可以帮你生成具体的部署命令！

