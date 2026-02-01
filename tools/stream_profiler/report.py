# -*- coding: utf-8 -*-
"""
Report generation: Markdown table or JSON from profile results.
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple


def _fmt(v: Optional[float]) -> str:
    if v is None:
        return "-"
    return f"{v:.3f}"


def to_markdown(
    rows: List[Tuple[str, str, Any]],
    base_url: str,
    runs_info: Optional[str] = None,
    xishen_input_sizes: Optional[Dict[str, int]] = None,
) -> str:
    """
    Build a Markdown report from profile result rows.

    Args:
        rows: List of (endpoint_name, path, ProfileResult or list of ProfileResult).
              If list, we aggregate (avg T_*, sum content_length, etc.).
        base_url: Base URL used for profiling.
        runs_info: Optional string like "runs=3" to append to header.
        xishen_input_sizes: 若测了喜神忌神且拉取到入参体量，则展示「优化前/后字符数、降低%」。

    Returns:
        Markdown string.
    """
    lines = [
        "# 流式接口各环节耗时报告",
        "",
        f"**基准 URL**: `{base_url}`",
        f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]
    if runs_info:
        lines.append(f"**说明**: {runs_info}")
        lines.append("")

    lines.extend([
        "## 汇总表（按阶段）",
        "",
        "| 接口名称 | 编排取数(s) | 大模型首字延迟(s) | 大模型流式输出(s) | 总耗时(s) | 流式内容长度 | 备注 |",
        "|----------|-------------|-------------------|-------------------|-----------|--------------|------|",
    ])

    conclusion_parts = []
    for name, path, res in rows:
        if isinstance(res, list):
            agg = _aggregate_results(res)
            note = "" if agg.get("success") else (agg.get("error_message") or "失败")
        else:
            agg = res.to_dict() if hasattr(res, "to_dict") else res
            note = "" if agg.get("success") else (agg.get("error_message") or "失败")

        t_data = agg.get("T_data")
        t_fp = agg.get("T_first_progress")
        t_complete = agg.get("T_complete")
        # 阶段含义：编排取数 = T_data；大模型首字延迟 = T_fp - T_data；大模型流式输出 = T_complete - T_fp；总耗时 = T_complete
        t_orch = _fmt(t_data)
        t_llm_first = None
        t_llm_stream = None
        if t_fp is not None and t_data is not None:
            t_llm_first = round(t_fp - t_data, 3)
        if t_complete is not None and t_fp is not None:
            t_llm_stream = round(t_complete - t_fp, 3)
        t_llm_first_str = _fmt(t_llm_first)
        t_llm_stream_str = _fmt(t_llm_stream)
        t_total_str = _fmt(t_complete)
        clen = agg.get("content_length_progress", 0)
        lines.append(
            f"| {name} | {t_orch} | {t_llm_first_str} | {t_llm_stream_str} | {t_total_str} | {clen} | {note} |"
        )
        # 结论一句：编排取数 Xs，大模型首字延迟 Xs，大模型流式输出 Xs，总耗时 Xs
        if agg.get("success") and t_data is not None and t_complete is not None:
            c_llm_first = _fmt(t_llm_first) if t_llm_first is not None else "-"
            c_llm_stream = _fmt(t_llm_stream) if t_llm_stream is not None else "-"
            conclusion_parts.append(
                f"- **{name}**：从编排取数 {_fmt(t_data)}s，大模型首字延迟 {c_llm_first}s，大模型流式输出 {c_llm_stream}s，总耗时 {_fmt(t_complete)}s。"
            )

    lines.extend([
        "",
        "## 指标含义（对应接口内部阶段）",
        "",
        "| 阶段 | 指标名 | 含义 |",
        "|------|--------|------|",
        "| 从统一编排获取数据 | 编排取数 | 从请求开始到收到首条「结构化数据」的时间（接口从 BaziDataOrchestrator 取数并返回首包） |",
        "| 数据交给大模型 → 大模型开始输出 | 大模型首字延迟 | 从首包(data)到首条流式内容(progress)的时间（含：数据交 LLM、LLM 计算、首字返回） |",
        "| 大模型逐字/逐段反馈 | 大模型流式输出 | 从首条 progress 到 complete 的时间（大模型持续输出内容的耗时） |",
        "| 整次请求结束 | 总耗时 | 从请求开始到收到 complete 的时间 |",
        "",
        "## 结论",
        "",
        "各接口本轮测量的阶段耗时如下（便于判断瓶颈在「编排取数」还是「大模型首字」或「大模型流式输出」）：",
        "",
    ])
    if conclusion_parts:
        lines.extend(conclusion_parts)
        lines.append("")
        lines.append("若「大模型首字延迟」和「总耗时」都很短，多为**缓存命中**（相同参数再次请求直接返回缓存）。若「大模型首字延迟」较长（如十几秒），多为**冷请求**（真实调用了大模型）。")
    else:
        lines.append("（无成功请求或无完整阶段数据，无法给出结论。）")

    if xishen_input_sizes:
        o = xishen_input_sizes.get("old_chars", 0)
        n = xishen_input_sizes.get("new_chars", 0)
        p = xishen_input_sizes.get("pct_reduced")
        if o and n is not None and p is not None:
            body = f"- **入参体量**：优化前 {o} 字符（完整 JSON），优化后 {n} 字符（描述文），**降低 {p}%**。"
        else:
            body = f"- **入参体量**：优化前 {o} 字符（完整 JSON）。"
        lines.extend([
            "",
            "## 喜神忌神优化（LLM 入参体量）",
            "",
            f"- **响应时间**：见上表「总耗时」等列（冷请求较慢，缓存命中较快）。",
            body,
            "",
        ])

    lines.extend([
        "",
        "## 原始指标说明（供排查用）",
        "",
        "- **T_data**：首条 `type=data` 时间（秒）。",
        "- **T_first_progress**：首条 `type=progress` 时间（秒）。",
        "- **T_llm_first_token**：T_first_progress - T_data。",
        "- **T_complete**：首条 `type=complete` 时间（秒）。",
        "- **content_length_progress**：所有 progress 的 content 总字符数。",
        "",
    ])
    return "\n".join(lines)


def _get_success(r: Any) -> bool:
    if isinstance(r, dict):
        return r.get("success", False)
    return getattr(r, "success", False)


def _get_error_message(r: Any) -> Optional[str]:
    if isinstance(r, dict):
        return r.get("error_message")
    return getattr(r, "error_message", None)


def _aggregate_results(results: List[Any]) -> Dict[str, Any]:
    """Aggregate multiple ProfileResults (e.g. avg T_*, sum content_length)."""
    if not results:
        return {"success": False, "error_message": "无结果"}
    success_count = sum(1 for r in results if _get_success(r))
    success = success_count == len(results)
    error_message = None
    if not success and results:
        first_fail = next((r for r in results if not _get_success(r)), None)
        if first_fail:
            error_message = _get_error_message(first_fail)

    def get_vals(key: str):
        out = []
        for r in results:
            if hasattr(r, key):
                out.append(getattr(r, key))
            elif isinstance(r, dict) and key in r:
                out.append(r[key])
            else:
                out.append(None)
        return out

    def avg_float(key: str) -> Optional[float]:
        vals = [v for v in get_vals(key) if v is not None]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 3)

    def sum_int(key: str) -> int:
        vals = get_vals(key)
        return sum(v or 0 for v in vals)

    def merge_counts() -> Dict[str, int]:
        merged = {}
        for r in results:
            c = getattr(r, "event_counts", None) or (r.get("event_counts") if isinstance(r, dict) else None)
            if not c:
                continue
            for k, v in c.items():
                merged[k] = merged.get(k, 0) + v
        return merged

    return {
        "success": success,
        "error_message": error_message,
        "T_data": avg_float("T_data"),
        "T_first_progress": avg_float("T_first_progress"),
        "T_complete": avg_float("T_complete"),
        "T_error": avg_float("T_error"),
        "T_llm_first_token": avg_float("T_llm_first_token"),
        "content_length_progress": sum_int("content_length_progress"),
        "content_length_complete": sum_int("content_length_complete"),
        "event_counts": merge_counts(),
    }


def to_json(
    rows: List[Tuple[str, str, Any]],
    base_url: str,
    runs: int = 1,
    xishen_input_sizes: Optional[Dict[str, int]] = None,
) -> str:
    """
    Build a JSON report from profile result rows.

    Args:
        rows: List of (endpoint_name, path, ProfileResult or list of ProfileResult).
        base_url: Base URL used.
        runs: Number of runs (for aggregation info).
        xishen_input_sizes: 喜神忌神入参体量（若有）。

    Returns:
        JSON string.
    """
    report = {
        "base_url": base_url,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "runs": runs,
        "endpoints": [],
    }
    if xishen_input_sizes:
        report["xishen_input_sizes"] = xishen_input_sizes
    for name, path, res in rows:
        if isinstance(res, list):
            agg = _aggregate_results(res)
            agg["name"] = name
            agg["path"] = path
            report["endpoints"].append(agg)
        else:
            d = res.to_dict() if hasattr(res, "to_dict") else res
            d["name"] = name
            d["path"] = path
            report["endpoints"].append(d)
    return json.dumps(report, ensure_ascii=False, indent=2)
