# DBeaver 快速配置指南

## 📋 已安装的组件

✅ DBeaver Community Edition 已成功安装
✅ 配置文件位置：`~/Library/DBeaverData/workspace6/General/.dbeaver/data-sources.json`

## 🔌 数据库连接信息

### MySQL 连接（生产 Node1 Docker）
- **主机**: `8.210.52.217`
- **端口**: `3306`
- **用户名**: `root`
- **密码**: `${SSH_PASSWORD}`
- **数据库**: `hifate_bazi`

### MongoDB 连接（生产 Node1 Docker）
- **主机**: `8.210.52.217`
- **端口**: `27017`
- **数据库**: `bazi_feedback`
- **认证**: 无认证（默认）

---

## ⚡ 快速配置步骤

### 方式一：在 DBeaver GUI 中配置（推荐）

#### 配置 MySQL 连接

1. **打开 DBeaver**
   - 如果 DBeaver 已经打开，跳到步骤 2
   - 如果未打开，运行：`open -a DBeaver`

2. **检查现有连接**
   - 在左侧导航器中查看是否已有 "hifate_bazi" 连接
   - 如果有，右键点击 → **"Edit Connection"** 编辑连接
   - 如果没有，继续步骤 3

3. **创建/编辑 MySQL 连接**
   - 点击左上角 **"新建数据库连接"** 按钮（或 `Cmd + Shift + N`）
   - 选择 **MySQL** → 点击 **"Next"**

4. **填写连接信息**
   - **Server Host**: `8.210.52.217`
   - **Port**: `3306`
   - **Database**: `hifate_bazi`
   - **Username**: `root`
   - **Password**: `${SSH_PASSWORD}`
   - ✅ 勾选 **"Save password"**

5. **测试连接**
   - 点击 **"Test Connection"**
   - 如果提示下载驱动，点击 **"Download"**
   - 等待驱动下载完成
   - 再次点击 **"Test Connection"**，应该显示 ✅ "Connected"

6. **保存连接**
   - 点击 **"Finish"** 保存

#### 配置 MongoDB 连接

1. **创建新连接**
   - 点击左上角 **"新建数据库连接"** 按钮（或 `Cmd + Shift + N`）
   - 选择 **MongoDB** → 点击 **"Next"**

2. **填写连接信息**
   - **Server Host**: `8.210.52.217`
   - **Port**: `27017`
   - **Database**: `bazi_feedback`
   - **Authentication**: 选择 **None**（无需认证）

3. **测试连接**
   - 点击 **"Test Connection"**
   - 如果提示下载驱动，点击 **"Download"**
   - 等待驱动下载完成
   - 再次点击 **"Test Connection"**，应该显示 ✅ "Connected"

4. **保存连接**
   - 点击 **"Finish"** 保存

---

## 🔍 验证连接

### 验证 MySQL 连接

1. 在左侧导航器中展开 MySQL 连接
2. 展开 `hifate_bazi` 数据库
3. 展开 `Tables`，应该能看到数据表列表
4. 双击任意表，应该能查看表数据

### 验证 MongoDB 连接

1. 在左侧导航器中展开 MongoDB 连接
2. 展开 `bazi_feedback` 数据库
3. 展开 `Collections`，应该能看到集合列表
4. 双击任意集合，应该能查看文档数据

---

## 🛠️ 故障排查

### MySQL 连接失败

**错误**: "Access denied for user..."
- ✅ 检查用户名和密码是否正确
- ✅ 确认密码为：`${SSH_PASSWORD}`

**错误**: "Can't connect to MySQL server..."
- ✅ 检查网络连接是否正常
- ✅ 确认防火墙允许访问 `8.210.52.217:3306`
- ✅ 尝试使用命令测试连接：
  ```bash
  mysql -h 8.210.52.217 -P 3306 -u root -p
  # 输入密码: ${SSH_PASSWORD}
  ```

### MongoDB 连接失败

**错误**: "Connection refused..."
- ✅ 检查网络连接是否正常
- ✅ 确认防火墙允许访问 `8.210.52.217:27017`
- ✅ 尝试使用命令测试连接：
  ```bash
  mongosh "mongodb://8.210.52.217:27017/bazi_feedback"
  ```

**错误**: "Driver not found..."
- ✅ 在 DBeaver 中：`Help` → `Driver Manager`
- ✅ 搜索 "MongoDB"，选择对应的驱动
- ✅ 点击 `Edit` → `Download` 下载驱动

---

## 📝 配置文件位置

如果需要手动查看或编辑配置文件（不推荐）：

```bash
# 配置文件路径
~/Library/DBeaverData/workspace6/General/.dbeaver/data-sources.json

# 查看配置
cat ~/Library/DBeaverData/workspace6/General/.dbeaver/data-sources.json | python3 -m json.tool
```

⚠️ **注意**: 密码是加密存储的，直接编辑 JSON 文件可能不会生效，建议使用 GUI 配置。

---

## 🚀 快速测试连接脚本

可以使用以下 Python 脚本快速测试数据库连接：

```python
# 测试 MySQL 连接
import pymysql
try:
    conn = pymysql.connect(
        host='8.210.52.217',
        port=3306,
        user='root',
        password='${SSH_PASSWORD}',
        database='hifate_bazi'
    )
    print("✅ MySQL 连接成功")
    conn.close()
except Exception as e:
    print(f"❌ MySQL 连接失败: {e}")

# 测试 MongoDB 连接
try:
    from pymongo import MongoClient
    client = MongoClient('mongodb://8.210.52.217:27017/')
    db = client['bazi_feedback']
    db.list_collection_names()
    print("✅ MongoDB 连接成功")
    client.close()
except Exception as e:
    print(f"❌ MongoDB 连接失败: {e}")
```

---

## ✅ 配置完成检查清单

- [ ] MySQL 连接已创建并测试成功
- [ ] MongoDB 连接已创建并测试成功
- [ ] 可以正常查看 MySQL 数据库表
- [ ] 可以正常查看 MongoDB 集合
- [ ] 驱动已正确下载和安装

配置完成后，你就可以在 DBeaver 中方便地管理生产环境的数据库了！🎉
