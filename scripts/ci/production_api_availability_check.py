#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境接口可用性检查

测试基本接口与流式接口的可用性，输出通过/失败及耗时。
用法:
  python3 scripts/ci/production_api_availability_check.py
  python3 scripts/ci/production_api_availability_check.py --base-url http://localhost:8001
  python3 scripts/ci/production_api_availability_check.py --basic-only
  python3 scripts/ci/production_api_availability_check.py --stream-only
"""

import argparse
import json
import sys
import time
from typing import Any, Dict, List, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# 默认生产环境
DEFAULT_BASE_URL = "http://8.210.52.217:8001"
REQUEST_TIMEOUT = 30
STREAM_READ_TIMEOUT = 45  # 流式接口：收到首包或超时即停


def _req(
    method: str,
    url: str,
    body: Dict[str, Any] = None,
    timeout: int = REQUEST_TIMEOUT,
) -> Tuple[bool, int, str, float]:
    """返回 (成功, 状态码, 响应摘要, 耗时秒)"""
    start = time.time()
    try:
        data = json.dumps(body).encode("utf-8") if body else None
        req = Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            elapsed = time.time() - start
            try:
                j = json.loads(raw)
                summary = f"success={j.get('success')}, keys={list(j.keys())[:6]}"
            except Exception:
                summary = raw[:200] if len(raw) > 200 else raw
            return True, resp.status, summary, elapsed
    except HTTPError as e:
        elapsed = time.time() - start
        try:
            body_read = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            body_read = ""
        return False, e.code, body_read or str(e), elapsed
    except URLError as e:
        elapsed = time.time() - start
        return False, -1, str(e.reason), elapsed
    except Exception as e:
        elapsed = time.time() - start
        return False, -1, str(e), elapsed


def _req_stream(
    base_url: str,
    path: str,
    body: Dict[str, Any],
    timeout: int = STREAM_READ_TIMEOUT,
) -> Tuple[bool, str, float]:
    """POST 流式接口，读到首包或超时即停。返回 (成功, 说明, 耗时)"""
    import urllib.request
    start = time.time()
    url = base_url.rstrip("/") + (path if path.startswith("/") else "/" + path)
    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8", "Accept": "text/event-stream"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text/event-stream" not in content_type and "application/json" in content_type:
                raw = resp.read().decode("utf-8", errors="replace")
                elapsed = time.time() - start
                try:
                    j = json.loads(raw)
                    ok = j.get("success", False)
                    return ok, f"status={resp.status}, success={ok}", elapsed
                except Exception:
                    return False, raw[:200], elapsed
            # SSE：读若干行或到超时
            chunk_count = 0
            line_count = 0
            while (time.time() - start) < timeout:
                line = resp.readline()
                if not line:
                    break
                line_count += 1
                if line.strip().startswith(b"data:"):
                    chunk_count += 1
                    if chunk_count >= 1:
                        break
            elapsed = time.time() - start
            return True, f"status=200, lines={line_count}, data_events={chunk_count}", elapsed
    except HTTPError as e:
        elapsed = time.time() - start
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            err_body = str(e)
        return False, f"HTTP {e.code}: {err_body}", elapsed
    except Exception as e:
        elapsed = time.time() - start
        return False, str(e), elapsed


def run_basic_tests(base_url: str) -> List[Dict[str, Any]]:
    """基本接口（GET/POST 非流式）"""
    base = base_url.rstrip("/")
    api_base = base + "/api/v1"
    results = []

    # 1. 健康检查
    ok, code, summary, elapsed = _req("GET", f"{api_base}/health", timeout=10)
    results.append({
        "name": "GET /api/v1/health",
        "ok": ok and code == 200,
        "code": code,
        "summary": summary,
        "elapsed_ms": round(elapsed * 1000),
    })

    # 2. 首页内容列表
    ok, code, summary, elapsed = _req("GET", f"{api_base}/homepage/contents", timeout=15)
    results.append({
        "name": "GET /api/v1/homepage/contents",
        "ok": ok and code == 200,
        "code": code,
        "summary": summary,
        "elapsed_ms": round(elapsed * 1000),
    })

    # 3. 首页内容详情
    ok, code, summary, elapsed = _req("GET", f"{api_base}/homepage/contents/19", timeout=15)
    results.append({
        "name": "GET /api/v1/homepage/contents/19",
        "ok": ok and code == 200,
        "code": code,
        "summary": summary,
        "elapsed_ms": round(elapsed * 1000),
    })

    # 4. 八字界面
    ok, code, summary, elapsed = _req(
        "POST",
        f"{api_base}/bazi/interface",
        body={"solar_date": "1990-01-01", "solar_time": "12:00", "gender": "male"},
        timeout=REQUEST_TIMEOUT,
    )
    results.append({
        "name": "POST /api/v1/bazi/interface",
        "ok": ok and code == 200,
        "code": code,
        "summary": summary,
        "elapsed_ms": round(elapsed * 1000),
    })

    # 5. 每日运势日历（查询）
    ok, code, summary, elapsed = _req(
        "POST",
        f"{api_base}/daily-fortune-calendar/query",
        body={"date": "2026-02-05"},
        timeout=REQUEST_TIMEOUT,
    )
    results.append({
        "name": "POST /api/v1/daily-fortune-calendar/query",
        "ok": ok and code == 200,
        "code": code,
        "summary": summary,
        "elapsed_ms": round(elapsed * 1000),
    })

    # 6. 万年历
    ok, code, summary, elapsed = _req(
        "POST",
        f"{api_base}/calendar/query",
        body={"date": "2026-02-05"},
        timeout=15,
    )
    results.append({
        "name": "POST /api/v1/calendar/query",
        "ok": ok and code == 200,
        "code": code,
        "summary": summary,
        "elapsed_ms": round(elapsed * 1000),
    })

    # 7. 热更新状态
    ok, code, summary, elapsed = _req("GET", f"{api_base}/hot-reload/status", timeout=10)
    results.append({
        "name": "GET /api/v1/hot-reload/status",
        "ok": ok and code == 200,
        "code": code,
        "summary": summary,
        "elapsed_ms": round(elapsed * 1000),
    })

    return results


def run_stream_tests(base_url: str) -> List[Dict[str, Any]]:
    """流式接口（SSE）"""
    base = base_url.rstrip("/")
    api_base = base + "/api/v1"
    results = []

    # 1. 每日运势流式
    ok, summary, elapsed = _req_stream(
        base_url,
        "/api/v1/daily-fortune-calendar/stream",
        body={"date": "2026-02-05"},
        timeout=STREAM_READ_TIMEOUT,
    )
    results.append({
        "name": "POST /api/v1/daily-fortune-calendar/stream",
        "ok": ok,
        "code": 200 if ok else -1,
        "summary": summary,
        "elapsed_ms": round(elapsed * 1000),
    })

    # 2. 五行占比流式
    ok, summary, elapsed = _req_stream(
        base_url,
        "/api/v1/bazi/wuxing-proportion/stream",
        body={"solar_date": "1990-01-01", "solar_time": "12:00", "gender": "male"},
        timeout=STREAM_READ_TIMEOUT,
    )
    results.append({
        "name": "POST /api/v1/bazi/wuxing-proportion/stream",
        "ok": ok,
        "code": 200 if ok else -1,
        "summary": summary,
        "elapsed_ms": round(elapsed * 1000),
    })

    # 3. 喜神忌神流式
    ok, summary, elapsed = _req_stream(
        base_url,
        "/api/v1/bazi/xishen-jishen/stream",
        body={"solar_date": "1990-01-01", "solar_time": "12:00", "gender": "male"},
        timeout=STREAM_READ_TIMEOUT,
    )
    results.append({
        "name": "POST /api/v1/bazi/xishen-jishen/stream",
        "ok": ok,
        "code": 200 if ok else -1,
        "summary": summary,
        "elapsed_ms": round(elapsed * 1000),
    })

    # 4. 诊断流式端点（轻量）
    ok, code, summary, elapsed = _req("GET", f"{api_base}/diagnose-stream", timeout=10)
    results.append({
        "name": "GET /api/v1/diagnose-stream",
        "ok": ok and code == 200,
        "code": code,
        "summary": summary,
        "elapsed_ms": round(elapsed * 1000),
    })

    return results


def main():
    parser = argparse.ArgumentParser(description="生产环境基本接口与流式接口可用性检查")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="服务根地址",
    )
    parser.add_argument("--basic-only", action="store_true", help="仅测基本接口")
    parser.add_argument("--stream-only", action="store_true", help="仅测流式接口")
    parser.add_argument("-q", "--quiet", action="store_true", help="仅输出通过/失败汇总")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    all_results: List[Dict[str, Any]] = []

    if not args.stream_only:
        all_results.extend(run_basic_tests(base_url))
    if not args.basic_only:
        all_results.extend(run_stream_tests(base_url))

    passed = sum(1 for r in all_results if r["ok"])
    total = len(all_results)

    if not args.quiet:
        print(f"Base URL: {base_url}\n")
        for r in all_results:
            status = "OK" if r["ok"] else "FAIL"
            code = r.get("code", "-")
            ms = r.get("elapsed_ms", 0)
            print(f"  [{status}] {r['name']}  (HTTP {code}, {ms}ms)")
            if not r["ok"] and r.get("summary"):
                print(f"         {str(r['summary'])[:200]}")
        print()

    print(f"结果: {passed}/{total} 通过")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
