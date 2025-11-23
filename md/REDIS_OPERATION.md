# Redis 操作文档

## Redis 安装状态

Redis 已通过 Homebrew 安装。
- **安装路径**: `/opt/homebrew/Cellar/redis/8.0.1/`
- **版本**: Redis 8.0.1

## 查看 Redis 状态

### 检查 Redis 是否运行
```bash
# 方式1：使用 Homebrew 服务管理
brew services list | grep redis

# 方式2：使用 ps 命令
ps aux | grep redis-server

# 方式3：检查端口是否监听
lsof -i :6379

# 方式4：使用 Redis CLI 测试
redis-cli ping
# 返回 PONG 表示运行正常
```

## 启动 Redis

### 方式1：使用 Homebrew 服务管理（推荐，开机自启）
```bash
brew services start redis
```

### 方式2：手动启动（前台运行）
```bash
redis-server
```

### 方式3：后台运行
```bash
redis-server --daemonize yes
```

## 停止 Redis

```bash
# 停止服务
brew services stop redis

# 或者使用 Redis CLI
redis-cli shutdown
```

## 登录 Redis CLI

```bash
# 连接到本地 Redis（默认端口 6379）
redis-cli

# 如果设置了密码，使用：
redis-cli -a your_password

# 连接到远程 Redis
redis-cli -h hostname -p port -a password

# 测试连接
redis-cli ping
# 应该返回：PONG
```

## 常用 Redis 命令

### 基础操作

```bash
# 在 redis-cli 中执行：

# 查看所有键（谨慎使用，数据量大时很慢）
KEYS *

# 查看匹配模式的键
KEYS bazi:*

# 查看键的数量
DBSIZE

# 检查键是否存在
EXISTS key_name

# 获取键的值
GET key_name

# 设置键值对
SET key_name "value"

# 设置带过期时间的键（秒）
SETEX key_name 3600 "value"

# 设置键的过期时间
EXPIRE key_name 3600

# 查看键的剩余过期时间（-1 表示永不过期，-2 表示键不存在）
TTL key_name

# 删除键
DEL key_name

# 删除多个键
DEL key1 key2 key3

# 清空当前数据库（谨慎使用）
FLUSHDB

# 清空所有数据库（谨慎使用）
FLUSHALL
```

### 字符串操作

```bash
# 设置字符串
SET mykey "Hello Redis"

# 获取字符串
GET mykey

# 追加字符串
APPEND mykey " World"

# 获取字符串长度
STRLEN mykey

# 自增
INCR counter

# 自增指定值
INCRBY counter 10

# 自减
DECR counter

# 自减指定值
DECRBY counter 5
```

### 哈希操作（适合存储对象）

```bash
# 设置哈希字段
HSET bazi:user:123 name "张三" gender "male"

# 获取哈希字段
HGET bazi:user:123 name

# 获取所有字段
HGETALL bazi:user:123

# 获取所有字段名
HKEYS bazi:user:123

# 获取所有字段值
HVALS bazi:user:123

# 删除哈希字段
HDEL bazi:user:123 name

# 检查字段是否存在
HEXISTS bazi:user:123 name
```

### 列表操作

```bash
# 从左边推入
LPUSH mylist "item1"

# 从右边推入
RPUSH mylist "item2"

# 从左边弹出
LPOP mylist

# 从右边弹出
RPOP mylist

# 获取列表长度
LLEN mylist

# 获取列表元素
LRANGE mylist 0 -1
```

### 集合操作

```bash
# 添加元素
SADD myset "member1"

# 获取所有成员
SMEMBERS myset

# 检查成员是否存在
SISMEMBER myset "member1"

# 获取集合大小
SCARD myset

# 删除成员
SREM myset "member1"
```

### 有序集合操作

```bash
# 添加成员（带分数）
ZADD myzset 100 "member1"

# 获取成员分数
ZSCORE myzset "member1"

# 获取排名
ZRANK myzset "member1"

# 获取范围
ZRANGE myzset 0 -1 WITHSCORES
```

## 查看 Redis 信息

```bash
# 查看 Redis 服务器信息
INFO

# 查看特定部分信息
INFO server
INFO memory
INFO stats
INFO clients

# 查看配置
CONFIG GET *

# 查看特定配置
CONFIG GET maxmemory

# 查看客户端连接
CLIENT LIST

# 查看慢查询
SLOWLOG GET 10
```

## 性能监控

```bash
# 实时监控命令
MONITOR

# 查看统计信息
INFO stats

# 查看内存使用
INFO memory

# 查看键空间信息
INFO keyspace
```

## 备份和恢复

```bash
# 手动触发 RDB 快照
BGSAVE

# 查看最后保存时间
LASTSAVE

# 查看 RDB 文件位置（在配置文件中）
CONFIG GET dir
```

## 安全设置

```bash
# 设置密码（在 redis.conf 中）
# requirepass your_password

# 或者在运行时设置
CONFIG SET requirepass your_password

# 使用密码连接
AUTH your_password

# 重命名危险命令（在 redis.conf 中）
# rename-command FLUSHDB ""
# rename-command FLUSHALL ""
```

## Python 中使用 Redis

### 安装 Redis 客户端
```bash
pip install redis
```

### 基本使用示例
```python
import redis

# 连接 Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# 或者使用连接池
from redis.connection import ConnectionPool
pool = ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)

# 基本操作
r.set('key', 'value')
value = r.get('key')

# 设置过期时间
r.setex('key', 3600, 'value')

# 哈希操作
r.hset('user:123', 'name', '张三')
name = r.hget('user:123', 'name')

# 批量操作
pipe = r.pipeline()
pipe.set('key1', 'value1')
pipe.set('key2', 'value2')
pipe.execute()
```

## 项目中的使用

本项目使用 Redis 作为 L2 缓存层，配合本地内存缓存（L1）实现多级缓存架构。

### 缓存键命名规范
- 八字计算结果：`bazi:result:{hash}`
- 规则匹配结果：`bazi:rules:{hash}`
- 用户会话：`session:{user_id}`

### 缓存过期策略
- L1（内存）：5分钟
- L2（Redis）：1小时
- 自动清理过期数据

## 故障排查

### Redis 无法启动
```bash
# 检查端口是否被占用
lsof -i :6379

# 查看 Redis 日志
tail -f /usr/local/var/log/redis.log

# 检查配置文件
redis-server /path/to/redis.conf --test-memory 1
```

### 连接被拒绝
```bash
# 检查 Redis 是否运行
redis-cli ping

# 检查防火墙设置
# 检查 bind 配置（redis.conf）
```

### 内存不足
```bash
# 查看内存使用
INFO memory

# 设置最大内存（在 redis.conf 中）
# maxmemory 2gb
# maxmemory-policy allkeys-lru
```

## 参考资源

- [Redis 官方文档](https://redis.io/docs/)
- [Redis 命令参考](https://redis.io/commands/)
- [Redis Python 客户端文档](https://redis-py.readthedocs.io/)












