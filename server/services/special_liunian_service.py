#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特殊流年服务 - 批量获取有关系的流年（冲合刑害、岁运并临等）
"""

import sys
import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_display_service import BaziDisplayService
from server.services.bazi_detail_service import BaziDetailService

# 配置日志
logger = logging.getLogger(__name__)


class SpecialLiunianService:
    """特殊流年服务 - 批量获取有关系的流年"""
    
    @staticmethod
    async def get_special_liunians_batch(
        solar_date: str,
        solar_time: str,
        gender: str,
        dayun_sequence: List[Dict[str, Any]],
        dayun_count: int = 8,
        current_time: Optional[datetime] = None,
        liunian_sequence: List[Dict[str, Any]] = None  # ✅ 新增：接收已计算的流年序列
    ) -> List[Dict[str, Any]]:
        """
        批量获取多个大运的特殊流年（有 relations 的流年）
        
        ⚠️ 不去重：同一年可能有多个关系，保留所有流年
        
        ✅ 架构规范：优先使用传入的 liunian_sequence，避免重复计算
        详见：standards/08_数据编排架构规范.md
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            dayun_sequence: 大运序列（已计算好的）
            dayun_count: 要查询的大运数量（默认8个）
            current_time: 当前时间（可选）
            liunian_sequence: 已计算的流年序列（由 BaziDataOrchestrator 传入，避免重复计算）
            
        Returns:
            List[Dict]: 所有特殊流年列表（不去重，按大运和年份排序）
        """
        if not dayun_sequence:
            logger.warning("dayun_sequence 为空，无法获取特殊流年")
            return []
        
        # 1. 生成缓存键（包含所有影响结果的参数）
        # 提取大运步骤列表并排序，用于缓存键
        dayun_steps = sorted([dayun.get('step') for dayun in dayun_sequence if dayun.get('step') is not None])
        dayun_steps_str = ','.join(map(str, dayun_steps))
        current_time_iso = current_time.strftime('%Y-%m-%dT%H') if current_time else None
        cache_key_parts = [
            'special_liunians',
            solar_date,
            solar_time,
            gender,
            dayun_steps_str,
            str(dayun_count),
            current_time_iso or 'default'
        ]
        cache_key = ':'.join(cache_key_parts)
        
        # 2. 先查缓存（L1内存 + L2 Redis）
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            # 设置 L2 Redis TTL 为 30 天（2592000秒）
            cache.l2.ttl = 2592000
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"✅ [缓存命中] SpecialLiunianService.get_special_liunians_batch: {cache_key[:50]}...")
                return cached_result
        except Exception as e:
            # Redis不可用，降级到直接计算
            logger.warning(f"⚠️  Redis缓存不可用，降级到直接计算: {e}")
        
        # 3. 缓存未命中，执行计算
        logger.info(f"⏱️ [缓存未命中] SpecialLiunianService.get_special_liunians_batch: {cache_key[:50]}...")
        
        import time
        start_time = time.time()
        
        # ✅ 架构规范：优先使用传入的 liunian_sequence，避免重复计算
        # 详见：standards/08_数据编排架构规范.md
        if liunian_sequence is not None and len(liunian_sequence) > 0:
            # ✅ 使用传入的数据（由 BaziDataOrchestrator 传入）
            logger.info(f"✅ [架构优化] 使用传入的 liunian_sequence，共 {len(liunian_sequence)} 个流年，避免重复计算")
        else:
            # ⚠️ 降级：只有在没有传入数据时才计算（应该避免这种情况）
            logger.warning("⚠️ [架构警告] liunian_sequence 未传入，降级到重新计算（违反架构规范，请检查调用方）")
            
            loop = asyncio.get_event_loop()
            executor = None
            
            # 调用 calculate_detail_full()（不指定 dayun_index，获取所有大运和流年）
            detail_result = await loop.run_in_executor(
                executor,
                BaziDetailService.calculate_detail_full,
                solar_date,
                solar_time,
                gender,
                current_time,
                None,  # dayun_index（不指定，获取所有大运）
                None   # target_year
            )
            
            if not detail_result:
                logger.warning("calculate_detail_full() 返回空结果，无法获取特殊流年")
                return []
            
            # 从结果中提取所有流年数据
            details = detail_result.get('details', {})
            liunian_sequence = details.get('liunian_sequence', [])
        
        logger.info(f"✅ [性能优化] 获取到 {len(liunian_sequence)} 个流年数据")
        
        # 筛选有 relations 的流年，并按大运分组
        special_liunians = []
        
        # 创建大运映射（用于快速查找大运信息）
        dayun_map = {}
        for dayun in dayun_sequence:
            step = dayun.get('step')
            if step is not None:
                dayun_map[step] = dayun
        
        # 遍历所有流年，筛选有 relations 的流年
        for liunian in liunian_sequence:
            liunian_year = liunian.get('year')
            relations = liunian.get('relations', [])
            
            # 只保留有 relations 的流年
            if not relations or len(relations) == 0:
                continue
            
            # 查找该流年属于哪个大运（根据年份范围）
            matched_dayun = None
            for dayun in dayun_sequence:
                step = dayun.get('step')
                dayun_year_start = dayun.get('year_start')
                dayun_year_end = dayun.get('year_end')
                dayun_stem = dayun.get('stem', '')
                
                # 跳过小运
                if dayun_stem == '小运':
                    continue
                
                # 检查流年是否在该大运的年份范围内
                if dayun_year_start and dayun_year_end:
                    if dayun_year_start <= liunian_year <= dayun_year_end:
                        matched_dayun = dayun
                        break
            
            if matched_dayun:
                # 添加大运信息到流年
                dayun_step = matched_dayun.get('step')
                dayun_ganzhi = f"{matched_dayun.get('stem', '')}{matched_dayun.get('branch', '')}"
                liunian['dayun_step'] = dayun_step
                liunian['dayun_ganzhi'] = dayun_ganzhi
                # 构建流年干支（如果不存在）
                if 'ganzhi' not in liunian:
                    liunian['ganzhi'] = f"{liunian.get('stem', '')}{liunian.get('branch', '')}"
                # ⚠️ 不去重：直接添加，同一年可能有多个关系
                special_liunians.append(liunian)
                liunian_ganzhi = liunian.get('ganzhi', f"{liunian.get('stem', '')}{liunian.get('branch', '')}")
                logger.debug(f"✅ [步骤1-流年查询] 发现特殊流年: {liunian_year}年 {liunian_ganzhi} - {relations} (大运{dayun_step})")
        
        elapsed_time = time.time() - start_time
        logger.info(f"⏱️ [性能优化] 流年筛选完成，耗时: {elapsed_time:.3f}秒，找到 {len(special_liunians)} 个特殊流年")
        
        # 按大运和年份排序
        special_liunians.sort(key=lambda x: (x.get('dayun_step', 0), x.get('year', 0)))
        
        total_elapsed = time.time() - start_time
        logger.info(f"✅ [步骤1-流年查询] 批量获取完成，共找到 {len(special_liunians)} 个特殊流年（不去重），总耗时: {total_elapsed:.3f}秒")
        
        # 记录前5个特殊流年详情（DEBUG级别）
        if special_liunians:
            logger.debug(f"📋 [步骤1-流年查询] 前5个特殊流年详情:")
            for liunian in special_liunians[:5]:
                logger.debug(f"   - {liunian.get('year')}年 {liunian.get('ganzhi')} (大运{liunian.get('dayun_step')}): {liunian.get('relations', [])}")
        
        # 4. 写入缓存（仅成功时）
        try:
            cache = get_multi_cache()
            cache.l2.ttl = 2592000  # 30天
            cache.set(cache_key, special_liunians)
            logger.info(f"✅ [缓存写入] SpecialLiunianService.get_special_liunians_batch: {cache_key[:50]}...")
        except Exception:
            pass  # 缓存写入失败不影响业务
        
        return special_liunians
    
    @staticmethod
    def format_special_liunians_for_prompt(
        special_liunians: List[Dict[str, Any]],
        dayun_sequence: List[Dict[str, Any]]
    ) -> str:
        """
        将特殊流年格式化为 Coze Bot 提示词格式
        
        Args:
            special_liunians: 特殊流年列表（来自 get_special_liunians_batch）
            dayun_sequence: 大运序列（可以是完整的 dayun_sequence 或 dayun_list）
            
        Returns:
            str: 格式化的提示词文本
        """
        if not special_liunians:
            return ""
        
        # 按大运分组
        dayun_groups = {}
        for liunian in special_liunians:
            step = liunian.get('dayun_step')
            if step is None:
                continue
            if step not in dayun_groups:
                dayun_groups[step] = []
            dayun_groups[step].append(liunian)
        
        if not dayun_groups:
            return ""
        
        # 创建大运映射（用于查找大运信息）
        dayun_map = {}
        for dayun in dayun_sequence:
            step = dayun.get('step')
            if step is not None:
                dayun_map[step] = dayun
        
        prompt_lines = []
        
        # 按大运分组输出
        sorted_steps = sorted(dayun_groups.keys())
        
        # 将大运分组（每2个大运一组，用于格式化输出）
        for i in range(0, len(sorted_steps), 2):
            steps_group = sorted_steps[i:i+2]
            
            # 获取大运信息
            dayuns_info = []
            age_ranges = []
            for step in steps_group:
                dayun = dayun_map.get(step)
                if dayun:
                    stem = dayun.get('stem', '')
                    branch = dayun.get('branch', '')
                    ganzhi = f"{stem}{branch}"
                    # 尝试从 age_range 获取年龄范围
                    age_range = dayun.get('age_range', {})
                    age_start = age_range.get('start', 0) if isinstance(age_range, dict) else 0
                    age_end = age_range.get('end', 0) if isinstance(age_range, dict) else 0
                    # 如果没有 age_range，尝试从 age_display 获取
                    if not age_start or not age_end:
                        age_display = dayun.get('age_display', '')
                        if age_display:
                            # 尝试解析 age_display（格式可能是 "X-X岁"）
                            import re
                            match = re.search(r'(\d+)-(\d+)', age_display)
                            if match:
                                age_start = int(match.group(1))
                                age_end = int(match.group(2))
                    dayuns_info.append(f"第{step}个大运")
                    if age_start and age_end:
                        age_ranges.append(f"{age_start}-{age_end}岁")
                else:
                    # 如果找不到大运信息，使用 step 作为标识
                    dayuns_info.append(f"第{step}个大运")
            
            # 构建标题
            if len(steps_group) == 2:
                if age_ranges:
                    title = f"**{age_ranges[0]}（{dayuns_info[0]}和{dayuns_info[1]}）：**"
                else:
                    title = f"**{dayuns_info[0]}和{dayuns_info[1]}：**"
            else:
                if age_ranges:
                    title = f"**{age_ranges[0]}（{dayuns_info[0]}）：**"
                else:
                    title = f"**{dayuns_info[0]}：**"
            
            prompt_lines.append(title)
            prompt_lines.append("")
            
            # 分析该大运的特征（简化版，实际应该从大运数据中提取）
            # 这里只输出关键年份，特征分析由 Coze Bot 完成
            prompt_lines.append("- **关键年份：**")
            
            # 输出该组大运的所有特殊流年
            for step in steps_group:
                liunians = dayun_groups[step]
                # 按年份排序
                liunians.sort(key=lambda x: x.get('year', 0))
                
                for liunian in liunians:
                    year = liunian.get('year', '')
                    ganzhi = liunian.get('ganzhi', '')
                    relations = liunian.get('relations', [])
                    
                    if year and ganzhi:
                        # ✅ 格式化关系描述（与 general_review_analysis.py 一致）
                        # relations 可能是字典列表或字符串列表
                        if relations:
                            if isinstance(relations[0], dict):
                                # 字典列表：提取 type 或 description
                                relations_str = '、'.join([
                                    r.get('type', r.get('description', '')) 
                                    for r in relations 
                                    if isinstance(r, dict)
                                ])
                            else:
                                # 字符串列表
                                relations_str = '、'.join([str(r) for r in relations])
                        else:
                            relations_str = '特殊关系'
                        prompt_lines.append(f"  - {year}年{ganzhi}：{relations_str}")
            
            prompt_lines.append("")
        
        return '\n'.join(prompt_lines)

