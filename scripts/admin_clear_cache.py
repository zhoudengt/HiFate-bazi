#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动清理生产/测试环境缓存

用法:
  # 清理生产 Node1 缓存
  .venv/bin/python scripts/admin_clear_cache.py --env production

  # 清理本地缓存（需本地服务运行在 8001）
  .venv/bin/python scripts/admin_clear_cache.py --env local
"""

import argparse
import sys

# 生产 Node1
PRODUCTION_URL = "http://8.210.52.217:8001"
LOCAL_URL = "http://localhost:8001"


def main():
    parser = argparse.ArgumentParser(description="清理 HiFate 业务缓存")
    parser.add_argument("--env", choices=["local", "production"], default="production")
    args = parser.parse_args()

    base = LOCAL_URL if args.env == "local" else PRODUCTION_URL
    url = f"{base}/api/v1/admin/cache/clear"

    try:
        import urllib.request
        import json
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode()
        try:
            j = json.loads(data)
            print(json.dumps(j, ensure_ascii=False, indent=2))
        except Exception:
            print(data)
        return 0
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
