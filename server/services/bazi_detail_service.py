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
                              target_year: int = None) -> dict:
        """
        完整计算详细八字信息（包含大运流年）
        
        Args:
            solar_date: 阳历日期，格式：YYYY-MM-DD
            solar_time: 出生时间，格式：HH:MM
            gender: 性别，'male' 或 'female'
            current_time: 当前时间，用于计算大运流年，默认为当前时间
            dayun_index: 大运索引（可选），指定要计算的大运，只计算该大运范围内的流年（性能优化）
            target_year: 目标年份（可选），指定要计算流月的年份，默认为大运起始年份或当前年份
        
        Returns:
            dict: 格式化的详细八字数据
        """
        # 转换性别格式
        if gender not in ["male", "female"]:
            if gender == "男":
                gender = "male"
            elif gender == "女":
                gender = "female"
        
        # 1. 生成缓存键（包含所有影响结果的参数）
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
        result = compute_local_detail(
            solar_date, solar_time, gender, 
            current_time=current_time, 
            dayun_index=dayun_index,
            target_year=target_year
        )
        
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

