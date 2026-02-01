# -*- coding: utf-8 -*-
"""
Stream API profiler: HTTP request + SSE parsing + per-stage timing.

Pure client: no server/core imports. Uses only stdlib + requests.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import requests


@dataclass
class ProfileResult:
    """Result of one stream profile run."""
    success: bool
    error_message: Optional[str] = None
    T_data: Optional[float] = None
    T_first_progress: Optional[float] = None
    T_complete: Optional[float] = None
    T_error: Optional[float] = None
    T_llm_first_token: Optional[float] = None
    content_length_progress: int = 0
    content_length_complete: int = 0
    event_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "success": self.success,
            "error_message": self.error_message,
            "T_data": self.T_data,
            "T_first_progress": self.T_first_progress,
            "T_complete": self.T_complete,
            "T_error": self.T_error,
            "T_llm_first_token": self.T_llm_first_token,
            "content_length_progress": self.content_length_progress,
            "content_length_complete": self.content_length_complete,
            "event_counts": dict(self.event_counts),
        }
        return d


def profile_one(
    base_url: str,
    path: str,
    method: str,
    payload_or_params: Optional[Dict[str, Any]] = None,
    timeout: int = 120,
) -> ProfileResult:
    """
    Profile one stream request: send HTTP, parse SSE, record first occurrence
    of each event type and content lengths.

    Args:
        base_url: e.g. http://localhost:8001
        path: e.g. /api/v1/bazi/wuxing-proportion/stream
        method: GET or POST
        payload_or_params: For POST = body (dict), for GET = query params (dict).
                           None treated as {}.
        timeout: Request timeout in seconds.

    Returns:
        ProfileResult with T_data, T_first_progress, T_complete, etc.
    """
    url = base_url.rstrip("/") + path
    headers = {"Accept": "text/event-stream", "Content-Type": "application/json"}
    payload_or_params = payload_or_params or {}

    # Filter None values so server can use defaults
    if method == "POST":
        payload = {k: v for k, v in payload_or_params.items() if v is not None}
    else:
        payload = payload_or_params

    result = ProfileResult(success=False, event_counts={})
    t0 = None

    try:
        t0 = time.perf_counter()
        if method == "GET":
            resp = requests.get(
                url,
                headers=headers,
                params=payload,
                stream=True,
                timeout=(10, timeout),
            )
        else:
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=(10, timeout),
            )
        resp.raise_for_status()

        buffer = b""
        first_data_time = None
        first_progress_time = None
        first_complete_time = None
        first_error_time = None
        content_length_progress = 0
        content_length_complete = 0
        counts = {"data": 0, "progress": 0, "complete": 0, "error": 0}

        for chunk in resp.iter_content(chunk_size=8192):
            if not chunk:
                continue
            buffer += chunk
            while b"\n" in buffer:
                line_bytes, buffer = buffer.split(b"\n", 1)
                try:
                    line = line_bytes.decode("utf-8").strip()
                except UnicodeDecodeError:
                    continue
                if not line or not line.startswith("data:"):
                    continue
                json_str = line[5:].strip()
                if not json_str:
                    continue
                try:
                    msg = json.loads(json_str)
                except json.JSONDecodeError:
                    continue
                event_type = msg.get("type", "")
                counts[event_type] = counts.get(event_type, 0) + 1

                now = time.perf_counter() - t0
                if event_type == "data" and first_data_time is None:
                    first_data_time = now
                elif event_type == "progress":
                    if first_progress_time is None:
                        first_progress_time = now
                    content_length_progress += len(msg.get("content", "") or "")
                elif event_type == "complete":
                    if first_complete_time is None:
                        first_complete_time = now
                    content_length_complete += len(msg.get("content", "") or "")
                elif event_type == "error":
                    if first_error_time is None:
                        first_error_time = now

        result.success = True
        result.T_data = round(first_data_time, 3) if first_data_time is not None else None
        result.T_first_progress = round(first_progress_time, 3) if first_progress_time is not None else None
        result.T_complete = round(first_complete_time, 3) if first_complete_time is not None else None
        result.T_error = round(first_error_time, 3) if first_error_time is not None else None
        if first_data_time is not None and first_progress_time is not None:
            result.T_llm_first_token = round(first_progress_time - first_data_time, 3)
        result.content_length_progress = content_length_progress
        result.content_length_complete = content_length_complete
        result.event_counts = counts
        return result

    except requests.exceptions.Timeout as e:
        result.error_message = f"超时: {e}"
        return result
    except requests.exceptions.RequestException as e:
        result.error_message = f"请求失败: {e}"
        return result
    except Exception as e:
        result.error_message = f"{type(e).__name__}: {e}"
        return result
    finally:
        pass
