#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字详细计算服务层
负责调用 BaziCalculator 和 BaziDetailPrinter 生成详细八字信息
"""

import logging
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.clients.bazi_fortune_client_grpc import BaziFortuneClient
from src.bazi_fortune.helpers import compute_local_detail

logger = logging.getLogger(__name__)


class BaziDetailService:
    """八字详细计算服务类"""
    
    @staticmethod
    def calculate_detail_full(solar_date: str, solar_time: str, gender: str, 
                              current_time: datetime = None, dayun_index: int = None, 
                              target_year: int = None,
                              quick_mode: bool = False,
                              async_warmup: bool = False,
                              include_wangshuai: bool = True,
                              include_shengong_minggong: bool = True,
                              include_rules: bool = True,
                              include_wuxing_proportion: bool = True,
                              include_rizhu_liujiazi: bool = True,
                              rule_types: list = None) -> dict:
        """
        完整计算详细八字信息（包含所有数据：基础八字、大运流年、旺衰、身宫命宫、规则匹配、五行比例、日柱六十甲子）
        
        Args:
            solar_date: 阳历日期，格式：YYYY-MM-DD
            solar_time: 出生时间，格式：HH:MM
            gender: 性别，'male' 或 'female'
            current_time: 当前时间，用于计算大运流年，默认为当前时间
            dayun_index: 大运索引（可选），指定要计算的大运，只计算该大运范围内的流年（性能优化）
            target_year: 目标年份（可选），指定要计算流月的年份，默认为大运起始年份或当前年份
            quick_mode: 快速模式，只计算当前大运（默认False）
            async_warmup: 是否触发异步预热（默认False）
            include_wangshuai: 是否包含旺衰数据（默认True）
            include_shengong_minggong: 是否包含身宫命宫数据（默认True）
            include_rules: 是否包含规则匹配数据（默认True）
            include_wuxing_proportion: 是否包含五行比例数据（默认True）
            include_rizhu_liujiazi: 是否包含日柱六十甲子数据（默认True）
            rule_types: 规则类型过滤（可选）
        
        Returns:
            dict: 格式化的详细八字数据（包含所有数据源）
        """
        # 转换性别格式
        if gender not in ["male", "female"]:
            if gender == "男":
                gender = "male"
            elif gender == "女":
                gender = "female"
        
        # 1. 生成缓存键（包含所有影响结果的参数）
        # 支持部分缓存：基础数据和每个大运独立缓存
        current_time_iso = current_time.isoformat() if current_time else None
        cache_key_parts = [
            'bazi_detail',
            solar_date,
            solar_time,
            gender,
            current_time_iso or 'default',
            str(dayun_index) if dayun_index is not None else 'all',
            str(target_year) if target_year is not None else 'all'
        ]
        # 如果需要包含所有数据，添加标识
        if include_wangshuai or include_shengong_minggong or include_rules:
            cache_key_parts.append('full')  # 标识完整数据
        cache_key = ':'.join(cache_key_parts)
        
        # 2. 先查缓存（L1内存 + L2 Redis）
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            # 设置 L2 Redis TTL 为 30 天（2592000秒）
            cache.l2.ttl = 2592000
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"✅ [缓存命中] BaziDetailService.calculate_detail_full: {cache_key[:50]}...")
                return cached_result
        except Exception as e:
            # Redis不可用，降级到直接计算
            logger.warning(f"⚠️  Redis缓存不可用，降级到直接计算: {e}")
        
        # 3. 缓存未命中，执行计算
        logger.info(f"⏱️ [缓存未命中] BaziDetailService.calculate_detail_full: {cache_key[:50]}...")
        
        # ⚠️ 如果指定了 dayun_index 或 dayun_year_start/dayun_year_end，必须使用本地计算
        # 因为 gRPC 客户端不支持这些参数，且本地计算的 relations 格式更完整（字典列表）
        fortune_service_url = os.getenv("BAZI_FORTUNE_SERVICE_URL")
        if fortune_service_url and dayun_index is None:
            try:
                # 使用30秒超时，确保有足够时间处理大运流年计算
                client = BaziFortuneClient(base_url=fortune_service_url, timeout=30.0)
                result = client.calculate_detail(
                    solar_date,
                    solar_time,
                    gender,
                    current_time=current_time.isoformat() if current_time else None,
                )
                # 写入缓存
                try:
                    cache = get_multi_cache()
                    cache.l2.ttl = 2592000  # 30天
                    cache.set(cache_key, result)
                    logger.info(f"✅ [缓存写入] BaziDetailService.calculate_detail_full: {cache_key[:50]}...")
                except Exception:
                    pass  # 缓存写入失败不影响业务
                return result
            except Exception as exc:  # pragma: no cover
                logger.warning("调用 bazi-fortune-service 失败，自动回退本地计算: %s", exc)
                if os.getenv("BAZI_FORTUNE_SERVICE_STRICT", "0") == "1":
                    raise

        # fallback to local computation
        # ✅ 使用本地计算确保 relations 格式正确（字典列表）且支持 dayun_index
        
        # 快速模式：只计算当前大运
        if quick_mode:
            # 计算当前大运索引
            if dayun_index is None:
                try:
                    from src.bazi_fortune.bazi_calculator_docs import BaziCalculator
                    fortune_calc = BaziCalculator(solar_date, solar_time, gender)
                    if current_time is None:
                        from datetime import datetime
                        current_time = datetime.now()
                    # 计算大运序列以获取当前大运索引
                    fortune_calc.calculate_dayun_liunian(current_time=current_time)
                    dayun_sequence = fortune_calc.details.get('dayun_sequence', [])
                    # 找到当前时间对应的大运索引
                    dayun_index = BaziDetailService._calculate_current_dayun_index(
                        dayun_sequence, current_time
                    )
                except Exception as e:
                    logger.warning(f"计算当前大运索引失败，使用默认值0: {e}")
                    dayun_index = 0
        
        result = compute_local_detail(
            solar_date, solar_time, gender, 
            current_time=current_time, 
            dayun_index=dayun_index,
            target_year=target_year
        )
        
        # ✅ 扩展：集成所有数据源
        # 获取八字计算器用于规则匹配和日柱查询
        bazi_calculator = None
        if include_rules or include_rizhu_liujiazi:
            try:
                from src.tool.BaziCalculator import BaziCalculator
                bazi_calculator = BaziCalculator(solar_date, solar_time, gender)
                bazi_calculator.calculate()
            except Exception as e:
                logger.warning(f"初始化八字计算器失败: {e}")
        
        # 1. 旺衰与喜忌神数据
        if include_wangshuai:
            try:
                from server.services.wangshuai_service import WangShuaiService
                wangshuai_result = WangShuaiService.calculate_wangshuai(solar_date, solar_time, gender)
                if wangshuai_result.get('success'):
                    result['wangshuai'] = wangshuai_result.get('data', {})
                else:
                    logger.warning(f"旺衰计算失败: {wangshuai_result.get('error')}")
                    result['wangshuai'] = None
            except Exception as e:
                logger.warning(f"旺衰计算异常（不影响业务）: {e}")
                result['wangshuai'] = None
        
        # 2. 身宫命宫数据
        if include_shengong_minggong:
            try:
                from server.services.bazi_interface_service import BaziInterfaceService
                interface_data = BaziInterfaceService.generate_interface_full(
                    solar_date, solar_time, gender, "", "未知地", 39.00, 120.00
                )
                # 提取身宫命宫数据
                palaces = interface_data.get('palaces', {})
                result['shengong'] = palaces.get('body_palace', {})
                result['minggong'] = palaces.get('life_palace', {})
                result['taiyuan'] = palaces.get('fetal_origin', {})
                result['taixi'] = palaces.get('fetal_breath', {})
            except Exception as e:
                logger.warning(f"身宫命宫计算异常（不影响业务）: {e}")
                result['shengong'] = None
                result['minggong'] = None
                result['taiyuan'] = None
                result['taixi'] = None
        
        # 3. 规则匹配数据
        if include_rules and bazi_calculator:
            try:
                from server.services.rule_service import RuleService
                bazi_data = bazi_calculator.build_rule_input()
                matched_rules = RuleService.match_rules(bazi_data, rule_types=rule_types, use_cache=True)
                result['matched_rules'] = matched_rules
                result['rule_count'] = len(matched_rules) if matched_rules else 0
            except Exception as e:
                logger.warning(f"规则匹配异常（不影响业务）: {e}")
                result['matched_rules'] = []
                result['rule_count'] = 0
        
        # 4. 五行比例数据
        if include_wuxing_proportion:
            try:
                from server.services.wuxing_proportion_service import WuxingProportionService
                wuxing_result = WuxingProportionService.calculate_proportion(solar_date, solar_time, gender)
                if wuxing_result.get('success'):
                    result['wuxing_proportion'] = wuxing_result
                else:
                    logger.warning(f"五行比例计算失败: {wuxing_result.get('error')}")
                    result['wuxing_proportion'] = None
            except Exception as e:
                logger.warning(f"五行比例计算异常（不影响业务）: {e}")
                result['wuxing_proportion'] = None
        
        # 5. 日柱六十甲子数据
        if include_rizhu_liujiazi and bazi_calculator:
            try:
                from server.services.rizhu_liujiazi_service import RizhuLiujiaziService
                # 获取日柱
                bazi_pillars = result.get('bazi_pillars', {})
                day_pillar = bazi_pillars.get('day', {})
                day_stem = day_pillar.get('stem', '')
                day_branch = day_pillar.get('branch', '')
                rizhu = day_stem + day_branch if day_stem and day_branch else ''
                
                if rizhu:
                    rizhu_result = RizhuLiujiaziService.get_rizhu_analysis(rizhu)
                    result['rizhu_liujiazi'] = rizhu_result if rizhu_result else None
                else:
                    result['rizhu_liujiazi'] = None
            except Exception as e:
                logger.warning(f"日柱六十甲子查询异常（不影响业务）: {e}")
                result['rizhu_liujiazi'] = None
        
        # 触发异步预热（不阻塞响应）
        if async_warmup and quick_mode:
            try:
                BaziDetailService._trigger_async_warmup(solar_date, solar_time, gender, current_time)
            except Exception as e:
                logger.warning(f"异步预热触发失败（不影响业务）: {e}")
        
        # 4. 写入缓存（仅成功时）
        try:
            cache = get_multi_cache()
            cache.l2.ttl = 2592000  # 30天
            cache.set(cache_key, result)
            logger.info(f"✅ [缓存写入] BaziDetailService.calculate_detail_full: {cache_key[:50]}...")
        except Exception:
            pass  # 缓存写入失败不影响业务
        
        return result
    
    @staticmethod
    def _format_detail_result(detail_result: dict, bazi_result: dict) -> dict:
        """
        格式化详细八字结果为前端需要的格式
        
        Args:
            detail_result: BaziCalculator.get_dayun_liunian_result() 返回的结果
            bazi_result: BaziCalculator.calculate() 返回的结果
        
        Returns:
            dict: 格式化后的详细八字数据
        """
        basic_info = detail_result.get('basic_info', {})
        bazi_pillars = detail_result.get('bazi_pillars', {})
        details = detail_result.get('details', {})
        
        # 格式化基本信息
        current_time = basic_info.get('current_time', None)
        if current_time and isinstance(current_time, datetime):
            current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
        elif current_time:
            current_time_str = str(current_time)
        else:
            current_time_str = ''
        
        formatted_basic_info = {
            "solar_date": basic_info.get('solar_date', ''),
            "solar_time": basic_info.get('solar_time', ''),
            "lunar_date": basic_info.get('lunar_date', {}),
            "gender": basic_info.get('gender', ''),
            "current_time": current_time_str,
            "adjusted_solar_date": basic_info.get('adjusted_solar_date', ''),
            "adjusted_solar_time": basic_info.get('adjusted_solar_time', ''),
            "is_zi_shi_adjusted": basic_info.get('is_zi_shi_adjusted', False)
        }
        
        # 格式化四柱信息
        formatted_pillars = {}
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar_details = details.get(pillar_type, {})
            formatted_pillars[pillar_type] = {
                "stem": bazi_pillars.get(pillar_type, {}).get('stem', ''),
                "branch": bazi_pillars.get(pillar_type, {}).get('branch', ''),
                "main_star": pillar_details.get('main_star', ''),
                "hidden_stars": pillar_details.get('hidden_stars', []),
                "sub_stars": pillar_details.get('sub_stars', pillar_details.get('hidden_stars', [])),
                "hidden_stems": pillar_details.get('hidden_stems', []),
                "star_fortune": pillar_details.get('star_fortune', ''),
                "self_sitting": pillar_details.get('self_sitting', ''),
                "kongwang": pillar_details.get('kongwang', ''),
                "nayin": pillar_details.get('nayin', ''),
                "deities": pillar_details.get('deities', [])
            }
        
        # 格式化大运流年信息 - 数据在 details 中
        dayun_info = details.get('dayun', {})
        liunian_info = details.get('liunian', {})
        qiyun_info = details.get('qiyun', {})
        jiaoyun_info = details.get('jiaoyun', {})
        
        # 格式化大运序列 - 数据在 details 中
        dayun_sequence = details.get('dayun_sequence', [])
        formatted_dayun = []
        for dayun in dayun_sequence:
            # 构建干支
            ganzhi = dayun.get('stem', '') + dayun.get('branch', '')
            formatted_dayun.append({
                "step": dayun.get('step', 0),
                "stem": dayun.get('stem', ''),
                "branch": dayun.get('branch', ''),
                "ganzhi": ganzhi,
                "main_star": dayun.get('main_star', ''),
                "age_display": dayun.get('age_display', ''),
                "year_start": dayun.get('year_start', 0),
                "year_end": dayun.get('year_end', 0),
                # 兼容字段
                "start_date": f"{dayun.get('year_start', '')}",
                "end_date": f"{dayun.get('year_end', '')}",
                "age": dayun.get('age_display', ''),
                "nayin": dayun.get('nayin', ''),
                "details": dayun
            })
        
        # 格式化流年序列 - 数据在 details 中
        liunian_sequence = details.get('liunian_sequence', [])
        formatted_liunian = []
        for liunian in liunian_sequence:
            # 构建干支
            ganzhi = liunian.get('stem', '') + liunian.get('branch', '')
            formatted_liunian.append({
                "year": liunian.get('year', ''),
                "stem": liunian.get('stem', ''),
                "branch": liunian.get('branch', ''),
                "ganzhi": ganzhi,
                "main_star": liunian.get('main_star', ''),
                "nayin": liunian.get('nayin', ''),
                "details": liunian
            })
        
        # 格式化流月序列
        liuyue_sequence = details.get('liuyue_sequence', [])
        formatted_liuyue = []
        for liuyue in liuyue_sequence:
            formatted_liuyue.append({
                "month": liuyue.get('month', ''),
                "ganzhi": liuyue.get('ganzhi', ''),
                "stem": liuyue.get('stem', ''),
                "branch": liuyue.get('branch', '')
            })
        
        # 格式化流日序列
        liuri_sequence = details.get('liuri_sequence', [])
        formatted_liuri = []
        for liuri in liuri_sequence:
            formatted_liuri.append({
                "date": liuri.get('date', ''),
                "stem": liuri.get('stem', ''),
                "branch": liuri.get('branch', ''),
                "main_star": liuri.get('main_star', '')
            })
        
        # 格式化流时序列
        liushi_sequence = details.get('liushi_sequence', [])
        formatted_liushi = []
        for liushi in liushi_sequence:
            formatted_liushi.append({
                "time": liushi.get('time', ''),
                "stem": liushi.get('stem', ''),
                "branch": liushi.get('branch', ''),
                "main_star": liushi.get('main_star', '')
            })
        
        return {
            "basic_info": formatted_basic_info,
            "bazi_pillars": formatted_pillars,
            "ten_gods_stats": bazi_result.get('ten_gods_stats', {}),
            "elements": bazi_result.get('elements', {}),
            "element_counts": bazi_result.get('element_counts', {}),
            "relationships": bazi_result.get('relationships', {}),
            "dayun_info": {
                "current_dayun": dayun_info,
                "next_dayun": {},
                "qiyun_date": qiyun_info.get('date', ''),
                "qiyun_age": qiyun_info.get('age_display', ''),
                "qiyun": qiyun_info,
                "jiaoyun_date": jiaoyun_info.get('date', ''),
                "jiaoyun_age": jiaoyun_info.get('age_display', ''),
                "jiaoyun": jiaoyun_info
            },
            "liunian_info": {
                "current_liunian": liunian_info,
                "next_liunian": {}
            },
            "dayun_sequence": formatted_dayun,
            "liunian_sequence": formatted_liunian,
            "liuyue_sequence": formatted_liuyue,
            "liuri_sequence": formatted_liuri,
            "liushi_sequence": formatted_liushi
        }
    
    @staticmethod
    def _calculate_current_dayun_index(dayun_sequence: list, current_time: datetime) -> int:
        """
        计算当前时间对应的大运索引
        
        Args:
            dayun_sequence: 大运序列
            current_time: 当前时间
        
        Returns:
            int: 当前大运索引，如果未找到则返回0
        """
        if not dayun_sequence:
            return 0
        
        current_year = current_time.year
        
        for idx, dayun in enumerate(dayun_sequence):
            year_start = dayun.get('year_start', 0)
            year_end = dayun.get('year_end', 0)
            
            if year_start <= current_year <= year_end:
                return idx
        
        # 如果未找到，返回第一个或最后一个
        if current_year < dayun_sequence[0].get('year_start', 0):
            return 0
        else:
            return len(dayun_sequence) - 1
    
    @staticmethod
    def _trigger_async_warmup(solar_date: str, solar_time: str, gender: str, current_time: datetime = None):
        """
        触发后台异步预热（10个大运并行计算）
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            current_time: 当前时间
        """
        from concurrent.futures import ThreadPoolExecutor
        import threading
        
        def warmup_dayun(dayun_idx: int):
            """预热单个大运"""
            try:
                # 计算该大运的数据并写入缓存
                compute_local_detail(
                    solar_date, solar_time, gender,
                    current_time=current_time,
                    dayun_index=dayun_idx
                )
                logger.debug(f"✅ [异步预热] 大运 {dayun_idx} 预热完成")
            except Exception as e:
                logger.warning(f"⚠️ [异步预热] 大运 {dayun_idx} 预热失败: {e}")
        
        # 在后台线程中执行预热任务
        def start_warmup():
            try:
                executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="bazi_warmup")
                futures = []
                for dayun_index in range(10):
                    future = executor.submit(warmup_dayun, dayun_index)
                    futures.append(future)
                # 不等待完成，让它在后台运行
                logger.info(f"✅ [异步预热] 已触发10个大运的异步预热任务")
            except Exception as e:
                logger.warning(f"⚠️ [异步预热] 启动预热任务失败: {e}")
        
        # 启动后台线程
        warmup_thread = threading.Thread(target=start_warmup, daemon=True)
        warmup_thread.start()

