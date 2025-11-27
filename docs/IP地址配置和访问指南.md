# IP 地址配置和访问指南

## 🎯 服务器信息

- **服务器 IP**：`192.168.1.8`
- **服务端口**：`8001`
- **访问地址**：`http://192.168.1.8:8001`

---

## 📝 需要修改的配置文件

### 1. 前端配置文件（必须修改）

**文件**：`frontend/config.js`

**修改内容**：

```javascript
// API 配置
const API_CONFIG = {
    baseURL: 'http://192.168.1.8:8001/api/v1',  // 修改这里
    timeout: 60000,
    fortuneApiKey: 'fortune_analysis_default_key_2024'
};

// gRPC-Web 配置
const GRPC_CONFIG = {
    enabled: true,
    baseURL: 'http://192.168.1.8:8001/api/grpc-web',  // 修改这里
    timeout: 60000,
    endpoints: []
};
```

**在服务器上修改**：

```bash
# 进入项目目录
cd /opt/HiFate-bazi

# 编辑配置文件
vim frontend/config.js

# 将 127.0.0.1 替换为 192.168.1.8
# 方法 1：使用 sed（快速）
sed -i 's/127.0.0.1/192.168.1.8/g' frontend/config.js

# 方法 2：手动编辑
vim frontend/config.js
# 找到这两行并修改：
# baseURL: 'http://127.0.0.1:8001/api/v1'  →  baseURL: 'http://192.168.1.8:8001/api/v1'
# baseURL: 'http://127.0.0.1:8001/api/grpc-web'  →  baseURL: 'http://192.168.1.8:8001/api/grpc-web'
```

---

### 2. 其他需要检查的文件

#### `frontend/smart-fortune.html` 和 `frontend/smart-fortune-stream.html`

**查找并替换**：
```bash
cd /opt/HiFate-bazi
sed -i 's/localhost:8001/192.168.1.8:8001/g' frontend/smart-fortune.html
sed -i 's/localhost:8001/192.168.1.8:8001/g' frontend/smart-fortune-stream.html
```

#### `frontend/shishen-debug.html`

**查找并替换**：
```bash
sed -i 's/127.0.0.1:8001/192.168.1.8:8001/g' frontend/shishen-debug.html
```

#### `frontend/js/desk-fengshui.js`

**查找并替换**：
```bash
sed -i 's/localhost:8001/192.168.1.8:8001/g' frontend/js/desk-fengshui.js
```

---

## 🚀 一键修改脚本

### 在服务器上执行：

```bash
# 进入项目目录
cd /opt/HiFate-bazi

# 一键替换所有 localhost 和 127.0.0.1
find frontend -type f \( -name "*.js" -o -name "*.html" \) -exec sed -i 's/127.0.0.1:8001/192.168.1.8:8001/g' {} \;
find frontend -type f \( -name "*.js" -o -name "*.html" \) -exec sed -i 's/localhost:8001/192.168.1.8:8001/g' {} \;

# 验证修改
grep -r "192.168.1.8:8001" frontend/config.js
```

---

## 🌐 访问地址

### 主页面

- **首页**：`http://192.168.1.8:8001/frontend/index.html`
- **登录页**：`http://192.168.1.8:8001/frontend/login.html`

### 功能页面

- **算法公式分析**：`http://192.168.1.8:8001/frontend/formula-analysis.html`
- **运势分析**：`http://192.168.1.8:8001/frontend/fortune.html`
- **面相分析 V2**：`http://192.168.1.8:8001/frontend/face-analysis-v2.html`
- **办公桌风水**：`http://192.168.1.8:8001/frontend/desk-fengshui.html`
- **智能运势分析**：`http://192.168.1.8:8001/frontend/smart-fortune.html`
- **排盘**：`http://192.168.1.8:8001/frontend/pan.html`
- **大运**：`http://192.168.1.8:8001/frontend/dayun.html`
- **流年**：`http://192.168.1.8:8001/frontend/liunian.html`
- **月运**：`http://192.168.1.8:8001/frontend/bazi-monthly-fortune.html`
- **日运**：`http://192.168.1.8:8001/frontend/bazi-daily-fortune.html`

