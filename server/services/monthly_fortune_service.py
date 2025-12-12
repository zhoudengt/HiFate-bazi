#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月运势分析服务 - 基于八字的本月运势分析
结合用户八字、大运、流年、流月，分析本月运势
"""

import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime, date
import calendar

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.services.bazi_service import BaziService
from server.services.bazi_detail_service import BaziDetailService
from server.services.rule_service import RuleService
from server.utils.data_validator import validate_bazi_data


class MonthlyFortuneService:
    """月运势分析服务"""
    
    @staticmethod
    def calculate_monthly_fortune(
        solar_date: str,
        solar_time: str,
        gender: str,
        target_month: Optional[str] = None,
        use_llm: bool = False,
        access_token: Optional[str] = None,
        bot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        计算月运势分析
        
        Args:
            solar_date: 用户出生日期（阳历）
            solar_time: 用户出生时间
            gender: 性别
            target_month: 目标月份（可选，默认为本月），格式：YYYY-MM
            use_llm: 是否使用 LLM 生成（可选，默认使用规则匹配）
            access_token: Coze Access Token（可选，use_llm=True 时需要）
            bot_id: Coze Bot ID（可选，use_llm=True 时需要）
            
        Returns:
            dict: 包含月运势分析结果
        """
        try:
            # 1. 确定目标月份
            if target_month:
                year, month = map(int, target_month.split('-'))
                target = date(year, month, 1)
            else:
                today = date.today()
                target = date(today.year, today.month, 1)
            
            target_datetime = datetime.combine(target, datetime.min.time())
            
            # 2. 计算用户八字（复用现有服务）
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
            
            # 3. 计算详细八字信息（包含流年流月，复用现有服务）
            detail_result = BaziDetailService.calculate_detail_full(
                solar_date,
                solar_time,
                gender,
                current_time=target_datetime,
                target_year=target.year  # 指定目标年份，获取流月数据
            )
            
            if not detail_result:
                return {
                    "success": False,
                    "error": "详细八字计算失败",
                    "fortune": None
                }
            
            # 4. 提取流月信息
            liuyue_info = MonthlyFortuneService._extract_liuyue_info(detail_result, target)
            
            # 5. 匹配月运势规则（复用规则系统）
            matched_rules = RuleService.match_rules(
                bazi_data,
                rule_types=['fortune', 'monthly', 'annual'],  # 运势相关规则
                use_cache=True
            )
            
            # 6. 生成月运势分析
            if use_llm:
                # 使用 LLM 生成（可选）
                fortune_analysis = MonthlyFortuneService._generate_with_llm(
                    bazi_data,
                    liuyue_info,
                    target,
                    access_token,
                    bot_id
                )
            else:
                # 使用规则匹配生成
                fortune_analysis = MonthlyFortuneService._generate_with_rules(
                    bazi_data,
                    liuyue_info,
                    matched_rules,
                    target
                )
            
            return {
                "success": True,
                "target_month": target.strftime("%Y-%m"),
                "bazi_data": bazi_data,
                "liuyue_info": liuyue_info,
                "fortune": fortune_analysis,
                "matched_rules_count": len(matched_rules)
            }
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"计算月运势异常: {str(e)}\n{traceback.format_exc()}",
                "fortune": None
            }
    
    @staticmethod
    def _extract_liuyue_info(detail_result: Dict[str, Any], target_date: date) -> Dict[str, Any]:
        """提取流月信息（直接使用LunarConverter计算当月干支）"""
        from src.tool.LunarConverter import LunarConverter
        
        liuyue_info = {
            "month": target_date.strftime("%Y-%m"),
            "year": target_date.year,
            "month_num": target_date.month,
            "liuyue": None,
            "liunian": None,
            "dayun": None
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
            
            # 获取当月的年月干支（返回字典格式）
            year_ganzhi_dict = LunarConverter.get_year_ganzhi(target_date.year)
            month_ganzhi_dict = LunarConverter.get_month_ganzhi(target_date.year, target_date.month, 1)
            
            # 提取月干支和五行
            if isinstance(month_ganzhi_dict, dict) and 'stem' in month_ganzhi_dict and 'branch' in month_ganzhi_dict:
                month_stem = month_ganzhi_dict['stem']
                month_branch = month_ganzhi_dict['branch']
                month_element = stem_elements.get(month_stem, '未知')
                
                liuyue_info['liuyue'] = {
                    'ganzhi': f"{month_stem}{month_branch}",
                    'stem': {'char': month_stem, 'element': month_element},
                    'branch': {'char': month_branch}
                }
            
            # 提取年干支和五行
            if isinstance(year_ganzhi_dict, dict) and 'stem' in year_ganzhi_dict and 'branch' in year_ganzhi_dict:
                year_stem = year_ganzhi_dict['stem']
                year_branch = year_ganzhi_dict['branch']
                year_element = stem_elements.get(year_stem, '未知')
                
                liuyue_info['liunian'] = {
                    'ganzhi': f"{year_stem}{year_branch}",
                    'stem': {'char': year_stem, 'element': year_element},
                    'branch': {'char': year_branch}
                }
        except Exception as e:
            # 计算失败时返回默认值
            import logging
            logging.warning(f"流月信息计算失败: {e}")
        
        return liuyue_info
    
    @staticmethod
    def _analyze_by_bazi(
        bazi_data: Dict[str, Any],
        liuyue_info: Dict[str, Any],
        matched_rules: list,
        target_date: date
    ) -> tuple:
        """基于八字分析本月运势"""
        # 提取关键信息
        day_element = bazi_data.get('elements', {}).get('day', {}).get('stem_element', '土')
        element_counts = bazi_data.get('element_counts', {})
        
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
                except:
                    totals = {}
            else:
                totals = {}
        ten_gods_stats = totals
        
        # 流月五行
        liuyue_stem_element = '未知'
        if isinstance(liuyue_info.get('liuyue'), dict):
            liuyue_stem_element = liuyue_info['liuyue'].get('stem', {}).get('element', '未知')
        
        # 五行生克关系影响评分
        element_relation = MonthlyFortuneService._get_element_relation(day_element, liuyue_stem_element)
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
        career_text = MonthlyFortuneService._generate_career_fortune(day_element, liuyue_stem_element, element_relation, ten_gods_stats)
        wealth_text = MonthlyFortuneService._generate_wealth_fortune(day_element, liuyue_stem_element, element_relation, ten_gods_stats)
        love_text = MonthlyFortuneService._generate_love_fortune(day_element, liuyue_stem_element, element_relation, ten_gods_stats)
        health_text = MonthlyFortuneService._generate_health_fortune(day_element, element_counts, element_relation)
        advice = MonthlyFortuneService._generate_advice_by_relation(element_relation, day_element, liuyue_stem_element)
        
        return career_text, wealth_text, love_text, health_text, base_score, advice
    
    @staticmethod
    def _get_element_relation(day_element: str, liuyue_element: str) -> str:
        """获取五行生克关系"""
        sheng_cycle = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
        ke_cycle = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}
        
        if day_element == liuyue_element:
            return '比和'
        elif sheng_cycle.get(liuyue_element) == day_element:
            return '生我'
        elif sheng_cycle.get(day_element) == liuyue_element:
            return '我生'
        elif ke_cycle.get(liuyue_element) == day_element:
            return '克我'
        elif ke_cycle.get(day_element) == liuyue_element:
            return '我克'
        return '平和'
    
    @staticmethod
    def _generate_career_fortune(day_element: str, liuyue_element: str, relation: str, ten_gods: dict) -> str:
        """生成事业运势"""
        # 【防御性代码】确保 ten_gods 是字典类型
        if not isinstance(ten_gods, dict):
            ten_gods = {}
        
        templates = {
            '生我': f"本月得{liuyue_element}相生，事业运势向好，适合推进重点项目，扩展业务。得上级赏识，晋升有望。",
            '我克': f"日主{day_element}克{liuyue_element}，本月事业运有利，适合主动争取机会，展现领导力。决策果断，易获成功。",
            '比和': f"本月与日主{day_element}比和，事业运势平稳，适合巩固基础，加强团队建设。合作顺利。",
            '我生': f"日主{day_element}生{liuyue_element}，本月事业付出较多，需注意平衡工作与休息。适合培养团队，长远投资。",
            '克我': f"本月受{liuyue_element}克制，事业运势需谨慎，宜低调行事，避免冲突。以守为攻，等待时机。"
        }
        
        base_text = templates.get(relation, "本月事业运势平稳，稳扎稳打推进工作即可。")
        
        # 根据十神补充（添加防御性检查）
        zhengguan = ten_gods.get('正官') if isinstance(ten_gods, dict) else {}
        if isinstance(zhengguan, dict) and zhengguan.get('count', 0) > 0:
            base_text += "命中正官，适合处理正式事务，遵守规则。"
        else:
            pian_guan = ten_gods.get('偏官') if isinstance(ten_gods, dict) else {}
            if isinstance(pian_guan, dict) and pian_guan.get('count', 0) > 0:
                base_text += "七杀在命，适合开拓创新，突破常规。"
        
        return base_text
    
    @staticmethod
    def _generate_wealth_fortune(day_element: str, liuyue_element: str, relation: str, ten_gods: dict) -> str:
        """生成财运"""
        templates = {
            '我克': f"日主{day_element}克{liuyue_element}为财，本月财运旺盛，投资理财时机好，把握商机可获利。",
            '生我': f"本月得{liuyue_element}相生，财运稳中有升，适合稳健投资，多方经营。",
            '比和': f"本月财运平稳，收入稳定，适合储蓄理财，控制开支。",
            '克我': f"本月受{liuyue_element}克制，财运稍弱，避免大额投资，守财为上。",
            '我生': f"本月泄气，财运一般，开支可能增加，需理性消费，避免浪费。"
        }
        
        base_text = templates.get(relation, "本月财运平稳，建议理性理财。")
        
        # 【防御性代码】确保 ten_gods 是字典类型
        if not isinstance(ten_gods, dict):
            ten_gods = {}
        
        # 根据十神补充（添加防御性检查）
        zhengcai = ten_gods.get('正财') if isinstance(ten_gods, dict) else {}
        if isinstance(zhengcai, dict) and zhengcai.get('count', 0) > 0:
            base_text += "正财在命，工资收入稳定，可增加储蓄。"
        else:
            piancai = ten_gods.get('偏财') if isinstance(ten_gods, dict) else {}
            if isinstance(piancai, dict) and piancai.get('count', 0) > 0:
                base_text += "偏财在命，投资理财有机会，但需谨慎。"
        
        return base_text
    
    @staticmethod
    def _generate_love_fortune(day_element: str, liuyue_element: str, relation: str, ten_gods: dict) -> str:
        """生成感情运势"""
        templates = {
            '生我': f"本月得{liuyue_element}相生，感情运势佳，单身者桃花运旺，有缘分出现。恋爱中感情升温，适合表白或定亲。",
            '比和': f"本月感情运势平和，与伴侣关系稳定，适合共同规划未来，增进默契。",
            '我克': f"本月感情运势尚可，主动关心对方，但避免过于强势，多倾听对方想法。",
            '我生': f"本月感情付出较多，对伴侣体贴关怀，真诚沟通可增进感情。",
            '克我': f"本月感情需注意，可能有摩擦，多包容理解，避免争吵。单身者缘分稍弱，顺其自然。"
        }
        
        return templates.get(relation, "本月感情运势平稳，适合与伴侣互动交流。")
    
    @staticmethod
    def _generate_health_fortune(day_element: str, element_counts: dict, relation: str) -> str:
        """生成健康运势"""
        # 【防御性代码】确保 element_counts 是字典类型
        if not isinstance(element_counts, dict):
            element_counts = {}
        
        weak_elements = [elem for elem, count in element_counts.items() if count < 2]
        
        health_tips = {
            '木': "注意肝胆保养，多食绿色蔬菜，保持心情舒畅",
            '火': "注意心脏和血液循环，保持情绪平和，避免熬夜",
            '土': "注意脾胃消化，规律饮食，避免暴饮暴食",
            '金': "注意呼吸系统和皮肤，适量运动，增强体质",
            '水': "注意肾脏和泌尿系统，多喝水，注意保暖"
        }
        
        base_text = "本月健康运势尚可，注意劳逸结合，规律作息。"
        
        if relation == '克我':
            base_text = "本月受克，身体稍弱，避免过度劳累，注意休息，增强免疫力。"
        elif relation == '生我':
            base_text = "本月得生，精力充沛，适合运动锻炼，增强体质。"
        elif relation == '我生':
            base_text = "本月泄气，注意补充营养，避免过度消耗，调养生息。"
        
        if weak_elements:
            tips = health_tips.get(weak_elements[0], '')
            if tips:
                base_text += tips + "。"
        
        return base_text
    
    @staticmethod
    def _generate_advice_by_relation(relation: str, day_element: str, liuyue_element: str) -> str:
        """根据五行关系生成本月建议"""
        advice_templates = {
            '生我': f"本月得{liuyue_element}相生，运势向好。建议：把握机遇，主动出击；发挥优势，展现才华；多与贵人合作，扩展人脉。",
            '我克': f"日主{day_element}克{liuyue_element}，本月有利。建议：果断决策，积极行动；把握财运，合理投资；注意不要过于强势，兼顾他人。",
            '比和': f"本月比和，运势平稳。建议：稳步推进工作计划；加强团队协作；巩固现有成果，为下月蓄力。",
            '我生': f"本月泄气，需注意能量。建议：量力而行，避免过度付出；注重休息调养；做好长远规划，培养后备力量。",
            '克我': f"本月受{liuyue_element}克制，需谨慎。建议：低调行事，避免冲突；以守代攻，积蓄力量；保持耐心，等待转机。"
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
    def _generate_with_rules(
        bazi_data: Dict[str, Any],
        liuyue_info: Dict[str, Any],
        matched_rules: list,
        target_date: date
    ) -> Dict[str, Any]:
        """使用规则匹配生成月运势分析（基于八字动态生成）"""
        # 添加数据类型验证
        if not isinstance(bazi_data, dict):
            raise TypeError(f"bazi_data 必须是字典类型，但实际是: {type(bazi_data).__name__}，值: {str(bazi_data)[:100]}")
        
        lines = []
        
        month_str = f"{target_date.year}年{target_date.month}月"
        lines.append(f"【{month_str}运势分析】")
        lines.append("=" * 60)
        lines.append("")
        
        # 提取八字关键信息
        day_stem = bazi_data.get('bazi_pillars', {}).get('day', {}).get('stem', '未知')
        day_branch = bazi_data.get('bazi_pillars', {}).get('day', {}).get('branch', '未知')
        day_element = bazi_data.get('elements', {}).get('day', {}).get('stem_element', '未知')
        
        # 流月信息
        liuyue_ganzhi = liuyue_info.get('liuyue', {}).get('ganzhi', '未知') if isinstance(liuyue_info.get('liuyue'), dict) else '未知'
        liunian_ganzhi = liuyue_info.get('liunian', {}).get('ganzhi', '未知') if isinstance(liuyue_info.get('liunian'), dict) else '未知'
        
        lines.append(f"八字日干：{day_stem}{day_branch}（{day_element}）")
        if liuyue_ganzhi != '未知':
            lines.append(f"流月：{liuyue_ganzhi}")
        if liunian_ganzhi != '未知':
            lines.append(f"流年：{liunian_ganzhi}")
        lines.append("")
        
        # 基于八字生成运势分析
        career_text, wealth_text, love_text, health_text, overall_score, advice = MonthlyFortuneService._analyze_by_bazi(
            bazi_data, liuyue_info, matched_rules, target_date
        )
        
        # 月度概况
        lines.append("【月度概况】")
        if matched_rules:
            summary_text = MonthlyFortuneService._generate_summary(matched_rules)
            lines.append(summary_text)
        else:
            lines.append(f"日主{day_element}，{month_str}{liuyue_ganzhi}。" + advice.split('。')[0] + "。")
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
        
        # 本月建议
        lines.append("【本月建议】")
        lines.append(advice)
        lines.append("")
        
        # 重要日期（本月的关键节点）
        lines.append("【重要日期】")
        important_dates = MonthlyFortuneService._generate_important_dates(target_date)
        for date_info in important_dates:
            lines.append(f"  {date_info['date']}：{date_info['description']}")
        lines.append("")
        lines.append("以上分析基于八字命理，仅供参考。")
        
        # 组织为字典格式返回
        fortune_text = "\n".join(lines)
        
        return {
            "full_text": fortune_text,
            "month": f"{target_date.year}年{target_date.month}月",
            "summary": f"{day_element}日主，{month_str}运势分析",
            "career": career_text,
            "wealth": wealth_text,
            "love": love_text,
            "health": health_text,
            "advice": advice,
            "important_dates": important_dates,
            "overall_score": overall_score,
            "categories": {
                "career": MonthlyFortuneService._get_category_level(overall_score + 5),
                "wealth": MonthlyFortuneService._get_category_level(overall_score),
                "love": MonthlyFortuneService._get_category_level(overall_score - 5),
                "health": MonthlyFortuneService._get_category_level(overall_score)
            }
        }
    
    @staticmethod
    def _generate_summary(matched_rules: list) -> str:
        """生成月度概况"""
        if not matched_rules:
            return "本月运势平稳。"
        
        # 从前3条规则中提取关键信息
        summary_parts = []
        for rule in matched_rules[:3]:
            content = rule.get('content', {})
            text = content.get('text', '')
            if text and len(summary_parts) < 3:
                # 取前50个字
                summary_parts.append(text[:50])
        
        return "；".join(summary_parts) if summary_parts else "本月运势平稳。"
    
    @staticmethod
    def _generate_advice(matched_rules: list) -> str:
        """生成本月建议"""
        if not matched_rules:
            return "保持积极心态，稳步前进。"
        
        # 从规则中提取建议
        for rule in matched_rules[:5]:
            content = rule.get('content', {})
            advice = content.get('advice', '')
            if advice:
                return advice
        
        return "把握机会，注意防范风险，保持平衡心态。"
    
    @staticmethod
    def _generate_important_dates(target_date: date) -> list:
        """生成重要日期提醒"""
        important_dates = []
        
        # 月初（1-5日）
        important_dates.append({
            "date": f"{target_date.month}月1-5日",
            "description": "月初，适合制定计划，开启新的工作项目。"
        })
        
        # 月中（10-15日）
        important_dates.append({
            "date": f"{target_date.month}月10-15日",
            "description": "月中，适合推进重要事务，把握机遇。"
        })
        
        # 月末（最后5天）
        last_day = calendar.monthrange(target_date.year, target_date.month)[1]
        important_dates.append({
            "date": f"{target_date.month}月{last_day-4}-{last_day}日",
            "description": "月末，适合总结反思，准备下月计划。"
        })
        
        return important_dates
    
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
        liuyue_info: Dict[str, Any],
        target_date: date,
        access_token: Optional[str],
        bot_id: Optional[str]
    ) -> Dict[str, Any]:
        """使用 LLM 生成月运势（可选功能）"""
        # 这里可以集成 Coze AI 或其他 LLM
        # 暂时返回规则生成结果
        return MonthlyFortuneService._generate_with_rules(bazi_data, liuyue_info, [], target_date)

