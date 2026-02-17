#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自定义 UTF-8 JSON 响应类"""

import json
from fastapi.responses import Response


class UTF8JSONResponse(Response):
    """确保中文正确编码 + 强制不缓存"""
    media_type = "application/json; charset=utf-8"

    def __init__(self, content, **kwargs):
        super().__init__(content, **kwargs)
        self.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        self.headers["Pragma"] = "no-cache"
        self.headers["Expires"] = "0"

    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")
