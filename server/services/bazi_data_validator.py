#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据一致性验证器 - 验证返回数据的一致性和完整性
"""

import logging
from typing import Dict, Any, Optional, List, Tuple

# 配置日志
logger = logging.getLogger(__name__)


class BaziDataValidator:
    """数据一致性验证器"""
    
    @staticmethod
    def validate_consistency(
        unified_data: Dict[str, Any],
        reference_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        验证数据一致性
        
        Args:
            unified_data: 统一接口返回的数据
            reference_data: 参考数据（可选，用于交叉验证）
        
        Returns:
            (is_consistent, errors): 是否一致，错误列表
        """
        errors = []
        
        # 1. 字段完整性验证
        required_fields = ['bazi', 'wangshuai', 'xishen_jishen']
        for field in required_fields:
            if field not in unified_data:
                errors.append(f"缺少必需字段: {field}")
        
        # 2. 数据类型验证
        if 'bazi' in unified_data:
            bazi = unified_data['bazi']
            if not isinstance(bazi, dict):
                errors.append("bazi 字段类型错误，应为 dict")
            elif 'bazi_pillars' not in bazi:
                errors.append("bazi.bazi_pillars 字段缺失")
            else:
                # 验证四柱结构
                bazi_pillars = bazi.get('bazi_pillars', {})
                for pillar_type in ['year', 'month', 'day', 'hour']:
                    if pillar_type not in bazi_pillars:
                        errors.append(f"bazi.bazi_pillars.{pillar_type} 字段缺失")
                    else:
                        pillar = bazi_pillars[pillar_type]
                        if not isinstance(pillar, dict):
                            errors.append(f"bazi.bazi_pillars.{pillar_type} 类型错误，应为 dict")
                        elif 'stem' not in pillar or 'branch' not in pillar:
                            errors.append(f"bazi.bazi_pillars.{pillar_type} 缺少 stem 或 branch 字段")
        
        # 3. 数据格式验证（与前端页面格式一致）
        if 'dayun' in unified_data:
            dayun = unified_data['dayun']
            if isinstance(dayun, list):
                for idx, item in enumerate(dayun):
                    if not isinstance(item, dict):
                        errors.append(f"dayun[{idx}] 类型错误，应为 dict")
                    else:
                        # 验证大运必需字段
                        if 'ganzhi' not in item and ('stem' not in item or 'branch' not in item):
                            errors.append(f"dayun[{idx}] 缺少 ganzhi 或 stem/branch 字段")
                        if 'step' not in item:
                            errors.append(f"dayun[{idx}] 缺少 step 字段")
            elif dayun is not None:
                errors.append("dayun 类型错误，应为 list 或 None")
        
        if 'liunian' in unified_data:
            liunian = unified_data['liunian']
            if isinstance(liunian, list):
                for idx, item in enumerate(liunian):
                    if not isinstance(item, dict):
                        errors.append(f"liunian[{idx}] 类型错误，应为 dict")
                    else:
                        # 验证流年必需字段
                        if 'year' not in item:
                            errors.append(f"liunian[{idx}] 缺少 year 字段")
                        if 'ganzhi' not in item and ('stem' not in item or 'branch' not in item):
                            errors.append(f"liunian[{idx}] 缺少 ganzhi 或 stem/branch 字段")
            elif liunian is not None:
                errors.append("liunian 类型错误，应为 list 或 None")
        
        # 4. 旺衰数据验证
        if 'wangshuai' in unified_data:
            wangshuai = unified_data['wangshuai']
            if not isinstance(wangshuai, dict):
                errors.append("wangshuai 字段类型错误，应为 dict")
            elif 'wangshuai' not in wangshuai:
                errors.append("wangshuai.wangshuai 字段缺失")
        
        # 5. 喜忌数据验证
        if 'xishen_jishen' in unified_data:
            xishen_jishen = unified_data['xishen_jishen']
            if xishen_jishen is not None:
                if hasattr(xishen_jishen, 'data'):
                    data = xishen_jishen.data
                    if not isinstance(data, dict):
                        errors.append("xishen_jishen.data 类型错误，应为 dict")
                    else:
                        if 'xi_shen_elements' not in data:
                            errors.append("xishen_jishen.data.xi_shen_elements 字段缺失")
                        if 'ji_shen_elements' not in data:
                            errors.append("xishen_jishen.data.ji_shen_elements 字段缺失")
                elif isinstance(xishen_jishen, dict):
                    if 'xi_shen_elements' not in xishen_jishen:
                        errors.append("xishen_jishen.xi_shen_elements 字段缺失")
                    if 'ji_shen_elements' not in xishen_jishen:
                        errors.append("xishen_jishen.ji_shen_elements 字段缺失")
        
        # 6. 规则匹配数据验证
        if 'rules' in unified_data:
            rules = unified_data['rules']
            if not isinstance(rules, list):
                errors.append("rules 字段类型错误，应为 list")
            else:
                for idx, rule in enumerate(rules):
                    if not isinstance(rule, dict):
                        errors.append(f"rules[{idx}] 类型错误，应为 dict")
                    elif 'rule_code' not in rule:
                        errors.append(f"rules[{idx}] 缺少 rule_code 字段")
        
        # 7. 交叉验证（如果有参考数据）
        if reference_data:
            # 对比关键字段
            if 'bazi' in unified_data and 'bazi' in reference_data:
                unified_bazi = unified_data['bazi']
                reference_bazi = reference_data['bazi']
                
                # 对比四柱
                unified_pillars = unified_bazi.get('bazi_pillars', {})
                reference_pillars = reference_bazi.get('bazi_pillars', {})
                
                for pillar_type in ['year', 'month', 'day', 'hour']:
                    if pillar_type in unified_pillars and pillar_type in reference_pillars:
                        unified_pillar = unified_pillars[pillar_type]
                        reference_pillar = reference_pillars[pillar_type]
                        
                        unified_ganzhi = f"{unified_pillar.get('stem', '')}{unified_pillar.get('branch', '')}"
                        reference_ganzhi = f"{reference_pillar.get('stem', '')}{reference_pillar.get('branch', '')}"
                        
                        if unified_ganzhi != reference_ganzhi:
                            errors.append(f"bazi_pillars.{pillar_type} 与参考数据不一致: {unified_ganzhi} != {reference_ganzhi}")
            
            # 对比大运
            if 'dayun' in unified_data and 'dayun' in reference_data:
                unified_dayun = unified_data['dayun']
                reference_dayun = reference_data['dayun']
                
                if isinstance(unified_dayun, list) and isinstance(reference_dayun, list):
                    if len(unified_dayun) != len(reference_dayun):
                        errors.append(f"dayun 数量不一致: {len(unified_dayun)} != {len(reference_dayun)}")
                    else:
                        for idx, (u_dayun, r_dayun) in enumerate(zip(unified_dayun, reference_dayun)):
                            u_ganzhi = u_dayun.get('ganzhi', f"{u_dayun.get('stem', '')}{u_dayun.get('branch', '')}")
                            r_ganzhi = r_dayun.get('ganzhi', f"{r_dayun.get('stem', '')}{r_dayun.get('branch', '')}")
                            
                            if u_ganzhi != r_ganzhi:
                                errors.append(f"dayun[{idx}] 与参考数据不一致: {u_ganzhi} != {r_ganzhi}")
        
        # 记录验证结果
        if errors:
            logger.warning(f"数据一致性验证失败，发现 {len(errors)} 个错误: {errors}")
        else:
            logger.info("数据一致性验证通过")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_module_data(
        module_name: str,
        module_data: Any,
        expected_type: type = None,
        required_fields: List[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        验证单个模块的数据
        
        Args:
            module_name: 模块名称
            module_data: 模块数据
            expected_type: 期望的数据类型
            required_fields: 必需字段列表
        
        Returns:
            (is_valid, errors): 是否有效，错误列表
        """
        errors = []
        
        # 类型验证
        if expected_type and not isinstance(module_data, expected_type):
            errors.append(f"{module_name} 类型错误，应为 {expected_type.__name__}，实际为 {type(module_data).__name__}")
            return False, errors
        
        # 字段验证
        if required_fields and isinstance(module_data, dict):
            for field in required_fields:
                if field not in module_data:
                    errors.append(f"{module_name}.{field} 字段缺失")
        
        return len(errors) == 0, errors

