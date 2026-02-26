#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
今日运势分析服务 - 类似 FateTell 的"日运日签"功能
结合用户八字和当前日期，分析今日运势
"""

import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime, date

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from server.services.bazi_detail_service import BaziDetailService
from server.services.rule_service import RuleService
from server.utils.data_validator import validate_bazi_data


class DailyFortuneService:
    """今日运势分析服务"""
    
    # Redis缓存TTL（24小时，因为每日运势每天变化）
    CACHE_TTL = 86400
    
    @staticmethod
    def _generate_cache_key(
        solar_date: str,
        solar_time: str,
        gender: str,
        target_date: Optional[str] = None,
        use_llm: bool = False
    ) -> str:
        """
        生成缓存键
        
        Args:
            solar_date: 用户出生日期
            solar_time: 用户出生时间
            gender: 性别
            target_date: 目标日期
            use_llm: 是否使用LLM
            
        Returns:
            str: 缓存键
        """
        # 标准化参数
        if target_date:
            date_key = target_date
        else:
            date_key = date.today().strftime('%Y-%m-%d')
        
        # 生成键（格式：daily_fortune:service:{date}:{solar_date}:{solar_time}:{gender}:{use_llm}）
        key_parts = [
            'daily_fortune',
            'service',
            date_key,
            solar_date,
            solar_time,
            gender,
            'llm' if use_llm else 'rule'
        ]
        return ':'.join(key_parts)
    
    @staticmethod
    def _calculate_daily_fortune_from_database(
        solar_date: str,
        solar_time: str,
        gender: str,
        target_date: Optional[str] = None,
        use_llm: bool = False,
        access_token: Optional[str] = None,
        bot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        计算今日运势分析
        
        Args:
            solar_date: 用户出生日期（阳历）
            solar_time: 用户出生时间
            gender: 性别
            target_date: 目标日期（可选，默认为今天），格式：YYYY-MM-DD
            use_llm: 是否使用 LLM 生成（可选，默认使用规则匹配）
            access_token: Coze Access Token（可选，use_llm=True 时需要）
            bot_id: Coze Bot ID（可选，use_llm=True 时需要）
            
        Returns:
            dict: 包含今日运势分析结果
        """
        try:
            # 1. 确定目标日期
            if target_date:
                target = datetime.strptime(target_date, "%Y-%m-%d").date()
            else:
                target = date.today()
            
            target_datetime = datetime.combine(target, datetime.min.time())
            
            # 2. 计算用户八字
            bazi_result = BaziService.calculate_bazi_full(solar_date, solar_time, gender)
            if not bazi_result:
                return {
                    "success": False,
                    "error": "八字计算失败",
                    "fortune": None
                }
            
            # 【修复】BaziService.calculate_bazi_full() 直接返回八字数据，不是 {'bazi': {...}}
            # 历史教训：2025-11-20 因错误使用 .get('bazi', {}) 导致 bazi_data 为空字典
            bazi_data = bazi_result.get('bazi', bazi_result)  # 如果没有 'bazi' 键，使用整个结果
            
            # ✅ 统一类型验证：确保所有字段类型正确（防止gRPC序列化问题）
            bazi_data = validate_bazi_data(bazi_data)
            
            # 3. 计算详细八字信息（包含流年流月流日）
            detail_result = BaziDetailService.calculate_detail_full(
                solar_date,
                solar_time,
                gender,
                current_time=target_datetime
            )
            
            if not detail_result:
                return {
                    "success": False,
                    "error": "详细八字计算失败",
                    "fortune": None
                }
            
            # 4. 提取流日信息
            liuri_info = DailyFortuneService._extract_liuri_info(detail_result, target)
            
            # 5. 匹配今日相关规则
            matched_rules = RuleService.match_rules(
                bazi_data,
                rule_types=['fortune', 'daily', 'annual'],  # 运势相关规则
                use_cache=True
            )
            
            # 6. 生成运势分析
            if use_llm:
                # 使用 LLM 生成（可选）
                fortune_analysis = DailyFortuneService._generate_with_llm(
                    bazi_data,
                    liuri_info,
                    target,
                    access_token,
                    bot_id
                )
            else:
                # 使用规则匹配生成
                fortune_analysis = DailyFortuneService._generate_with_rules(
                    bazi_data,
                    liuri_info,
                    matched_rules,
                    target
                )
            
            return {
                "success": True,
                "target_date": target.strftime("%Y-%m-%d"),
                "bazi_data": bazi_data,
                "liuri_info": liuri_info,
                "fortune": fortune_analysis,
                "matched_rules_count": len(matched_rules)
            }
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"计算今日运势异常: {str(e)}\n{traceback.format_exc()}",
                "fortune": None
            }
    
    @staticmethod
    def calculate_daily_fortune(
        solar_date: str,
        solar_time: str,
        gender: str,
        target_date: Optional[str] = None,
        use_llm: bool = False,
        access_token: Optional[str] = None,
        bot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        计算今日运势分析（带Redis缓存）
        
        Args:
            solar_date: 用户出生日期（阳历）
            solar_time: 用户出生时间
            gender: 性别
            target_date: 目标日期（可选，默认为今天），格式：YYYY-MM-DD
            use_llm: 是否使用 LLM 生成（可选，默认使用规则匹配）
            access_token: Coze Access Token（可选，use_llm=True 时需要）
            bot_id: Coze Bot ID（可选，use_llm=True 时需要）
            
        Returns:
            dict: 包含今日运势分析结果
        """
        # 1. 生成缓存键
        cache_key = DailyFortuneService._generate_cache_key(
            solar_date, solar_time, gender, target_date, use_llm
        )
        
        # 2. 先查缓存（L1内存 + L2 Redis）
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            cached_result = cache.get(cache_key)
            if cached_result:
                # 缓存命中，直接返回（0个数据库连接）
                return cached_result
        except Exception as e:
            # Redis不可用，降级到数据库查询
            logger.warning(f"⚠️  Redis缓存不可用，降级到数据库查询: {e}")
        
        # 3. 缓存未命中，查询数据库
        result = DailyFortuneService._calculate_daily_fortune_from_database(
            solar_date, solar_time, gender, target_date, use_llm, access_token, bot_id
        )
        
        # 4. 写入缓存（仅成功时）
        if result.get('success'):
            try:
                from server.utils.cache_multi_level import get_multi_cache
                cache = get_multi_cache()
                # 使用自定义TTL（24小时）
                cache.l2.ttl = DailyFortuneService.CACHE_TTL
                cache.set(cache_key, result)
                # 恢复默认TTL
                cache.l2.ttl = 3600
            except Exception as e:
                # 缓存写入失败不影响业务
                logger.warning(f"⚠️  缓存写入失败（不影响业务）: {e}")
        
        return result
    
    @staticmethod
    def _extract_liuri_info(detail_result: Dict[str, Any], target_date: date) -> Dict[str, Any]:
        """提取流日信息（直接使用LunarConverter计算今日干支）"""
        from core.calculators.LunarConverter import LunarConverter
        
        liuri_info = {
            "date": target_date.strftime("%Y-%m-%d"),
            "liuri": None,
            "liuyue": None,
            "liunian": None
        }
        
        try:
            # 天干五行对应表
            stem_elements = {
                '甲': '木', '乙': '木',
                '丙': '火', '丁': '火',
                '戊': '土', '己': '土',
                '庚': '金', '辛': '金',
                '壬': '水', '癸': '水'
            }
            
            # 获取今日的年月日干支（返回字典格式）
            year_ganzhi_dict = LunarConverter.get_year_ganzhi(target_date.year)
            month_ganzhi_dict = LunarConverter.get_month_ganzhi(target_date.year, target_date.month, target_date.day)
            day_ganzhi_dict = LunarConverter.get_day_ganzhi(target_date.year, target_date.month, target_date.day)
            
            # 提取日干支和五行
            if isinstance(day_ganzhi_dict, dict) and 'stem' in day_ganzhi_dict and 'branch' in day_ganzhi_dict:
                day_stem = day_ganzhi_dict['stem']
                day_branch = day_ganzhi_dict['branch']
                day_element = stem_elements.get(day_stem, '未知')
                
                liuri_info['liuri'] = {
                    'ganzhi': f"{day_stem}{day_branch}",
                    'stem': {'char': day_stem, 'element': day_element},
                    'branch': {'char': day_branch}
                }
            
            # 提取月干支和五行
            if isinstance(month_ganzhi_dict, dict) and 'stem' in month_ganzhi_dict and 'branch' in month_ganzhi_dict:
                month_stem = month_ganzhi_dict['stem']
                month_branch = month_ganzhi_dict['branch']
                month_element = stem_elements.get(month_stem, '未知')
                
                liuri_info['liuyue'] = {
                    'ganzhi': f"{month_stem}{month_branch}",
                    'stem': {'char': month_stem, 'element': month_element},
                    'branch': {'char': month_branch}
                }
            
            # 提取年干支和五行
            if isinstance(year_ganzhi_dict, dict) and 'stem' in year_ganzhi_dict and 'branch' in year_ganzhi_dict:
                year_stem = year_ganzhi_dict['stem']
                year_branch = year_ganzhi_dict['branch']
                year_element = stem_elements.get(year_stem, '未知')
                
                liuri_info['liunian'] = {
                    'ganzhi': f"{year_stem}{year_branch}",
                    'stem': {'char': year_stem, 'element': year_element},
                    'branch': {'char': year_branch}
                }
        except Exception as e:
            # 计算失败时返回默认值
            import logging
            logging.warning(f"流日信息计算失败: {e}")
        
        return liuri_info
    
    @staticmethod
    def _generate_with_rules(
        bazi_data: Dict[str, Any],
        liuri_info: Dict[str, Any],
        matched_rules: list,
        target_date: date
    ) -> Dict[str, Any]:
        """使用规则匹配生成运势分析（基于八字动态生成）"""
        # 第一行就打印参数类型
        import logging
        logger = logging.getLogger(__name__)
        # DEBUG日志已移除，如需调试请使用logger.debug()
        
        # 【防御性代码】确保 bazi_data 是字典类型
        # 注意：在调用此函数前应该已经检查并修复了 bazi_data 的类型
        # 但为了安全，这里再次检查
        if not isinstance(bazi_data, dict):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"_generate_with_rules: bazi_data 类型错误: {type(bazi_data)}, 值: {str(bazi_data)[:100]}")
            # 返回默认值而不是抛出异常
            return {
                "overall_score": 60,
                "details": f"数据格式错误，无法生成运势分析"
            }
        
        lines = []
        
        lines.append(f"【{target_date.strftime('%Y年%m月%d日')}运势分析】")
        lines.append("=" * 60)
        lines.append("")
        
        # 提取八字关键信息
        day_stem = bazi_data.get('bazi_pillars', {}).get('day', {}).get('stem', '未知')
        day_branch = bazi_data.get('bazi_pillars', {}).get('day', {}).get('branch', '未知')
        day_element = bazi_data.get('elements', {}).get('day', {}).get('stem_element', '未知')
        
        # 流日信息
        liuri_ganzhi = liuri_info.get('liuri', {}).get('ganzhi', '未知') if isinstance(liuri_info.get('liuri'), dict) else '未知'
        liuyue_ganzhi = liuri_info.get('liuyue', {}).get('ganzhi', '未知') if isinstance(liuri_info.get('liuyue'), dict) else '未知'
        liunian_ganzhi = liuri_info.get('liunian', {}).get('ganzhi', '未知') if isinstance(liuri_info.get('liunian'), dict) else '未知'
        
        lines.append(f"八字日干：{day_stem}{day_branch}（{day_element}）")
        if liuri_ganzhi != '未知':
            lines.append(f"流日：{liuri_ganzhi}")
        if liuyue_ganzhi != '未知':
            lines.append(f"流月：{liuyue_ganzhi}")
        if liunian_ganzhi != '未知':
            lines.append(f"流年：{liunian_ganzhi}")
        lines.append("")
        
        # 基于八字生成运势分析
        career_text, wealth_text, love_text, health_text, overall_score, advice = DailyFortuneService._analyze_by_bazi(
            bazi_data, liuri_info, matched_rules, target_date
        )
        
        # 今日运势分析
        lines.append("【今日运势】")
        if matched_rules:
            for i, rule in enumerate(matched_rules[:3], 1):
                rule_text = rule.get('content', {}).get('text', '')
                if rule_text:
                    lines.append(f"{i}. {rule_text}")
        else:
            lines.append(f"日主{day_element}，今日{liuri_ganzhi}。" + advice.split('；')[0])
        lines.append("")
        
        # 分类运势
        lines.append("【分类运势】")
        lines.append("")
        lines.append(f"📈 事业运势：{career_text}")
        lines.append("")
        lines.append(f"💰 财运：{wealth_text}")
        lines.append("")
        lines.append(f"💕 感情运势：{love_text}")
        lines.append("")
        lines.append(f"🏥 健康运势：{health_text}")
        lines.append("")
        
        # 今日建议
        lines.append("【今日建议】")
        lines.append(advice)
        lines.append("")
        lines.append("以上分析基于八字命理，仅供参考。")
        
        return {
            "text": "\n".join(lines),
            "date": target_date.strftime('%Y年%m月%d日'),
            "summary": f"{day_element}日主，{target_date.strftime('%Y年%m月%d日')}运势分析",
            "overall_score": overall_score,
            "career": career_text,
            "wealth": wealth_text,
            "love": love_text,
            "health": health_text,
            "advice": advice,
            "categories": {
                "career": DailyFortuneService._get_category_level(overall_score + 5),
                "wealth": DailyFortuneService._get_category_level(overall_score),
                "love": DailyFortuneService._get_category_level(overall_score - 5),
                "health": DailyFortuneService._get_category_level(overall_score)
            }
        }
    
    @staticmethod
    def _analyze_by_bazi(
        bazi_data: Dict[str, Any],
        liuri_info: Dict[str, Any],
        matched_rules: list,
        target_date: date
    ) -> tuple:
        """基于八字分析今日运势"""
        # 【防御性代码】确保 bazi_data 是字典类型
        if not isinstance(bazi_data, dict):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"_analyze_by_bazi: bazi_data 类型错误: {type(bazi_data)}, 值: {str(bazi_data)[:100]}")
            bazi_data = {}
        
        # 提取关键信息
        day_element = bazi_data.get('elements', {}).get('day', {}).get('stem_element', '土') if isinstance(bazi_data, dict) else '土'
        
        # 【防御性代码】修复 element_counts 可能为字符串的问题
        element_counts_raw = bazi_data.get('element_counts', {})
        if isinstance(element_counts_raw, str):
            try:
                import ast
                element_counts = ast.literal_eval(element_counts_raw)
            except (ValueError, SyntaxError):
                try:
                    import json
                    element_counts = json.loads(element_counts_raw)
                except (json.JSONDecodeError, TypeError):
                    element_counts = {}
        elif isinstance(element_counts_raw, dict):
            element_counts = element_counts_raw
        else:
            element_counts = {}
        
        # 【防御性代码】修复 ten_gods_stats 可能为字符串的问题
        # 历史教训：2025-11-20 因 gRPC 序列化问题，ten_gods_stats 可能是字符串
        ten_gods_stats_raw = bazi_data.get('ten_gods_stats', {})
        if isinstance(ten_gods_stats_raw, str):
            try:
                import ast
                ten_gods_stats_raw = ast.literal_eval(ten_gods_stats_raw)
            except (ValueError, SyntaxError):
                try:
                    import json
                    ten_gods_stats_raw = json.loads(ten_gods_stats_raw)
                except (json.JSONDecodeError, TypeError):
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"ten_gods_stats 解析失败: {ten_gods_stats_raw[:100]}")
                    ten_gods_stats_raw = {}
        if not isinstance(ten_gods_stats_raw, dict):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"ten_gods_stats_raw 类型错误: {type(ten_gods_stats_raw)}")
            ten_gods_stats_raw = {}
        
        # 确保 totals 也是字典
        totals = ten_gods_stats_raw.get('totals', {}) if isinstance(ten_gods_stats_raw, dict) else {}
        if not isinstance(totals, dict):
            if isinstance(totals, str):
                try:
                    import ast
                    totals = ast.literal_eval(totals)
                except Exception:
                    totals = {}
            else:
                totals = {}
        ten_gods_stats = totals
        
        # 流日五行
        liuri_stem_element = '未知'
        if isinstance(liuri_info.get('liuri'), dict):
            liuri_stem_element = liuri_info['liuri'].get('stem', {}).get('element', '未知')
        
        # 五行生克关系影响评分
        element_relation = DailyFortuneService._get_element_relation(day_element, liuri_stem_element)
        base_score = 60
        
        if element_relation == '生我':
            base_score = 75  # 得生，运势较好
        elif element_relation == '我生':
            base_score = 55  # 泄气，运势稍弱
        elif element_relation == '克我':
            base_score = 50  # 受克，需谨慎
        elif element_relation == '我克':
            base_score = 70  # 克出，有利
        elif element_relation == '比和':
            base_score = 65  # 平稳
        
        # 根据规则调整评分
        if matched_rules:
            rule_score_adj = len(matched_rules) * 2
            base_score = min(95, base_score + rule_score_adj)
        
        # 生成各项运势
        # 【防御性检查】确保 ten_gods_stats 是字典
        import logging
        logger = logging.getLogger(__name__)
        if not isinstance(ten_gods_stats, dict):
            logger.error(f"_analyze_by_bazi: ten_gods_stats 类型错误: {type(ten_gods_stats)}, 值: {str(ten_gods_stats)[:100]}")
            ten_gods_stats = {}
        career_text = DailyFortuneService._generate_career_fortune(day_element, liuri_stem_element, element_relation, ten_gods_stats)
        wealth_text = DailyFortuneService._generate_wealth_fortune(day_element, liuri_stem_element, element_relation, ten_gods_stats)
        love_text = DailyFortuneService._generate_love_fortune(day_element, liuri_stem_element, element_relation, ten_gods_stats)
        health_text = DailyFortuneService._generate_health_fortune(day_element, element_counts, element_relation)
        advice = DailyFortuneService._generate_advice(element_relation, day_element, liuri_stem_element)
        
        return career_text, wealth_text, love_text, health_text, base_score, advice
    
    @staticmethod
    def _get_element_relation(day_element: str, liuri_element: str) -> str:
        """获取五行生克关系"""
        sheng_cycle = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
        ke_cycle = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}
        
        if day_element == liuri_element:
            return '比和'
        elif sheng_cycle.get(liuri_element) == day_element:
            return '生我'
        elif sheng_cycle.get(day_element) == liuri_element:
            return '我生'
        elif ke_cycle.get(liuri_element) == day_element:
            return '克我'
        elif ke_cycle.get(day_element) == liuri_element:
            return '我克'
        return '平和'
    
    @staticmethod
    def _generate_career_fortune(day_element: str, liuri_element: str, relation: str, ten_gods: dict) -> str:
        """生成事业运势"""
        # 【防御性代码】确保 ten_gods 是字典类型
        if not isinstance(ten_gods, dict):
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"_generate_career_fortune: ten_gods 类型错误: {type(ten_gods)}, 值: {str(ten_gods)[:100]}")
            ten_gods = {}
        
        templates = {
            '生我': f"今日得{liuri_element}相生，事业运势向好，适合推进重要项目，把握机遇。有贵人相助，工作进展顺利。",
            '我克': f"日主{day_element}克{liuri_element}，今日事业运有利，适合主动出击，展现实力。决策果断，易获成功。",
            '比和': f"今日与日主{day_element}比和，事业运势平稳，适合巩固基础，稳步推进。团队协作顺畅。",
            '我生': f"日主{day_element}生{liuri_element}，今日事业付出较多，需注意劳逸结合。适合培养下属，长远布局。",
            '克我': f"今日受{liuri_element}克制，事业运势需谨慎，宜守不宜攻。避免冲动决策，稳字当头。"
        }
        
        base_text = templates.get(relation, "今日事业运势平稳，按部就班完成工作任务即可。")
        
        # 根据十神补充（添加防御性检查）
        zhengguan = ten_gods.get('正官') if isinstance(ten_gods, dict) else {}
        if isinstance(zhengguan, dict) and zhengguan.get('count', 0) > 0:
            base_text += "命中有官星，适合处理正式公务。"
        else:
            pian_guan = ten_gods.get('偏官') if isinstance(ten_gods, dict) else {}
            if isinstance(pian_guan, dict) and pian_guan.get('count', 0) > 0:
                base_text += "偏官在命，适合开拓创新。"
        
        return base_text
    
    @staticmethod
    def _generate_wealth_fortune(day_element: str, liuri_element: str, relation: str, ten_gods: dict) -> str:
        """生成财运"""
        # 【防御性代码】确保 ten_gods 是字典类型
        if not isinstance(ten_gods, dict):
            ten_gods = {}
        
        templates = {
            '我克': f"日主{day_element}克{liuri_element}为财，今日财运较旺，适合投资理财，把握商机。",
            '生我': f"今日得{liuri_element}相生，财运平稳有进，适合稳健投资。",
            '比和': f"今日财运平稳，收入稳定，适合储蓄理财。",
            '克我': f"今日受{liuri_element}克制，财运稍弱，宜守财不宜大额支出。",
            '我生': f"今日泄气，财运一般，避免冲动消费，理性支出。"
        }
        
        base_text = templates.get(relation, "今日财运平稳，建议理性理财。")
        
        # 根据十神补充（添加防御性检查）
        zhengcai = ten_gods.get('正财') if isinstance(ten_gods, dict) else {}
        if isinstance(zhengcai, dict) and zhengcai.get('count', 0) > 0:
            base_text += "正财在命，适合正当经营获利。"
        else:
            piancai = ten_gods.get('偏财') if isinstance(ten_gods, dict) else {}
            if isinstance(piancai, dict) and piancai.get('count', 0) > 0:
                base_text += "偏财在命，可关注投资机会。"
        
        return base_text
    
    @staticmethod
    def _generate_love_fortune(day_element: str, liuri_element: str, relation: str, ten_gods: dict) -> str:
        """生成感情运势"""
        # 【防御性代码】确保 ten_gods 是字典类型
        if not isinstance(ten_gods, dict):
            ten_gods = {}
        
        templates = {
            '生我': f"今日得{liuri_element}相生，感情运势佳，适合表达心意，增进感情。单身者桃花运旺。",
            '比和': f"今日感情运势平和，适合与伴侣平等沟通，共同成长。",
            '我克': f"今日感情运势尚可，适合主动关心对方，但避免过于强势。",
            '我生': f"今日感情付出较多，多关心伴侣感受，真诚沟通。",
            '克我': f"今日感情需注意，避免争执，多包容理解。单身者缘分稍弱。"
        }
        
        return templates.get(relation, "今日感情运势平稳，适合与伴侣互动交流。")
    
    @staticmethod
    def _generate_health_fortune(day_element: str, element_counts: dict, relation: str) -> str:
        """生成健康运势"""
        # 【防御性代码】确保 element_counts 是字典类型
        if not isinstance(element_counts, dict):
            element_counts = {}
        
        weak_elements = [elem for elem, count in element_counts.items() if count < 2]
        
        health_tips = {
            '木': "注意肝胆保养，多食绿色蔬菜",
            '火': "注意心脏和血液循环，保持情绪平和",
            '土': "注意脾胃消化，规律饮食",
            '金': "注意呼吸系统和皮肤，适量运动",
            '水': "注意肾脏和泌尿系统，多喝水"
        }
        
        base_text = "今日健康运势尚可，注意劳逸结合。"
        
        if relation == '克我':
            base_text = "今日受克，身体稍弱，避免过度劳累，早休息。"
        elif relation == '生我':
            base_text = "今日得生，精力充沛，适合运动锻炼。"
        
        if weak_elements:
            tips = health_tips.get(weak_elements[0], '')
            if tips:
                base_text += tips + "。"
        
        return base_text
    
    @staticmethod
    def _generate_advice(relation: str, day_element: str, liuri_element: str) -> str:
        """生成今日建议"""
        advice_templates = {
            '生我': f"今日得{liuri_element}相生，运势向好。建议：1.把握机遇，主动出击；2.保持积极心态；3.多与他人合作。",
            '我克': f"日主{day_element}克{liuri_element}，今日有利。建议：1.果断决策，展现能力；2.注意不要过于强势；3.兼顾他人感受。",
            '比和': f"今日比和，运势平稳。建议：1.稳步推进计划；2.加强团队协作；3.巩固现有成果。",
            '我生': f"今日泄气，需注意能量。建议：1.量力而行，避免过度付出；2.注意休息调养；3.做好长远规划。",
            '克我': f"今日受{liuri_element}克制，需谨慎。建议：1.低调行事，避免冲突；2.多观察少行动；3.保持耐心等待时机。"
        }
        
        return advice_templates.get(relation, "保持平常心，顺势而为，把握当下。")
    
    @staticmethod
    def _get_category_level(score: int) -> str:
        """根据评分返回运势等级"""
        if score >= 80:
            return "旺盛"
        elif score >= 70:
            return "良好"
        elif score >= 60:
            return "平稳"
        elif score >= 50:
            return "稍弱"
        else:
            return "需谨慎"
    
    @staticmethod
    def _calculate_score(matched_rules: list) -> int:
        """计算综合运势评分"""
        if not matched_rules:
            return 60  # 默认平稳分数
        
        # 根据规则中的评分计算平均值
        scores = []
        for rule in matched_rules[:10]:  # 取前10条规则
            content = rule.get('content', {})
            score = content.get('score')
            if isinstance(score, (int, float)):
                scores.append(score)
        
        if scores:
            avg_score = sum(scores) / len(scores)
            return int(avg_score)
        
        return 65  # 默认略偏正面的分数
    
    @staticmethod
    def _generate_with_llm(
        bazi_data: Dict[str, Any],
        liuri_info: Dict[str, Any],
        target_date: date,
        access_token: Optional[str] = None,
        bot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用 LLM 生成运势分析（可选）"""
        try:
            from server.services.llm_generate_service import LLMGenerateService
            from core.analyzers.bazi_ai_analyzer import BaziAIAnalyzer
            
            # 构建 Prompt
            prompt_lines = []
            prompt_lines.append("你是一位资深的命理师，请根据用户的八字信息和流日信息，生成今日运势分析。")
            prompt_lines.append("")
            prompt_lines.append("【用户八字信息】")
            basic_info = bazi_data.get('basic_info', {})
            prompt_lines.append(f"出生日期：{basic_info.get('solar_date', '')} {basic_info.get('solar_time', '')}")
            prompt_lines.append(f"性别：{'男' if basic_info.get('gender') == 'male' else '女'}")
            
            bazi_pillars = bazi_data.get('bazi_pillars', {})
            prompt_lines.append("四柱八字：")
            for pillar_type in ['year', 'month', 'day', 'hour']:
                pillar = bazi_pillars.get(pillar_type, {})
                pillar_name = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}.get(pillar_type, pillar_type)
                prompt_lines.append(f"  {pillar_name}：{pillar.get('stem', '')}{pillar.get('branch', '')}")
            
            prompt_lines.append("")
            prompt_lines.append("【流日信息】")
            if liuri_info.get('liuri'):
                prompt_lines.append(f"流日：{liuri_info['liuri']}")
            if liuri_info.get('liuyue'):
                prompt_lines.append(f"流月：{liuri_info['liuyue']}")
            if liuri_info.get('liunian'):
                prompt_lines.append(f"流年：{liuri_info['liunian']}")
            
            prompt_lines.append("")
            prompt_lines.append(f"【目标日期】{target_date.strftime('%Y年%m月%d日')}")
            prompt_lines.append("")
            prompt_lines.append("请生成今日运势分析，包括：")
            prompt_lines.append("1. 整体运势")
            prompt_lines.append("2. 事业运势")
            prompt_lines.append("3. 财运")
            prompt_lines.append("4. 感情运势")
            prompt_lines.append("5. 健康运势")
            prompt_lines.append("6. 今日建议")
            prompt_lines.append("")
            prompt_lines.append("要求：语言自然流畅，避免过于玄学化，给出具体建议。")
            
            prompt = "\n".join(prompt_lines)
            
            # 调用 LLM
            init_kwargs = {}
            if access_token:
                init_kwargs['access_token'] = access_token
            if bot_id:
                init_kwargs['bot_id'] = bot_id
            
            ai_analyzer = BaziAIAnalyzer(**init_kwargs)
            result = ai_analyzer._call_coze_api(prompt, bazi_data)
            
            if result.get('success'):
                analysis_text = result.get('analysis', '')
                return {
                    "text": analysis_text,
                    "summary": f"{target_date.strftime('%Y年%m月%d日')}运势分析（LLM生成）",
                    "generated_by": "llm"
                }
            else:
                # LLM 生成失败，降级到规则匹配
                return DailyFortuneService._generate_with_rules(
                    bazi_data,
                    liuri_info,
                    [],
                    target_date
                )
        except Exception as e:
            # LLM 生成异常，降级到规则匹配
            return DailyFortuneService._generate_with_rules(
                bazi_data,
                liuri_info,
                [],
                target_date
            )
    
    @staticmethod
    def invalidate_cache_for_date(target_date: Optional[str] = None):
        """
        使指定日期的缓存失效（支持双机同步）
        
        Args:
            target_date: 目标日期（可选，默认为今天），格式：YYYY-MM-DD
        """
        try:
            from server.utils.cache_multi_level import get_multi_cache
            from shared.config.redis import get_redis_client
            
            # 1. 清理本地L1缓存
            cache = get_multi_cache()
            cache.l1.clear()  # 清空所有L1缓存（简单实现）
            
            # 2. 清理Redis缓存（支持pattern匹配）
            redis_client = get_redis_client()
            if redis_client:
                if target_date:
                    # 清理指定日期的缓存
                    pattern = f"daily_fortune:service:{target_date}:*"
                else:
                    # 清理所有每日运势缓存
                    pattern = "daily_fortune:service:*"
                
                # 使用SCAN迭代删除（避免阻塞）
                cursor = 0
                deleted_count = 0
                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        deleted_count += redis_client.delete(*keys)
                    if cursor == 0:
                        break
                
                # 3. 发布缓存失效事件（双机同步）
                try:
                    redis_client.publish('cache:invalidate:daily_fortune', target_date or 'all')
                except Exception as e:
                    logger.warning(f"⚠️  发布缓存失效事件失败: {e}")
                
                logger.info(f"✅ 已清理每日运势服务缓存: {deleted_count} 条（日期: {target_date or 'all'}）")
        except Exception as e:
            logger.warning(f"⚠️  缓存失效操作失败（不影响业务）: {e}")

