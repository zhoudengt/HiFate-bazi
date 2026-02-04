# 日元-六十甲子接口：直接后端 + 网关两种 curl 示例

## 1. 直接请求后端（HiFate-bazi 服务，端口 8001）

**最全参数**（7 个标准参数都带上）：

```bash
curl -s -X POST 'http://8.210.52.217:8001/api/v1/bazi/rizhu-liujiazi' \
  -H 'Content-Type: application/json' \
  -d '{
    "solar_date": "1990-01-15",
    "solar_time": "12:00",
    "gender": "male",
    "calendar_type": "solar",
    "location": "北京",
    "latitude": 39.9,
    "longitude": 116.4
  }'
```

**最简参数**（仅必填 3 项）：

```bash
curl -s -X POST 'http://8.210.52.217:8001/api/v1/bazi/rizhu-liujiazi' \
  -H 'Content-Type: application/json' \
  -d '{"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"}'
```

---

## 2. 经 gRPC-Web 网关（前端同域地址）

网关地址：`https://www.yuanqistation.com/destiny/api/grpc-web/frontend.gateway.FrontendGateway/Call`

**网关要求**：必须使用 `Content-Type: application/grpc-web`，**不支持** `application/json`。

- 若用 `Content-Type: application/json` 请求，网关会返回：
  ```json
  {"msg":"不支持的内容类型:application/json","code":3,"requiredContentType":"application/grpc-web"}
  ```
- 因此不能用「普通 curl + JSON body」直接调网关，必须按 gRPC-Web 编码请求体。

网关协议：gRPC-Web，请求体为 **FrontendJsonRequest**（二进制 protobuf）：
- `endpoint`：如 `/destiny/frontend/api/v1/bazi/rizhu-liujiazi` 或 `/bazi/rizhu-liujiazi`
- `payload_json`：业务参数的 **JSON 字符串**，例如 `"{\"solar_date\":\"1990-01-15\",\"solar_time\":\"12:00\",\"gender\":\"male\"}"`

### 2.1 如何调用网关（需 gRPC-Web 客户端）

用 **grpcurl**（需启用 gRPC-Web 或使用 Envoy 等代理）或前端/脚本里的 **gRPC-Web 客户端**，对 `FrontendGateway.Call` 发送：
- Content-Type: `application/grpc-web`
- Body：FrontendJsonRequest 的二进制编码，其中 `payload_json` 为上述 JSON 字符串

**联调建议**：直接用「1. 直接后端」的 curl（`application/json`）验证参数与返回；网关链路用浏览器或前端工程里的 gRPC-Web 调用即可。

---

## 3. 两种方式对照

| 项目         | 直接后端                               | 经网关                                                                 |
|--------------|----------------------------------------|------------------------------------------------------------------------|
| URL          | `http://8.210.52.217:8001/api/v1/bazi/rizhu-liujiazi` | `https://www.yuanqistation.com/destiny/api/grpc-web/frontend.gateway.FrontendGateway/Call` |
| 方法         | POST                                   | POST                                                                   |
| Content-Type | application/json                       | **必须** application/grpc-web（不支持 application/json）              |
| Body         | 直接 JSON 对象（7 个标准参数）          | FrontendJsonRequest 二进制编码：endpoint + payload_json（payload 为 JSON 字符串） |
| 响应         | `{"success":true,"data":{...},"message":null}` | 网关返回 FrontendJsonResponse（含 success、data_json、error 等）      |

---

## 4. 7 个标准参数说明（与 proto / BaziBaseRequest 一致）

| 参数           | 必填 | 说明 |
|----------------|------|------|
| solar_date     | 是   | 阳历/农历日期，YYYY-MM-DD |
| solar_time     | 是   | 出生时间，HH:MM |
| gender         | 是   | male / female |
| calendar_type  | 否   | solar / lunar，默认 solar |
| location       | 否   | 出生地点（时区） |
| latitude       | 否   | 纬度 |
| longitude      | 否   | 经度 |

网关侧若要求带 token，可在 FrontendJsonRequest 中加 `auth_token` 字段（见 proto）。
