
> 本文档从 `.cursorrules` 提取，包含安全规范的完整内容。详见 `.cursorrules` 核心规范章节。

## 🔐 安全规范 【必须遵守】

### 🔴 安全开发原则

> **安全是最高优先级，所有代码必须遵循安全最佳实践。**

| 原则 | 要求 | 说明 |
|------|------|------|
| **最小权限** | ✅ 必须 | 只授予必要的权限，禁止过度授权 |
| **输入验证** | ✅ 必须 | 所有用户输入必须验证和过滤 |
| **输出编码** | ✅ 必须 | 所有输出必须正确编码，防止 XSS |
| **敏感数据保护** | ✅ 必须 | 密码、密钥、Token 等必须加密存储 |
| **错误处理** | ✅ 必须 | 不暴露系统内部信息给用户 |
| **依赖安全** | ✅ 必须 | 定期更新依赖，修复已知漏洞 |

---

### 🛡️ 常见安全漏洞防护

#### 1. SQL 注入防护 【高危】

**禁止**：
```python
# ❌ 错误：直接拼接 SQL
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)

# ❌ 错误：使用 % 格式化
cursor.execute("SELECT * FROM users WHERE name = '%s'" % user_name)
```

**正确做法**：
```python
# ✅ 正确：使用参数化查询
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
cursor.execute("SELECT * FROM users WHERE name = %s AND age = %s", (user_name, age))

# ✅ 正确：使用 ORM（SQLAlchemy）
from server.config.mysql_config import get_mysql_connection
with get_mysql_connection() as conn:
    result = conn.execute(
        text("SELECT * FROM users WHERE id = :id"),
        {"id": user_id}
    )
```

**检查清单**：
- [ ] 所有 SQL 查询使用参数化
- [ ] 禁止字符串拼接构建 SQL
- [ ] 使用 ORM 或参数化查询接口

---

#### 2. XSS（跨站脚本攻击）防护 【高危】

**禁止**：
```python
# ❌ 错误：直接输出用户输入
return f"<div>{user_input}</div>"

# ❌ 错误：在 JavaScript 中直接嵌入
return f"<script>var data = '{user_data}';</script>"
```

**正确做法**：
```python
# ✅ 正确：使用模板引擎自动转义（FastAPI + Jinja2）
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
return templates.TemplateResponse("page.html", {
    "request": request,
    "user_input": user_input  # 自动转义
})

# ✅ 正确：手动转义（如需要）
import html
safe_output = html.escape(user_input)

# ✅ 正确：JSON 输出（自动转义）
from fastapi.responses import JSONResponse
return JSONResponse({"data": user_input})  # 自动转义
```

**前端防护**：
```javascript
// ✅ 正确：使用 textContent 而不是 innerHTML
element.textContent = userInput;

// ✅ 正确：使用 DOMPurify 清理 HTML
import DOMPurify from 'dompurify';
element.innerHTML = DOMPurify.sanitize(userInput);
```

**检查清单**：
- [ ] 所有用户输入在输出前转义
- [ ] 使用模板引擎自动转义
- [ ] 前端使用安全的 DOM 操作方式

---

#### 3. CSRF（跨站请求伪造）防护 【高危】

**后端防护**：
```python
# ✅ 正确：使用 CSRF Token（FastAPI）
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

@router.post("/api/v1/sensitive-action")
async def sensitive_action(
    request: Request,
    csrf_protect: CsrfProtect = Depends()
):
    await csrf_protect.validate_csrf(request)
    # 处理请求
    ...

# ✅ 正确：检查 Referer 头
referer = request.headers.get("referer")
if not referer or not referer.startswith("https://yourdomain.com"):
    raise HTTPException(status_code=403, detail="Invalid referer")
```

**前端防护**：
```javascript
// ✅ 正确：从后端获取 CSRF Token
const csrfToken = await fetch('/api/csrf-token').then(r => r.json());

// ✅ 正确：在请求头中携带 Token
fetch('/api/v1/sensitive-action', {
    method: 'POST',
    headers: {
        'X-CSRF-Token': csrfToken,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
});
```

**检查清单**：
- [ ] 所有修改操作需要 CSRF Token
- [ ] 验证 Referer 头（可选，作为额外保护）
- [ ] 使用 SameSite Cookie 属性

---

#### 4. 敏感信息泄露防护 【高危】

