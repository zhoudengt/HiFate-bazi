#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字数据编排服务 - 统一管理所有数据模块的获取逻辑
支持并行计算、依赖解析、错误处理、大运模式筛选
"""

import sys
import os
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from server.services.wangshuai_service import WangShuaiService
from server.services.bazi_detail_service import BaziDetailService
from server.services.rule_service import RuleService
from server.services.health_analysis_service import HealthAnalysisService
from server.services.rizhu_liujiazi_service import RizhuLiujiaziService
from server.services.special_liunian_service import SpecialLiunianService
from server.services.daily_fortune_service import DailyFortuneService
from server.services.monthly_fortune_service import MonthlyFortuneService
from server.services.daily_fortune_calendar_service import DailyFortuneCalendarService
from server.services.wuxing_proportion_service import WuxingProportionService
from server.services.bazi_interface_service import BaziInterfaceService
from server.services.bazi_display_service import BaziDisplayService
from server.services.yigua_service import YiGuaService
from server.services.bazi_ai_service import BaziAIService
from server.services.liunian_enhanced_service import LiunianEnhancedService
from server.api.v1.xishen_jishen import get_xishen_jishen, XishenJishenRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.utils.data_validator import validate_bazi_data
from src.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
from server.config.mysql_config import get_mysql_connection, return_mysql_connection

# 配置日志
logger = logging.getLogger(__name__)


class BaziDataOrchestrator:
    """八字数据编排服务 - 统一管理所有数据模块的获取逻辑"""
    
    @staticmethod
    def _get_dayun_by_mode(
        dayun_sequence: List[Dict],
        current_time: datetime,
        birth_year: int,
        mode: Optional[str] = None,
        count: Optional[int] = None,
        indices: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        根据模式获取大运列表
        
        Args:
            dayun_sequence: 完整的大运序列
            current_time: 当前时间
            birth_year: 出生年份
            mode: 查询模式 ('count', 'current', 'current_with_neighbors', 'indices')
            count: 数量（仅用于 count 模式）
            indices: 索引列表（用于 indices 模式，如[1,2,3]表示第2-4步大运）
        
        Returns:
            筛选后的大运列表
        """
        if not dayun_sequence:
            return []
        
        # 1. 确定当前大运
        current_age = current_time.year - birth_year + 1  # 虚岁
        current_dayun_index = None
        
        for idx, dayun in enumerate(dayun_sequence):
            age_range = dayun.get('age_range', {})
            if age_range:
                age_start = age_range.get('start', 0)
                age_end = age_range.get('end', 0)
                if age_start <= current_age <= age_end:
                    current_dayun_index = idx
                    break
        
        # 2. 根据模式筛选
        if mode == 'current':
            # 仅当前大运
            if current_dayun_index is not None:
                return [dayun_sequence[current_dayun_index]]
            return []
        
        elif mode == 'current_with_neighbors':
            # 当前大运及前后各一个（共3个）
            if current_dayun_index is None:
                return []
            
            result = []
            # 前一个大运
            if current_dayun_index > 0:
                result.append(dayun_sequence[current_dayun_index - 1])
            # 当前大运
            result.append(dayun_sequence[current_dayun_index])
            # 后一个大运
            if current_dayun_index < len(dayun_sequence) - 1:
                result.append(dayun_sequence[current_dayun_index + 1])
            
            return result
        
        elif mode == 'indices' and indices:
            # 索引模式：返回指定索引的大运（如[1,2,3]表示第2-4步大运）
            result = []
            for idx in indices:
                if 0 <= idx < len(dayun_sequence):
                    result.append(dayun_sequence[idx])
            return result
        
        elif mode == 'count' or mode is None:
            # 数量模式：返回前N个大运
            count = count or 8  # 默认8个
            # ✅ 确保返回足够的大运（包括大运9，如果count>=9）
            return dayun_sequence[:count] if count <= len(dayun_sequence) else dayun_sequence
        
        return []
    
    @staticmethod
    async def fetch_data(
        solar_date: str,
        solar_time: str,
        gender: str,
        modules: Dict[str, Any],
        use_cache: bool = True,
        parallel: bool = True,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        根据模块配置获取数据
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            modules: 模块配置字典
            use_cache: 是否使用缓存
            parallel: 是否并行获取
            current_time: 当前时间（可选）
        
        Returns:
            dict: 包含所有请求模块的数据
        """
        if current_time is None:
            current_time = datetime.now()
        
        # 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, "solar", None, None, None
        )
        
        result = {}
        
        # 准备并行任务列表
        tasks = []
        loop = asyncio.get_event_loop()
        executor = None
        
        # 1. 基础模块（必需，并行获取）
        if modules.get('bazi') or modules.get('wangshuai') or modules.get('xishen_jishen') or modules.get('wuxing'):
            bazi_task = loop.run_in_executor(
                executor, BaziService.calculate_bazi_full,
                final_solar_date, final_solar_time, gender
            )
            wangshuai_task = loop.run_in_executor(
                executor, WangShuaiService.calculate_wangshuai,
                final_solar_date, final_solar_time, gender
            )
            # ✅ 修复：get_xishen_jishen 是异步函数，返回 XishenJishenResponse (Pydantic模型)
            # 需要转换为字典，但这里先获取响应对象，在结果处理时转换
            xishen_jishen_task = get_xishen_jishen(XishenJishenRequest(
                solar_date=final_solar_date,
                solar_time=final_solar_time,
                gender=gender,
                calendar_type="solar",
                location=None,
                latitude=None,
                longitude=None
            ))
            tasks.extend([
                ('bazi', bazi_task),
                ('wangshuai', wangshuai_task),
                ('xishen_jishen', xishen_jishen_task)
            ])
        
        # 2. 大运流年模块（需要基础八字数据）
        # ✅ 修复：支持 special_liunians（新命名）和 special_liunian（旧命名）
        # ✅ 修复：支持直接启用 detail 模块
        need_detail = (modules.get('detail') or modules.get('dayun') or modules.get('liunian') or modules.get('liuyue') or 
                       modules.get('special_liunian') or modules.get('special_liunians') or 
                       modules.get('fortune_display'))
        logger.info(f"[DEBUG] 检查是否需要 detail_task: need_detail={need_detail}, special_liunians={modules.get('special_liunians')}")
        if need_detail:
            detail_task = loop.run_in_executor(
                executor, BaziDetailService.calculate_detail_full,
                final_solar_date, final_solar_time, gender, current_time
            )
            tasks.append(('detail', detail_task))
            logger.info(f"[DEBUG] 已添加 detail_task 到 tasks")
        
        # 3. 规则匹配模块（需要基础八字数据，在获取基础数据后处理）
        # 注意：规则匹配需要在获取八字数据后才能执行，所以不在并行任务中
        
        # 4. 分析模块（需要基础八字数据）
        if modules.get('health'):
            health_task = loop.run_in_executor(
                executor, HealthAnalysisService.analyze,
                final_solar_date, final_solar_time, gender
            )
            tasks.append(('health', health_task))
        
        # personality 和 rizhu 需要在获取八字数据后才能执行，所以不在并行任务中
        
        if modules.get('wuxing_proportion'):
            wuxing_proportion_task = loop.run_in_executor(
                executor, WuxingProportionService.calculate_proportion,
                final_solar_date, final_solar_time, gender
            )
            tasks.append(('wuxing_proportion', wuxing_proportion_task))
        
        if modules.get('liunian_enhanced'):
            liunian_enhanced_task = loop.run_in_executor(
                executor, LiunianEnhancedService.analyze_liunian_enhanced,
                final_solar_date, final_solar_time, gender, None, 10
            )
            tasks.append(('liunian_enhanced', liunian_enhanced_task))
        
        # 5. 辅助模块（需要基础八字数据）
        if modules.get('shengong_minggong'):
            interface_task = loop.run_in_executor(
                executor, BaziInterfaceService.generate_interface_full,
                final_solar_date, final_solar_time, gender
            )
            tasks.append(('interface', interface_task))
        
        if modules.get('fortune_display'):
            # 已经在 detail 中获取，这里不需要单独获取
            pass
        
        # 6. 运势模块
        if modules.get('daily_fortune'):
            daily_fortune_task = loop.run_in_executor(
                executor, DailyFortuneService.calculate_daily_fortune,
                final_solar_date, final_solar_time, gender
            )
            tasks.append(('daily_fortune', daily_fortune_task))
        
        if modules.get('monthly_fortune'):
            monthly_fortune_task = loop.run_in_executor(
                executor, MonthlyFortuneService.calculate_monthly_fortune,
                final_solar_date, final_solar_time, gender
            )
            tasks.append(('monthly_fortune', monthly_fortune_task))
        
        # 7. 其他模块
        if modules.get('yigua'):
            # YiGuaService.divinate 需要 question 参数，这里使用默认问题
            yigua_question = modules['yigua'].get('question', '占卜') if isinstance(modules['yigua'], dict) else '占卜'
            yigua_task = loop.run_in_executor(
                executor, YiGuaService.divinate,
                yigua_question, current_time
            )
            tasks.append(('yigua', yigua_task))
        
        if modules.get('bazi_ai'):
            ai_question = modules['bazi_ai'].get('question') if isinstance(modules.get('bazi_ai'), dict) else None
            ai_task = loop.run_in_executor(
                executor, BaziAIService.analyze_bazi_with_ai,
                final_solar_date, final_solar_time, gender, ai_question, None, None, None, True
            )
            tasks.append(('bazi_ai', ai_task))
        
        # 执行并行任务
        logger.info(f"[DEBUG] 执行并行任务: parallel={parallel}, tasks数量={len(tasks)}, task_names={[name for name, _ in tasks]}")
        if parallel and tasks:
            task_results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            logger.info(f"[DEBUG] 并行任务完成，结果数量={len(task_results)}")
            
            # 处理任务结果
            task_data = {}
            for (name, _), task_result in zip(tasks, task_results):
                # ✅ 修复：使用 task_result 而不是 result，避免覆盖外层的 result 字典
                if isinstance(task_result, Exception):
                    logger.error(f"获取 {name} 数据失败: {task_result}")
                    task_data[name] = None
                else:
                    # ✅ 修复：如果是 Pydantic 模型（如 XishenJishenResponse），立即转换为字典
                    try:
                        if hasattr(task_result, 'model_dump'):
                            # Pydantic v2（优先使用）
                            task_data[name] = task_result.model_dump()
                        elif hasattr(task_result, 'dict'):
                            # Pydantic v1（向后兼容）
                            task_data[name] = task_result.dict()
                        else:
                            task_data[name] = task_result
                    except Exception as e:
                        logger.error(f"转换 {name} 数据失败: {e}, 类型: {type(task_result)}")
                        # 如果转换失败，尝试直接使用（可能是其他类型）
                        task_data[name] = task_result
        else:
            # 串行执行
            task_data = {}
            for name, task in tasks:
                try:
                    if asyncio.iscoroutine(task):
                        result = await task
                    else:
                        result = await task
                    
                    # ✅ 修复：如果是 Pydantic 模型（如 XishenJishenResponse），立即转换为字典
                    if hasattr(result, 'model_dump'):
                        # Pydantic v2（优先使用）
                        task_data[name] = result.model_dump()
                    elif hasattr(result, 'dict'):
                        # Pydantic v1（向后兼容）
                        task_data[name] = result.dict()
                    else:
                        task_data[name] = result
                except Exception as e:
                    logger.error(f"获取 {name} 数据失败: {e}")
                    task_data[name] = None
        
        # 提取基础数据
        bazi_data = task_data.get('bazi')
        logger.info(f"[DEBUG 基础数据提取] bazi_data存在={bazi_data is not None}, type={type(bazi_data) if bazi_data else None}")
        if bazi_data:
            logger.info(f"[DEBUG 基础数据提取] bazi_data keys={list(bazi_data.keys()) if isinstance(bazi_data, dict) else 'Not dict'}")
            bazi_data = validate_bazi_data(bazi_data)
            logger.info(f"[DEBUG 基础数据提取] validate后 bazi_data keys={list(bazi_data.keys()) if isinstance(bazi_data, dict) else 'Not dict'}")
            result['bazi'] = bazi_data
        
        wangshuai_data = task_data.get('wangshuai')
        if wangshuai_data:
            result['wangshuai'] = wangshuai_data
        
        xishen_jishen_data = task_data.get('xishen_jishen')
        if xishen_jishen_data:
            # ✅ 修复：确保 XishenJishenResponse 转换为字典
            # 双重保险：即使 gather 时已转换，这里再次检查
            if isinstance(xishen_jishen_data, dict):
                result['xishen_jishen'] = xishen_jishen_data
            else:
                # 如果仍然是 Pydantic 模型，立即转换
                if hasattr(xishen_jishen_data, 'model_dump'):
                    result['xishen_jishen'] = xishen_jishen_data.model_dump()
                elif hasattr(xishen_jishen_data, 'dict'):
                    result['xishen_jishen'] = xishen_jishen_data.dict()
                else:
                    # 如果都不是，尝试直接使用（可能是其他类型）
                    result['xishen_jishen'] = xishen_jishen_data
        
        # 提取五行数据
        if modules.get('wuxing') and bazi_data:
            wuxing_data = {
                'elements': bazi_data.get('elements', {}),
                'element_counts': bazi_data.get('element_counts', {})
            }
            result['wuxing'] = wuxing_data
        
        # 处理大运流年数据
        detail_data = task_data.get('detail')
        logger.info(f"[DEBUG] detail_data 获取结果: detail_data存在={detail_data is not None}, task_data的键={list(task_data.keys())}")
        
        # ✅ 修复：如果启用了 special_liunians 但 detail_data 不存在，需要先获取 detail_data
        if (modules.get('special_liunian') or modules.get('special_liunians')) and not detail_data:
            # 需要获取 detail_data 以获取 dayun_sequence
            logger.info("special_liunians 已启用但 detail_data 不存在，开始获取 detail_data")
            detail_task = loop.run_in_executor(
                executor, BaziDetailService.calculate_detail_full,
                final_solar_date, final_solar_time, gender, current_time
            )
            detail_data = await detail_task
            task_data['detail'] = detail_data
            # ✅ 修复：检查 detail_data 的结构
            if detail_data:
                if 'details' in detail_data:
                    dayun_count = len(detail_data.get('details', {}).get('dayun_sequence', []))
                else:
                    dayun_count = len(detail_data.get('dayun_sequence', []))
                logger.info(f"detail_data 获取成功，dayun_sequence 数量: {dayun_count}")
            else:
                logger.warning("detail_data 获取失败，返回 None")
        
        if detail_data:
            # ✅ 修复：detail_data 同时包含顶层和 details 中的 dayun_sequence
            # 优先使用顶层的 dayun_sequence（更完整），如果没有则使用 details 中的
            if isinstance(detail_data, dict):
                # 优先使用顶层的 dayun_sequence
                dayun_sequence = detail_data.get('dayun_sequence', [])
                liunian_sequence = detail_data.get('liunian_sequence', [])
                
                # 如果顶层没有，则从 details 中获取
                if not dayun_sequence and 'details' in detail_data:
                    dayun_sequence = detail_data.get('details', {}).get('dayun_sequence', [])
                if not liunian_sequence and 'details' in detail_data:
                    liunian_sequence = detail_data.get('details', {}).get('liunian_sequence', [])
            else:
                dayun_sequence = []
                liunian_sequence = []
            
            # 处理大运
            if modules.get('dayun'):
                dayun_config = modules['dayun']
                if isinstance(dayun_config, dict):
                    mode = dayun_config.get('mode')
                    count = dayun_config.get('count')
                    indices = dayun_config.get('indices')
                else:
                    mode = 'count'
                    count = 8
                    indices = None
                
                # 获取出生年份
                birth_year = int(final_solar_date.split('-')[0])
                
                # 根据模式筛选大运
                filtered_dayun = BaziDataOrchestrator._get_dayun_by_mode(
                    dayun_sequence, current_time, birth_year, mode, count, indices
                )
                result['dayun'] = filtered_dayun
            else:
                result['dayun'] = dayun_sequence
            
            # ✅ 修复：确保每个大运包含其下的流年序列
            # 如果大运数据中包含 liunian_sequence，保留它；否则根据年份范围从全局流年序列中提取
            if result.get('dayun'):
                for dayun in result['dayun']:
                    if 'liunian_sequence' not in dayun or not dayun.get('liunian_sequence'):
                        # 如果大运中没有流年序列，从全局流年序列中提取
                        year_start = dayun.get('year_start', 0)
                        year_end = dayun.get('year_end', 0)
                        dayun_liunians = [
                            l for l in liunian_sequence
                            if year_start <= l.get('year', 0) <= year_end
                        ]
                        dayun['liunian_sequence'] = dayun_liunians
            
            # 处理流年
            if modules.get('liunian'):
                liunian_count = modules['liunian'].get('count', 10) if isinstance(modules['liunian'], dict) else 10
                result['liunian'] = liunian_sequence[:liunian_count] if liunian_sequence else []
            else:
                result['liunian'] = liunian_sequence
            
            # 处理流月
            if modules.get('liuyue'):
                liuyue_count = modules['liuyue'].get('count', 12) if isinstance(modules['liuyue'], dict) else 12
                liuyue_sequence = detail_data.get('liuyue_sequence', [])
                result['liuyue'] = liuyue_sequence[:liuyue_count] if liuyue_sequence else []
            
            # ✅ 处理特殊流年（确保按大运分组，格式与 general_review_analysis.py 一致）
            if modules.get('special_liunian') or modules.get('special_liunians'):
                # 支持两种命名：special_liunian 和 special_liunians
                special_config = modules.get('special_liunian') or modules.get('special_liunians', {})
                
                logger.info(f"[DEBUG] 特殊流年处理: dayun_sequence总数={len(dayun_sequence)}, special_config={special_config}")
                
                # ✅ 获取目标大运（根据 dayun_config 或使用前N个大运）
                target_dayuns = dayun_sequence
                special_count = 8  # 默认值
                if 'dayun_config' in special_config:
                    dayun_config = special_config['dayun_config']
                    if isinstance(dayun_config, dict):
                        mode = dayun_config.get('mode', 'count')
                        count = dayun_config.get('count', 8)
                        special_count = count  # ✅ 使用 dayun_config 中的 count
                        indices = dayun_config.get('indices')
                        birth_year = int(final_solar_date.split('-')[0])
                        logger.info(f"[DEBUG] _get_dayun_by_mode调用: mode={mode}, count={count}, dayun_sequence长度={len(dayun_sequence)}")
                        target_dayuns = BaziDataOrchestrator._get_dayun_by_mode(
                            dayun_sequence, current_time, birth_year, mode, count, indices
                        )
                        logger.info(f"[DEBUG] target_dayuns结果: 长度={len(target_dayuns)}, 大运步数={[d.get('step') for d in target_dayuns]}")
                else:
                    # 如果没有 dayun_config，使用 special_config 中的 count
                    special_count = special_config.get('count', 8) if isinstance(special_config, dict) else 8
                
                # ✅ 获取特殊流年（确保每个大运都完整获取，不去重）
                logger.info(f"[DEBUG] 调用get_special_liunians_batch: target_dayuns长度={len(target_dayuns)}, 大运步数={[d.get('step') for d in target_dayuns]}, special_count={special_count}")
                special_liunians = await SpecialLiunianService.get_special_liunians_batch(
                    final_solar_date, final_solar_time, gender,
                    target_dayuns, special_count, current_time
                )
                logger.info(f"[DEBUG] get_special_liunians_batch返回: 特殊流年数量={len(special_liunians)}, 大运步数={set(l.get('dayun_step') for l in special_liunians)}")
                
                # ✅ 按大运分组，确保格式与 general_review_analysis.py 一致
                # 格式：{dayun_step: [liunian1, liunian2, ...]}
                special_liunians_by_dayun = {}
                for liunian in special_liunians:
                    dayun_step = liunian.get('dayun_step')
                    if dayun_step is not None:
                        if dayun_step not in special_liunians_by_dayun:
                            special_liunians_by_dayun[dayun_step] = []
                        special_liunians_by_dayun[dayun_step].append(liunian)
                
                # ✅ 同时提供三种格式：
                # 1. 原始列表格式（用于兼容）
                # 2. 按大运分组格式（用于确保每个大运的特殊流年都完整）
                # 3. 格式化后的提示词（与 general_review_analysis.py 一致，用于 Coze Bot）
                result['special_liunians'] = {
                    'list': special_liunians,  # 原始列表（不去重）
                    'by_dayun': special_liunians_by_dayun,  # 按大运分组（确保完整）
                    'formatted': SpecialLiunianService.format_special_liunians_for_prompt(
                        special_liunians, dayun_sequence
                    ) if special_liunians else ""  # 格式化后的提示词（与 general_review_analysis.py 一致）
                }
            
            # 处理大运流年流月统一展示
            if modules.get('fortune_display'):
                fortune_display = BaziDisplayService.get_fortune_display(
                    final_solar_date, final_solar_time, gender, current_time
                )
                result['fortune_display'] = fortune_display
        
        # 处理规则匹配（需要八字数据，在获取基础数据后执行）
        if modules.get('rules') and bazi_data:
            rule_types = modules['rules'].get('types', [])
            if rule_types:
                # 准备规则匹配数据
                rule_data = {
                    'bazi_pillars': bazi_data.get('bazi_pillars', {}),
                    'ten_gods': bazi_data.get('ten_gods', {}),
                    'elements': bazi_data.get('elements', {}),
                    'wangshuai': wangshuai_data.get('wangshuai', '') if wangshuai_data else '',
                    'gender': gender
                }
                
                # RuleService 内部已经处理了连接池，直接调用即可
                matched_rules = []
                try:
                    matched_rules = RuleService.match_rules(
                        rule_data, rule_types, use_cache=use_cache
                    )
                except Exception as e:
                    logger.error(f"规则匹配失败: {e}")
                
                result['rules'] = matched_rules
        
        # 处理分析模块
        if modules.get('health'):
            result['health'] = task_data.get('health')
        
        if modules.get('personality') and bazi_data:
            # RizhuGenderAnalyzer 需要先创建实例
            # ⚠️ 修复：bazi_data 可能是嵌套结构，需要从 bazi_data['bazi'] 中提取
            inner_bazi_data = bazi_data.get('bazi', bazi_data) if isinstance(bazi_data, dict) and 'bazi' in bazi_data else bazi_data
            bazi_pillars = inner_bazi_data.get('bazi_pillars', {})
            analyzer = RizhuGenderAnalyzer(bazi_pillars, gender)
            personality_result = analyzer.analyze_rizhu_gender()
            result['personality'] = personality_result
        
        logger.info(f"[DEBUG 模块处理] modules.get('rizhu')={modules.get('rizhu')}, bazi_data存在={bazi_data is not None}")
        if modules.get('rizhu') and bazi_data:
            # RizhuLiujiaziService.get_rizhu_analysis 需要日柱字符串
            # ⚠️ 修复：bazi_data 可能是嵌套结构 {bazi: {...}, rizhu: "庚寅", matched_rules: [...]}
            # 需要从 bazi_data['bazi'] 中提取 bazi_pillars
            logger.info(f"[DEBUG rizhu模块] bazi_data type={type(bazi_data)}, has 'bazi' key={'bazi' in bazi_data if isinstance(bazi_data, dict) else False}")
            inner_bazi_data = bazi_data.get('bazi', bazi_data) if isinstance(bazi_data, dict) and 'bazi' in bazi_data else bazi_data
            logger.info(f"[DEBUG rizhu模块] inner_bazi_data keys={list(inner_bazi_data.keys()) if isinstance(inner_bazi_data, dict) else 'Not dict'}")
            bazi_pillars = inner_bazi_data.get('bazi_pillars', {})
            logger.info(f"[DEBUG rizhu模块] bazi_pillars={bazi_pillars}")
            day_pillar = bazi_pillars.get('day', {})
            logger.info(f"[DEBUG rizhu模块] day_pillar={day_pillar}")
            rizhu = f"{day_pillar.get('stem', '')}{day_pillar.get('branch', '')}"
            logger.info(f"[DEBUG rizhu模块] rizhu={rizhu}")
            if rizhu and rizhu != '':  # ⚠️ 确保日柱不为空
                rizhu_result = RizhuLiujiaziService.get_rizhu_analysis(rizhu)
                logger.info(f"[DEBUG rizhu模块] rizhu_result type={type(rizhu_result)}, has data={rizhu_result is not None}")
                if rizhu_result:
                    result['rizhu'] = rizhu_result
                else:
                    result['rizhu'] = None
            else:
                logger.warning(f"[DEBUG rizhu模块] rizhu为空，跳过")
                result['rizhu'] = None
        
        if modules.get('wuxing_proportion'):
            result['wuxing_proportion'] = task_data.get('wuxing_proportion')
        
        if modules.get('liunian_enhanced'):
            liunian_enhanced_data = task_data.get('liunian_enhanced')
            if liunian_enhanced_data and isinstance(liunian_enhanced_data, dict):
                result['liunian_enhanced'] = liunian_enhanced_data.get('data', liunian_enhanced_data)
            else:
                result['liunian_enhanced'] = liunian_enhanced_data
        
        # 处理辅助模块（从基础数据中提取）
        if modules.get('deities') and bazi_data:
            deities = {}
            for pillar_type in ['year', 'month', 'day', 'hour']:
                pillar_details = bazi_data.get('details', {}).get(pillar_type, {})
                deities[pillar_type] = pillar_details.get('deities', [])
            result['deities'] = deities
        
        if modules.get('branch_relations') and bazi_data:
            branch_relations = bazi_data.get('relationships', {}).get('branch_relations', {})
            result['branch_relations'] = branch_relations
        
        if modules.get('career_star') and bazi_data:
            ten_gods = bazi_data.get('ten_gods', {})
            # 提取事业星（正官、七杀等）
            career_stars = []
            for pillar_type in ['year', 'month', 'day', 'hour']:
                main_star = ten_gods.get(pillar_type, {}).get('main_star', '')
                if main_star in ['正官', '七杀']:
                    career_stars.append({
                        'pillar': pillar_type,
                        'star': main_star
                    })
            result['career_star'] = career_stars
        
        if modules.get('wealth_star') and bazi_data:
            ten_gods = bazi_data.get('ten_gods', {})
            # 提取财富星（正财、偏财等）
            wealth_stars = []
            for pillar_type in ['year', 'month', 'day', 'hour']:
                main_star = ten_gods.get(pillar_type, {}).get('main_star', '')
                if main_star in ['正财', '偏财']:
                    wealth_stars.append({
                        'pillar': pillar_type,
                        'star': main_star
                    })
            result['wealth_star'] = wealth_stars
        
        if modules.get('children_star') and bazi_data:
            ten_gods = bazi_data.get('ten_gods', {})
            # 提取子女星（食神、伤官等）
            children_stars = []
            for pillar_type in ['year', 'month', 'day', 'hour']:
                main_star = ten_gods.get(pillar_type, {}).get('main_star', '')
                if main_star in ['食神', '伤官']:
                    children_stars.append({
                        'pillar': pillar_type,
                        'star': main_star
                    })
            result['children_star'] = children_stars
        
        if modules.get('shengong_minggong'):
            interface_data = task_data.get('interface')
            if interface_data:
                result['shengong_minggong'] = {
                    'minggong': interface_data.get('minggong', {}),
                    'shengong': interface_data.get('shengong', {}),
                    'taiyuan': interface_data.get('taiyuan', {}),
                    'taixi': interface_data.get('taixi', {})
                }
        
        # 处理运势模块
        if modules.get('daily_fortune'):
            result['daily_fortune'] = task_data.get('daily_fortune')
        
        if modules.get('monthly_fortune'):
            result['monthly_fortune'] = task_data.get('monthly_fortune')
        
        if modules.get('daily_fortune_calendar'):
            calendar_data = DailyFortuneCalendarService.get_daily_fortune_calendar(
                final_solar_date, final_solar_time, gender
            )
            result['daily_fortune_calendar'] = calendar_data
        
        # 处理其他模块
        if modules.get('yigua'):
            result['yigua'] = task_data.get('yigua')
        
        if modules.get('bazi_interface'):
            result['bazi_interface'] = task_data.get('interface')
        
        if modules.get('bazi_ai'):
            result['bazi_ai'] = task_data.get('bazi_ai')
        
        # ✅ 处理 detail 模块：如果启用了 detail 模块，返回完整的 detail_data
        if modules.get('detail') and detail_data:
            result['detail'] = detail_data
        
        return result

