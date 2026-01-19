# DBeaver 数据库连接配置指南

## 数据库连接信息

### MySQL 连接信息（生产 Node1 Docker）
- **主机**: `8.210.52.217`
- **端口**: `3306`
- **用户名**: `root`
- **密码**: `${SSH_PASSWORD}`
- **数据库**: `hifate_bazi`

### MongoDB 连接信息（生产 Node1 Docker）
- **主机**: `8.210.52.217`
- **端口**: `27017`
- **数据库**: `bazi_feedback`
- **认证**: 无认证（默认）

---

## 配置 MySQL 连接

### 步骤 1: 创建新连接
1. 打开 DBeaver
2. 点击左上角的 **"新建数据库连接"** 按钮（或 `Cmd + Shift + N`）
3. 在数据库列表中选择 **MySQL**

### 步骤 2: 填写连接信息
在 "Main" 标签页中填写以下信息：

- **Server Host**: `8.210.52.217`
- **Port**: `3306`
- **Database**: `hifate_bazi`
- **Username**: `root`
- **Password**: `${SSH_PASSWORD}`

### 步骤 3: 测试连接
1. 点击左下角的 **"Test Connection"** 按钮
2. 如果提示下载驱动，点击 **"Download"** 下载 MySQL 驱动
3. 等待驱动下载完成
4. 再次点击 **"Test Connection"**，应该显示 "Connected" 成功消息

### 步骤 4: 保存连接
1. 点击 **"Finish"** 保存连接
2. 连接会出现在左侧的数据库导航器中

---

## 配置 MongoDB 连接

### 步骤 1: 创建新连接
1. 点击左上角的 **"新建数据库连接"** 按钮（或 `Cmd + Shift + N`）
2. 在数据库列表中选择 **MongoDB**

### 步骤 2: 填写连接信息
在 "Main" 标签页中填写以下信息：

- **Server Host**: `8.210.52.217`
- **Port**: `27017`
- **Database**: `bazi_feedback`
- **Authentication**: 选择 **None**（无需认证）

### 步骤 3: 测试连接
1. 点击左下角的 **"Test Connection"** 按钮
2. 如果提示下载驱动，点击 **"Download"** 下载 MongoDB 驱动
3. 等待驱动下载完成
4. 再次点击 **"Test Connection"**，应该显示 "Connected" 成功消息

### 步骤 4: 保存连接
1. 点击 **"Finish"** 保存连接
2. 连接会出现在左侧的数据库导航器中

---

## 验证连接

### MySQL 连接验证
1. 在左侧导航器中展开 MySQL 连接
2. 展开 `hifate_bazi` 数据库
3. 查看表列表，确认可以正常访问

### MongoDB 连接验证
1. 在左侧导航器中展开 MongoDB 连接
2. 展开 `bazi_feedback` 数据库
3. 查看集合（Collections）列表，确认可以正常访问

---

## 故障排查

### 如果 MySQL 连接失败
- 检查网络连接是否正常
- 确认防火墙允许访问 `8.210.52.217:3306`
- 确认 MySQL 服务正在运行
- 检查用户名和密码是否正确

### 如果 MongoDB 连接失败
- 检查网络连接是否正常
- 确认防火墙允许访问 `8.210.52.217:27017`
- 确认 MongoDB 服务正在运行
- 确认 MongoDB 配置允许无认证连接

### 如果驱动下载失败
- 检查网络连接
- 尝试手动下载驱动：`Help` -> `Driver Manager` -> 选择对应的驱动 -> `Edit` -> `Download`

---

## 快速连接字符串（参考）

### MySQL 连接字符串
```
jdbc:mysql://8.210.52.217:3306/hifate_bazi?useUnicode=true&characterEncoding=utf8mb4
```

### MongoDB 连接字符串
```
mongodb://8.210.52.217:27017/bazi_feedback
```
