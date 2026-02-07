#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump all 60 【深度解读】 from original SQL to text for analysis."""
import re, os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SQL_FILE = os.path.join(PROJECT_ROOT, 'scripts', 'migration', 'rizhu_update_production.sql')

def decode_hex(s): return bytes.fromhex(s).decode("utf-8")
def extract_shendu(a):
    s, e = a.find("【深度解读】"), a.find("【断语展示】")
    return a[s:e].strip() if s != -1 and e != -1 else ""

with open(SQL_FILE, "r", encoding="utf-8") as f:
    content = f.read()
pattern = r"UNHEX\('([A-F0-9]+)'\) WHERE BINARY rizhu=UNHEX\('([A-F0-9]+)'\)"
for m in re.finditer(pattern, content):
    rizhu = decode_hex(m.group(2))
    full = decode_hex(m.group(1))
    sd = extract_shendu(full)
    print(f"=== {rizhu} ===")
    print(sd)
    print()
