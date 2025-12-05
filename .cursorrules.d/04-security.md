# 安全规范 【必须遵守】

## 🔴 安全开发原则

> **安全是最高优先级，所有代码必须遵循安全最佳实践。**

| 原则 | 要求 | 说明 |
|------|------|------|
| **最小权限** | ✅ 必须 | 只授予必要的权限，禁止过度授权 |
| **输入验证** | ✅ 必须 | 所有用户输入必须验证和过滤 |
| **输出编码** | ✅ 必须 | 所有输出必须正确编码，防止 XSS |
| **敏感数据保护** | ✅ 必须 | 密码、密钥、Token 等必须加密存储 |
| **错误处理** | ✅ 必须 | 不暴露系统内部信息给用户 |
| **依赖安全** | ✅ 必须 | 定期更新依赖，修复已知漏洞 |

## 🛡️ 常见安全漏洞防护

### 1. SQL 注入防护 【高危】

**禁止**：
```python
# ❌ 错误：直接拼接 SQL
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)
```

**正确做法**：
```python
# ✅ 正确：使用参数化查询
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### 2. XSS（跨站脚本攻击）防护 【高危】

**禁止**：
```python
# ❌ 错误：直接输出用户输入
return f"<div>{user_input}</div>"
```

**正确做法**：
```python
# ✅ 正确：使用模板引擎自动转义
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")
return templates.TemplateResponse("page.html", {
    "request": request,
    "user_input": user_input  # 自动转义
})
```

### 3. CSRF（跨站请求伪造）防护 【高危】

**后端防护**：
```python
# ✅ 正确：使用 CSRF Token
from fastapi_csrf_protect import CsrfProtect

@router.post("/api/v1/sensitive-action")
async def sensitive_action(
    request: Request,
    csrf_protect: CsrfProtect = Depends()
):
    await csrf_protect.validate_csrf(request)
    # 处理请求
```

### 4. 敏感信息泄露防护 【高危】

**禁止**：
```python
# ❌ 错误：在错误信息中暴露系统信息
except Exception as e:
    return {"error": f"Database error: {str(e)}"}  # 暴露数据库结构
```

**正确做法**：
```python
# ✅ 正确：通用错误信息
except Exception as e:
    logger.error(f"Database error: {e}", exc_info=True)  # 记录详细日志
    return {"error": "操作失败，请稍后重试"}  # 用户友好的错误信息
```

### 5. 身份认证与授权防护 【高危】

**密码安全**：
```python
# ✅ 正确：使用 bcrypt 加密密码
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')
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
```

### 6. 文件上传安全防护 【高危】

**正确做法**：
```python
# ✅ 正确：验证文件类型和大小
from fastapi import UploadFile, File
import magic

ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件过大")
    
    mime_type = magic.from_buffer(content, mime=True)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
```

### 7. API 限流防护 【中危】

```python
# ✅ 正确：使用 slowapi 限流
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/api/v1/login")
@limiter.limit("5/minute")  # 每分钟最多 5 次
async def login(request: Request):
    # 登录逻辑
```

### 8-10. 其他安全防护

详细内容请参考原始 `.cursorrules` 文件：
- 依赖安全更新（行 1239-1260）
- 日志安全（行 1264-1289）
- 配置安全（行 1293-1330）

## 🔍 安全代码审查清单

每次提交代码前，必须检查：

### 输入验证
- [ ] 所有用户输入都经过验证
- [ ] 验证数据类型、长度、格式
- [ ] 禁止直接使用用户输入构建 SQL/命令

### 输出编码
- [ ] 所有输出都正确编码
- [ ] 防止 XSS 攻击

### 身份认证
- [ ] 密码加密存储
- [ ] Token 设置过期时间
- [ ] 敏感操作验证用户身份

### 权限控制
- [ ] 每个操作检查用户权限
- [ ] 防止越权访问
- [ ] 使用最小权限原则

### 错误处理
- [ ] 不暴露系统内部信息
- [ ] 记录详细错误日志（服务器端）
- [ ] 返回用户友好的错误信息

### 依赖安全
- [ ] 定期检查依赖漏洞
- [ ] 及时更新有安全问题的依赖
- [ ] 使用固定版本号

## 🚨 安全事件响应

### 发现安全漏洞时

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

## 📚 安全资源

- **OWASP Top 10**：https://owasp.org/www-project-top-ten/
- **Python 安全最佳实践**：https://python.readthedocs.io/en/latest/library/security.html
- **FastAPI 安全文档**：https://fastapi.tiangolo.com/tutorial/security/

**安全开发核心原则**：
- 🔒 **默认拒绝**：默认情况下拒绝所有访问，只允许明确授权的操作
- 🔍 **深度防御**：多层安全防护，不依赖单一安全措施
- 🛡️ **最小权限**：只授予必要的权限，禁止过度授权
- 📝 **安全审计**：定期审查代码和配置，及时发现安全问题
- 🚨 **快速响应**：发现安全问题立即处理，不拖延

