#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日运势数据加载器 - 从JSON文件加载，不查数据库
"""

import json
import os
from typing import Dict, List, Optional, Any

_DATA_DIR = os.path.join(os.path.dirname(__file__), 'daily_fortune')
_CACHE: Dict[str, List[Dict]] = {}
_ORDER = ('合', '冲', '刑', '破', '害')


def _load(filename: str) -> List[Dict]:
    if filename not in _CACHE:
        path = os.path.join(_DATA_DIR, filename)
        with open(path, 'r', encoding='utf-8') as f:
            _CACHE[filename] = json.load(f)
    return _CACHE[filename]


def get_jiazi_fortune(jiazi_day: str) -> Optional[str]:
    if not jiazi_day.endswith('日'):
        jiazi_day = jiazi_day + '日'
    for row in _load('jiazi.json'):
        if row.get('jiazi_day') == jiazi_day:
            content = row.get('content')
            if content and isinstance(content, str) and '\\n' in content:
                content = content.replace('\\n', '\n')
            return content
    return None


def get_shishen(day_stem: str, birth_stem: str) -> Optional[str]:
    for row in _load('shishen_query.json'):
        if row.get('day_stem') == day_stem and row.get('birth_stem') == birth_stem:
            return row.get('shishen')
    return None


def get_shishen_meaning(shishen: str) -> Optional[Dict[str, str]]:
    mapping = {'偏官': '七杀', '偏印': '偏印'}
    mapped = mapping.get(shishen, shishen)
    for row in _load('shishen_meaning.json'):
        if row.get('shishen') == mapped:
            return {'hint': row.get('hint', ''), 'hint_keywords': row.get('hint_keywords', '')}
    return None


def get_shishen_hint(day_stem: str, birth_stem: str) -> Optional[str]:
    shishen = get_shishen(day_stem, birth_stem)
    if not shishen:
        return None
    meaning = get_shishen_meaning(shishen)
    if not meaning:
        return None
    hint = meaning.get('hint', '')
    hint_keywords = meaning.get('hint_keywords', '')
    if hint_keywords:
        return f"{hint}今日提示词：{hint_keywords}"
    return hint


def get_zodiac_relations(day_branch: str) -> Optional[str]:
    rows = [r for r in _load('zodiac.json') if r.get('day_branch') == day_branch]
    if not rows:
        return None
    ordered = sorted(rows, key=lambda x: _ORDER.index(x['relation_type']) if x['relation_type'] in _ORDER else 99)
    lines = []
    for r in ordered:
        lines.append(f"{r['relation_type']} {r['target_zodiac']} ({r['target_branch']})：{r.get('content', '')}")
    return "\n".join(lines)


def get_jianchu_info(jianchu: str) -> Optional[Dict[str, Any]]:
    if not jianchu:
        return None
    for row in _load('jianchu.json'):
        if row.get('jianchu') == jianchu:
            return {
                'name': row.get('jianchu', jianchu),
                'energy': row.get('score'),
                'summary': row.get('content', '')
            }
    return {'name': jianchu, 'energy': None, 'summary': None}


def get_lucky_colors_wannianli(direction: str) -> Optional[str]:
    for row in _load('lucky_color_wannianli.json'):
        if row.get('direction') == direction:
            return row.get('colors')
    return None


def get_lucky_color_shishen(shishen: str) -> Optional[str]:
    for row in _load('lucky_color_shishen.json'):
        if row.get('shishen') == shishen:
            return row.get('color', '').strip() or None
    return None


def get_guiren_direction(day_stem: str) -> Optional[str]:
    for row in _load('guiren_direction.json'):
        if row.get('day_stem') == day_stem:
            return row.get('directions')
    return None


def get_wenshen_direction(day_branch: str) -> Optional[str]:
    for row in _load('wenshen_direction.json'):
        if row.get('day_branch') == day_branch:
            return row.get('direction', '').strip() or None
    return None
