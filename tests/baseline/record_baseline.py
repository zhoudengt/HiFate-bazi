#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Record baseline: call /api/v1/bazi/calculate for test cases and save response data to baseline_data.json.
Run from project root: python tests/baseline/record_baseline.py
"""

import json
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

CASES = [
    {"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"},
    {"solar_date": "1985-06-20", "solar_time": "08:30", "gender": "female"},
]


def main():
    from fastapi.testclient import TestClient
    from server.main import app
    client = TestClient(app)
    results = []
    for case in CASES:
        response = client.post("/api/v1/bazi/calculate", json=case)
        if response.status_code != 200:
            print(f"Failed: {case} -> {response.status_code} {response.text}", file=sys.stderr)
            sys.exit(1)
        body = response.json()
        if not body.get("success"):
            print(f"API returned success=False: {case}", file=sys.stderr)
            sys.exit(1)
        results.append({"request": case, "expected_data": body.get("data")})
    baseline = {"bazi_calculate": results}
    path = os.path.join(os.path.dirname(__file__), "baseline_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)
    print(f"Recorded {len(results)} cases to {path}")


if __name__ == "__main__":
    main()