**禁止**：
```python
# ❌ 错误：在错误信息中暴露系统信息
except Exception as e:
    return {"error": f"Database error: {str(e)}"}  # 暴露数据库结构

# ❌ 错误：在日志中记录敏感信息
logger.info(f"User login: {username}, password: {password}")

# ❌ 错误：在响应中返回敏感字段
return {"user": {"id": 1, "password": "hashed_password", "api_key": "xxx"}}
```

**正确做法**：
```python
# ✅ 正确：通用错误信息
except Exception as e:
    logger.error(f"Database error: {e}", exc_info=True)  # 记录详细日志
    return {"error": "操作失败，请稍后重试"}  # 用户友好的错误信息

# ✅ 正确：不记录敏感信息
logger.info(f"User login: {username}")  # 不记录密码

# ✅ 正确：过滤敏感字段
def sanitize_user_data(user):
    return {
        "id": user.id,
        "username": user.username,
        # 不返回 password, api_key 等敏感字段
    }
```

**环境变量保护**：
```python
# ✅ 正确：使用环境变量，不提交到代码库
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")  # 从 .env 读取
DATABASE_PASSWORD = os.getenv("MYSQL_PASSWORD")

# ❌ 错误：硬编码密钥
SECRET_KEY = "my-secret-key-12345"  # 禁止！
```

**检查清单**：
- [ ] 错误信息不暴露系统内部信息
- [ ] 日志不记录密码、Token 等敏感信息
- [ ] API 响应不返回敏感字段
- [ ] 所有密钥使用环境变量，不提交到代码库

---

#### 5. 身份认证与授权防护 【高危】

**密码安全**：
```python
# ✅ 正确：使用 bcrypt 加密密码
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# ❌ 错误：明文存储密码
user.password = password  # 禁止！
```

**Token 安全**：
```python
# ✅ 正确：使用 JWT，设置过期时间
import jwt
from datetime import datetime, timedelta

def generate_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24),  # 24小时过期
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# ✅ 正确：验证 Token
def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的 Token")
```

**权限检查**：
```python
# ✅ 正确：每个操作都检查权限
@router.post("/api/v1/admin/delete-user")
async def delete_user(user_id: int, current_user: User = Depends(get_current_user)):
    # 检查是否为管理员
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 执行删除操作
    ...
```

**检查清单**：
- [ ] 密码必须加密存储（bcrypt/argon2）
- [ ] Token 设置合理的过期时间
- [ ] 所有敏感操作验证用户身份
- [ ] 所有操作检查用户权限

---

#### 6. 文件上传安全防护 【高危】

**禁止**：
```python
# ❌ 错误：不验证文件类型
@router.post("/upload")
async def upload(file: UploadFile):
    content = await file.read()
    with open(f"uploads/{file.filename}", "wb") as f:
        f.write(content)  # 危险！可能上传恶意文件
```

**正确做法**：
```python
# ✅ 正确：验证文件类型和大小
from fastapi import UploadFile, File
import magic  # 或使用 python-magic

ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    # 1. 检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件过大")
    
    # 2. 验证文件类型（使用 MIME 类型，不依赖扩展名）
    mime_type = magic.from_buffer(content, mime=True)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    
    # 3. 生成安全的文件名（防止路径遍历）
    import uuid
    import os
    safe_filename = f"{uuid.uuid4()}.{mime_type.split('/')[1]}"
    safe_path = os.path.join("uploads", safe_filename)
    
    # 4. 保存文件
    with open(safe_path, "wb") as f:
        f.write(content)
    
    return {"filename": safe_filename}
```

**检查清单**：
- [ ] 验证文件 MIME 类型（不依赖扩展名）
- [ ] 限制文件大小
- [ ] 生成安全的文件名（防止路径遍历）
- [ ] 文件存储在隔离目录，不在 Web 根目录

---

#### 7. API 限流防护 【中危】

**防止暴力破解和 DDoS**：
```python
# ✅ 正确：使用 slowapi 限流
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

@router.post("/api/v1/login")
@limiter.limit("5/minute")  # 每分钟最多 5 次
async def login(request: Request):
    # 登录逻辑
    ...

@router.post("/api/v1/bazi/calculate")
@limiter.limit("100/hour")  # 每小时最多 100 次
async def calculate_bazi(request: Request):
    # 计算逻辑
    ...
```

**检查清单**：
- [ ] 登录接口设置严格限流（如 5次/分钟）
- [ ] 计算接口设置合理限流（如 100次/小时）
- [ ] 使用 IP 地址作为限流键

---

#### 8. 依赖安全更新 【中危】

