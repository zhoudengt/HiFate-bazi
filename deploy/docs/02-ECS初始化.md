# 02 - ECS 初始化

## 前置条件

- 阿里云 ECS × 2（2C8G）
- 系统：Alibaba Cloud Linux 3
- 安全组：开放端口 80, 443, 22
- 内网互通（同一 VPC）

## 初始化步骤

### 1. 登录 ECS

```bash
# 通过 SSH 登录两台机器
ssh root@NODE1_PUBLIC_IP
ssh root@NODE2_PUBLIC_IP
```

### 2. 执行初始化脚本

**方式一：一键执行**
```bash
curl -fsSL https://raw.githubusercontent.com/your-repo/HiFate-bazi/master/deploy/scripts/init-ecs.sh | bash
```

**方式二：手动执行**
```bash
# 更新系统
yum update -y

# 安装基础工具
yum install -y git curl wget vim htop net-tools jq

# 安装 Docker
yum install -y yum-utils
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 启动 Docker
systemctl start docker
systemctl enable docker

# 配置 Docker 镜像加速
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"],
  "log-driver": "json-file",
  "log-opts": {"max-size": "100m", "max-file": "3"},
  "storage-driver": "overlay2",
  "live-restore": true
}
EOF

systemctl daemon-reload
systemctl restart docker

# 安装 Docker Compose
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r '.tag_name')
curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
```

### 3. 验证安装

```bash
docker --version
# Docker version 24.x.x

docker-compose --version
# Docker Compose version v2.x.x

docker run hello-world
# Hello from Docker!
```

### 4. 创建项目目录

```bash
mkdir -p /opt/HiFate-bazi
cd /opt/HiFate-bazi
```

### 5. 克隆代码

```bash
git clone https://github.com/your-org/HiFate-bazi.git .
# 或
git clone git@github.com:your-org/HiFate-bazi.git .
```

### 6. 配置防火墙（如果需要）

```bash
# 查看防火墙状态
systemctl status firewalld

# 开放端口
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --permanent --add-port=3306/tcp
firewall-cmd --permanent --add-port=6379/tcp
firewall-cmd --reload
```

### 7. 系统优化（可选）

```bash
# 文件描述符限制
cat >> /etc/security/limits.conf << 'EOF'
* soft nofile 65535
* hard nofile 65535
EOF

# 内核参数
cat >> /etc/sysctl.conf << 'EOF'
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
vm.swappiness = 10
EOF
sysctl -p
```

## 两台机器都要执行

以上步骤需要在 **Node1** 和 **Node2** 上都执行。

## 下一步

完成初始化后，继续 [03-首次部署](03-首次部署.md)。
