#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旺衰缓存清理脚本

旺衰算法从三因子升级为五因子后，旧缓存结果全部失效。
发布新版本后执行此脚本清理 Redis 中的旺衰缓存。

使用方式：
    .venv/bin/python scripts/flush_wangshuai_cache.py
    .venv/bin/python scripts/flush_wangshuai_cache.py --dry-run   # 预览，不实际删除
    .venv/bin/python scripts/flush_wangshuai_cache.py --host 127.0.0.1 --port 6379
"""

import sys
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def flush_wangshuai_cache(host: str, port: int, db: int, dry_run: bool) -> int:
    """
    使用 SCAN + DEL 模式清理旺衰缓存（不影响其他 key）。
    返回删除的 key 数量。
    """
    try:
        import redis
    except ImportError:
        logger.error("redis 模块未安装，请运行: .venv/bin/pip install redis")
        sys.exit(1)

    client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
    try:
        client.ping()
        logger.info(f"✅ 已连接 Redis {host}:{port} db={db}")
    except Exception as e:
        logger.error(f"❌ Redis 连接失败: {e}")
        sys.exit(1)

    pattern = 'wangshuai:*'
    logger.info(f"🔍 扫描 pattern: {pattern}")

    deleted = 0
    cursor = 0
    batch_keys = []

    while True:
        cursor, keys = client.scan(cursor, match=pattern, count=200)
        batch_keys.extend(keys)
        if cursor == 0:
            break

    total = len(batch_keys)
    logger.info(f"   找到 {total} 个旺衰缓存 key")

    if total == 0:
        logger.info("✅ 无需清理")
        return 0

    if dry_run:
        logger.info(f"[dry-run] 将删除 {total} 个 key（未实际执行）")
        for k in batch_keys[:10]:
            logger.info(f"   示例: {k}")
        if total > 10:
            logger.info(f"   ... 还有 {total - 10} 个")
        return total

    # 分批删除，每批 100 个
    batch_size = 100
    for i in range(0, len(batch_keys), batch_size):
        batch = batch_keys[i:i + batch_size]
        if batch:
            client.delete(*batch)
            deleted += len(batch)
            logger.info(f"   已删除 {deleted}/{total}")

    logger.info(f"✅ 清理完成，共删除 {deleted} 个旺衰缓存 key")
    return deleted


def main():
    parser = argparse.ArgumentParser(description='清理旺衰 Redis 缓存')
    parser.add_argument('--host', default='127.0.0.1', help='Redis 主机')
    parser.add_argument('--port', type=int, default=6379, help='Redis 端口')
    parser.add_argument('--db', type=int, default=0, help='Redis DB')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际删除')
    args = parser.parse_args()

    flush_wangshuai_cache(args.host, args.port, args.db, args.dry_run)


if __name__ == '__main__':
    main()
