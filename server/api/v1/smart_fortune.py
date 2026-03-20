# -*- coding: utf-8 -*-
"""
智能运势分析API - 基于Intent Service
"""
from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any, List, Tuple, AsyncGenerator
import sys
import os
import json
import logging
import asyncio
from server.utils.async_executor import get_executor

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from server.services.intent_client import IntentServiceClient
from server.services.bazi_service import BaziService
from server.services.fortune_llm_client import get_fortune_llm_client
from server.services.llm_service_factory import LLMServiceFactory
from server.utils.performance_monitor import PerformanceMonitor
from server.utils.prompt_builders import format_smart_fortune_for_llm
from core.calculators.BaziCalculator import BaziCalculator
from server.utils.dayun_liunian_helper import (
    calculate_user_age,
    get_current_dayun,
    build_enhanced_dayun_structure
)
from server.api.base.stream_handler import generate_request_id

router = APIRouter()
bazi_service = BaziService()

# 关键词到规则类型的映射（当意图识别失败时使用）
# 注意：映射到数据库中实际存在的规则类型
KEYWORD_TO_RULE_TYPE = {
    "财": "wealth",
    "发财": "wealth",
    "财运": "wealth",
    "赚钱": "wealth",
    "收入": "wealth",
    "投资": "wealth",
    "事业": "character",  # 数据库中没有career类型，映射到character（性格影响事业）
    "工作": "character",  # 同上
    "职业": "character",  # 同上
    "升职": "character",  # 同上
    "婚姻": "marriage",
    "结婚": "marriage",
    "恋爱": "marriage",
    "感情": "marriage",
    "对象": "marriage",
    "健康": "health",
    "身体": "health",
    "疾病": "health",
    "性格": "character",
    "脾气": "character",
    "命": "general",
}

# Category到规则类型的映射（场景2直接使用，不需要意图识别）
CATEGORY_TO_RULE_TYPE = {
    "事业财富": "wealth",  # 根据实际数据库规则类型调整
    "婚姻": "marriage",
    "健康": "health",
    "子女": "children",
    "流年运势": "general",
    "年运报告": "general"
}

def _extract_rule_types_from_question(question: str) -> list:
    """
    从问题中提取关键词，映射到规则类型
    """
    rule_types = []
    for keyword, rule_type in KEYWORD_TO_RULE_TYPE.items():
        if keyword in question:
            if rule_type not in rule_types:
                rule_types.append(rule_type)
    
    return rule_types if rule_types else ["ALL"]


