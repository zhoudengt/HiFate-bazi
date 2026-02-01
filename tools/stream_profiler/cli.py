# -*- coding: utf-8 -*-
"""
CLI for stream profiler: argparse, run profiler for one or all endpoints, output report.
"""

import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests

from .endpoints import STREAM_ENDPOINTS, get_endpoint_by_name, get_endpoint_by_path, StreamEndpoint
from .profiler import profile_one, ProfileResult
from .report import to_markdown, to_json

# 喜神忌神测试接口路径（用于拉取优化前后入参体量）
XISHEN_TEST_PATH = "/api/v1/bazi/xishen-jishen/test"


def _xishen_format_len(data: Dict[str, Any]) -> int:
    """根据喜神忌神 input_data 计算描述文长度（与 server _format_xishen_jishen_for_llm 一致，便于未热更新时也能出数）。"""
    def _names(items: Any) -> str:
        if not items:
            return "无"
        names = []
        for x in items:
            if isinstance(x, dict):
                names.append(x.get("name", str(x)))
            else:
                names.append(str(x))
        return "、".join(names) if names else "无"

    lines = []
    lines.append(f"【喜神】{_names(data.get('xi_shen_elements', []))}")
    lines.append(f"【忌神】{_names(data.get('ji_shen_elements', []))}")
    w = data.get("wangshuai", "")
    s = data.get("total_score", 0)
    lines.append(f"【旺衰】{w}({s}分)")
    lines.append(f"【十神命格】{_names(data.get('shishen_mingge', []))}")
    pillars = data.get("bazi_pillars", {})
    if pillars:
        labels = {"year": "年", "month": "月", "day": "日", "hour": "时"}
        parts = []
        for k in ["year", "month", "day", "hour"]:
            p = pillars.get(k, {})
            stem = p.get("stem", "") if isinstance(p, dict) else ""
            branch = p.get("branch", "") if isinstance(p, dict) else ""
            if stem or branch:
                parts.append(f"{labels.get(k, k)}{stem}{branch}")
        if parts:
            lines.append(f"【四柱】{' '.join(parts)}")
    if data.get("day_stem"):
        lines.append(f"【日主】{data['day_stem']}")
    ec = data.get("element_counts", {})
    if ec and isinstance(ec, dict):
        parts = [f"{e}{c}" for e, c in ec.items() if c]
        if parts:
            lines.append(f"【五行个数】{' '.join(parts)}")
    tg = data.get("ten_gods", {})
    if tg and isinstance(tg, dict):
        labels = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
        parts = []
        for k in ["year", "month", "day", "hour"]:
            t = tg.get(k, {})
            main = t.get("main_star", "") if isinstance(t, dict) else ""
            if main:
                parts.append(f"{labels.get(k, k)}{main}")
        if parts:
            lines.append(f"【十神】{'、'.join(parts)}")
    return len("\n".join(lines))


def _fetch_xishen_input_sizes(base_url: str, payload: Dict[str, Any]) -> Optional[Dict[str, int]]:
    """拉取喜神忌神 LLM 入参体量：优化前(完整JSON) / 优化后(描述文)。返回 {"old_chars": N, "new_chars": M, "pct_reduced": Z} 或 None。"""
    url = base_url.rstrip("/") + XISHEN_TEST_PATH
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data.get("success"):
            return None
        old_chars = data.get("formatted_data_length", 0)
        new_chars = data.get("formatted_data_length_optimized")
        if new_chars is None:
            new_chars = _xishen_format_len(data.get("input_data") or {})
        pct = round((1 - new_chars / old_chars) * 100) if old_chars else None
        return {"old_chars": old_chars, "new_chars": new_chars, "pct_reduced": pct}
    except Exception:
        return None


def _get_payload_or_params(ep: StreamEndpoint) -> Optional[dict]:
    if ep.payload_builder:
        return ep.payload_builder()
    if ep.params_builder:
        return ep.params_builder()
    return None


def run_profiler(
    base_url: str,
    endpoint_filter: Optional[str],
    runs: int,
    timeout: int,
    skip_image: bool = True,
) -> List[Tuple[str, str, Any]]:
    """
    Run profiler for endpoints matching endpoint_filter (or all non-skip if None).
    If runs > 1, aggregate results per endpoint.

    Returns:
        List of (endpoint_name, path, ProfileResult or list of ProfileResult).
    """
    if endpoint_filter:
        ep = get_endpoint_by_path(endpoint_filter) or get_endpoint_by_name(endpoint_filter)
        if not ep:
            return []
        endpoints = [ep]
    else:
        endpoints = [
            ep for ep in STREAM_ENDPOINTS
            if not (skip_image and ep.skip_reason)
        ]

    rows: List[Tuple[str, str, Any]] = []
    for ep in endpoints:
        payload = _get_payload_or_params(ep)
        results: List[ProfileResult] = []
        for _ in range(runs):
            res = profile_one(
                base_url=base_url,
                path=ep.path,
                method=ep.method,
                payload_or_params=payload,
                timeout=timeout,
            )
            results.append(res)
        if runs == 1:
            rows.append((ep.name, ep.path, results[0]))
        else:
            rows.append((ep.name, ep.path, results))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="流式接口各环节耗时与效率测试（纯客户端，与 server 解耦）"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8001",
        help="API 基准 URL（默认: http://localhost:8001）",
    )
    parser.add_argument(
        "--endpoint",
        default=None,
        help="只测指定接口：传 path 或 name，如 /api/v1/bazi/wuxing-proportion/stream 或 五行占比",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="每个接口测试次数，多次时取平均（默认: 1）",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="单次请求超时秒数（默认: 120）",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="报告输出文件路径（默认: 打印到 stdout）",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式（默认: markdown）",
    )
    parser.add_argument(
        "--with-image",
        action="store_true",
        help="包含需要上传图片的接口（默认跳过）",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    rows = run_profiler(
        base_url=base_url,
        endpoint_filter=args.endpoint,
        runs=args.runs,
        timeout=args.timeout,
        skip_image=not args.with_image,
    )

    if not rows:
        if args.endpoint:
            print(f"未找到接口: {args.endpoint}", file=sys.stderr)
        else:
            print("没有可测的流式接口（可用 --with-image 包含需图片的接口）", file=sys.stderr)
        return 1

    # 若本次测了喜神忌神，拉取一次入参体量（优化前/后）供报告展示
    xishen_input_sizes = None
    for name, _path, _res in rows:
        if name == "喜神忌神":
            payload = _get_payload_or_params(get_endpoint_by_name("喜神忌神"))
            if payload:
                xishen_input_sizes = _fetch_xishen_input_sizes(base_url, payload)
            break

    if args.format == "markdown":
        runs_info = f"每个接口 {args.runs} 次" if args.runs > 1 else None
        report = to_markdown(rows, base_url, runs_info=runs_info, xishen_input_sizes=xishen_input_sizes)
    else:
        report = to_json(rows, base_url, runs=args.runs, xishen_input_sizes=xishen_input_sizes)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已写入: {args.output}", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
