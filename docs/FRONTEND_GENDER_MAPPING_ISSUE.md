# 前端性别映射缺陷 - 需前端团队排查

## 问题描述

排盘与总评接口对同一档案使用不同的 `gender` 参数，导致大运流年计算结果不一致。

## 证据

### 糖糖（sex: 0，显示 ♂ 男）

- **浏览器控制台**：请求参数 `gender: female`
- **后端日志**：总评、排盘接收 `gender=male`；旺衰接收 `gender=female`

### xx（显示 ♀ 女）

- **后端日志**：排盘/BaziInterface 接收 `gender=male`；旺衰接收 `gender=female`

## 影响

- 大运顺逆方向由性别决定（男逆女顺）
- 性别错误 → 大运序列完全错误 → 关键年份归属错误 → LLM 输出错误

## 排查方向

1. **sex 到 gender 的映射**：`sex: 0` / `sex: 1` 与 `male` / `female` 的对应关系是否一致
2. **不同 API 路径**：
   - gRPC-Web（排盘）：`/destiny/api/grpc-web/frontend.gateway.FrontendGateway/Call`
   - SSE Forward（总评等流式）：`/destiny/frontend/api/v1/sse/forward`
3. 确保所有接口使用同一套 sex → gender 映射逻辑

## 后端状态

后端无性别转换逻辑，直接透传前端 payload。问题位于前端请求构造层。