@router.get("/smart-analyze", deprecated=True)
async def smart_analyze(
    question: str = Query(..., description="用户问题"),
    year: int = Query(..., description="出生年份"),
    month: int = Query(..., description="出生月份"),
    day: int = Query(..., description="出生日期"),
    hour: int = Query(12, description="出生时辰（0-23）"),
    gender: str = Query(..., description="性别（male/female）"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    include_fortune_context: bool = Query(False, description="是否包含流年大运分析（实验性功能，默认关闭）")
):
    """
    智能运势分析
    
    ⚠️ **接口已标记为下线（deprecated）**
    
    此接口已标记为下线，建议使用流式接口：`GET /api/v1/smart-fortune/smart-analyze-stream`
    流式接口返回相同的分析结果，并额外提供流式输出体验。
    
    自动识别用户问题意图，返回针对性的分析结果
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ [DEPRECATED] 非流式接口 /smart-fortune/smart-analyze 已标记为下线，建议使用流式接口 /smart-fortune/smart-analyze-stream")
    # 初始化性能监控器
    monitor = PerformanceMonitor()
    
    try:
        # ==================== 阶段1：意图识别 ====================
        with monitor.stage("intent_recognition", "意图识别", question=question):
            intent_client = IntentServiceClient()
            intent_result = intent_client.classify(
                question=question,
                user_id=user_id or "anonymous"
            )
            
            # 防御性检查：确保intent_result不为None
            if intent_result is None:
                logger.warning("[smart_fortune] intent_result is None, using default")
                intent_result = {
                    "intents": ["general"],
                    "confidence": 0.5,
                    "keywords": [],
                    "is_ambiguous": True,
                    "time_intent": None,
                    "is_fortune_related": True
                }
            
            monitor.add_metric("intent_recognition", "intents_count", len(intent_result.get("intents", [])))
            monitor.add_metric("intent_recognition", "confidence", intent_result.get("confidence", 0))
            monitor.add_metric("intent_recognition", "method", intent_result.get("method", "unknown"))
            
            # ==================== 记录用户问题（用于模型微调）====================
            try:
                from server.services.intent_question_logger import get_question_logger
                question_logger = get_question_logger()
                solar_date = f"{year:04d}-{month:02d}-{day:02d}"
                solar_time = f"{hour:02d}:00"
                question_logger.log_question(
                    question=question,
                    intent_result=intent_result,
                    user_id=user_id,
                    session_id=None,  # 可以后续添加session管理
                    solar_date=solar_date,
                    solar_time=solar_time,
                    gender=gender
                )
            except Exception as e:
                logger.warning(f"[smart_fortune] 记录用户问题失败: {e}", exc_info=True)
                # 不影响主流程，仅记录警告
        
        # 如果问题不相关（LLM已判断）
        if not intent_result.get("is_fortune_related", True) or "non_fortune" in intent_result.get("intents", []):
            monitor.log_summary()
            return {
                "success": False,
                "message": intent_result.get("reject_message", "您的问题似乎与命理运势无关，我只能回答关于八字、运势等相关问题。"),
                "intent_result": intent_result,
                "performance": monitor.get_summary()
            }
        
        # 获取时间意图（LLM已识别）
        time_intent = intent_result.get("time_intent", {})
        target_years = time_intent.get("target_years", []) if time_intent else []
        logger.info(f"[smart_fortune] 时间意图识别: {time_intent.get('description', 'N/A')} -> {target_years}")
        
        # ==================== 阶段2：八字计算 ====================
        solar_date = f"{year:04d}-{month:02d}-{day:02d}"
        solar_time = f"{hour:02d}:00"
        
        with monitor.stage("bazi_calculation", "八字计算", solar_date=solar_date, solar_time=solar_time, gender=gender):
            calculator = BaziCalculator(solar_date, solar_time, gender)
            bazi_result = calculator.calculate()
            
            if not bazi_result or "error" in bazi_result:
                raise HTTPException(status_code=400, detail="八字计算失败")
        
        # ==================== 阶段3：规则匹配 ====================
        rule_types = intent_result.get("rule_types", ["ALL"])
        confidence = intent_result.get("confidence", 0)
        
        # 如果意图识别置信度低（<60%），使用关键词fallback
        if confidence < 0.6 and "ALL" in rule_types:
            with monitor.stage("intent_fallback", "意图识别回退（关键词匹配）"):
                fallback_types = _extract_rule_types_from_question(question)
                if fallback_types != ["ALL"]:
                    rule_types = fallback_types
                    intent_result["rule_types"] = rule_types
                    intent_result["fallback_used"] = True
                    intent_result["intents"] = fallback_types
        
        with monitor.stage("rule_matching", "规则匹配", rule_types=rule_types):
            matched_rules = []
            for rule_type in rule_types:
                if rule_type != "ALL":
                    rules = bazi_service._match_rules(bazi_result, [rule_type])
                    matched_rules.extend(rules)
            
            # 如果是综合分析或没有匹配到特定规则
            if not matched_rules or "ALL" in rule_types:
                rules = bazi_service._match_rules(bazi_result)
                matched_rules = rules
            
            monitor.add_metric("rule_matching", "matched_rules_count", len(matched_rules))
            monitor.add_metric("rule_matching", "rule_types_count", len(rule_types))
            
            # 统计各类型规则数量
            if matched_rules:
                rule_type_counts = {}
                for rule in matched_rules:
                    rt = rule.get('rule_type', 'unknown')
                    rule_type_counts[rt] = rule_type_counts.get(rt, 0) + 1
                monitor.add_metric("rule_matching", "rule_type_counts", rule_type_counts)
                logger.info(f"规则匹配结果: 匹配到{len(matched_rules)}条规则，意图={rule_types}, 统计={rule_type_counts}")
        
        # ==================== 阶段4：流年大运分析（可选）====================
        fortune_context = None
        if include_fortune_context:
            with monitor.stage("fortune_context", "流年大运分析", target_years=target_years, rule_types=rule_types):
                try:
                    from server.orchestrators.fortune_context_service import FortuneContextService
                    
                    fortune_context = FortuneContextService.get_fortune_context(
                        solar_date=solar_date,
                        solar_time=solar_time,
                        gender=gender,
                        intent_types=rule_types,
                        target_years=target_years
                    )
                    
                    if fortune_context:
                        liunian_list = fortune_context.get('time_analysis', {}).get('liunian_list', [])
                        monitor.add_metric("fortune_context", "liunian_count", len(liunian_list))
                        logger.info(f"流年大运分析完成: {len(liunian_list)}个流年")
                except Exception as e:
                    logger.error(f"流年大运分析失败: {e}", exc_info=True)
                    monitor.end_stage("fortune_context", success=False, error=str(e))
        
        # ==================== 阶段5：LLM深度解读（可选）====================
        llm_deep_analysis = None
        if fortune_context:
            with monitor.stage("llm_analysis", "LLM深度解读", intent=rule_types[0] if rule_types else "general"):
                try:
                    llm_client = get_fortune_llm_client()
                    main_intent = rule_types[0] if rule_types and rule_types[0] != "ALL" else "general"
                    
                    llm_result = llm_client.analyze_fortune(
                        intent=main_intent,
                        question=question,
                        bazi_data=bazi_result,
                        fortune_context=fortune_context,
                        matched_rules=matched_rules
                    )
                    
                    if llm_result.get("success"):
                        llm_deep_analysis = llm_result.get("analysis")
                        monitor.add_metric("llm_analysis", "analysis_length", len(llm_deep_analysis) if llm_deep_analysis else 0)
                        logger.info(f"LLM深度分析生成成功，长度：{len(llm_deep_analysis) if llm_deep_analysis else 0}")
                    else:
                        monitor.end_stage("llm_analysis", success=False, error=llm_result.get('error', 'Unknown error'))
                        logger.warning(f"LLM深度分析失败: {llm_result.get('error')}")
                except Exception as e:
                    logger.error(f"LLM深度分析异常: {e}", exc_info=True)
                    monitor.end_stage("llm_analysis", success=False, error=str(e))
            
        # ==================== 阶段6：生成响应文本 ====================
        with monitor.stage("response_generation", "生成响应文本"):
            if fortune_context:
                response_text = _generate_response_with_fortune(
                    question=question,
                    intent_result=intent_result,
                    bazi_result=bazi_result,
                    matched_rules=matched_rules,
                    fortune_context=fortune_context,
                    llm_deep_analysis=llm_deep_analysis
                )
            else:
                response_text = _generate_response(
                    question=question,
                    intent_result=intent_result,
                    bazi_result=bazi_result,
                    matched_rules=matched_rules
                )
            
            monitor.add_metric("response_generation", "response_length", len(response_text))
        
        # ==================== 构建最终结果 ====================
        bazi_pillars = bazi_result.get("bazi_pillars", {})
        formatted_pillars = {}
        if bazi_pillars:
            pillar_names = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
            for eng_name, cn_name in pillar_names.items():
                if eng_name in bazi_pillars:
                    formatted_pillars[cn_name] = {
                        "天干": bazi_pillars[eng_name].get("stem", ""),
                        "地支": bazi_pillars[eng_name].get("branch", "")
                    }
        
        result = {
            "success": True,
            "question": question,
            "intent_result": intent_result,
            "bazi_info": {
                "四柱": formatted_pillars,
                "十神": bazi_result.get("ten_gods_stats", {}),
                "五行": bazi_result.get("element_counts", {})
            },
            "matched_rules_count": len(matched_rules),
            "response": response_text,
            "performance": monitor.get_summary()  # ⭐ 添加性能摘要
        }
        
        if fortune_context:
            result["fortune_context"] = fortune_context
        
        # 输出性能摘要
        monitor.log_summary()
        
        return result
        
    except Exception as e:
        monitor.end_stage(monitor.current_stage or "unknown", success=False, error=str(e))
        monitor.log_summary()
        logger.error(f"[smart_fortune] 请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _generate_response_with_fortune(
    question: str,
    intent_result: dict,
    bazi_result: dict,
    matched_rules: list,
    fortune_context: dict,
    llm_deep_analysis: str = None
) -> str:
    """生成包含流年大运的增强版回答"""
    intents = intent_result.get("intents", [])
    confidence = intent_result.get("confidence", 0.0)
    
    # 开头
    response = f"根据您的问题「{question}」，"
    
    if confidence < 0.75:
        response += "我理解您可能想了解多方面的运势情况。"
    else:
        intent_names = {
            "career": "事业运势",
            "wealth": "财富运势",
            "marriage": "婚姻感情",
            "health": "健康运势",
            "character": "性格特点",
            "personality": "性格特点",
            "general": "综合运势"
        }
        intent_text = "、".join([intent_names.get(i, i) for i in intents])
        response += f"我将为您分析{intent_text}方面的情况。\n\n"
    
    # 八字基本信息
    bazi_pillars = bazi_result.get("bazi_pillars", {})
    day_pillar = bazi_pillars.get("day", {})
    day_stem = day_pillar.get("stem", "未知")
    day_branch = day_pillar.get("branch", "")
    
    response += f"【八字信息】\n"
    response += f"日主：{day_stem}{day_branch}\n"
    
    element_counts = bazi_result.get("element_counts", {})
    if element_counts:
        element_text = " ".join([f"{k}{v}" for k, v in element_counts.items()])
        response += f"五行：{element_text}\n\n"
    
    # 🆕 流年大运分析
    if fortune_context:
        time_analysis = fortune_context.get("time_analysis", {})
        fortune_summary = fortune_context.get("fortune_summary", {})
        
        if time_analysis:
            response += f"【{time_analysis.get('period', '时运')}分析】\n"
            
            # 显示流年大运基本信息
            if time_analysis.get("type") == "yearly":
                is_multi = time_analysis.get("is_multi_year", False)
                liunian_list = time_analysis.get("liunian_list", [])
                dayun = time_analysis.get("dayun", {})
                
                # 显示大运
                if dayun:
                    response += f"当前大运：{dayun.get('stem', '')}{dayun.get('branch', '')} "
                    start_age = dayun.get('start_age')
                    if start_age:
                        response += f"（{start_age}岁起）"
                    response += "\n"
                
                # 显示流年（单年或多年）
                if is_multi and len(liunian_list) > 1:
                    response += f"\n对比{len(liunian_list)}年流年：\n"
                    for liunian in liunian_list:
                        year = liunian.get('year', '')
                        stem = liunian.get('stem', '')
                        branch = liunian.get('branch', '')
                        
                        # 五行
                        elements = []
                        if liunian.get('stem_element'):
                            elements.append(liunian['stem_element'])
                        if liunian.get('branch_element'):
                            elements.append(liunian['branch_element'])
                        element_str = "、".join(set(elements)) if elements else ""
                        
                        response += f"  • {year}年：{stem}{branch}"
                        if element_str:
                            response += f"（{element_str}）"
                        
                        # ⭐ 显示特殊关系（岁运并临、天克地冲、天合地合）
                        relations = liunian.get('relations', [])
                        if relations:
                            relation_types = []
                            for rel in relations:
                                rel_type = rel.get('type', '') if isinstance(rel, dict) else str(rel)
                                if rel_type:
                                    relation_types.append(rel_type)
                            if relation_types:
                                response += f"\n    ⚠️ 特殊年份：{', '.join(relation_types)}"
                        
                        # ⭐ 添加深度分析
                        balance_analysis = liunian.get('balance_analysis', {})
                        if balance_analysis:
                            summary = balance_analysis.get('analysis', {}).get('summary', '')
                            if summary:
                                response += f"\n    📊 {summary}"
                        
                        relation_analysis = liunian.get('relation_analysis', {})
                        if relation_analysis:
                            rel_summary = relation_analysis.get('summary', '')
                            if rel_summary and "无明显" not in rel_summary:
                                response += f"\n    🔗 {rel_summary}"
                        
                        response += "\n"
                    response += "\n"
                elif liunian_list:
                    # 单年
                    liunian = liunian_list[0]
                    response += f"当年流年：{liunian.get('stem', '')}{liunian.get('branch', '')} "
                    response += f"（{liunian.get('year', '')}年）\n"
                    
                    # ⭐ 显示特殊关系（岁运并临、天克地冲、天合地合）
                    relations = liunian.get('relations', [])
                    if relations:
                        relation_types = []
                        for rel in relations:
                            rel_type = rel.get('type', '') if isinstance(rel, dict) else str(rel)
                            if rel_type:
                                relation_types.append(rel_type)
                        if relation_types:
                            response += f"⚠️ 特殊年份：{', '.join(relation_types)}\n"
                    
                    # ⭐ 添加深度分析（单年）
                    balance_analysis = liunian.get('balance_analysis', {})
                    if balance_analysis:
                        summary = balance_analysis.get('analysis', {}).get('summary', '')
                        if summary:
                            response += f"📊 五行平衡：{summary}\n"
                    
                    relation_analysis = liunian.get('relation_analysis', {})
                    if relation_analysis:
                        rel_summary = relation_analysis.get('summary', '')
                        if rel_summary and "无明显" not in rel_summary:
                            response += f"🔗 关系分析：{rel_summary}\n"
                    
                    response += "\n"
            
            elif time_analysis.get("type") == "monthly":
                response += f"本月：{time_analysis.get('period', '')}\n\n"
            
            elif time_analysis.get("type") == "daily":
                response += f"今日：{time_analysis.get('period', '')}\n\n"
            
            # 显示各方面的时运分析
            intent_emoji = {
                "wealth": "💰",
                "character": "💼",
                "marriage": "💕",
                "health": "🏥"
            }
            
            intent_names_map = {
                "wealth": "财运",
                "character": "事业",
                "marriage": "感情",
                "health": "健康"
            }
            
            for intent in intents:
                if intent in fortune_summary and fortune_summary[intent]:
                    emoji = intent_emoji.get(intent, "📊")
                    name = intent_names_map.get(intent, intent)
                    
                    response += f"{emoji} **时运{name}分析**\n"
                    # 多年对比的分析已经包含换行，不需要额外处理
                    response += fortune_summary[intent] + "\n\n"
    
    # 🆕 LLM深度解读（如果有）
    if llm_deep_analysis:
        response += "【🔮 命理专家深度解读】\n\n"
        response += llm_deep_analysis + "\n\n"
        response += "="* 60 + "\n\n"
    
    # 八字命理规则分析
    response += "【八字命理分析】\n"
    
    if matched_rules:
        # 按意图分组规则
        intent_rules = {}
        for rule in matched_rules:
            rule_type = rule.get("rule_type", "general")
            if rule_type not in intent_rules:
                intent_rules[rule_type] = []
            intent_rules[rule_type].append(rule)
        
        # 规则类型中文名映射
        rule_type_names = {
            "wealth": "💰 财运分析",
            "career": "💼 事业分析",
            "marriage": "💕 婚配分析",
            "health": "🏥 健康分析",
            "character": "🎭 性格分析",
            "general": "📊 综合分析"
        }
        
        # 优先显示用户关心的类型
        user_intents = intent_result.get("intents", [])
        rule_types_order = []
        
        # 先添加用户意图对应的规则类型
        for intent in user_intents:
            if intent in intent_rules:
                rule_types_order.append(intent)
        
        # 再添加其他规则类型
        for rule_type in intent_rules.keys():
            if rule_type not in rule_types_order:
                rule_types_order.append(rule_type)
        
        # 按顺序显示规则
        total_shown = 0
        max_rules = 6  # 有流年大运时减少规则显示数量
        
        for rule_type in rule_types_order:
            if total_shown >= max_rules:
                break
            
            rules = intent_rules[rule_type]
            type_name = rule_type_names.get(rule_type, rule_type)
            
            # 如果是用户关心的类型，显示更多条；否则最多2条
            max_per_type = 3 if rule_type in user_intents else 2
            rules_to_show = min(len(rules), max_per_type, max_rules - total_shown)
            
            if rules_to_show > 0:
                response += f"\n{type_name}\n"
                
                for rule in rules[:rules_to_show]:
                    # ⭐ 修复：同时支持 content（单数）和 contents（复数）
                    desc = ""
                    
                    # 优先处理 contents（复数）- 日柱规则使用这种格式
                    contents = rule.get("contents", [])
                    if contents and isinstance(contents, list):
                        text_parts = []
                        for item in contents:
                            if isinstance(item, dict):
                                item_text = item.get("text", "")
                                if item_text:
                                    text_parts.append(item_text)
                            elif isinstance(item, str):
                                text_parts.append(item)
                        if text_parts:
                            desc = ' '.join(text_parts)
                    
                    # 如果没有 contents，尝试 content（单数）
                    if not desc:
                        content = rule.get("content", {})
                        if isinstance(content, dict):
                            desc = content.get("text", "")
                        else:
                            desc = str(content) if content else ""
                    
                    if desc:
                        desc = desc[:200] + "..." if len(desc) > 200 else desc
                        response += f"• {desc}\n"
                        total_shown += 1
    else:
        response += "暂无特定规则匹配。\n"
    
    # 结尾
    response += f"\n以上分析基于您的八字信息"
    if fortune_context:
        response += f"和{fortune_context.get('time_analysis', {}).get('period', '当前时运')}"
    response += "，仅供参考。"
    
    if intent_result.get("is_ambiguous"):
        response += "\n\n💡 如需更精准的分析，建议您提出更具体的问题，例如：\"我今年的事业运势如何？\"、\"我什么时候会结婚？\"等。"
    
    return response


def _generate_response(
    question: str,
    intent_result: dict,
    bazi_result: dict,
    matched_rules: list
) -> str:
    """生成自然语言回答"""
    intents = intent_result.get("intents", [])
    confidence = intent_result.get("confidence", 0.0)
    
    # 开头
    response = f"根据您的问题「{question}」，"
    
    if confidence < 0.75:
        response += "我理解您可能想了解多方面的运势情况。"
    else:
        intent_names = {
            "career": "事业运势",
            "wealth": "财富运势",
            "marriage": "婚姻感情",
            "health": "健康运势",
            "personality": "性格特点",
            "general": "综合运势"
        }
        intent_text = "、".join([intent_names.get(i, i) for i in intents])
        response += f"我将为您分析{intent_text}方面的情况。\n\n"
    
    # 八字基本信息（适配BaziCalculator的数据结构）
    bazi_pillars = bazi_result.get("bazi_pillars", {})
    day_pillar = bazi_pillars.get("day", {})
    day_stem = day_pillar.get("stem", "未知")
    day_branch = day_pillar.get("branch", "")
    
    response += f"【八字信息】\n"
    response += f"日主：{day_stem}{day_branch}\n"
    
    # 五行统计
    element_counts = bazi_result.get("element_counts", {})
    if element_counts:
        element_text = " ".join([f"{k}{v}" for k, v in element_counts.items()])
        response += f"五行：{element_text}\n\n"
    else:
        response += "五行：暂无数据\n\n"
    
    # 分析结果
    response += "【详细分析】\n"
    if matched_rules:
        # 按意图分组规则
        intent_rules = {}
        for rule in matched_rules:
            rule_type = rule.get("rule_type", "general")
            if rule_type not in intent_rules:
                intent_rules[rule_type] = []
            intent_rules[rule_type].append(rule)
        
        # 规则类型中文名映射
        rule_type_names = {
            "wealth": "💰 财运分析",
            "career": "💼 事业分析",
            "marriage": "💕 婚配分析",
            "health": "🏥 健康分析",
            "character": "🎭 性格分析",
            "general": "📊 综合分析"
        }
        
        # 优先显示用户关心的类型
        user_intents = intent_result.get("intents", [])
        rule_types_order = []
        
        # 先添加用户意图对应的规则类型
        for intent in user_intents:
            if intent in intent_rules:
                rule_types_order.append(intent)
        
        # 再添加其他规则类型
        for rule_type in intent_rules.keys():
            if rule_type not in rule_types_order:
                rule_types_order.append(rule_type)
        
        # 按顺序显示规则
        total_shown = 0
        max_rules = 8  # 总共最多显示8条规则
        
        for rule_type in rule_types_order:
            if total_shown >= max_rules:
                break
            
            rules = intent_rules[rule_type]
            type_name = rule_type_names.get(rule_type, rule_type)
            
            # 如果是用户关心的类型，显示更多条；否则最多2条
            max_per_type = 5 if rule_type in user_intents else 2
            rules_to_show = min(len(rules), max_per_type, max_rules - total_shown)
            
            if rules_to_show > 0:
                # 添加分类标题（总是显示，让用户知道这是哪个类型的分析）
                response += f"\n{type_name}\n"
                
                for rule in rules[:rules_to_show]:
                    # ⭐ 修复：同时支持 content（单数）和 contents（复数）
                    desc = ""
                    
                    # 优先处理 contents（复数）- 日柱规则使用这种格式
                    contents = rule.get("contents", [])
                    if contents and isinstance(contents, list):
                        text_parts = []
                        for item in contents:
                            if isinstance(item, dict):
                                item_text = item.get("text", "")
                                if item_text:
                                    text_parts.append(item_text)
                            elif isinstance(item, str):
                                text_parts.append(item)
                        if text_parts:
                            desc = ' '.join(text_parts)
                    
                    # 如果没有 contents，尝试 content（单数）
                    if not desc:
                        content = rule.get("content", {})
                        if isinstance(content, dict):
                            desc = content.get("text", "")
                        else:
                            desc = str(content) if content else ""
                    
                    if desc:
                        # 限制每条规则的长度，避免过长
                        desc = desc[:200] + "..." if len(desc) > 200 else desc
                        response += f"• {desc}\n"
                        total_shown += 1
    else:
        response += "暂无特定规则匹配，建议查看综合运势分析。\n"
    
    # 结尾
    response += f"\n以上分析基于您的八字信息，仅供参考。"
    
    if intent_result.get("is_ambiguous"):
        response += "\n\n💡 如需更精准的分析，建议您提出更具体的问题，例如：\"我今年的事业运势如何？\"、\"我什么时候会结婚？\"等。"
    
    return response


@router.get("/test-intent")
async def test_intent(
    question: str = Query(..., description="测试问题")
):
    """测试意图识别（调试用）"""
    try:
        intent_client = IntentServiceClient()
        result = intent_client.classify(question=question)
        return {
            "success": True,
            "question": question,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def get_smart_analyze_stream_generator(
    payload: Dict[str, Any]
) -> Tuple[Optional[AsyncGenerator[str, None]], Optional[Dict[str, Any]]]:
    """
    根据 payload 构建智能运势流式生成器（与 gRPC-Web handler 共用逻辑）。
    
    Returns:
        (generator, None) 表示成功，可迭代产出 SSE 字符串；
        (None, error_dict) 表示参数错误，error_dict 为 { "success": False, "error": "..." }。
    """
    question = payload.get("question")
    year = payload.get("year")
    month = payload.get("month")
    day = payload.get("day")
    hour = payload.get("hour", 12)
    gender = payload.get("gender")
    user_id = payload.get("user_id")
    category = payload.get("category")
    request_id = payload.pop("_request_id", None) or payload.get("request_id") or generate_request_id()
    monitor = PerformanceMonitor()
    is_scenario_1 = category and (not question or question == category)
    is_scenario_2 = category and question and question != category

    if is_scenario_1:
        if not user_id or not year or not month or not day or not gender:
            return None, {"success": False, "error": "场景1需要提供完整的生辰信息（year, month, day, gender, user_id）"}
        gen = _scenario_1_generator(year, month, day, hour, gender, category, user_id, monitor, request_id)
        return gen, None
    if is_scenario_2:
        if not user_id:
            return None, {"success": False, "error": "场景2需要提供user_id参数"}
        gen = _scenario_2_generator(question, category, user_id, year, month, day, hour, gender, monitor, request_id)
        return gen, None
    if question and year and month and day and gender:
        gen = _original_scenario_generator(question, year, month, day, hour, gender, user_id, monitor, request_id)
        return gen, None
    return None, {"success": False, "error": "参数不完整，请检查输入"}


@router.get("/smart-analyze-stream")
async def smart_analyze_stream(request: Request):
    """
    智能运势分析（流式输出版）
    
    支持两种场景：
    1. 场景1（点击选择项）：category有值，question为空或为选择项名称
       - 返回：简短答复（100字内，流式）+ 预设问题列表（10-15个）
    2. 场景2（点击预设问题/输入问题）：category有值，question有值
       - 返回：详细流式回答 + 3个相关问题列表
    
    用户体验优化：
    - 立即返回基础分析
    - 流式输出LLM深度解读
    - 感知速度大幅提升
    """
    
    async def event_generator():
        """生成SSE事件流"""
        # 初始化性能监控器
        monitor = PerformanceMonitor()
        request_id = generate_request_id(request.headers) if request else generate_request_id()
        
        try:
            # ✅ 性能优化：立即返回首条消息，让用户感知到连接已建立
            # 这个优化将首次响应时间从 24秒 降低到 <1秒
            yield _sse_message("progress", {"message": "正在连接服务..."})
            
            # 从Request对象手动获取查询参数（绕过FastAPI参数验证问题）
            query_params = request.query_params
            question = query_params.get("question")
            year_str = query_params.get("year")
            year = int(year_str) if year_str else None
            month_str = query_params.get("month")
            month = int(month_str) if month_str else None
            day_str = query_params.get("day")
            day = int(day_str) if day_str else None
            hour_str = query_params.get("hour", "12")
            hour = int(hour_str) if hour_str else 12
            gender = query_params.get("gender")
            user_id = query_params.get("user_id")
            category = query_params.get("category")
            
            # ==================== 场景判断 ====================
            # 场景1：点击选择项（category有值，question为空或为选择项名称）
            # 场景2：点击预设问题/输入问题（有question，category可选）
            is_scenario_1 = category and (not question or question == category)
            is_scenario_2 = question and question != category  # 只要有question就走场景2，category可选
            
            # 场景1：需要生辰信息
            if is_scenario_1:
                if not user_id:
                    yield _sse_message("error", {"message": "场景1需要提供user_id参数"})
                    yield _sse_message("end", {})
                    return
                if not year or not month or not day or not gender:
                    yield _sse_message("error", {"message": "场景1需要提供完整的生辰信息（year, month, day, gender）"})
                    yield _sse_message("end", {})
                    return
                
                # 执行场景1逻辑
                async for event in _scenario_1_generator(
                    year, month, day, hour, gender, category, user_id, monitor, request_id
                ):
                    yield event
                return
            
            # 场景2：从会话缓存获取生辰信息
            if is_scenario_2:
                if not user_id:
                    yield _sse_message("error", {"message": "场景2需要提供user_id参数"})
                    yield _sse_message("end", {})
                    return
                # 执行场景2逻辑
                async for event in _scenario_2_generator(
                    question, category, user_id, year, month, day, hour, gender, monitor, request_id
                ):
                    yield event
                return
            
            # 默认场景：使用原有逻辑（兼容性）
            if not category:
                # 原有逻辑：需要生辰信息和问题
                if not year or not month or not day or not gender or not question:
                    yield _sse_message("error", {"message": "需要提供完整的生辰信息和问题"})
                    yield _sse_message("end", {})
                    return
                
                # 执行原有逻辑
                async for event in _original_scenario_generator(
                    question, year, month, day, hour, gender, user_id or None, monitor, request_id  # 允许 user_id 为空
                ):
                    yield event
                return
            
            # 未知场景
            yield _sse_message("error", {"message": "无法识别场景，请检查参数"})
            yield _sse_message("end", {})
        
        except Exception as e:
            if monitor.current_stage:
                monitor.end_stage(monitor.current_stage, success=False, error=str(e))
            monitor.log_summary()
            logger.error(f"[smart_fortune_stream] Stream error: {e}", exc_info=True)
            yield _sse_message("error", {"message": str(e), "performance": monitor.get_summary()})
            yield _sse_message("end", {})
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
    )


@router.post("/smart-analyze-stream/stream")
async def smart_analyze_stream_post(payload: Dict[str, Any]):
    """
    智能运势分析（真正 SSE 流式，POST JSON body，供前端流式消费）。
    
    请求体与 gRPC-Web Call 的 payload_json 一致，例如：
    {"question":"...", "year":1990, "month":1, "day":1, "hour":12, "gender":"male", "user_id":"...", "category":"事业财富"}
    
    返回：text/event-stream，与 GET /smart-analyze-stream 的 SSE 格式一致。
    前端可用 fetch() + ReadableStream 或 EventSource 消费，无需等待全量结束。
    """
    generator, error = await get_smart_analyze_stream_generator(payload)
    if error is not None:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content=error)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _fetch_bazi_data_via_orchestrator(
    year: int, month: int, day: int, hour: int, gender: str, user_id: str,
    save_to_cache: bool = True
) -> Dict[str, Any]:
    """
    通过 BaziDataOrchestrator 统一获取八字数据（供场景1和场景2共用）
    符合 08_数据编排架构规范
    
    Args:
        year: 年
        month: 月
        day: 日
        hour: 时
        gender: 性别
        user_id: 用户ID
        save_to_cache: 是否保存到会话缓存（默认True）
        
    Returns:
        完整八字数据字典（与 _calculate_bazi_data 返回结构兼容）
    """
    from server.services.bazi_session_service import BaziSessionService
    from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
    
    solar_date = f"{year:04d}-{month:02d}-{day:02d}"
    solar_time = f"{hour:02d}:00"
    
    # 通过 BaziDataOrchestrator 统一获取数据（含 fortune_context 编排层接入）
    from datetime import datetime
    current_year = datetime.now().year
    target_years = list(range(current_year, current_year + 6))
    
    modules = {
        'bazi': True,
        'wangshuai': True,
        'detail': True,
        'rules': {'types': ['ALL']},
        'fortune_context': {'intent_types': ['ALL'], 'target_years': target_years},
        # ⚠️ 统一架构：添加 special_liunians 模块，使关键年份数据与其他流式接口一致
        'special_liunians': {
            'dayun_config': {'mode': 'count', 'count': 13},  # ⚠️ 统一为 count:13（与 fortune/display 一致）
            'target_years': target_years[:3] if len(target_years) >= 3 else target_years,
            'count': 200
        }
    }
    
    unified_data = await BaziDataOrchestrator.fetch_data(
        solar_date=solar_date,
        solar_time=solar_time,
        gender=gender,
        modules=modules,
        use_cache=True,
        parallel=True,
        preprocessed=True
    )
    
    # 映射到 complete_bazi_data 结构（与原有 _calculate_bazi_data 兼容）
    bazi_result = unified_data.get('bazi', {})
    if isinstance(bazi_result, dict) and 'bazi' not in bazi_result:
        bazi_result = {'bazi': bazi_result, 'rizhu': {}, 'matched_rules': []}
    
    # BaziService.calculate_bazi_full 返回的 matched_rules 可能为空，优先使用编排层 rules 模块
    matched_rules = bazi_result.get('matched_rules') or unified_data.get('rules', [])
    detail_result = unified_data.get('detail', {})
    wangshuai_result = unified_data.get('wangshuai', {})
    
    # 流年大运分析（由编排层 fortune_context 模块返回，复用 detail/wangshuai 避免重复计算）
    fortune_context = unified_data.get('fortune_context')
    
    # ⚠️ 统一架构：将 special_liunians 注入到 fortune_context 中作为 key_liunians
    # 数据来源与 fortune/display 一致（BaziDetailService.calculate_detail_full → liunian_sequence.relations）
    special_liunians_data = unified_data.get('special_liunians', {})
    special_liunians_list = special_liunians_data.get('list', []) if isinstance(special_liunians_data, dict) else []
    if special_liunians_list:
        if fortune_context is None:
            fortune_context = {}
        fortune_context['key_liunians'] = special_liunians_list
    
    # ⚠️ 统一架构：注入 current_dayun / key_dayuns 到 fortune_context（与其他流式接口一致）
    # format_smart_fortune_for_llm 读 fortune_context['current_dayun'] / fortune_context['key_dayuns']
    # 但 FortuneContextService 返回的 fortune_context 没有这两个字段，需要用 build_enhanced_dayun_structure 构建
    # ⚠️ 关键：即使 fortune_context 为 None（FortuneContextService 未返回），也要构建
    dayun_sequence = (detail_result.get('dayun_sequence') or (detail_result.get('details') or {}).get('dayun_sequence', [])) if isinstance(detail_result, dict) else []
    if fortune_context is None and dayun_sequence:
        fortune_context = {}  # 创建空的 fortune_context，后续注入 current_dayun/key_dayuns
        logger.info("⚠️ fortune_context 为 None，从 detail_result 构建")
    if fortune_context is not None and dayun_sequence:
        try:
            from datetime import datetime as _dt
            current_age = calculate_user_age(solar_date, _dt.now())
            current_dayun_info = get_current_dayun(dayun_sequence, current_age)
            birth_year = int(solar_date.split('-')[0])
            
            enhanced_dayun_structure = build_enhanced_dayun_structure(
                dayun_sequence=dayun_sequence,
                special_liunians=special_liunians_list,
                current_age=current_age,
                current_dayun=current_dayun_info,
                birth_year=birth_year,
                business_type='default',
                bazi_data=bazi_result,
                gender=gender
            )
            
            # 构建 current_dayun_data（与其他流式接口保持一致的 ganzhi 合成逻辑）
            current_dayun_enhanced = enhanced_dayun_structure.get('current_dayun')
            if current_dayun_enhanced:
                _stem = current_dayun_enhanced.get('gan', current_dayun_enhanced.get('stem', ''))
                _branch = current_dayun_enhanced.get('zhi', current_dayun_enhanced.get('branch', ''))
                fortune_context['current_dayun'] = {
                    'step': str(current_dayun_enhanced.get('step', '')),
                    'ganzhi': f"{_stem}{_branch}",
                    'stem': _stem,
                    'branch': _branch,
                    'age_display': current_dayun_enhanced.get('age_display', current_dayun_enhanced.get('age_range', '')),
                    'main_star': current_dayun_enhanced.get('main_star', ''),
                    'life_stage': current_dayun_enhanced.get('life_stage', ''),
                    'liunians': current_dayun_enhanced.get('liunians', [])
                }
                logger.info(f"✅ fortune_context 注入 current_dayun: {_stem}{_branch}({current_dayun_enhanced.get('age_display', '')})")
            
            # 构建 key_dayuns_data（与其他流式接口保持一致的 ganzhi 合成逻辑）
            key_dayuns_enhanced = enhanced_dayun_structure.get('key_dayuns', [])
            if key_dayuns_enhanced:
                key_dayuns_data = []
                for kd in key_dayuns_enhanced:
                    _kd_stem = kd.get('gan', kd.get('stem', ''))
                    _kd_branch = kd.get('zhi', kd.get('branch', ''))
                    key_dayuns_data.append({
                        'step': str(kd.get('step', '')),
                        'ganzhi': f"{_kd_stem}{_kd_branch}",
                        'stem': _kd_stem,
                        'branch': _kd_branch,
                        'age_display': kd.get('age_display', kd.get('age_range', '')),
                        'main_star': kd.get('main_star', ''),
                        'life_stage': kd.get('life_stage', ''),
                        'business_reason': kd.get('business_reason', ''),
                        'liunians': kd.get('liunians', [])
                    })
                fortune_context['key_dayuns'] = key_dayuns_data
                logger.info(f"✅ fortune_context 注入 key_dayuns: {len(key_dayuns_data)}个关键大运")
        except Exception as e:
            logger.error(f"构建增强大运结构失败: {e}", exc_info=True)
    
    complete_bazi_data = {
        "bazi_result": bazi_result,
        "detail_result": detail_result,
        "matched_rules": matched_rules,
        "wangshuai_result": wangshuai_result,
        "fortune_context": fortune_context,
        "solar_date": solar_date,
        "solar_time": solar_time,
        "gender": gender
    }
    
    if save_to_cache and user_id:
        BaziSessionService.save_bazi_session(user_id, complete_bazi_data)
        logger.info(f"✅ 八字数据已保存到会话缓存: user_id={user_id}")
    
    return complete_bazi_data


async def _scenario_1_generator(
    year: int, month: int, day: int, hour: int, gender: str,
    category: str, user_id: str, monitor: PerformanceMonitor,
    request_id: Optional[str] = None
):
    """场景1：点击选择项 → 生成简短答复 + 预设问题列表（百炼平台）"""
    from server.services.bazi_session_service import BaziSessionService
    from server.services.conversation_history_service import ConversationHistoryService
    import time
    
    start_time = time.time()  # 记录开始时间，用于计算响应时间
    request_id = request_id or generate_request_id()
    
    try:
        yield f"data: {json.dumps({'type': 'request_id', 'request_id': request_id}, ensure_ascii=False)}\n\n"
        # ==================== 计算完整八字数据 ====================
        yield _sse_message("status", {"stage": "bazi", "message": "正在计算八字..."})
        
        with monitor.stage("bazi_calculation", "八字计算", solar_date=f"{year:04d}-{month:02d}-{day:02d}", solar_time=f"{hour:02d}:00", gender=gender):
            # 通过 BaziDataOrchestrator 统一获取八字数据
            complete_bazi_data = await _fetch_bazi_data_via_orchestrator(year, month, day, hour, gender, user_id, save_to_cache=True)
            logger.info(f"✅ 场景1：完整八字数据已保存到会话缓存（包含所有信息）: user_id={user_id}")
        
        # ==================== 并行：简短答复（流式）+ 预设问题列表 ====================
        yield _sse_message("brief_response_start", {})
        
        # ⭐ 使用百炼平台：并行启动预设问题生成
        preset_questions_task = asyncio.create_task(
            _generate_preset_questions_bailian(complete_bazi_data, category)
        )
        
        with monitor.stage("brief_response", "生成简短答复（百炼）", category=category):
            # ⭐ 使用 LLMServiceFactory 获取百炼服务
            llm_service = LLMServiceFactory.get_service(scene="qa_question_generate")
            
            # 构建简短答复 Prompt
            bazi_result_for_prompt = complete_bazi_data.get("bazi_result", {})
            category_names = {
                "事业财富": "事业和财富", "婚姻": "婚姻感情",
                "健康": "健康运势", "子女": "子女运势",
                "流年运势": "流年运势", "年运报告": "年运报告"
            }
            category_cn = category_names.get(category, category)
            
            brief_prompt = f"""请基于用户的八字信息，生成关于"{category_cn}"的简短答复（100字以内）。

【用户八字信息】
{_format_bazi_brief(bazi_result_for_prompt)}

【要求】
1. 内容要简洁明了，控制在100字以内
2. 聚焦于{category_cn}方面
3. 语言通俗易懂
4. 直接给出核心结论，不需要详细分析

请直接回答："""
            
            full_brief_response = ""
            
            async for result in llm_service.stream_analysis(brief_prompt):
                result_type = result.get('type')
                if result_type == 'progress':
                    content = result.get('content', '')
                    if content:
                        full_brief_response += content
                        yield _sse_message("brief_response_chunk", {"content": content})
                elif result_type == 'complete':
                    break
                elif result_type == 'error':
                    error_msg = result.get('content', '未知错误')
                    yield _sse_message("brief_response_error", {"message": error_msg})
                    return
            
            if len(full_brief_response) > 100:
                full_brief_response = full_brief_response[:100]
            
            yield _sse_message("llm_end", {"full_content": full_brief_response})
        
        # ==================== 取预设问题结果（已与简短答复并行执行） ====================
        yield _sse_message("status", {"stage": "preset_questions", "message": "正在生成预设问题..."})
        
        with monitor.stage("preset_questions", "生成预设问题列表（百炼）", category=category):
            try:
                preset_questions = await preset_questions_task
                if not preset_questions:
                    preset_questions = _get_default_preset_questions(category)
            except Exception as e:
                logger.warning(f"生成预设问题失败: {e}")
                preset_questions = _get_default_preset_questions(category)
            
            yield _sse_message("preset_questions", {"questions": preset_questions})
        
        # ==================== 异步保存对话记录到MySQL ====================
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # 获取八字摘要
        bazi_result = complete_bazi_data.get('bazi_result', {})
        bazi_pillars = bazi_result.get('bazi', {}).get('bazi_pillars', {})
        bazi_summary = ""
        if bazi_pillars:
            bazi_summary = f"{bazi_pillars.get('year', {}).get('stem', '')}{bazi_pillars.get('year', {}).get('branch', '')}、{bazi_pillars.get('month', {}).get('stem', '')}{bazi_pillars.get('month', {}).get('branch', '')}、{bazi_pillars.get('day', {}).get('stem', '')}{bazi_pillars.get('day', {}).get('branch', '')}、{bazi_pillars.get('hour', {}).get('stem', '')}{bazi_pillars.get('hour', {}).get('branch', '')}"
        
        # 异步保存到MySQL（场景1）
        asyncio.create_task(
            ConversationHistoryService.save_conversation_async(
                user_id=user_id,
                session_id=user_id,
                category=category,
                question=f"[选择项] {category}",
                answer=full_brief_response,
                intent="category_selection",
                bazi_summary=bazi_summary,
                round_number=1,
                response_time_ms=response_time_ms,
                conversation_id="",
                scenario_type="scenario1"
            )
        )
        logger.info(f"✅ 场景1：对话记录已提交异步保存: user_id={user_id}, category={category}")
        
        # 发送性能摘要
        performance_summary = monitor.get_summary()
        yield _sse_message("performance", performance_summary)
        monitor.log_summary()
        
        # 结束
        yield _sse_message("end", {})
        
    except Exception as e:
        logger.error(f"[scenario_1] 错误: {e}", exc_info=True)
        yield _sse_message("error", {"message": str(e)})
        yield _sse_message("end", {})




def _format_bazi_brief(bazi_result: Dict[str, Any]) -> str:
    """格式化八字信息为简短文本（供场景1简短答复 Prompt）"""
    pillars = (
        bazi_result.get('bazi_pillars') or
        bazi_result.get('bazi', {}).get('bazi_pillars') or
        {}
    )
    if not pillars:
        return "（八字信息不可用）"
    
    parts = []
    for eng, cn in [("year", "年柱"), ("month", "月柱"), ("day", "日柱"), ("hour", "时柱")]:
        p = pillars.get(eng, {})
        if isinstance(p, dict):
            parts.append(f"{cn}:{p.get('stem', '')}{p.get('branch', '')}")
        elif isinstance(p, str):
            parts.append(f"{cn}:{p}")
    return ' '.join(parts) if parts else "（八字信息不可用）"


async def _generate_preset_questions_bailian(
    bazi_data: Dict[str, Any],
    category: str
) -> List[str]:
    """使用百炼平台生成预设问题列表（10-15个）"""
    try:
        llm_service = LLMServiceFactory.get_service(scene="qa_question_generate")
        
        bazi_result = bazi_data.get("bazi_result", {})
        category_names = {
            "事业财富": "事业和财富", "婚姻": "婚姻感情",
            "健康": "健康运势", "子女": "子女运势",
            "流年运势": "流年运势", "年运报告": "年运报告"
        }
        category_cn = category_names.get(category, category)
        
        prompt = f"""请基于用户的八字信息，生成10-15个关于"{category_cn}"的预设问题。

【用户八字信息】
{_format_bazi_brief(bazi_result)}

【要求】
1. 生成10-15个相关问题
2. 问题要具体、实用，覆盖{category_cn}的各个方面
3. 问题要通俗易懂，不使用专业术语
4. 必须以JSON数组格式返回，例如：["问题1", "问题2", "问题3"]

请直接返回JSON数组："""
        
        full_text = ""
        async for result in llm_service.stream_analysis(prompt):
            result_type = result.get('type')
            if result_type == 'progress':
                full_text += result.get('content', '')
            elif result_type in ('complete', 'error'):
                break
        
        # 解析 JSON 数组
        if full_text:
            try:
                # 尝试提取 JSON 数组
                import re
                json_match = re.search(r'\[.*\]', full_text, re.DOTALL)
                if json_match:
                    questions = json.loads(json_match.group())
                    if isinstance(questions, list) and len(questions) > 0:
                        logger.info(f"✅ 百炼生成预设问题: {len(questions)}个")
                        return [q for q in questions if isinstance(q, str)][:15]
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"解析预设问题JSON失败: {e}")
        
        logger.warning("百炼生成预设问题为空，使用默认问题")
        return _get_default_preset_questions(category)
    except Exception as e:
        logger.error(f"百炼生成预设问题异常: {e}", exc_info=True)
        return _get_default_preset_questions(category)


async def _generate_questions_async_bailian(
    partial_response: str,
    user_intent: Dict[str, Any],
    bazi_data: Dict[str, Any],
    category: str
) -> List[str]:
    """异步生成相关问题（百炼版，使用 LLMServiceFactory）"""
    try:
        # 使用场景2同一个百炼智能体，发送问题生成 Prompt
        llm_service = LLMServiceFactory.get_service(scene="qa_analysis")
        
        category_names = {
            "事业财富": "事业和财富", "婚姻": "婚姻感情",
            "健康": "健康运势", "子女": "子女运势",
            "流年运势": "流年运势", "年运报告": "年运报告"
        }
        category_cn = category_names.get(category, category or "综合运势")
        
        prompt = f"""请基于以下已回答内容，快速生成2个相关的后续问题。

【已回答内容】
{partial_response[:300]}

【分类】{category_cn}

【要求】
1. 只生成2个问题，每行一个，不编号，不加说明
2. 问题必须用通俗易懂的语言，禁止使用任何命理专业术语
3. 每个问题不超过20字
4. 直接输出问题，不要其他内容"""
        
        full_text = ""
        async for result in llm_service.stream_analysis(prompt):
            result_type = result.get('type')
            if result_type == 'progress':
                full_text += result.get('content', '')
            elif result_type in ('complete', 'error'):
                break
        
        # 解析问题列表
        if full_text:
            questions = _parse_questions_from_text(full_text)
            if questions:
                logger.info(f"✅ 百炼生成相关问题: {questions}")
                return questions[:2]
        
        logger.warning("百炼生成相关问题为空，使用默认问题")
        return _get_default_related_questions(category)[:2]
    except Exception as e:
        logger.error(f"百炼生成相关问题异常: {e}", exc_info=True)
        return _get_default_related_questions(category)[:2]


def _parse_questions_from_text(text: str) -> List[str]:
    """从纯文本中解析问题列表（每行一个问题）"""
    questions = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        # 去掉可能的编号前缀（1. 2. 或 1、2、等）
        import re
        line = re.sub(r'^[\d]+[.、)）]\s*', '', line).strip()
        if line and 3 <= len(line) <= 30:
            questions.append(line)
    return questions


async def _scenario_2_generator(
    question: str, category: Optional[str], user_id: str,
    year: Optional[int], month: Optional[int], day: Optional[int],
    hour: int, gender: Optional[str], monitor: PerformanceMonitor,
    request_id: Optional[str] = None
):
    """场景2：点击预设问题/输入问题 → 生成详细流式回答 + 2个相关问题（category可选，百炼平台）"""
    from server.services.bazi_session_service import BaziSessionService
    from server.services.conversation_history_service import ConversationHistoryService
    import time
    
    start_time = time.time()  # 记录开始时间，用于计算响应时间
    request_id = request_id or generate_request_id()
    
    try:
        yield f"data: {json.dumps({'type': 'request_id', 'request_id': request_id}, ensure_ascii=False)}\n\n"
        # ==================== 并行获取会话数据（非阻塞，2个Redis调用并行执行） ====================
        loop = asyncio.get_event_loop()
        _pool = get_executor()
        complete_bazi_data, history_context = await asyncio.gather(
            loop.run_in_executor(_pool, BaziSessionService.get_bazi_session, user_id),
            loop.run_in_executor(_pool, ConversationHistoryService.get_history_from_redis, user_id)
        )
        
        if not complete_bazi_data:
            # 降级处理：如果有完整生辰信息，自动计算八字数据
            if year and month and day and gender:
                logger.info(f"⚠️ 场景2：缓存不存在，使用生辰信息重新计算八字数据: user_id={user_id}")
                yield _sse_message("status", {"stage": "bazi", "message": "正在计算八字数据..."})
                try:
                    complete_bazi_data = await _fetch_bazi_data_via_orchestrator(
                        year=year, month=month, day=day, hour=hour,
                        gender=gender, user_id=user_id, save_to_cache=True
                    )
                    logger.info(f"✅ 场景2：八字数据计算完成并已缓存: user_id={user_id}")
                except Exception as calc_error:
                    logger.error(f"❌ 场景2：八字数据计算失败: {calc_error}", exc_info=True)
                    yield _sse_message("error", {"message": f"八字数据计算失败: {calc_error}"})
                    yield _sse_message("end", {})
                    return
            else:
                # 没有生辰信息，返回错误
                yield _sse_message("error", {"message": "会话不存在，请先点击选择项或提供完整生辰信息（year, month, day, gender）"})
                yield _sse_message("end", {})
                return
        
        current_round = len(history_context) + 1
        logger.info(f"✅ 场景2：获取历史上下文，当前第{current_round}轮对话，历史{len(history_context)}轮")
        
        # 从session获取所有数据
        bazi_result = complete_bazi_data.get("bazi_result", {})
        detail_result = complete_bazi_data.get("detail_result", {})
        matched_rules = complete_bazi_data.get("matched_rules", [])
        wangshuai_result = complete_bazi_data.get("wangshuai_result", {})
        fortune_context = complete_bazi_data.get("fortune_context")
        
        # ==================== 场景2：直接使用category，不需要意图识别 ====================
        # 根据category直接确定规则类型
        rule_type = CATEGORY_TO_RULE_TYPE.get(category, "general")
        
        # 构建简化的intent_result（仅用于LLM调用）
        intent_result = {
            "intents": [rule_type],
            "rule_types": [rule_type],
            "confidence": 1.0,  # 直接使用category，置信度为1.0
            "is_fortune_related": True,
            "time_intent": {}  # 如果需要时间意图，可以从问题中简单提取
        }
        
        # ==================== 直接使用session中的规则，不再重新匹配 ====================
        # 根据category过滤规则（如果需要）
        if rule_type != "general":
            matched_rules = [rule for rule in matched_rules if rule.get("rule_type") == rule_type]
        
        # 如果过滤后没有规则，使用所有规则
        if not matched_rules:
            matched_rules = complete_bazi_data.get("matched_rules", [])
        
        # ==================== 直接使用session中的流年大运数据，不再重新计算 ====================
        # fortune_context 已经从session获取，不需要重新计算
        
        # ==================== 发送基础分析结果 ====================
        yield _sse_message("basic_analysis", {
            "intent": intent_result,
            "bazi_info": {
                "四柱": _format_pillars(bazi_result.get("bazi_pillars", {})),
                "十神": bazi_result.get("ten_gods_stats", {}),
                "五行": bazi_result.get("element_counts", {})
            },
            "matched_rules_count": len(matched_rules),
            "fortune_context": fortune_context
        })
        
        # ==================== 流式输出LLM深度解读（百炼平台） ====================
        yield _sse_message("status", {"stage": "llm", "message": "正在生成深度解读..."})
        
        main_intent = rule_type  # 直接使用rule_type，不再需要从rule_types获取
        
        with monitor.stage("llm_analysis", "LLM深度解读（流式）", intent=main_intent):
            # ⭐ 使用 LLMServiceFactory 获取百炼服务（根据数据库 LLM_PLATFORM 配置自动选择）
            llm_service = LLMServiceFactory.get_service(scene="qa_analysis")
            
            # ⭐ 使用 format_smart_fortune_for_llm 构建精简中文 Prompt（含历史上下文记忆压缩）
            formatted_prompt = format_smart_fortune_for_llm(
                bazi_data=bazi_result,
                fortune_context=fortune_context,
                matched_rules=matched_rules or [],
                question=question,
                intent=main_intent,
                category=category,
                history_context=history_context,
                details=(detail_result or {}).get('details', {}),
                branch_relations=bazi_result.get('relationships', {}).get('branch_relations', {}),
            )
            logger.info(f"📤 场景2 Prompt 构建完成: intent={main_intent}, category={category}, size={len(formatted_prompt)}字符")
            
            full_response = ""
            chunk_received = False
            questions_task = None  # 后台任务
            cached_questions = []  # 缓存的问题
            
            yield _sse_message("llm_start", {})
            
            async for result in llm_service.stream_analysis(formatted_prompt):
                chunk_received = True
                result_type = result.get('type') if isinstance(result, dict) else None
                
                if result_type == 'progress':
                    content = result.get('content', '')
                    if content:
                        full_response += content
                        yield _sse_message("llm_chunk", {"content": content})
                        
                        # 当累积内容达到约80字时即开始并行生成问题，减少等待时间
                        if not questions_task and len(full_response) >= 80:
                            questions_task = asyncio.create_task(
                                _generate_questions_async_bailian(
                                    full_response[:200],
                                    intent_result,
                                    complete_bazi_data,
                                    category
                                )
                            )
                            logger.info("✅ 开始并行生成相关问题（答案已输出80字）")
                elif result_type == 'complete':
                    # ⚡ 先发送 llm_end，让前端尽早感知LLM输出完成
                    yield _sse_message("llm_end", {"full_content": full_response})
                    
                    # ==================== 以下保存操作在 llm_end 之后执行（不影响前端体验） ====================
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    # 获取八字摘要
                    bazi_pillars = bazi_result.get('bazi', {}).get('bazi_pillars', {})
                    bazi_summary = ""
                    if bazi_pillars:
                        bazi_summary = f"{bazi_pillars.get('year', {}).get('stem', '')}{bazi_pillars.get('year', {}).get('branch', '')}、{bazi_pillars.get('month', {}).get('stem', '')}{bazi_pillars.get('month', {}).get('branch', '')}、{bazi_pillars.get('day', {}).get('stem', '')}{bazi_pillars.get('day', {}).get('branch', '')}、{bazi_pillars.get('hour', {}).get('stem', '')}{bazi_pillars.get('hour', {}).get('branch', '')}"
                    
                    asyncio.create_task(
                        ConversationHistoryService.save_conversation_async(
                            user_id=user_id,
                            session_id=user_id,
                            category=category,
                            question=question,
                            answer=full_response,
                            intent=main_intent,
                            bazi_summary=bazi_summary,
                            round_number=current_round,
                            response_time_ms=response_time_ms,
                            conversation_id="",
                            scenario_type="scenario2"
                        )
                    )
                    
                    # 更新历史摘要到Redis（非阻塞）
                    keywords = ConversationHistoryService.extract_keywords(question, full_response)
                    summary = ConversationHistoryService.compress_to_summary(question, full_response)
                    
                    round_data = {
                        "round": current_round,
                        "keywords": keywords,
                        "summary": summary
                    }
                    await loop.run_in_executor(get_executor(), ConversationHistoryService.save_history_to_redis, user_id, round_data)
                    
                    logger.info(f"✅ 场景2：第{current_round}轮对话完成，关键词={keywords}，摘要={summary[:50]}...")
                    break
                elif result_type == 'error':
                    error_msg = result.get('content', '未知错误')
                    yield _sse_message("llm_error", {"message": error_msg})
                    break
            
            if not chunk_received:
                yield _sse_message("llm_error", {"message": "AI深度解读服务无响应"})
        
        # ==================== 生成相关问题（并行生成或等待完成） ====================
        # 如果答案内容足够，处理相关问题生成
        if not full_response or len(full_response.strip()) < 50:
            logger.warning("详细回答内容为空或太短，跳过相关问题生成")
            yield _sse_message("related_questions", {"questions": []})
        else:
            # 如果已经启动了并行任务，等待完成
            if questions_task:
                if not questions_task.done():
                    logger.info("⏳ 答案已完成，等待问题生成完成...")
                    yield _sse_message("status", {"stage": "related_questions", "message": "正在生成相关问题..."})
                    try:
                        cached_questions = await questions_task
                    except Exception as e:
                        logger.error(f"并行生成相关问题失败: {e}", exc_info=True)
                        cached_questions = []
                else:
                    try:
                        cached_questions = questions_task.result()
                    except Exception as e:
                        logger.error(f"获取并行生成的问题失败: {e}", exc_info=True)
                        cached_questions = []
                
                # 如果并行生成失败，使用默认问题
                if not cached_questions:
                    logger.warning("并行生成问题失败，使用默认问题")
                    cached_questions = _get_default_related_questions(category)[:2]
            else:
                # 如果没有启动并行任务（答案太短），串行生成
                logger.info(f"详细回答已完成（{len(full_response)}字），开始生成相关问题")
                yield _sse_message("status", {"stage": "related_questions", "message": "正在生成相关问题..."})
                
                with monitor.stage("related_questions", "生成相关问题（百炼）"):
                    try:
                        cached_questions = await _generate_questions_async_bailian(
                            full_response[:200],
                            intent_result,
                            complete_bazi_data,
                            category
                        )
                    except Exception as e:
                        logger.error(f"生成相关问题失败: {e}", exc_info=True)
                        cached_questions = _get_default_related_questions(category)[:2]
            
            # 发送缓存的问题
            yield _sse_message("related_questions", {"questions": cached_questions})
        
        # 发送性能摘要
        performance_summary = monitor.get_summary()
        yield _sse_message("performance", performance_summary)
        monitor.log_summary()
        
        # 结束
        yield _sse_message("end", {})
        
    except Exception as e:
        logger.error(f"[scenario_2] 错误: {e}", exc_info=True)
        yield _sse_message("error", {"message": str(e)})
        yield _sse_message("end", {})


async def _original_scenario_generator(
    question: str, year: int, month: int, day: int, hour: int,
    gender: str, user_id: Optional[str], monitor: PerformanceMonitor,
    request_id: Optional[str] = None
):
    """原有场景：兼容原有逻辑（保留原有完整流程）"""
    request_id = request_id or generate_request_id()
    try:
        yield f"data: {json.dumps({'type': 'request_id', 'request_id': request_id}, ensure_ascii=False)}\n\n"
        # ==================== 阶段1：意图识别 ====================
        yield _sse_message("status", {"stage": "intent", "message": "正在识别意图..."})
        
        with monitor.stage("intent_recognition", "意图识别", question=question):
            intent_client = IntentServiceClient()
            intent_result = intent_client.classify(
                question=question,
                user_id=user_id or "anonymous"
            )
        
        # 防御性检查：确保intent_result不为None
        if intent_result is None:
            intent_result = {
                "intents": ["general"],
                "confidence": 0.5,
                "keywords": [],
                "is_ambiguous": True,
                "time_intent": None,
                "is_fortune_related": True
            }
            
            monitor.add_metric("intent_recognition", "intents_count", len(intent_result.get("intents", [])))
            monitor.add_metric("intent_recognition", "confidence", intent_result.get("confidence", 0))
            monitor.add_metric("intent_recognition", "method", intent_result.get("method", "unknown"))
            
            # ==================== 记录用户问题（用于模型微调）====================
            try:
                from server.services.intent_question_logger import get_question_logger
                question_logger = get_question_logger()
                solar_date = f"{year:04d}-{month:02d}-{day:02d}"
                solar_time = f"{hour:02d}:00"
                question_logger.log_question(
                    question=question,
                    intent_result=intent_result,
                    user_id=user_id,
                    session_id=None,  # 可以后续添加session管理
                    solar_date=solar_date,
                    solar_time=solar_time,
                    gender=gender
                )
            except Exception as e:
                logger.warning(f"[smart_fortune_stream] 记录用户问题失败: {e}", exc_info=True)
                # 不影响主流程，仅记录警告
        
        # 如果问题不相关（LLM已判断）
        if not intent_result.get("is_fortune_related", True) or "non_fortune" in intent_result.get("intents", []):
            monitor.log_summary()
            yield _sse_message("error", {
                "message": intent_result.get("reject_message", "您的问题似乎与命理运势无关，我只能回答关于八字、运势等相关问题。"),
                "performance": monitor.get_summary()
            })
            yield _sse_message("end", {})
            return
        
        # 获取时间意图（LLM已识别）
        time_intent = intent_result.get("time_intent", {})
        target_years = time_intent.get("target_years", [])
        
        # ==================== 阶段2：八字计算 ====================
        yield _sse_message("status", {"stage": "bazi", "message": "正在计算八字..."})
        
        solar_date = f"{year:04d}-{month:02d}-{day:02d}"
        solar_time = f"{hour:02d}:00"
        
        with monitor.stage("bazi_calculation", "八字计算", solar_date=solar_date, solar_time=solar_time, gender=gender):
            calculator = BaziCalculator(solar_date, solar_time, gender)
            bazi_result = calculator.calculate()
            
            if not bazi_result or "error" in bazi_result:
                raise HTTPException(status_code=400, detail="八字计算失败")
        
        # ==================== 阶段3：规则匹配 ====================
        yield _sse_message("status", {"stage": "rules", "message": "正在匹配规则..."})
        
        rule_types = intent_result.get("rule_types", ["ALL"])
        confidence = intent_result.get("confidence", 0)
        
        # 关键词fallback
        if confidence < 0.6 and "ALL" in rule_types:
            with monitor.stage("intent_fallback", "意图识别回退（关键词匹配）"):
                fallback_types = _extract_rule_types_from_question(question)
                if fallback_types != ["ALL"]:
                    rule_types = fallback_types
        
        with monitor.stage("rule_matching", "规则匹配", rule_types=rule_types):
            matched_rules = []
            for rule_type in rule_types:
                if rule_type != "ALL":
                    rules = BaziService._match_rules(bazi_result, [rule_type])
                    matched_rules.extend(rules)
            
            if not matched_rules or "ALL" in rule_types:
                rules = BaziService._match_rules(bazi_result)
                matched_rules = rules
            
            monitor.add_metric("rule_matching", "matched_rules_count", len(matched_rules))
            monitor.add_metric("rule_matching", "rule_types_count", len(rule_types))
        
        # ==================== 阶段4：流年大运分析 ====================
        fortune_context = None
        if target_years:
            yield _sse_message("status", {"stage": "fortune", "message": "正在分析流年大运..."})
            
            with monitor.stage("fortune_context", "流年大运分析", target_years=target_years, rule_types=rule_types):
                try:
                    from server.orchestrators.fortune_context_service import FortuneContextService
                    
                    fortune_context = FortuneContextService.get_fortune_context(
                        solar_date=solar_date,
                        solar_time=solar_time,
                        gender=gender,
                        intent_types=rule_types,
                        target_years=target_years
                    )
                    
                    if fortune_context:
                        liunian_list = fortune_context.get('time_analysis', {}).get('liunian_list', [])
                        monitor.add_metric("fortune_context", "liunian_count", len(liunian_list))
                        
                        # ⚠️ 旧路径兼容：从 time_analysis.dayun 提取当前大运，注入为 fortune_context['current_dayun']
                        # 使 format_smart_fortune_for_llm 能通过 fortune_context.get('current_dayun') 读到数据
                        time_analysis = fortune_context.get('time_analysis', {})
                        dayun_raw = time_analysis.get('dayun', {})
                        if dayun_raw and 'current_dayun' not in fortune_context:
                            _stem = dayun_raw.get('stem', dayun_raw.get('gan', ''))
                            _branch = dayun_raw.get('branch', dayun_raw.get('zhi', ''))
                            fortune_context['current_dayun'] = {
                                'step': str(dayun_raw.get('step', '')),
                                'ganzhi': f"{_stem}{_branch}",
                                'stem': _stem,
                                'branch': _branch,
                                'age_display': dayun_raw.get('age_display', dayun_raw.get('age_range', '')),
                                'main_star': dayun_raw.get('main_star', ''),
                                'life_stage': dayun_raw.get('life_stage', ''),
                            }
                            logger.info(f"[旧路径] 从 time_analysis.dayun 注入 current_dayun: {_stem}{_branch}")
                except Exception as e:
                    logger.error(f"流年大运分析失败: {e}", exc_info=True)
                    monitor.end_stage("fortune_context", success=False, error=str(e))
        
        # ==================== 阶段5：发送基础分析结果 ====================
        yield _sse_message("basic_analysis", {
            "intent": intent_result,
            "bazi_info": {
                "四柱": _format_pillars(bazi_result.get("bazi_pillars", {})),
                "十神": bazi_result.get("ten_gods_stats", {}),
                "五行": bazi_result.get("element_counts", {})
            },
            "matched_rules_count": len(matched_rules),
            "fortune_context": fortune_context
        })
        
        # ==================== 阶段6：流式输出LLM深度解读 ====================
        yield _sse_message("status", {"stage": "llm", "message": "正在生成深度解读..."})
        
        main_intent = rule_types[0] if rule_types and rule_types[0] != "ALL" else "general"
        logger.info(f"[smart_fortune_stream] 🌊 开始流式输出LLM深度解读，意图: {main_intent}, 问题: {question[:50]}...")
        
        with monitor.stage("llm_analysis", "LLM深度解读（流式）", intent=main_intent):
            try:
                llm_client = get_fortune_llm_client()
                
                logger.info(f"[smart_fortune_stream] 📞 调用 analyze_fortune(stream=True)")
                
                # ⭐ 调用LLM并检查返回值类型
                llm_result = llm_client.analyze_fortune(
                    intent=main_intent,
                    question=question,
                    bazi_data=bazi_result,
                    fortune_context=fortune_context,
                    matched_rules=matched_rules,
                    stream=True
                )
                
                # ⭐ 关键检查：确保返回的是生成器，不是字典
                if isinstance(llm_result, dict):
                    logger.error(f"[smart_fortune_stream] ❌ analyze_fortune 返回了字典而不是生成器！")
                    logger.error(f"[smart_fortune_stream] 返回值: {json.dumps(llm_result, ensure_ascii=False)[:500]}")
                    monitor.end_stage("llm_analysis", success=False, error="返回类型错误：期望生成器，实际返回字典")
                    yield _sse_message("llm_error", {"message": "AI服务配置错误：流式输出模式返回了非流式数据"})
                elif not hasattr(llm_result, '__iter__') or isinstance(llm_result, str):
                    logger.error(f"[smart_fortune_stream] ❌ analyze_fortune 返回的不是生成器！类型: {type(llm_result)}, 值: {str(llm_result)[:200]}")
                    monitor.end_stage("llm_analysis", success=False, error=f"返回类型错误：{type(llm_result)}")
                    yield _sse_message("llm_error", {"message": "AI服务配置错误：流式输出模式返回了非流式数据"})
                else:
                    logger.info(f"[smart_fortune_stream] ✅ analyze_fortune 返回生成器，类型: {type(llm_result)}")
                
                chunk_received = False
                chunk_count = 0
                total_content_length = 0
                full_response = ""  # 累积完整内容
                
                logger.info(f"[smart_fortune_stream] 🔄 开始迭代生成器（异步非阻塞）...")
                
                async for chunk in llm_result:
                    chunk_received = True
                    chunk_count += 1
                    chunk_type = chunk.get('type') if isinstance(chunk, dict) else None
                    
                    if chunk_type == 'start':
                        logger.info(f"[smart_fortune_stream] ✅ LLM流式输出开始")
                        yield _sse_message("llm_start", {})
                    elif chunk_type == 'chunk':
                        content = chunk.get('content', '')
                        if content:
                            total_content_length += len(content)
                            full_response += content  # 累积内容
                            yield _sse_message("llm_chunk", {"content": content})
                        else:
                            logger.warning(f"[smart_fortune_stream] ⚠️ chunk #{chunk_count} 类型为chunk但content为空")
                    elif chunk_type == 'end':
                        logger.info(f"[smart_fortune_stream] ✅ LLM流式输出完成: 共{chunk_count}个chunk, 总长度{total_content_length}字符")
                        monitor.add_metric("llm_analysis", "chunk_count", chunk_count)
                        monitor.add_metric("llm_analysis", "total_length", total_content_length)
                        yield _sse_message("llm_end", {"full_content": full_response})
                        break
                    elif chunk_type == 'error':
                        error_msg = chunk.get('error', '未知错误')
                        logger.error(f"[smart_fortune_stream] ❌ LLM流式输出错误: {error_msg}")
                        monitor.end_stage("llm_analysis", success=False, error=error_msg)
                        yield _sse_message("llm_error", {"message": error_msg})
                        break
                    else:
                        logger.warning(f"[smart_fortune_stream] ⚠️ 未知chunk类型: {chunk_type}, chunk内容: {json.dumps(chunk, ensure_ascii=False)[:200] if isinstance(chunk, dict) else str(chunk)[:200]}")
                
                if not chunk_received:
                    logger.warning(f"[smart_fortune_stream] ⚠️ 未收到任何chunk，可能流式输出失败")
                    monitor.end_stage("llm_analysis", success=False, error="无响应")
                    yield _sse_message("llm_error", {"message": "AI深度解读服务无响应，请检查Bot配置和网络连接"})
                else:
                    logger.info(f"[smart_fortune_stream] ✅ LLM流式输出成功完成，共处理{chunk_count}个chunk")
                    monitor.end_stage("llm_analysis", success=True)
            
            except ValueError as e:
                error_msg = str(e)
                logger.error(f"[smart_fortune_stream] ❌ ValueError: {error_msg}", exc_info=True)
                monitor.end_stage("llm_analysis", success=False, error=error_msg)
                yield _sse_message("llm_error", {"message": f"AI服务配置错误: {error_msg}"})
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[smart_fortune_stream] ❌ 流式输出异常: {error_msg}", exc_info=True)
                monitor.end_stage("llm_analysis", success=False, error=error_msg)
                yield _sse_message("llm_error", {"message": f"AI深度解读失败: {error_msg}"})
        
        # 发送性能摘要
        performance_summary = monitor.get_summary()
        yield _sse_message("performance", performance_summary)
        
        # 输出性能摘要到日志
        monitor.log_summary()
        
        # 结束
        yield _sse_message("end", {})
    
    except Exception as e:
        if monitor.current_stage:
            monitor.end_stage(monitor.current_stage, success=False, error=str(e))
        monitor.log_summary()
        logger.error(f"[original_scenario] 错误: {e}", exc_info=True)
        yield _sse_message("error", {"message": str(e), "performance": monitor.get_summary()})
        yield _sse_message("end", {})


def _get_default_preset_questions(category: str) -> list:
    """获取默认预设问题列表（当LLM生成失败时使用）"""
    default_questions = {
        "事业财富": [
            "想了解整体事业发展趋势？",
            "想了解事业的关键转折点？",
            "哪一年会有好的事业机会？",
            "什么时候适合换工作？",
            "我适合做什么类型的工作？",
            "我适合在哪个方向/城市发展？",
            "我在当前工作会有升职机会吗？",
            "我适合在出生地还是外地发展？",
            "我的财富格局有多大？",
            "我这辈子能赚多少钱？",
            "我适合投机性工作还是稳定工作？",
            "哪几年适合我创业？",
            "我的财富来自正财还是偏财？",
            "我适合买彩票吗？"
        ],
        "婚姻": [
            "我的婚姻运势如何？",
            "什么时候会遇到正缘？",
            "我的配偶性格特点？",
            "我的婚姻是否稳定？",
            "什么时候适合结婚？",
            "我的桃花运如何？",
            "我的感情运势如何？"
        ],
        "健康": [
            "我的健康状况如何？",
            "需要注意哪些疾病？",
            "我的体质特点？",
            "什么时候需要特别注意健康？",
            "我的养生建议？"
        ],
        "子女": [
            "我的子女运势如何？",
            "什么时候会有子女？",
            "我的子女数量？",
            "我的子女性格特点？",
            "我的子女运势如何？"
        ],
        "流年运势": [
            "我今年的运势如何？",
            "我明年的运势如何？",
            "我后三年的运势如何？",
            "我2025年的运势如何？",
            "我2025-2028年的运势如何？"
        ],
        "年运报告": [
            "我的整体运势如何？",
            "我的事业运势如何？",
            "我的财运如何？",
            "我的健康运势如何？",
            "我的感情运势如何？"
        ]
    }
    
    return default_questions.get(category, [
        "我的整体运势如何？",
        "我的事业运势如何？",
        "我的财运如何？"
    ])


def _get_default_related_questions(category: str) -> list:
    """获取默认相关问题列表（当LLM生成失败时使用）"""
    default_questions = {
        "事业财富": [
            "我的事业关键转折点是什么时候？",
            "我适合在哪个方向发展？",
            "我的财富格局有多大？"
        ],
        "婚姻": [
            "我什么时候会遇到正缘？",
            "我的配偶性格特点？",
            "我的婚姻是否稳定？"
        ],
        "健康": [
            "我需要注意哪些疾病？",
            "我的体质特点？",
            "什么时候需要特别注意健康？"
        ],
        "子女": [
            "我什么时候会有子女？",
            "我的子女数量？",
            "我的子女性格特点？"
        ],
        "流年运势": [
            "我今年的运势如何？",
            "我明年的运势如何？",
            "我后三年的运势如何？"
        ],
        "年运报告": [
            "我的整体运势如何？",
            "我的事业运势如何？",
            "我的财运如何？"
        ]
    }
    
    return default_questions.get(category, [
        "我的整体运势如何？",
        "我的事业运势如何？",
        "我的财运如何？"
    ])


def _sse_message(event_type: str, data: dict) -> str:
    """
    构造SSE消息格式
    
    SSE格式：
    event: <event_type>
    data: <json_data>
    
    """
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {json_data}\n\n"


def _format_pillars(pillars: dict) -> dict:
    """格式化四柱数据"""
    formatted = {}
    pillar_names = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
    for eng_name, cn_name in pillar_names.items():
        if eng_name in pillars:
            formatted[cn_name] = {
                "天干": pillars[eng_name].get("stem", ""),
                "地支": pillars[eng_name].get("branch", "")
            }
    return formatted

