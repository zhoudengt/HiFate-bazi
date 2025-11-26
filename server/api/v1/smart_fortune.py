# -*- coding: utf-8 -*-
"""
智能运势分析API - 基于Intent Service
"""
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import sys
import os
import json
import logging

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from server.services.intent_client import IntentServiceClient
from server.services.bazi_service import BaziService
from server.services.fortune_llm_client import get_fortune_llm_client
from src.tool.BaziCalculator import BaziCalculator

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


@router.get("/smart-analyze")
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
    
    自动识别用户问题意图，返回针对性的分析结果
    """
    try:
        # 步骤1：意图识别
        intent_client = IntentServiceClient()
        intent_result = intent_client.classify(
            question=question,
            user_id=user_id or "anonymous"
        )
        print(f"[DEBUG] intent_result type: {type(intent_result)}")
        print(f"[DEBUG] intent_result: {intent_result}")
        
        # 防御性检查：确保intent_result不为None
        if intent_result is None:
            print("[DEBUG] intent_result is None, using default")
            intent_result = {
                "intents": ["general"],
                "confidence": 0.5,
                "keywords": [],
                "is_ambiguous": True,
                "time_intent": None,
                "is_fortune_related": True
            }
        
        # 如果问题不相关（LLM已判断）
        if not intent_result.get("is_fortune_related", True) or "non_fortune" in intent_result.get("intents", []):
            return {
                "success": False,
                "message": intent_result.get("reject_message", "您的问题似乎与命理运势无关，我只能回答关于八字、运势等相关问题。"),
                "intent_result": intent_result
            }
        
        # 步骤1.5：获取时间意图（LLM已识别）
        time_intent = intent_result.get("time_intent", {})
        print(f"[DEBUG] time_intent: {time_intent}")
        target_years = time_intent.get("target_years", []) if time_intent else []
        print(f"[smart_fortune] 时间意图识别（LLM）: {time_intent.get('description', 'N/A')} -> {target_years}")
        
        # 步骤2：计算八字
        solar_date = f"{year:04d}-{month:02d}-{day:02d}"
        solar_time = f"{hour:02d}:00"
        calculator = BaziCalculator(solar_date, solar_time, gender)
        bazi_result = calculator.calculate()
        
        if not bazi_result or "error" in bazi_result:
            raise HTTPException(status_code=400, detail="八字计算失败")
        
        # 步骤3：根据意图匹配规则
        rule_types = intent_result.get("rule_types", ["ALL"])
        confidence = intent_result.get("confidence", 0)
        
        # 如果意图识别置信度低（<60%），使用关键词fallback
        if confidence < 0.6 and "ALL" in rule_types:
            fallback_types = _extract_rule_types_from_question(question)
            if fallback_types != ["ALL"]:
                rule_types = fallback_types
                intent_result["rule_types"] = rule_types  # 更新结果
                intent_result["fallback_used"] = True
                intent_result["intents"] = fallback_types  # 同时更新intents
        
        matched_rules = []
        for rule_type in rule_types:
            if rule_type != "ALL":
                # rule_type是字符串，需要包装成列表传递给_match_rules
                rules = bazi_service._match_rules(bazi_result, [rule_type])
                matched_rules.extend(rules)
        
        # 如果是综合分析或没有匹配到特定规则
        if not matched_rules or "ALL" in rule_types:
            rules = bazi_service._match_rules(bazi_result)
            matched_rules = rules
        
        # 步骤3.5：获取流年大运上下文（可选，默认关闭）
        fortune_context = None
        if include_fortune_context:  # ⭐ 移除 rule_types != ["ALL"] 限制
            try:
                from server.services.fortune_context_service import FortuneContextService
                print(f"[smart_fortune] 开始获取流年大运分析，rule_types={rule_types}, years={target_years}")
                
                # 获取流年大运上下文（使用LLM识别的时间意图）
                fortune_context = FortuneContextService.get_fortune_context(
                    solar_date=solar_date,
                    solar_time=solar_time,
                    gender=gender,
                    intent_types=rule_types,
                    target_years=target_years  # 使用LLM识别的年份列表
                )
            except Exception as e:
                # 静默失败，不影响主流程
                print(f"[smart_fortune] Fortune context error (ignored): {e}")
                import traceback
                print(f"[smart_fortune] Traceback:")
                traceback.print_exc()
                fortune_context = None
        
        # 步骤4：生成回答
        llm_deep_analysis = None  # 用于存储LLM深度解读
        
        if fortune_context:
            # 🆕 步骤4.1：调用命理分析Bot生成深度解读
            try:
                llm_client = get_fortune_llm_client()
                
                # 提取意图（使用第一个意图，如果没有则为"general"）
                main_intent = rule_types[0] if rule_types and rule_types[0] != "ALL" else "general"
                
                # 调用命理分析Bot（传递匹配到的规则）
                llm_result = llm_client.analyze_fortune(
                    intent=main_intent,
                    question=question,
                    bazi_data=bazi_result,
                    fortune_context=fortune_context,
                    matched_rules=matched_rules  # ⭐ 传递规则内容
                )
                
                if llm_result.get("success"):
                    llm_deep_analysis = llm_result.get("analysis")
                    print(f"[smart_fortune] ✅ LLM深度分析生成成功，长度：{len(llm_deep_analysis) if llm_deep_analysis else 0}")
                else:
                    print(f"[smart_fortune] ⚠️ LLM深度分析失败: {llm_result.get('error')}")
            
            except Exception as e:
                print(f"[smart_fortune] ❌ LLM深度分析异常: {e}")
                import traceback
                traceback.print_exc()
            
            # 步骤4.2：使用增强版响应生成（包含流年大运 + LLM深度解读）
            response_text = _generate_response_with_fortune(
                question=question,
                intent_result=intent_result,
                bazi_result=bazi_result,
                matched_rules=matched_rules,
                fortune_context=fortune_context,
                llm_deep_analysis=llm_deep_analysis  # 传入LLM深度解读
            )
        else:
            # 使用原有响应生成（保持不变）
            response_text = _generate_response(
                question=question,
                intent_result=intent_result,
                bazi_result=bazi_result,
                matched_rules=matched_rules
            )
        
        # 提取八字信息（适配BaziCalculator的数据结构）
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
            "intent_result": intent_result,  # 保留完整的意图结果（含time_intent、is_fortune_related等）
            "bazi_info": {
                "四柱": formatted_pillars,
                "十神": bazi_result.get("ten_gods_stats", {}),
                "五行": bazi_result.get("element_counts", {})
            },
            "matched_rules_count": len(matched_rules),
            "response": response_text
        }
        
        # ⭐ 添加fortune_context（如果有）
        if fortune_context:
            result["fortune_context"] = fortune_context
            print(f"[smart_fortune] ✅ fortune_context已添加到响应中")
        
        return result
        
    except Exception as e:
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
                    # 提取规则内容（content是字典格式）
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


@router.get("/smart-analyze-stream")
async def smart_analyze_stream(
    question: str = Query(..., description="用户问题"),
    year: int = Query(..., description="出生年份"),
    month: int = Query(..., description="出生月份"),
    day: int = Query(..., description="出生日期"),
    hour: int = Query(12, description="出生时辰（0-23）"),
    gender: str = Query(..., description="性别（male/female）"),
    user_id: Optional[str] = Query(None, description="用户ID")
):
    """
    智能运势分析（流式输出版）
    
    用户体验优化：
    - 立即返回基础分析
    - 流式输出LLM深度解读
    - 感知速度大幅提升
    """
    
    async def event_generator():
        """生成SSE事件流"""
        try:
            # 步骤1：意图识别
            yield _sse_message("status", {"stage": "intent", "message": "正在识别意图..."})
            
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
            
            # 如果问题不相关（LLM已判断）
            if not intent_result.get("is_fortune_related", True) or "non_fortune" in intent_result.get("intents", []):
                yield _sse_message("error", {
                    "message": intent_result.get("reject_message", "您的问题似乎与命理运势无关，我只能回答关于八字、运势等相关问题。")
                })
                yield _sse_message("end", {})
                return
            
            # 步骤1.5：获取时间意图（LLM已识别）
            time_intent = intent_result.get("time_intent", {})
            target_years = time_intent.get("target_years", [])
            
            # 精简日志：只在需要时输出关键信息
            import json
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"[STEP1] Intent识别: question={question}, intents={intent_result.get('intents', [])}, target_years={target_years}")
            
            # 步骤2：计算八字
            yield _sse_message("status", {"stage": "bazi", "message": "正在计算八字..."})
            
            solar_date = f"{year:04d}-{month:02d}-{day:02d}"
            solar_time = f"{hour:02d}:00"
            calculator = BaziCalculator(solar_date, solar_time, gender)
            bazi_result = calculator.calculate()
            
            if not bazi_result or "error" in bazi_result:
                yield _sse_message("error", {"message": "八字计算失败"})
                yield _sse_message("end", {})
                return
            
            # 精简日志
            logger.debug(f"[STEP2] 八字计算完成: {solar_date} {solar_time}, gender={gender}")
            
            # 步骤3：匹配规则
            yield _sse_message("status", {"stage": "rules", "message": "正在匹配规则..."})
            
            rule_types = intent_result.get("rule_types", ["ALL"])
            confidence = intent_result.get("confidence", 0)
            
            # 关键词fallback
            if confidence < 0.6 and "ALL" in rule_types:
                fallback_types = _extract_rule_types_from_question(question)
                if fallback_types != ["ALL"]:
                    rule_types = fallback_types
            
            matched_rules = []
            for rule_type in rule_types:
                if rule_type != "ALL":
                    rules = bazi_service._match_rules(bazi_result, [rule_type])
                    matched_rules.extend(rules)
            
            if not matched_rules or "ALL" in rule_types:
                rules = bazi_service._match_rules(bazi_result)
                matched_rules = rules
            
            # 步骤4：获取流年大运上下文
            yield _sse_message("status", {"stage": "fortune", "message": "正在分析流年大运..."})
            
            # 步骤4：获取流年大运上下文
            fortune_context = None
            if target_years:
                try:
                    from server.services.fortune_context_service import FortuneContextService
                    
                    # 精简日志
                    logger.debug(f"[STEP4] Fortune Context开始: target_years={target_years}, intent_types={rule_types}")
                    
                    fortune_context = FortuneContextService.get_fortune_context(
                        solar_date=solar_date,
                        solar_time=solar_time,
                        gender=gender,
                        intent_types=rule_types,
                        target_years=target_years
                    )
                    
                    # 精简日志
                    if fortune_context:
                        liunian_list = fortune_context.get('time_analysis', {}).get('liunian_list', [])
                        logger.debug(f"[STEP4] Fortune Context完成: 流年数量={len(liunian_list)}")
                    else:
                        logger.debug(f"[STEP4] Fortune Context完成: 返回None")
                except Exception as e:
                    logger.error(f"Fortune context error: {e}", exc_info=True)
            else:
                logger.debug("无目标年份，跳过流年大运分析")
            
            # 步骤5：发送基础分析结果（立即显示）
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
            
            # 步骤6：流式输出LLM深度解读
            yield _sse_message("status", {"stage": "llm", "message": "正在生成深度解读..."})
            
            try:
                llm_client = get_fortune_llm_client()
                main_intent = rule_types[0] if rule_types and rule_types[0] != "ALL" else "general"
                
                # 调用流式API（传递匹配到的规则）
                for chunk in llm_client.analyze_fortune(
                    intent=main_intent,
                    question=question,
                    bazi_data=bazi_result,
                    fortune_context=fortune_context,
                    matched_rules=matched_rules,  # ⭐ 传递规则内容
                    stream=True  # 启用流式输出
                ):
                    chunk_type = chunk.get('type')
                    
                    if chunk_type == 'start':
                        yield _sse_message("llm_start", {})
                    elif chunk_type == 'chunk':
                        content = chunk.get('content', '')
                        yield _sse_message("llm_chunk", {"content": content})
                    elif chunk_type == 'end':
                        yield _sse_message("llm_end", {})
                    elif chunk_type == 'error':
                        error_msg = chunk.get('error', '未知错误')
                        yield _sse_message("llm_error", {"message": error_msg})
            
            except Exception as e:
                print(f"[smart_fortune_stream] LLM streaming error: {e}")
                yield _sse_message("llm_error", {"message": str(e)})
            
            # 结束
            yield _sse_message("end", {})
        
        except Exception as e:
            print(f"[smart_fortune_stream] Stream error: {e}")
            import traceback
            traceback.print_exc()
            yield _sse_message("error", {"message": str(e)})
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

