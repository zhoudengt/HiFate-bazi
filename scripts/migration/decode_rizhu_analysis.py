#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 rizhu_update_production.sql 解码指定日柱的 analysis，并提取【深度解读】段落。"""
import re
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SQL_FILE = os.path.join(PROJECT_ROOT, 'scripts', 'migration', 'rizhu_update_production.sql')

def decode_hex_analysis(hex_str: str) -> str:
    raw = bytes.fromhex(hex_str).decode('utf-8')
    return raw

def extract_shendu(analysis: str) -> str:
    start = analysis.find('【深度解读】')
    end = analysis.find('【断语展示】')
    if start == -1:
        return ""
    if end == -1:
        return analysis[start:]
    return analysis[start:end].strip()

def main():
    if not os.path.exists(SQL_FILE):
        print(f"File not found: {SQL_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    # 每条 UPDATE 一行，格式: UPDATE ... UNHEX('...') WHERE BINARY rizhu=UNHEX('...');
    pattern = r"UPDATE rizhu_liujiazi SET analysis=UNHEX\('([A-F0-9]+)'\) WHERE BINARY rizhu=UNHEX\('([A-F0-9]+)'\)"
    matches = list(re.finditer(pattern, content))
    names = ['甲子', '乙丑', '丙寅']
    for i, name in enumerate(names):
        if i >= len(matches):
            print(f"Not enough rows for {name}", file=sys.stderr)
            continue
        m = matches[i]
        hex_analysis = m.group(1)
        hex_rizhu = m.group(2)
        rizhu = bytes.fromhex(hex_rizhu).decode('utf-8')
        full = decode_hex_analysis(hex_analysis)
        sd = extract_shendu(full)
        print("=" * 60)
        print(f"日柱: {rizhu} (expected {name})")
        print("=" * 60)
        print("【深度解读】原文:")
        print(sd)
        print()

if __name__ == '__main__':
    main()
