# -*- coding: utf-8 -*-
"""V2 DAO：从连接池取连接并在用完后归还，避免泄漏。"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from shared.config.database import get_mysql_connection, return_mysql_connection


@contextmanager
def v2_mysql_conn() -> Generator[Any, None, None]:
    conn = get_mysql_connection()
    try:
        yield conn
    finally:
        return_mysql_connection(conn)
