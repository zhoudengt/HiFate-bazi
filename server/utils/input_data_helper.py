#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入数据处理工具类
提供公共的数据简化和安全访问方法，供各流式接口复用
不修改底层计算逻辑，只处理数据格式化
"""

from typing import Dict, Any, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class InputDataHelper:
    """输入数据处理工具类"""
    
    @staticmethod
    def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """安全获取字典值"""
        if not isinstance(data, dict):
            return default
        return data.get(key, default)
    
    @staticmethod
    def safe_get_dict(data: Dict[str, Any], key: str) -> Dict[str, Any]:
        """安全获取字典字段（避免 KeyError）"""
        if not isinstance(data, dict):
            return {}
        result = data.get(key)
        if not isinstance(result, dict):
            return {}
        return result
    
    @staticmethod
    def safe_get_list(data: Dict[str, Any], key: str) -> List[Any]:
        """安全获取列表字段"""
        if not isinstance(data, dict):
            return []
        result = data.get(key)
        if not isinstance(result, list):
            return []
        return result
    
    @staticmethod
    def ensure_dict_key(data: Dict[str, Any], key: str) -> None:
        """确保字典键存在，不存在则创建空字典"""
        if key not in data:
            data[key] = {}
    
    @staticmethod
    def simplify_liunian(liunian: Dict[str, Any], include_relations: bool = True) -> Dict[str, Any]:
        """
        简化流年数据：移除冗余字段，保留核心信息
        
        保留字段：year, ganzhi, stem, branch, relations, dayun_step, dayun_ganzhi, priority
        移除字段：liuyue_sequence, liuri_sequence, liushi_sequence
        """
        if not isinstance(liunian, dict):
            return {}
        
        # 构建干支
        stem = liunian.get('stem', '')
        branch = liunian.get('branch', '')
        ganzhi = liunian.get('ganzhi', f'{stem}{branch}')
        
        simplified = {
            'year': liunian.get('year'),
            'ganzhi': ganzhi,
            'stem': stem,
            'branch': branch,
            'dayun_step': liunian.get('dayun_step'),
            'dayun_ganzhi': liunian.get('dayun_ganzhi', ''),
            'priority': liunian.get('priority', 999999)
        }
        
        # 保留 relations 字段（岁运并临、天克地冲、天合地合）
        if include_relations:
            simplified['relations'] = liunian.get('relations', [])
            simplified['type_display'] = liunian.get('type_display', '')
        
        return simplified
    
    @staticmethod
    def simplify_dayun(dayun: Dict[str, Any], simplify_liunians: bool = True) -> Dict[str, Any]:
        """
        简化大运数据：保留核心字段
        
        保留字段：step, ganzhi, stem, branch, age_display, start_age, end_age, liunians
        """
        if not isinstance(dayun, dict):
            return {}
        
        stem = dayun.get('stem', dayun.get('gan', ''))
        branch = dayun.get('branch', dayun.get('zhi', ''))
        ganzhi = dayun.get('ganzhi', f'{stem}{branch}')
        
        simplified = {
            'step': dayun.get('step', ''),
            'ganzhi': ganzhi,
            'stem': stem,
            'branch': branch,
            'age_display': dayun.get('age_display', ''),
            'start_age': dayun.get('start_age'),
            'end_age': dayun.get('end_age')
        }
        
        # 简化流年列表
        liunians = dayun.get('liunians', [])
        if simplify_liunians and liunians:
            simplified['liunians'] = [
                InputDataHelper.simplify_liunian(ln) for ln in liunians
            ]
        else:
            simplified['liunians'] = liunians
        
        return simplified
    
    @staticmethod
    def ensure_relations(liunians: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        确保所有流年都有 relations 字段
        不修改原数据，返回新列表
        """
        if not isinstance(liunians, list):
            return []
        
        result = []
        for liunian in liunians:
            if not isinstance(liunian, dict):
                continue
            ln = liunian.copy()
            if 'relations' not in ln:
                ln['relations'] = []
            result.append(ln)
        return result
    
    @staticmethod
    def clean_liunian_data(liunian: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理流年数据：移除流月流日字段
        不修改原数据，返回新字典
        """
        if not isinstance(liunian, dict):
            return {}
        
        cleaned = liunian.copy()
        fields_to_remove = ['liuyue_sequence', 'liuri_sequence', 'liushi_sequence']
        for field in fields_to_remove:
            cleaned.pop(field, None)
        return cleaned
    
    @staticmethod
    def format_to_json(data: Dict[str, Any], indent: int = 2) -> str:
        """格式化数据为 JSON 字符串"""
        try:
            return json.dumps(data, ensure_ascii=False, indent=indent)
        except Exception as e:
            logger.error(f"JSON 格式化失败: {e}")
            return json.dumps({}, ensure_ascii=False)
