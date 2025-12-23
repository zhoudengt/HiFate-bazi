#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
十神命格名称提取器

提供统一的命格名称提取函数，确保所有接口使用相同的逻辑提取命格名称。
"""

import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def extract_mingge_names_from_rules(shishen_rules: List[Dict]) -> List[str]:
    """
    从十神命格规则中提取命格名称
    
    提取优先级：
    1. content.mingge_name 字段（如果规则中专门存储了命格名称）
    2. rule_name（如果是标准命格名称格式）
    3. content.text 中匹配命格名称（按长度降序匹配，避免部分匹配）
    4. description 中提取
    
    Args:
        shishen_rules: 匹配的十神命格规则列表
        
    Returns:
        List[str]: 提取的命格名称列表（去重）
    """
    from server.services.config_service import ConfigService
    
    shishen_mingge_names = []
    
    try:
        # 获取所有命格名称列表
        all_mingge_names = list(ConfigService.get_all_mingge().keys())
        
        # 按长度降序排序，避免部分匹配问题（如"正官格"应该匹配，而不是先匹配到"正官"）
        all_mingge_names_sorted = sorted(all_mingge_names, key=len, reverse=True)
        
        logger.debug(f"开始提取命格名称，规则数量: {len(shishen_rules)}, 可用命格名称数量: {len(all_mingge_names)}")
        
        for rule in shishen_rules:
            found_mingge = None
            
            # 方法1: 优先从 content.mingge_name 字段提取（如果规则中专门存储了命格名称）
            content = rule.get('content', {})
            if isinstance(content, dict):
                mingge_name_field = content.get('mingge_name')
                if mingge_name_field and mingge_name_field in all_mingge_names:
                    found_mingge = mingge_name_field
                    logger.debug(f"从 content.mingge_name 提取到命格名称: {found_mingge}")
            
            # 方法2: 从 rule_name 中精确匹配（优先完整匹配）
            if not found_mingge:
                rule_name = rule.get('rule_name', '')
                if rule_name:
                    # 精确匹配优先
                    if rule_name in all_mingge_names:
                        found_mingge = rule_name
                        logger.debug(f"从 rule_name 精确匹配到命格名称: {found_mingge}")
                    else:
                        # 如果rule_name包含命格名称（使用长的优先匹配）
                        for mingge_name in all_mingge_names_sorted:
                            if mingge_name in rule_name:
                                found_mingge = mingge_name
                                logger.debug(f"从 rule_name 包含匹配到命格名称: {found_mingge} (rule_name: {rule_name})")
                                break
            
            # 方法3: 从 content.text 中提取命格名称
            if not found_mingge and isinstance(content, dict):
                text = content.get('text', '')
                if text:
                    # 在文本中查找命格名称（按长度降序，避免部分匹配）
                    for mingge_name in all_mingge_names_sorted:
                        if mingge_name in text:
                            found_mingge = mingge_name
                            logger.debug(f"从 content.text 提取到命格名称: {found_mingge} (text片段: {text[:50]}...)")
                            break
            
            # 方法4: 从 description 中提取
            if not found_mingge:
                description = rule.get('description', {})
                if description:
                    desc_text = ''
                    if isinstance(description, dict):
                        desc_text = json.dumps(description, ensure_ascii=False)
                    elif isinstance(description, str):
                        desc_text = description
                    
                    if desc_text:
                        for mingge_name in all_mingge_names_sorted:
                            if mingge_name in desc_text:
                                found_mingge = mingge_name
                                logger.debug(f"从 description 提取到命格名称: {found_mingge}")
                                break
            
            # 如果找到命格名称，添加到列表（去重）
            if found_mingge and found_mingge not in shishen_mingge_names:
                shishen_mingge_names.append(found_mingge)
        
        logger.info(f"提取命格名称完成，共提取到 {len(shishen_mingge_names)} 个命格名称: {shishen_mingge_names}")
        
    except Exception as e:
        logger.error(f"提取命格名称时发生错误: {e}", exc_info=True)
        # 返回空列表，不抛出异常，确保不影响主流程
        return []
    
    return shishen_mingge_names