### API 文档

- **Swagger API 文档**：`http://192.168.1.8:8001/docs`
- **健康检查**：`http://192.168.1.8:8001/health`

---

## 🔧 修改后重启服务

### 如果使用 Docker：

```bash
# 进入项目目录
cd /opt/HiFate-bazi

# 重启 Web 服务（使配置生效）
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart web

# 或者重新构建并启动
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build web
```

### 如果直接运行：

```bash
# 重启服务
systemctl restart hifate-bazi
# 或
./restart_server.sh
```

---

## ✅ 验证配置

### 1. 检查配置文件

```bash
# 检查 config.js
cat frontend/config.js | grep 192.168.1.8

# 应该看到：
# baseURL: 'http://192.168.1.8:8001/api/v1'
# baseURL: 'http://192.168.1.8:8001/api/grpc-web'
```

### 2. 测试访问

```bash
# 在服务器上测试
curl http://192.168.1.8:8001/health

# 应该返回健康状态
```

### 3. 浏览器访问

在浏览器中打开：
```
http://192.168.1.8:8001/frontend/formula-analysis.html
```

如果页面正常加载，说明配置成功。

---

## 🔒 防火墙配置

### 确保端口已开放

```bash
# CentOS/RHEL (firewalld)
firewall-cmd --permanent --add-port=8001/tcp
firewall-cmd --reload

# Ubuntu/Debian (UFW)
ufw allow 8001/tcp
ufw reload

# 或者使用 iptables
iptables -A INPUT -p tcp --dport 8001 -j ACCEPT
```

---

## 📱 从其他设备访问

### 局域网访问

如果服务器在局域网中，其他设备可以通过以下地址访问：

```
http://192.168.1.8:8001
```

### 外网访问（需要配置）

如果需要外网访问：

1. **配置路由器端口转发**：
   - 外部端口：8001
   - 内部 IP：192.168.1.8
   - 内部端口：8001

2. **使用公网 IP 或域名**：
   - 将配置中的 `192.168.1.8` 替换为公网 IP 或域名
   - 例如：`http://your-domain.com:8001`

---

## 🐛 常见问题

### Q1: 无法访问页面

**检查**：
1. 服务是否运行：`docker compose ps`
2. 端口是否开放：`netstat -tlnp | grep 8001`
3. 防火墙是否阻止：`firewall-cmd --list-ports`

### Q2: API 调用失败

**检查**：
1. 前端配置是否正确：`cat frontend/config.js`
2. 浏览器控制台是否有错误（F12）
3. 网络连接是否正常

### Q3: CORS 错误

**解决**：
- 确保使用正确的 IP 地址访问
- 检查后端 CORS 配置

---

## 📝 快速配置命令（一键执行）

```bash
# 在服务器上执行
cd /opt/HiFate-bazi

# 1. 修改配置文件
sed -i 's/127.0.0.1:8001/192.168.1.8:8001/g' frontend/config.js
sed -i 's/localhost:8001/192.168.1.8:8001/g' frontend/*.html
sed -i 's/localhost:8001/192.168.1.8:8001/g' frontend/js/*.js

# 2. 验证修改
grep -r "192.168.1.8:8001" frontend/config.js

# 3. 重启服务
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart web

# 4. 测试访问
curl http://192.168.1.8:8001/health
```

---

## ✅ 总结

1. **修改配置文件**：`frontend/config.js`（最重要）
2. **替换其他文件**：所有 `localhost` 和 `127.0.0.1`
3. **重启服务**：使配置生效
4. **访问地址**：`http://192.168.1.8:8001`

**完成以上步骤后，就可以通过 `http://192.168.1.8:8001` 访问服务了！**