**定期检查依赖漏洞**：
```bash
# ✅ 使用安全扫描工具
pip install safety
safety check

# ✅ 使用 pip-audit（Python 官方推荐）
pip install pip-audit
pip-audit

# ✅ 定期更新依赖
pip list --outdated
pip install --upgrade package_name
```

**检查清单**：
- [ ] 每月检查一次依赖漏洞
- [ ] 及时更新有安全漏洞的依赖
- [ ] 使用 `requirements.txt` 固定版本号
- [ ] 记录依赖更新日志

---

#### 9. 日志安全 【中危】

**禁止记录敏感信息**：
```python
# ❌ 错误：记录敏感信息
logger.info(f"User {username} login with password {password}")
logger.debug(f"API Key: {api_key}")

# ✅ 正确：不记录敏感信息
logger.info(f"User {username} login successful")
logger.debug(f"API Key: {api_key[:10]}...")  # 只记录部分
```

**日志访问控制**：
```python
# ✅ 正确：日志文件权限控制
# 日志文件只允许应用用户访问
chmod 600 logs/app.log
chown app:app logs/app.log
```

**检查清单**：
- [ ] 日志不包含密码、Token、API Key
- [ ] 日志文件权限设置为 600
- [ ] 定期清理旧日志
- [ ] 生产环境日志级别设置为 WARNING 或 ERROR

---

#### 10. 配置安全 【中危】

**环境变量管理**：
```python
# ✅ 正确：使用 .env 文件（不提交到代码库）
# .env 文件添加到 .gitignore
# .env.example 作为模板提交

# .env.example
SECRET_KEY=your-secret-key-here
MYSQL_PASSWORD=your-password-here
REDIS_PASSWORD=your-redis-password

# .env（不提交）
SECRET_KEY=actual-secret-key-12345
MYSQL_PASSWORD=actual-password-12345
```

**配置文件安全**：
```python
# ✅ 正确：敏感配置从环境变量读取
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY 环境变量未设置")

# ❌ 错误：硬编码配置
SECRET_KEY = "hardcoded-secret-key"  # 禁止！
```

**检查清单**：
- [ ] `.env` 文件添加到 `.gitignore`
- [ ] 提供 `.env.example` 作为模板
- [ ] 所有敏感配置从环境变量读取
- [ ] 生产环境使用强密码和密钥

---

### 🔍 安全代码审查清单

每次提交代码前，必须检查：

#### 输入验证
- [ ] 所有用户输入都经过验证
- [ ] 验证数据类型、长度、格式
- [ ] 禁止直接使用用户输入构建 SQL/命令

#### 输出编码
- [ ] 所有输出都正确编码
- [ ] 防止 XSS 攻击
- [ ] JSON 输出使用 `ensure_ascii=False` 时确保安全

#### 身份认证
- [ ] 密码加密存储
- [ ] Token 设置过期时间
- [ ] 敏感操作验证用户身份

#### 权限控制
- [ ] 每个操作检查用户权限
- [ ] 防止越权访问
- [ ] 使用最小权限原则

#### 错误处理
- [ ] 不暴露系统内部信息
- [ ] 记录详细错误日志（服务器端）
- [ ] 返回用户友好的错误信息

#### 依赖安全
- [ ] 定期检查依赖漏洞
- [ ] 及时更新有安全问题的依赖
- [ ] 使用固定版本号

---

### 🚨 安全事件响应

#### 发现安全漏洞时

1. **立即处理**
   - 评估漏洞严重程度（高危/中危/低危）
   - 立即修复或临时禁用相关功能
   - 通知相关人员

2. **修复流程**
   - 创建修复分支：`git checkout -b security/fix-xxx-vulnerability`
   - 修复漏洞并编写测试
   - 代码审查（重点关注安全性）
   - 合并到主分支并部署

3. **记录与复盘**
   - 记录漏洞详情和修复方案
   - 更新安全规范，防止类似问题
   - 检查是否有其他类似问题

---

### 📚 安全资源

- **OWASP Top 10**：https://owasp.org/www-project-top-ten/
- **Python 安全最佳实践**：https://python.readthedocs.io/en/latest/library/security.html
- **FastAPI 安全文档**：https://fastapi.tiangolo.com/tutorial/security/

---

**安全开发核心原则**：
- 🔒 **默认拒绝**：默认情况下拒绝所有访问，只允许明确授权的操作
- 🔍 **深度防御**：多层安全防护，不依赖单一安全措施
- 🛡️ **最小权限**：只授予必要的权限，禁止过度授权
- 📝 **安全审计**：定期审查代码和配置，及时发现安全问题
- 🚨 **快速响应**：发现安全问题立即处理，不拖延

