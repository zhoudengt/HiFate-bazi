# -*- coding: utf-8 -*-
"""V2 剧情：配置表走内存缓存，避免每次请求占连接。"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List

from server.services.v2 import juqing_dao

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache: Dict[int, List[Dict[str, Any]]] = {}
_loaded = False


def reload_cache() -> None:
    """从数据库重建缓存（部署/热更新后可调用）。"""
    global _cache, _loaded
    try:
        data = juqing_dao.load_all_dialogues_grouped()
    except Exception:
        logger.exception("v2_juqing 加载失败，使用空缓存（请检查库表与 MYSQL 配置）")
        data = {}
    with _lock:
        _cache = data
        _loaded = True
    logger.info("v2_juqing 缓存已加载，对话组数=%s", len(_cache))


def _ensure_loaded() -> None:
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
    reload_cache()


def get_dialogue(dialogue_id: int) -> List[Dict[str, Any]]:
    """返回指定对话组的有序行列表（拷贝，避免调用方修改缓存）。"""
    _ensure_loaded()
    with _lock:
        lines = _cache.get(int(dialogue_id), [])
        return [dict(x) for x in lines]
