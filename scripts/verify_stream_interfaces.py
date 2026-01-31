#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证所有改过的流式接口（BaziDataOrchestrator + FortuneContextService 编排层）

覆盖接口：
- marriage-analysis/stream
- health/stream
- children-study/stream
- career-wealth/stream
- smart-analyze-stream (FortuneContextService 编排层)

用法：
  python scripts/verify_stream_interfaces.py [--base-url URL] [--timeout N] [--quick]
  python scripts/verify_stream_interfaces.py --code-only   # 仅验证代码结构，不发起 HTTP
  # 本地服务未启动时，可使用远程: --base-url http://8.210.52.217:8001
"""

import sys
import os
import json
import argparse
from typing import Dict, Any, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

TEST_SOLAR = {"solar_date": "1990-06-15", "solar_time": "14:30", "gender": "male"}
TEST_SOLAR_FEMALE = {"solar_date": "1992-03-20", "solar_time": "09:00", "gender": "female"}


def _parse_sse_chunks(iter_lines, max_events: int = 20):
    events = []
    for line in iter_lines:
        if not line:
            continue
        try:
            line_str = line.decode("utf-8") if isinstance(line, bytes) else str(line)
        except Exception:
            continue
        if line_str.startswith("data: "):
            data_str = line_str[6:].strip()
            if data_str in ("[DONE]", ""):
                continue
            try:
                data = json.loads(data_str)
                events.append(data)
                if len(events) >= max_events:
                    break
            except json.JSONDecodeError:
                pass
    return events


def test_post_stream(base_url: str, path: str, body: Dict[str, Any], timeout: int) -> Tuple[bool, str]:
    import requests
    url = f"{base_url}{path}"
    try:
        r = requests.post(url, json=body, stream=True, timeout=timeout)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        events = _parse_sse_chunks(r.iter_lines(), max_events=15)
        if not events:
            return False, "未收到任何 SSE 事件"
        types = {e.get("type") for e in events if isinstance(e, dict)}
        if "error" in types and len(types) == 1:
            return False, events[0].get("message", "未知错误")
        return True, f"OK ({len(events)} 事件, 类型: {types})"
    except Exception as e:
        err_msg = str(e)
        if "Timeout" in type(e).__name__:
            return False, "请求超时"
        if "Connection" in err_msg or "ConnectionError" in type(e).__name__:
            return False, "连接失败（服务未启动?）"
        return False, err_msg


def test_smart_analyze_stream(base_url: str, timeout: int) -> Tuple[bool, str]:
    import requests
    url = f"{base_url}/api/v1/smart-fortune/smart-analyze-stream"
    params = {"year": 1990, "month": 6, "day": 15, "hour": 14, "gender": "male",
              "user_id": "test_stream_user", "category": "事业财富"}
    try:
        r = requests.get(url, params=params, stream=True, timeout=timeout)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        events = _parse_sse_chunks(r.iter_lines(), max_events=25)
        if not events:
            return False, "未收到任何 SSE 事件"
        types = {e.get("type") for e in events if isinstance(e, dict)}
        if "error" in types and len(types) <= 2:
            msg = next((e.get("message", "") for e in events if e.get("type") == "error"), "未知")
            return False, f"error: {msg}"
        return True, f"OK ({len(events)} 事件, 类型: {types})"
    except Exception as e:
        err_msg = str(e)
        if "Timeout" in type(e).__name__:
            return False, "请求超时"
        if "Connection" in err_msg or "ConnectionError" in type(e).__name__:
            return False, "连接失败"
        return False, err_msg


def check_code_structure() -> Tuple[bool, str]:
    """验证编排层代码结构（无需启动服务，轻量级检查）"""
    try:
        from server.utils.analysis_stream_helpers import get_modules_config
        for scene in ('marriage', 'health', 'children', 'career_wealth'):
            cfg = get_modules_config(scene)
            if not isinstance(cfg, dict) or 'bazi' not in cfg:
                return False, f"get_modules_config('{scene}') 结构异常"
        # 静态检查 FortuneContextService 新参数（避免导入 grpc 等重依赖）
        fc_path = os.path.join(project_root, "server", "orchestrators", "fortune_context_service.py")
        with open(fc_path, "r", encoding="utf-8") as f:
            fc_content = f.read()
        if "detail_result" not in fc_content or "wangshuai_result" not in fc_content:
            return False, "FortuneContextService 缺少 detail_result/wangshuai_result 参数"
        orch_path = os.path.join(project_root, "server", "orchestrators", "bazi_data_orchestrator.py")
        if "fortune_context" not in open(orch_path, encoding="utf-8").read():
            return False, "BaziDataOrchestrator 未注册 fortune_context 模块"
        return True, "OK (编排层代码结构正确)"
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--quick", action="store_true", help="只测前 2 个接口")
    parser.add_argument("--code-only", action="store_true", help="仅验证代码结构，不发起 HTTP 请求")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    # 1. 代码结构验证（始终执行）
    print("=" * 60)
    print("1. 代码结构验证")
    print("=" * 60)
    ok, msg = check_code_structure()
    print(f"  [{'PASS' if ok else 'FAIL'}] 编排层: {msg}")
    if not ok:
        print("\n❌ 代码结构验证失败，请检查上述错误")
        return 1
    if args.code_only:
        print("\n✅ 代码结构验证通过 (--code-only)")
        return 0
    print()

    timeout = args.timeout
    quick = args.quick

    tests = [
        ("婚姻分析流式", "/api/v1/bazi/marriage-analysis/stream", {**TEST_SOLAR}),
        ("健康分析流式", "/api/v1/health/stream", {**TEST_SOLAR}),
        ("子女学习流式", "/api/v1/children-study/stream", {**TEST_SOLAR_FEMALE}),
        ("事业财富流式", "/api/v1/career-wealth/stream", {**TEST_SOLAR}),
    ]
    if quick:
        tests = tests[:2]

    print("=" * 60)
    print("2. 流式接口 HTTP 验证（需服务已启动）")
    print("=" * 60)
    print(f"Base: {base} | Timeout: {timeout}s")
    print()

    passed = failed = 0
    for name, path, body in tests:
        ok, msg = test_post_stream(base, path, body, timeout)
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")
        passed += 1 if ok else 0
        failed += 0 if ok else 1

    ok, msg = test_smart_analyze_stream(base, timeout)
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] 智能运势流式(smart-analyze-stream): {msg}")
    passed += 1 if ok else 0
    failed += 0 if ok else 1

    print()
    print("=" * 60)
    print(f"结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
