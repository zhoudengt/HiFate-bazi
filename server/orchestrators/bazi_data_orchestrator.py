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
from server.services.bazi_ai_service import BaziAIService
# 注意：get_xishen_jishen 和 XishenJishenRequest 延迟导入，避免循环依赖
# from server.api.v1.xishen_jishen import get_xishen_jishen, XishenJishenRequest
from server.utils.bazi_input_processor import BaziInputProcessor
from server.utils.data_validator import validate_bazi_data
from core.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
from shared.config.database import get_mysql_connection, return_mysql_connection
from core.data.constants import STEM_ELEMENTS, BRANCH_ELEMENTS
from server.services.config_service import ConfigService
from server.services.mingge_extractor import extract_mingge_names_from_rules
from server.utils.async_executor import get_executor

# 配置日志
logger = logging.getLogger(__name__)

# 编排层并行度控制：最多 24 个并行任务（从 8 提升以支持高并发场景）
# 8 个 Uvicorn worker 共享此信号量（进程隔离，每个 worker 独立一份）
_ORCHESTRATOR_SEMAPHORE = asyncio.Semaphore(24)


async def _fetch_with_semaphore(coro):
    """在信号量限制下执行单个异步任务"""
    async with _ORCHESTRATOR_SEMAPHORE:
        return await coro


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
        current_time: Optional[datetime] = None,
        calendar_type: Optional[str] = "solar",
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        preprocessed: bool = False,
        dayun_index: Optional[int] = None,
        dayun_year_start: Optional[int] = None,
        dayun_year_end: Optional[int] = None,
        target_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        根据模块配置获取数据（支持7个标准参数 + 大运范围）
        
        Args:
            solar_date: 阳历日期或农历日期
            solar_time: 出生时间
            gender: 性别
            modules: 模块配置字典
            use_cache: 是否使用缓存
            parallel: 是否并行获取
            current_time: 当前时间（可选）
            calendar_type: 历法类型（solar/lunar），默认solar
            location: 出生地点（可选，用于时区转换）
            latitude: 纬度（可选，用于时区转换）
            longitude: 经度（可选，用于时区转换和真太阳时计算）
            preprocessed: 如果为True，表示solar_date和solar_time已经过process_input处理，跳过重复处理
            dayun_index: 大运索引（可选），指定要计算的大运，仅该大运有流年序列
            dayun_year_start: 大运起始年份（可选），与 dayun_year_end 一起用于解析 dayun_index
            dayun_year_end: 大运结束年份（可选）
            target_year: 目标年份（可选），用于流月
        
        Returns:
            dict: 包含所有请求模块的数据
        """
        if current_time is None:
            current_time = datetime.now()
        
        # ✅ 优化：使用缓存（如果启用），key 含 current_time 与 dayun 范围
        if use_cache:
            try:
                from server.utils.cache_key_generator import CacheKeyGenerator
                from server.utils.cache_multi_level import get_multi_cache
                
                cache_key = CacheKeyGenerator.generate_orchestrator_key(
                    solar_date, solar_time, gender, modules,
                    calendar_type, location, latitude, longitude,
                    current_time=current_time,
                    dayun_index=dayun_index,
                    dayun_year_start=dayun_year_start,
                    dayun_year_end=dayun_year_end,
                    target_year=target_year
                )
                
                cache = get_multi_cache()
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info(f"[BaziDataOrchestrator] 缓存命中: {cache_key[:50]}...")
                    return cached_result
            except Exception as e:
                logger.warning(f"[BaziDataOrchestrator] 缓存查询失败（降级到数据库）: {e}")
        
        # 处理输入（农历转换和时区转换）- 如果已预处理则跳过
        if preprocessed:
            final_solar_date, final_solar_time = solar_date, solar_time
        else:
            final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
                solar_date, solar_time, calendar_type or "solar", location, latitude, longitude
            )
        
        result = {}
        
        # =====================================================================
        # ✅ 自动依赖推导：衍生模块隐式依赖基础模块
        # daily_fortune_calendar 依赖 bazi（提取 birth_stem）和 wangshuai（判断喜用）
        # =====================================================================
        if modules.get('daily_fortune_calendar') and final_solar_date and final_solar_time and gender:
            if not modules.get('bazi'):
                modules['bazi'] = True  # 隐式依赖
                logger.debug("[Orchestrator] daily_fortune_calendar 自动依赖 bazi")
            if not modules.get('wangshuai'):
                modules['wangshuai'] = True  # 隐式依赖
                logger.debug("[Orchestrator] daily_fortune_calendar 自动依赖 wangshuai")
        
        # 准备并行任务列表
        tasks = []
        loop = asyncio.get_event_loop()
        executor = get_executor()  # 使用全局线程池，统一管理
        
        # 1. 基础模块（必需，并行获取）
        # ✅ 优化：bazi/wangshuai 与 xishen_jishen 分离，仅请求 wuxing_proportion 时不启动喜神忌神任务
        need_bazi = (modules.get('bazi') or modules.get('wangshuai') or
                    modules.get('wuxing_proportion') or modules.get('wuxing'))
        need_xishen_jishen = modules.get('xishen_jishen')

        if need_bazi:
            bazi_task = loop.run_in_executor(
                executor, BaziService.calculate_bazi_full,
                final_solar_date, final_solar_time, gender
            )
            wangshuai_task = loop.run_in_executor(
                executor, WangShuaiService.calculate_wangshuai,
                final_solar_date, final_solar_time, gender
            )
            tasks.extend([
                ('bazi', bazi_task),
                ('wangshuai', wangshuai_task)
            ])

        if need_xishen_jishen:
            # ✅ 修复：get_xishen_jishen 是异步函数，返回 XishenJishenResponse (Pydantic模型)
            # 需要转换为字典，但这里先获取响应对象，在结果处理时转换
            # ✅ 扩展：支持7个标准参数
            # ✅ 延迟导入，避免循环依赖
            from server.api.v1.xishen_jishen import get_xishen_jishen, XishenJishenRequest
            xishen_jishen_task = get_xishen_jishen(XishenJishenRequest(
                solar_date=final_solar_date,
                solar_time=final_solar_time,
                gender=gender,
                calendar_type=calendar_type or "solar",
                location=location,
                latitude=latitude,
                longitude=longitude
            ))
            tasks.append(('xishen_jishen', xishen_jishen_task))
        
        # 2. 大运流年模块（需要基础八字数据）
        # ✅ 修复：支持 special_liunians（新命名）和 special_liunian（旧命名）
        # ✅ 修复：支持直接启用 detail 模块
        need_detail = (modules.get('detail') or modules.get('dayun') or modules.get('liunian') or modules.get('liuyue') or 
                       modules.get('special_liunian') or modules.get('special_liunians') or 
                       modules.get('fortune_display') or modules.get('fortune_context'))
        logger.debug(f"[Orchestrator] 检查是否需要 detail_task: need_detail={need_detail}, special_liunians={modules.get('special_liunians')}")
        if need_detail:
            # ✅ 与上一版一致：quick_mode=True；支持 dayun_index 指定大运（切换大运时一次调用）
            # 传参顺序：solar_date, solar_time, gender, current_time, dayun_index, target_year, quick_mode, async_warmup
            resolved_dayun_index = dayun_index  # 若仅传 year_start/end，在拿到 detail 后再解析并可能二次调用
            detail_task = loop.run_in_executor(
                executor, BaziDetailService.calculate_detail_full,
                final_solar_date, final_solar_time, gender, current_time,
                resolved_dayun_index,
                target_year,
                True,   # quick_mode=True
                False   # async_warmup
            )
            tasks.append(('detail', detail_task))
            logger.debug(f"[Orchestrator] 已添加 detail_task 到 tasks (quick_mode=True, dayun_index={resolved_dayun_index})")
        
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
        
        # 五行占比：当已请求 bazi 或 wangshuai 时，不再单独起 wuxing_proportion 任务，
        # 后续用 bazi + wangshuai 组装（_assemble_wuxing_proportion_from_data），避免重复计算、提升首包速度
        if modules.get('wuxing_proportion') and not (modules.get('bazi') or modules.get('wangshuai')):
            wuxing_proportion_task = loop.run_in_executor(
                executor, WuxingProportionService.calculate_proportion,
                final_solar_date, final_solar_time, gender
            )
            tasks.append(('wuxing_proportion', wuxing_proportion_task))
        
        # 5. 辅助模块（需要基础八字数据）
        if modules.get('shengong_minggong'):
            # ✅ 扩展：支持7个标准参数
            interface_task = loop.run_in_executor(
                executor, BaziInterfaceService.generate_interface_full,
                final_solar_date, final_solar_time, gender,
                "",  # name
                location or "未知地",  # location
                latitude or 39.00,  # latitude
                longitude or 120.00  # longitude
            )
            tasks.append(('interface', interface_task))
        
        if modules.get('fortune_display'):
            # ✅ 扩展：使用 BaziDataService.get_fortune_display（支持7个标准参数）
            # 注意：fortune_display 通常从 detail 中获取，但如果需要单独获取，使用 BaziDataService
            from server.orchestrators.bazi_data_service import BaziDataService
            fortune_display_task = BaziDataService.get_fortune_display(
                final_solar_date, final_solar_time, gender,
                calendar_type or "solar",
                location, latitude, longitude,
                current_time
            )
            tasks.append(('fortune_display', fortune_display_task))
        
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
        
        # ✅ daily_fortune_calendar 已移到阶段2（依赖 bazi_data + wangshuai_data）
        # 不再在阶段1独立计算，避免内部重复调用 BaziService/WangShuaiService
        # 详见下方阶段2的 daily_fortune_calendar 处理逻辑
        
        # 7. 其他模块
        if modules.get('bazi_ai'):
            ai_question = modules['bazi_ai'].get('question') if isinstance(modules.get('bazi_ai'), dict) else None
            ai_task = loop.run_in_executor(
                executor, BaziAIService.analyze_bazi_with_ai,
                final_solar_date, final_solar_time, gender, ai_question, None, None, None, True
            )
            tasks.append(('bazi_ai', ai_task))
        
        # 执行阶段1并行任务（带超时保护，防止单个任务卡住拖垮整个请求）
        _PHASE1_TIMEOUT = 15  # 阶段1超时15秒（含 bazi 计算 + detail 计算）
        logger.debug(f"[Orchestrator] 执行阶段1并行任务: parallel={parallel}, tasks数量={len(tasks)}, task_names={[name for name, _ in tasks]}")
        if parallel and tasks:
            wrapped = [_fetch_with_semaphore(task) for _, task in tasks]
            try:
                task_results = await asyncio.wait_for(
                    asyncio.gather(*wrapped, return_exceptions=True),
                    timeout=_PHASE1_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.error(f"[Orchestrator] 阶段1并行任务超时（{_PHASE1_TIMEOUT}s），返回已完成的数据")
                task_results = [asyncio.TimeoutError(f"Phase1 timeout after {_PHASE1_TIMEOUT}s")] * len(tasks)
            logger.debug(f"[Orchestrator] 阶段1并行任务完成，结果数量={len(task_results)}")
            
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
        logger.debug(f"[Orchestrator] bazi_data存在={bazi_data is not None}")
        if bazi_data:
            bazi_data = validate_bazi_data(bazi_data)
            # 处理嵌套结构：bazi_data 可能是 {bazi: {...}, rizhu: "...", matched_rules: [...]}
            if isinstance(bazi_data, dict) and 'bazi' in bazi_data:
                result['bazi'] = bazi_data
                # 提取内部 bazi 数据用于后续组装
                inner_bazi_data = bazi_data.get('bazi', {})
            else:
                result['bazi'] = bazi_data
                inner_bazi_data = bazi_data
        else:
            inner_bazi_data = None
        
        wangshuai_data = task_data.get('wangshuai')
        if wangshuai_data:
            result['wangshuai'] = wangshuai_data
        
        # 注意：喜神忌神模块的处理需要在 rules 处理之后，因为需要 rules 数据
        # 所以这里先保存接口调用结果，在 rules 处理后再进行组装
        xishen_jishen_data_from_task = task_data.get('xishen_jishen')
        
        # 提取五行数据
        if modules.get('wuxing') and bazi_data:
            wuxing_data = {
                'elements': bazi_data.get('elements', {}),
                'element_counts': bazi_data.get('element_counts', {})
            }
            result['wuxing'] = wuxing_data
        
        # 处理大运流年数据
        detail_data = task_data.get('detail')
        logger.debug(f"[Orchestrator] detail_data存在={detail_data is not None}")
        
        # ✅ 修复：如果启用了 special_liunians 但 detail_data 不存在，需要先获取 detail_data
        if (modules.get('special_liunian') or modules.get('special_liunians')) and not detail_data:
            # 需要获取 detail_data 以获取 dayun_sequence
            logger.debug("special_liunians 已启用但 detail_data 不存在，开始获取 detail_data")
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
                logger.debug(f"detail_data 获取成功，dayun_sequence 数量: {dayun_count}")
            else:
                logger.warning("detail_data 获取失败，返回 None")
        
        # ✅ 若仅传 dayun_year_start/end 未传 dayun_index，从首轮 detail 解析 step，若非当前大运则二次调用
        if detail_data and dayun_index is None and dayun_year_start is not None and dayun_year_end is not None:
            ds = detail_data.get('dayun_sequence') or (detail_data.get('details') or {}).get('dayun_sequence') or []
            birth_year = int(final_solar_date.split('-')[0])
            current_year = current_time.year
            current_step = None
            target_step = None
            for d in ds:
                ys, ye = d.get('year_start'), d.get('year_end')
                if ys is not None and ye is not None:
                    if ys <= current_year <= ye:
                        current_step = d.get('step')
                    if dayun_year_start == ys and dayun_year_end == ye:
                        target_step = d.get('step')
                        break
                    if ys <= dayun_year_start <= ye:
                        target_step = d.get('step')
                        break
            if target_step is not None and target_step != current_step:
                detail_task_2 = loop.run_in_executor(
                    executor, BaziDetailService.calculate_detail_full,
                    final_solar_date, final_solar_time, gender, current_time,
                    target_step, target_year, True, False
                )
                detail_data = await detail_task_2
                task_data['detail'] = detail_data
                logger.debug(f"[Orchestrator] 按年份范围二次获取大运流年: dayun_index={target_step}")
        
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
                
                logger.debug(f"[Orchestrator] 特殊流年处理: dayun_sequence总数={len(dayun_sequence)}")
                
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
                        logger.debug(f"[Orchestrator] _get_dayun_by_mode: mode={mode}, count={count}")
                        target_dayuns = BaziDataOrchestrator._get_dayun_by_mode(
                            dayun_sequence, current_time, birth_year, mode, count, indices
                        )
                        logger.debug(f"[Orchestrator] target_dayuns: 长度={len(target_dayuns)}")
                else:
                    # 如果没有 dayun_config，使用 special_config 中的 count
                    special_count = special_config.get('count', 8) if isinstance(special_config, dict) else 8
                
                # ✅ 获取特殊流年（确保每个大运都完整获取，不去重）
                # ✅ 架构规范：传入已计算的 liunian_sequence，避免 SpecialLiunianService 重复计算
                # 详见：standards/08_数据编排架构规范.md
                logger.debug(f"[Orchestrator] get_special_liunians_batch: target_dayuns={len(target_dayuns)}, special_count={special_count}")
                special_liunians = await SpecialLiunianService.get_special_liunians_batch(
                    final_solar_date, final_solar_time, gender,
                    target_dayuns, special_count, current_time,
                    liunian_sequence=liunian_sequence  # ✅ 传入已计算的流年序列
                )
                logger.debug(f"[Orchestrator] get_special_liunians_batch返回: 特殊流年数量={len(special_liunians)}")
                
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
        
        # =====================================================================
        # 阶段2：依赖任务并行执行（rules、fortune_context、personality、rizhu）
        # 这些任务都依赖 bazi_data，但彼此之间无依赖，可以并行执行
        # =====================================================================
        phase2_tasks = []
        
        # 规则匹配（需要 bazi_data + wangshuai_data）
        need_rules = modules.get('rules') and bazi_data
        if need_rules:
            rule_types = modules['rules'].get('types', [])
            if rule_types:
                rule_data = {
                    'bazi_pillars': bazi_data.get('bazi_pillars', {}),
                    'ten_gods': bazi_data.get('ten_gods', {}),
                    'elements': bazi_data.get('elements', {}),
                    'wangshuai': wangshuai_data.get('wangshuai', '') if wangshuai_data else '',
                    'gender': gender
                }
                rules_task = loop.run_in_executor(
                    executor, RuleService.match_rules,
                    rule_data, rule_types, use_cache
                )
                phase2_tasks.append(('rules', rules_task))
        
        # fortune_context（需要 detail_data + wangshuai_data）
        if modules.get('fortune_context') and detail_data:
            from server.orchestrators.fortune_context_service import FortuneContextService
            fc_config = modules['fortune_context'] if isinstance(modules.get('fortune_context'), dict) else {}
            intent_types = fc_config.get('intent_types', ['ALL'])
            target_years = fc_config.get('target_years')
            if target_years is None:
                current_year = datetime.now().year
                target_years = list(range(current_year, current_year + 6))
            fortune_ctx_task = loop.run_in_executor(
                executor, FortuneContextService.get_fortune_context,
                final_solar_date, final_solar_time, gender,
                intent_types, target_years,
                detail_data,
                wangshuai_data or task_data.get('wangshuai')
            )
            phase2_tasks.append(('fortune_context', fortune_ctx_task))
        
        # personality（需要 bazi_data）
        if modules.get('personality') and bazi_data:
            _inner = bazi_data.get('bazi', bazi_data) if isinstance(bazi_data, dict) and 'bazi' in bazi_data else bazi_data
            _pillars = _inner.get('bazi_pillars', {})
            def _calc_personality(pillars=_pillars, g=gender):
                analyzer = RizhuGenderAnalyzer(pillars, g)
                return analyzer.analyze_rizhu_gender()
            personality_task = loop.run_in_executor(executor, _calc_personality)
            phase2_tasks.append(('personality', personality_task))
        
        # rizhu（需要 bazi_data）
        if modules.get('rizhu') and bazi_data:
            _inner = bazi_data.get('bazi', bazi_data) if isinstance(bazi_data, dict) and 'bazi' in bazi_data else bazi_data
            _pillars = _inner.get('bazi_pillars', {})
            _day_pillar = _pillars.get('day', {})
            _rizhu_str = f"{_day_pillar.get('stem', '')}{_day_pillar.get('branch', '')}"
            if _rizhu_str:
                rizhu_task = loop.run_in_executor(
                    executor, RizhuLiujiaziService.get_rizhu_analysis, _rizhu_str
                )
                phase2_tasks.append(('rizhu', rizhu_task))
            else:
                logger.warning("[Orchestrator] rizhu为空，跳过")
                result['rizhu'] = None
        
        # ✅ daily_fortune_calendar（Stage 2：依赖 bazi_data + wangshuai_data）
        # 从 Stage 1 的 bazi_data 提取 birth_stem，传入服务避免重复计算
        if modules.get('daily_fortune_calendar'):
            calendar_config = modules['daily_fortune_calendar']
            query_date = calendar_config.get('date') if isinstance(calendar_config, dict) else None
            
            # 从数据总线提取 birth_stem（bazi Stage 1 已计算）
            _birth_stem_for_calendar = None
            if inner_bazi_data:
                _birth_stem_for_calendar = inner_bazi_data.get('bazi_pillars', {}).get('day', {}).get('stem')
                logger.debug(f"[Orchestrator] daily_fortune_calendar 从总线获取 birth_stem={_birth_stem_for_calendar}")
            
            # wangshuai_data 直接从 Stage 1 传入
            _wangshuai_for_calendar = wangshuai_data
            
            daily_fortune_calendar_task = loop.run_in_executor(
                executor, DailyFortuneCalendarService.get_daily_fortune_calendar,
                query_date,                   # date_str（查询日期）
                final_solar_date,             # user_solar_date（用户出生日期）
                final_solar_time,             # user_solar_time
                gender,                       # user_gender
                _birth_stem_for_calendar,     # ✅ birth_stem（从数据总线传入）
                _wangshuai_for_calendar       # ✅ wangshuai_data（从数据总线传入）
            )
            phase2_tasks.append(('daily_fortune_calendar', daily_fortune_calendar_task))
        
        # 执行阶段2并行任务（带超时保护）
        _PHASE2_TIMEOUT = 10  # 阶段2超时10秒（规则匹配、上下文组装等）
        if phase2_tasks:
            phase2_wrapped = [_fetch_with_semaphore(task) for _, task in phase2_tasks]
            try:
                phase2_results = await asyncio.wait_for(
                    asyncio.gather(*phase2_wrapped, return_exceptions=True),
                    timeout=_PHASE2_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.error(f"[Orchestrator] 阶段2并行任务超时（{_PHASE2_TIMEOUT}s）")
                phase2_results = [asyncio.TimeoutError(f"Phase2 timeout after {_PHASE2_TIMEOUT}s")] * len(phase2_tasks)
            
            phase2_data = {}
            for (name, _), task_result in zip(phase2_tasks, phase2_results):
                if isinstance(task_result, Exception):
                    logger.error(f"[Orchestrator] 阶段2任务 {name} 失败: {task_result}")
                    phase2_data[name] = None
                else:
                    phase2_data[name] = task_result
        else:
            phase2_data = {}
        
        # 提取阶段2结果
        if need_rules:
            matched_rules = phase2_data.get('rules') or []
            result['rules'] = matched_rules
        
        if modules.get('fortune_context') and detail_data:
            fortune_ctx = phase2_data.get('fortune_context')
            result['fortune_context'] = fortune_ctx
            if fortune_ctx:
                logger.info("[BaziDataOrchestrator] fortune_context 已组装（复用 detail/wangshuai）")
        
        if modules.get('personality') and bazi_data:
            result['personality'] = phase2_data.get('personality')
        
        if modules.get('rizhu') and bazi_data and 'rizhu' not in result:
            result['rizhu'] = phase2_data.get('rizhu')
        
        # ✅ 提取 daily_fortune_calendar（Stage 2 结果）
        if modules.get('daily_fortune_calendar'):
            result['daily_fortune_calendar'] = phase2_data.get('daily_fortune_calendar')
        
        # 处理喜神忌神模块（优先使用组装数据，需要在 rules 处理之后）
        if modules.get('xishen_jishen'):
            rules_module_data = result.get('rules', [])
            
            if inner_bazi_data and wangshuai_data:
                xishen_jishen_data = BaziDataOrchestrator._assemble_xishen_jishen_complete_data(
                    bazi_data=inner_bazi_data,
                    wangshuai_data=wangshuai_data,
                    rules_data=rules_module_data,
                    solar_date=final_solar_date,
                    solar_time=final_solar_time,
                    gender=gender,
                    calendar_type=calendar_type or "solar",
                    location=location,
                    latitude=latitude,
                    longitude=longitude
                )
                if xishen_jishen_data:
                    result['xishen_jishen'] = xishen_jishen_data
                    logger.info("[BaziDataOrchestrator] 喜神忌神数据已自动组装")
                else:
                    if xishen_jishen_data_from_task:
                        if isinstance(xishen_jishen_data_from_task, dict):
                            result['xishen_jishen'] = xishen_jishen_data_from_task
                        elif hasattr(xishen_jishen_data_from_task, 'model_dump'):
                            result['xishen_jishen'] = xishen_jishen_data_from_task.model_dump()
                        elif hasattr(xishen_jishen_data_from_task, 'dict'):
                            result['xishen_jishen'] = xishen_jishen_data_from_task.dict()
                        else:
                            result['xishen_jishen'] = xishen_jishen_data_from_task
                    logger.warning("[BaziDataOrchestrator] 喜神忌神数据组装失败，使用接口调用结果")
            else:
                if xishen_jishen_data_from_task:
                    if isinstance(xishen_jishen_data_from_task, dict):
                        result['xishen_jishen'] = xishen_jishen_data_from_task
                    elif hasattr(xishen_jishen_data_from_task, 'model_dump'):
                        result['xishen_jishen'] = xishen_jishen_data_from_task.model_dump()
                    elif hasattr(xishen_jishen_data_from_task, 'dict'):
                        result['xishen_jishen'] = xishen_jishen_data_from_task.dict()
                    else:
                        result['xishen_jishen'] = xishen_jishen_data_from_task
                logger.info("[BaziDataOrchestrator] 使用接口调用的喜神忌神数据")
        
        # 处理分析模块
        if modules.get('health'):
            result['health'] = task_data.get('health')
        
        # 处理五行占比模块（优先使用组装数据）
        if modules.get('wuxing_proportion'):
            # 如果 bazi 和 wangshuai 数据已获取，自动组装
            if inner_bazi_data and wangshuai_data:
                wuxing_proportion_data = BaziDataOrchestrator._assemble_wuxing_proportion_from_data(
                    bazi_data=inner_bazi_data,
                    wangshuai_data=wangshuai_data,
                    solar_date=final_solar_date,
                    solar_time=final_solar_time,
                    gender=gender
                )
                if wuxing_proportion_data:
                    result['wuxing_proportion'] = wuxing_proportion_data
                    logger.info("[BaziDataOrchestrator] ✅ 五行占比数据已自动组装")
                else:
                    # 组装失败，降级到服务调用结果
                    result['wuxing_proportion'] = task_data.get('wuxing_proportion')
                    logger.warning("[BaziDataOrchestrator] ⚠️ 五行占比数据组装失败，使用服务调用结果")
            else:
                # 数据不完整，使用服务调用结果
                result['wuxing_proportion'] = task_data.get('wuxing_proportion')
                logger.info("[BaziDataOrchestrator] 使用服务调用的五行占比数据")
        
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
        
        # ✅ daily_fortune_calendar 已在阶段2处理（从 phase2_data 提取），此处不再从 task_data 获取
        
        # 处理其他模块
        if modules.get('bazi_interface'):
            result['bazi_interface'] = task_data.get('interface')
        
        if modules.get('bazi_ai'):
            result['bazi_ai'] = task_data.get('bazi_ai')
        
        # ✅ 处理 detail 模块：如果启用了 detail 模块，返回完整的 detail_data
        if modules.get('detail') and detail_data:
            result['detail'] = detail_data
        
        # ✅ 优化：写入缓存（如果启用），key 含 current_time 与 dayun 范围
        if use_cache:
            try:
                from server.utils.cache_key_generator import CacheKeyGenerator
                from server.utils.cache_multi_level import get_multi_cache
                
                cache_key = CacheKeyGenerator.generate_orchestrator_key(
                    solar_date, solar_time, gender, modules,
                    calendar_type, location, latitude, longitude,
                    current_time=current_time,
                    dayun_index=dayun_index,
                    dayun_year_start=dayun_year_start,
                    dayun_year_end=dayun_year_end,
                    target_year=target_year
                )
                
                cache = get_multi_cache()
                # 设置缓存TTL（24小时）
                cache.l2.ttl = 86400
                cache.set(cache_key, result)
                # 恢复默认TTL
                cache.l2.ttl = 3600
                
                logger.info(f"[BaziDataOrchestrator] 缓存写入成功: {cache_key[:50]}...")
            except Exception as e:
                logger.warning(f"[BaziDataOrchestrator] 缓存写入失败（不影响业务）: {e}")
        
        return result
    
    @staticmethod
    def _assemble_wuxing_proportion_from_data(
        bazi_data: Dict[str, Any],
        wangshuai_data: Dict[str, Any],
        solar_date: str,
        solar_time: str,
        gender: str
    ) -> Dict[str, Any]:
        """
        从已有数据组装五行占比数据（避免重复计算）
        
        使用已有数据：
        - bazi_data: 包含 bazi_pillars, details, element_counts
        - wangshuai_data: 包含 wangshuai, total_score, xi_ji, final_xi_ji
        
        计算生成：
        - proportions: 从 bazi_pillars 计算五行占比
        - element_relations: 从 proportions 分析相生相克关系
        - ten_gods: 从 details 提取四柱十神信息
        
        Returns:
            dict: 与 WuxingProportionService.calculate_proportion() 格式完全一致
        """
        try:
            # 1. 提取基础数据
            bazi_pillars = bazi_data.get('bazi_pillars', {})
            details = bazi_data.get('details', {})
            
            if not bazi_pillars or not isinstance(bazi_pillars, dict):
                logger.warning("[BaziDataOrchestrator] bazi_pillars 数据无效，降级到服务调用")
                return None
            
            # 2. 统计五行占比（天干+地支，8个位置）
            element_counts = {'金': 0, '木': 0, '水': 0, '火': 0, '土': 0}
            element_details = {'金': [], '木': [], '水': [], '火': [], '土': []}
            
            # 统计天干五行（4个位置）
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar = bazi_pillars.get(pillar_name, {})
                stem = pillar.get('stem', '')
                if stem and stem in STEM_ELEMENTS:
                    element = STEM_ELEMENTS[stem]
                    element_counts[element] += 1
                    element_details[element].append(stem)
            
            # 统计地支五行（4个位置）
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar = bazi_pillars.get(pillar_name, {})
                branch = pillar.get('branch', '')
                if branch and branch in BRANCH_ELEMENTS:
                    element = BRANCH_ELEMENTS[branch]
                    element_counts[element] += 1
                    element_details[element].append(branch)
            
            # 3. 计算占比（保留两位小数）
            total = 8
            proportions = {}
            for element in ['金', '木', '水', '火', '土']:
                count = element_counts[element]
                percentage = round(count / total * 100, 2) if total > 0 else 0.0
                proportions[element] = {
                    'count': count,
                    'percentage': percentage,
                    'details': element_details[element]
                }
            
            # 4. 提取四柱十神信息（从 details）
            ten_gods_info = {}
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar_detail = details.get(pillar_name, {})
                if not isinstance(pillar_detail, dict):
                    pillar_detail = {}
                
                main_star = pillar_detail.get('main_star', '')
                hidden_stars = pillar_detail.get('hidden_stars', [])
                if not isinstance(hidden_stars, list):
                    hidden_stars = []
                
                ten_gods_info[pillar_name] = {
                    'main_star': main_star,
                    'hidden_stars': hidden_stars
                }
            
            # 5. 分析相生相克关系（从 proportions）
            element_relations = BaziDataOrchestrator._calculate_element_relations(proportions)
            
            # 6. 提取旺衰数据
            wangshuai_result = wangshuai_data.get('data', wangshuai_data) if isinstance(wangshuai_data, dict) and 'data' in wangshuai_data else wangshuai_data
            
            # 7. 组装完整数据（与 WuxingProportionService.calculate_proportion() 格式一致）
            return {
                "success": True,
                "bazi_pillars": bazi_pillars,
                "proportions": proportions,
                "ten_gods": ten_gods_info,
                "wangshuai": wangshuai_result,
                "element_relations": element_relations,
                "bazi_data": bazi_data
            }
        except Exception as e:
            logger.error(f"[BaziDataOrchestrator] 组装五行占比数据失败: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _calculate_element_relations(proportions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析五行相生相克关系
        
        Args:
            proportions: 五行占比数据
            
        Returns:
            dict: 相生相克关系分析
        """
        # 五行生克关系
        element_relations_map = {
            '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
            '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
            '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
            '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
            '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
        }
        
        relations = {
            'produces': [],  # 生
            'controls': [],  # 克
            'produced_by': [],  # 被生
            'controlled_by': []  # 被克
        }
        
        # 分析每个五行与其他五行的关系
        for element, data in proportions.items():
            if data.get('count', 0) == 0:
                continue
            
            element_relation = element_relations_map.get(element, {})
            
            # 检查生（我生）
            produces = element_relation.get('produces', '')
            if produces and proportions.get(produces, {}).get('count', 0) > 0:
                relations['produces'].append({
                    'from': element,
                    'to': produces,
                    'from_count': data['count'],
                    'to_count': proportions[produces]['count']
                })
            
            # 检查克（我克）
            controls = element_relation.get('controls', '')
            if controls and proportions.get(controls, {}).get('count', 0) > 0:
                relations['controls'].append({
                    'from': element,
                    'to': controls,
                    'from_count': data['count'],
                    'to_count': proportions[controls]['count']
                })
            
            # 检查被生（生我）
            produced_by = element_relation.get('produced_by', '')
            if produced_by and proportions.get(produced_by, {}).get('count', 0) > 0:
                relations['produced_by'].append({
                    'from': produced_by,
                    'to': element,
                    'from_count': proportions[produced_by]['count'],
                    'to_count': data['count']
                })
            
            # 检查被克（克我）
            controlled_by = element_relation.get('controlled_by', '')
            if controlled_by and proportions.get(controlled_by, {}).get('count', 0) > 0:
                relations['controlled_by'].append({
                    'from': controlled_by,
                    'to': element,
                    'from_count': proportions[controlled_by]['count'],
                    'to_count': data['count']
                })
        
        return relations
    
    @staticmethod
    def _assemble_xishen_jishen_complete_data(
        bazi_data: Dict[str, Any],
        wangshuai_data: Dict[str, Any],
        rules_data: List[Dict[str, Any]],
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: Optional[str] = "solar",
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        从已有数据组装喜神忌神完整数据（避免重复计算）
        
        使用已有数据：
        - bazi_data: 包含 bazi_pillars, ten_gods, element_counts, details
        - wangshuai_data: 包含 xi_shen_elements, ji_shen_elements, wangshuai, total_score, final_xi_ji
        - rules_data: 包含 shishen 类型的规则
        
        Returns:
            dict: 与 get_xishen_jishen() 格式一致，但包含扩展字段
        """
        try:
            # 1. 提取旺衰数据
            wangshuai_data_inner = wangshuai_data.get('data', wangshuai_data) if isinstance(wangshuai_data, dict) and 'data' in wangshuai_data else wangshuai_data
            
            # 2. 提取喜神五行和忌神五行（优先使用final_xi_ji中的综合结果）
            final_xi_ji = wangshuai_data_inner.get('final_xi_ji', {})
            
            if final_xi_ji and final_xi_ji.get('xi_shen_elements'):
                # 使用综合调候后的最终结果
                xi_shen_elements_raw = final_xi_ji.get('xi_shen_elements', [])
                ji_shen_elements_raw = final_xi_ji.get('ji_shen_elements', [])
            else:
                # 使用原始旺衰结果
                xi_shen_elements_raw = wangshuai_data_inner.get('xi_shen_elements', [])
                ji_shen_elements_raw = wangshuai_data_inner.get('ji_shen_elements', [])
            
            # 3. 从规则数据中提取十神命格
            shishen_mingge_names = []
            if rules_data:
                # 筛选 shishen 类型的规则
                shishen_rules = []
                for rule in rules_data:
                    rule_type = rule.get('rule_type', '')
                    if rule_type == 'shishen':
                        shishen_rules.append(rule)
                
                if shishen_rules:
                    shishen_mingge_names = extract_mingge_names_from_rules(shishen_rules)
            
            # 4. 映射ID
            xi_shen_elements = ConfigService.map_elements_to_ids(xi_shen_elements_raw)
            ji_shen_elements = ConfigService.map_elements_to_ids(ji_shen_elements_raw)
            shishen_mingge = ConfigService.map_mingge_to_ids(shishen_mingge_names)
            
            # 5. 提取八字数据（用于LLM分析）
            bazi_pillars = bazi_data.get('bazi_pillars', {})
            day_stem = bazi_pillars.get('day', {}).get('stem', '')
            
            # 提取十神数据
            ten_gods = bazi_data.get('ten_gods', {})
            if not ten_gods:
                # 如果 ten_gods 不存在，从 details 中提取
                details = bazi_data.get('details', {})
                ten_gods = {}
                for pillar_name in ['year', 'month', 'day', 'hour']:
                    pillar_detail = details.get(pillar_name, {})
                    if isinstance(pillar_detail, dict):
                        ten_gods[pillar_name] = {
                            'main_star': pillar_detail.get('main_star', ''),
                            'hidden_stars': pillar_detail.get('hidden_stars', [])
                        }
            
            # 提取五行统计
            element_counts = bazi_data.get('element_counts', {})
            
            # 提取神煞数据
            deities = {}
            details = bazi_data.get('details', {})
            for pillar_name in ['year', 'month', 'day', 'hour']:
                pillar_detail = details.get(pillar_name, {})
                if isinstance(pillar_detail, dict):
                    deities[pillar_name] = pillar_detail.get('deities', [])
            
            # 提取旺衰详细数据
            wangshuai_detail = {
                'wangshuai': wangshuai_data_inner.get('wangshuai', ''),
                'total_score': wangshuai_data_inner.get('total_score', 0)
            }
            # 如果有得令、得地、得助信息，也提取
            if 'de_ling' in wangshuai_data_inner:
                wangshuai_detail['de_ling'] = wangshuai_data_inner.get('de_ling')
            if 'de_di' in wangshuai_data_inner:
                wangshuai_detail['de_di'] = wangshuai_data_inner.get('de_di')
            if 'de_zhu' in wangshuai_data_inner:
                wangshuai_detail['de_zhu'] = wangshuai_data_inner.get('de_zhu')
            
            # 6. 构建响应数据（与普通接口格式一致，但包含扩展字段）
            response_data = {
                # 基础字段（与普通接口一致）
                'solar_date': solar_date,
                'solar_time': solar_time,
                'gender': gender,
                'xi_shen_elements': xi_shen_elements,
                'ji_shen_elements': ji_shen_elements,
                'shishen_mingge': shishen_mingge,
                'wangshuai': wangshuai_data_inner.get('wangshuai', ''),
                'total_score': wangshuai_data_inner.get('total_score', 0),
                
                # 扩展字段（用于LLM分析，不影响普通接口）
                'bazi_pillars': bazi_pillars,
                'day_stem': day_stem,
                'ten_gods': ten_gods,
                'element_counts': element_counts,
                'deities': deities,
                'wangshuai_detail': wangshuai_detail
            }
            
            return {
                "success": True,
                "data": response_data
            }
        except Exception as e:
            logger.error(f"[BaziDataOrchestrator] 组装喜神忌神数据失败: {e}", exc_info=True)
            return None

