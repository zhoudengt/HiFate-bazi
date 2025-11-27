# 前端 gRPC-Web 网关说明

## 1. 架构概览

- 浏览器通过 `GrpcGatewayClient` 以 gRPC-Web (binary) 调用 `/api/grpc-web/frontend.gateway.FrontendGateway/Call`
- FastAPI 中的 `server/api/grpc_gateway.py` 解包请求后，直接复用现有 Pydantic/Service 逻辑
- 返回数据与原 REST JSON 完全一致，前端渲染逻辑复用
- 现已完全切换至 gRPC-Web，REST 入口仅作为后端兼容层，不再由前端调用

```
Frontend JS  ──gRPC-Web──>  FastAPI 网关  ──函数调用──>  既有 Service
```

## 2. 前端配置

编辑 `frontend/config.js`：

```js
const GRPC_CONFIG = {
    enabled: true,
    baseURL: 'http://127.0.0.1:8001/api/grpc-web',
    timeout: 60000,
    endpoints: [] // 空数组 = 允许所有已注册端点
};
```

- 调试需要落回 REST 时，可临时将 `enabled` 设为 `false`
- 如需限制调用范围，可填写 `endpoints` 白名单；为空表示自动放行全部接口

## 3. 服务端路由

- 入口：`server/api/grpc_gateway.py`
- 新增函数需在 `SUPPORTED_ENDPOINTS` 中注册，例如：

```python
@_register("/bazi/example")
async def _handle_example(payload: Dict[str, Any]):
    request_model = ExampleRequest(**payload)
    return await example_handler(request_model)
```

## 4. 支持的接口

| 前端 Path | 后端处理函数 |
|-----------|--------------|
| `/bazi/fortune/display` | `get_fortune_display` |
| `/bazi/pan/display` | `get_pan_display` |
| `/bazi/dayun/display` | `get_dayun_display` |
| `/bazi/liunian/display` | `get_liunian_display` |
| `/bazi/liuyue/display` | `get_liuyue_display` |
| `/bazi/wangshuai` | `calculate_wangshuai` |
| `/bazi/yigua/divinate` | `divinate` |
| `/auth/login` | `login` |
| `/payment/create-session` | `create_payment_session` |
| `/payment/verify` | `verify_payment` |

## 5. 调试步骤

1. 启动主服务 `./start_all_services.sh`
2. 浏览器打开 `frontend/fortune.html`（或其他页面）
3. 在 Network 面板可看到 gRPC-Web 请求：
   - URL: `http://127.0.0.1:8001/api/grpc-web/frontend.gateway.FrontendGateway/Call`
   - Header: `Content-Type: application/grpc-web+proto`
4. 若 gRPC 出现异常：
   - 检查 `logs/server.log` 中的 `gRPC-Web handler` 日志
   - 前端不会再自动回退 REST，如需临时降级请修改 `GRPC_CONFIG.enabled`

## 6. 注意事项

- 返回 JSON 与 REST 完全一致，后端可继续复用原有 Service
- gRPC-Web 请求仍需遵守 CORS 规则，默认允许 `*`
- 该实现为轻量化内置网关，后续可替换为 Envoy/NGINX，前端无需改动
- 如需扩展更多接口，请在 `server/api/grpc_gateway.py` 中 `_register`，并（可选）调整 `GRPC_CONFIG.endpoints`

