#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字计算服务层
负责调用现有计算逻辑并格式化输出
"""

import logging
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.tool.BaziCalculator import BaziCalculator
from src.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
from src.clients.bazi_core_client_grpc import BaziCoreClient
from src.clients.bazi_rule_client_grpc import BaziRuleClient

logger = logging.getLogger(__name__)


class BaziService:
    """八字计算服务类"""
    
    @staticmethod
    def calculate_bazi_full(solar_date: str, solar_time: str, gender: str) -> dict:
        """
        完整计算八字信息
        
        Args:
            solar_date: 阳历日期，格式：YYYY-MM-DD
            solar_time: 出生时间，格式：HH:MM
            gender: 性别，'male' 或 'female'
        
        Returns:
            dict: 格式化的八字数据
        """
        # 1. 优先尝试调用 bazi-core-service（使用较短的超时时间，快速失败）
        bazi_result = None
        core_service_url = os.getenv("BAZI_CORE_SERVICE_URL")
        if core_service_url:
            try:
                # 使用30秒超时，确保有足够时间处理复杂计算
                client = BaziCoreClient(base_url=core_service_url, timeout=30.0)
                bazi_result = client.calculate_bazi(solar_date, solar_time, gender)
                logger.debug("BaziService 使用 bazi-core-service 计算八字")
            except Exception as exc:  # pragma: no cover - 仅在服务异常时触发
                # 静默失败，快速回退到本地计算（不打印警告，避免日志噪音）
                if os.getenv("BAZI_CORE_SERVICE_STRICT", "0") == "1":
                    # 严格模式：直接抛错由上层处理
                    raise

        # 2. 如未调用远程或失败，则使用本地计算
        if bazi_result is None:
            calculator = BaziCalculator(solar_date, solar_time, gender)
            bazi_result = calculator.calculate()
            calculator = None
        else:
            # ✅ 修复：如果 gRPC 服务返回的数据缺少某些字段，使用本地计算补充
            try:
                calculator = BaziCalculator(solar_date, solar_time, gender)
                # 只计算缺失的字段，不重新计算整个八字
                calculator._calculate_with_lunar()  # 初始化四柱数据
                calculator._calculate_ten_gods()  # 计算十神（包含 hidden_stars）
                calculator._calculate_hidden_stems()  # 计算藏干
                calculator._calculate_star_fortune()  # 计算星运和自坐
                
                # 补充缺失的字段
                local_details = calculator.details
                remote_details = bazi_result.get('details', {})
                
                for pillar_type in ['year', 'month', 'day', 'hour']:
                    if pillar_type in remote_details and pillar_type in local_details:
                        # 如果远程数据缺少这些字段，使用本地计算的值
                        if not remote_details[pillar_type].get('hidden_stems'):
                            remote_details[pillar_type]['hidden_stems'] = local_details[pillar_type].get('hidden_stems', [])
                        if not remote_details[pillar_type].get('hidden_stars'):
                            remote_details[pillar_type]['hidden_stars'] = local_details[pillar_type].get('hidden_stars', [])
                        if not remote_details[pillar_type].get('star_fortune'):
                            remote_details[pillar_type]['star_fortune'] = local_details[pillar_type].get('star_fortune', '')
                        if not remote_details[pillar_type].get('self_sitting'):
                            remote_details[pillar_type]['self_sitting'] = local_details[pillar_type].get('self_sitting', '')
            except Exception as e:
                # 如果本地计算失败，记录日志但不影响主流程
                logger.warning(f"本地计算补充字段失败: {e}")
        
        if not bazi_result:
            raise ValueError("八字计算失败，请检查输入参数")
        
        # 2. 获取日柱
        bazi_pillars = bazi_result.get('bazi_pillars', {})
        if not isinstance(bazi_pillars, dict):
            raise TypeError(f"bazi_result['bazi_pillars'] 必须是字典类型，但实际是: {type(bazi_pillars)}")
        
        day_pillar = bazi_pillars.get('day', {})
        if not isinstance(day_pillar, dict):
            raise TypeError(f"bazi_result['bazi_pillars']['day'] 必须是字典类型，但实际是: {type(day_pillar)}")
        
        day_stem = day_pillar.get('stem', '')
        day_branch = day_pillar.get('branch', '')
        rizhu = f"{day_stem}{day_branch}"
        
        # 3. 匹配规则（优化：跳过 gRPC 调用，因为规则匹配会在 API 层统一处理）
        # 注意：在 /api/v1/bazi/rules/match 接口中，规则匹配已经由 RuleService.match_rules 处理
        # 这里只返回空列表，避免重复调用和超时
        matched_rules = []
        
        # 4. 格式化输出
        return {
            "bazi": BaziService._format_bazi_result(bazi_result),
            "rizhu": rizhu,
            "matched_rules": matched_rules
        }
    
    @staticmethod
    def _format_bazi_result(bazi_result: dict) -> dict:
        """
        格式化八字结果为前端需要的格式
        
        Args:
            bazi_result: BaziCalculator.calculate() 返回的原始结果
        
        Returns:
            dict: 格式化后的八字数据
        """
        # 安全地获取字段，确保类型正确
        basic_info = bazi_result.get('basic_info', {})
        if not isinstance(basic_info, dict):
            raise TypeError(f"bazi_result['basic_info'] 必须是字典类型，但实际是: {type(basic_info)}")
        
        bazi_pillars = bazi_result.get('bazi_pillars', {})
        if not isinstance(bazi_pillars, dict):
            raise TypeError(f"bazi_result['bazi_pillars'] 必须是字典类型，但实际是: {type(bazi_pillars)}")
        
        details = bazi_result.get('details', {})
        if not isinstance(details, dict):
            raise TypeError(f"bazi_result['details'] 必须是字典类型，但实际是: {type(details)}")
        
        ten_gods_stats_raw = bazi_result.get('ten_gods_stats', {})
        elements_raw = bazi_result.get('elements', {})
        element_counts_raw = bazi_result.get('element_counts', {})
        relationships_raw = bazi_result.get('relationships', {})
        
        # ========== 修复 gRPC 序列化问题：确保所有字段都是正确的数据类型 ==========
        # 【重要警示】此处修复 gRPC 返回的字符串序列化问题
        # 历史教训：2025-11-20 因未全面修复所有字段，导致今日运势、月运势、大运流年全部失败
        # 原则：任何对 gRPC 相关代码的修改，必须检查所有可能受影响的字段，并进行全面测试！
        
        # 1. 修复 ten_gods_stats 字段
        ten_gods_stats = {}
        if isinstance(ten_gods_stats_raw, str):
            try:
                import ast
                ten_gods_stats = ast.literal_eval(ten_gods_stats_raw)
                logger.debug(f"ten_gods_stats 从字符串解析成功")
            except (ValueError, SyntaxError):
                try:
                    import json
                    ten_gods_stats = json.loads(ten_gods_stats_raw)
                    logger.debug(f"ten_gods_stats 使用JSON解析成功")
                except (json.JSONDecodeError, TypeError):
                    logger.error(f"ten_gods_stats 解析失败: {ten_gods_stats_raw[:100]}")
                    ten_gods_stats = {}
        elif isinstance(ten_gods_stats_raw, dict):
            ten_gods_stats = ten_gods_stats_raw
        else:
            logger.warning(f"ten_gods_stats 类型异常: {type(ten_gods_stats_raw)}")
            ten_gods_stats = {}
        
        # 2. 修复 element_counts 字段
        element_counts = {}
        if isinstance(element_counts_raw, str):
            try:
                import ast
                element_counts = ast.literal_eval(element_counts_raw)
            except:
                try:
                    import json
                    element_counts = json.loads(element_counts_raw)
                except:
                    logger.error(f"element_counts 解析失败: {element_counts_raw[:100]}")
                    element_counts = {}
        elif isinstance(element_counts_raw, dict):
            element_counts = element_counts_raw
        else:
            element_counts = {}
        
        # 3. 修复 relationships 字段
        relationships = {}
        if isinstance(relationships_raw, str):
            try:
                import ast
                relationships = ast.literal_eval(relationships_raw)
            except:
                try:
                    import json
                    relationships = json.loads(relationships_raw)
                except:
                    logger.error(f"relationships 解析失败: {relationships_raw[:100]}")
                    relationships = {}
        elif isinstance(relationships_raw, dict):
            relationships = relationships_raw
        else:
            relationships = {}
        
        # 4. 修复 elements 字段：确保所有值都是字典而不是字符串
        elements = {}
        if isinstance(elements_raw, dict):
            for pillar_type in ['year', 'month', 'day', 'hour']:
                pillar_element = elements_raw.get(pillar_type, {})
                # 如果是字符串（gRPC 序列化问题），尝试解析或使用空字典
                if isinstance(pillar_element, str):
                    try:
                        # 先尝试用 ast.literal_eval（支持Python字典格式，单引号）
                        import ast
                        pillar_element = ast.literal_eval(pillar_element)
                    except (ValueError, SyntaxError):
                        # 如果失败，尝试 json.loads（标准JSON，双引号）
                        try:
                            import json
                            pillar_element = json.loads(pillar_element)
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(f"elements['{pillar_type}'] 是字符串且无法解析: {pillar_element[:100]}")
                            pillar_element = {}
                # 确保是字典类型
                if not isinstance(pillar_element, dict):
                    pillar_element = {}
                elements[pillar_type] = pillar_element
        else:
            logger.warning(f"elements 不是字典类型: {type(elements_raw)}, 使用空字典")
        
        # 格式化农历日期
        lunar_date_info = basic_info.get('lunar_date', {})
        if not isinstance(lunar_date_info, dict):
            # 如果 lunar_date 不是字典，尝试从其他字段获取
            lunar_date_info = {}
        
        lunar_date = {
            "year": lunar_date_info.get('year', ''),
            "month": lunar_date_info.get('month', ''),
            "day": lunar_date_info.get('day', '')
        }
        
        # 格式化四柱信息
        formatted_details = {}
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar_details = details.get(pillar_type, {})
            if not isinstance(pillar_details, dict):
                pillar_details = {}
            
            formatted_details[pillar_type] = {
                "main_star": pillar_details.get('main_star', ''),
                "hidden_stars": pillar_details.get('hidden_stars', []),
                "hidden_stems": pillar_details.get('hidden_stems', []),
                "star_fortune": pillar_details.get('star_fortune', ''),
                "self_sitting": pillar_details.get('self_sitting', ''),
                "kongwang": pillar_details.get('kongwang', ''),
                "nayin": pillar_details.get('nayin', ''),
                "deities": pillar_details.get('deities', [])
            }
        
        # 安全地获取四柱信息
        year_pillar = bazi_pillars.get('year', {})
        month_pillar = bazi_pillars.get('month', {})
        day_pillar = bazi_pillars.get('day', {})
        hour_pillar = bazi_pillars.get('hour', {})
        
        if not isinstance(year_pillar, dict):
            year_pillar = {}
        if not isinstance(month_pillar, dict):
            month_pillar = {}
        if not isinstance(day_pillar, dict):
            day_pillar = {}
        if not isinstance(hour_pillar, dict):
            hour_pillar = {}
        
        return {
            "basic_info": {
                "solar_date": basic_info.get('solar_date', ''),
                "solar_time": basic_info.get('solar_time', ''),
                "lunar_date": lunar_date,
                "gender": basic_info.get('gender', 'male')
            },
            "bazi_pillars": {
                "year": {
                    "stem": year_pillar.get('stem', ''),
                    "branch": year_pillar.get('branch', '')
                },
                "month": {
                    "stem": month_pillar.get('stem', ''),
                    "branch": month_pillar.get('branch', '')
                },
                "day": {
                    "stem": day_pillar.get('stem', ''),
                    "branch": day_pillar.get('branch', '')
                },
                "hour": {
                    "stem": hour_pillar.get('stem', ''),
                    "branch": hour_pillar.get('branch', '')
                }
            },
            "details": formatted_details,
            "ten_gods_stats": ten_gods_stats,
            "elements": elements,
            "element_counts": element_counts,
            "relationships": relationships
        }
    
    @staticmethod
    def _match_rules(bazi_result: dict, rule_types=None) -> list:
        """
        通过规则微服务匹配规则，失败时回退日柱性别分析
        """
        rule_service_url = os.getenv("BAZI_RULE_SERVICE_URL")
        if rule_service_url:
            try:
                # 安全地获取基本信息
                basic_info = bazi_result.get('basic_info', {})
                if not isinstance(basic_info, dict):
                    logger.warning("bazi_result['basic_info'] 不是字典类型，跳过规则服务调用")
                else:
                    # 使用较短的超时时间（3秒），快速失败并回退到本地分析
                    # 规则匹配可能需要较长时间（处理462条规则），使用60秒超时
                    client = BaziRuleClient(base_url=rule_service_url, timeout=60.0)
                    rule_data = client.match_rules(
                        solar_date=basic_info.get('solar_date', ''),
                        solar_time=basic_info.get('solar_time', ''),
                        gender=basic_info.get('gender', 'male'),
                        rule_types=rule_types,
                    )
                    return rule_data.get('matched', [])
            except Exception as exc:
                # 静默失败，快速回退到本地日柱分析（不打印警告，避免日志噪音）
                pass

        # 回退：使用日柱性别分析构造简单规则
        bazi_pillars = bazi_result.get('bazi_pillars', {})
        if not isinstance(bazi_pillars, dict):
            logger.error("bazi_result['bazi_pillars'] 不是字典类型: %s", type(bazi_pillars))
            return []
        
        day_pillar = bazi_pillars.get('day', {})
        if not isinstance(day_pillar, dict):
            logger.error("bazi_result['bazi_pillars']['day'] 不是字典类型: %s", type(day_pillar))
            return []
        
        day_stem = day_pillar.get('stem', '')
        day_branch = day_pillar.get('branch', '')
        
        basic_info = bazi_result.get('basic_info', {})
        if not isinstance(basic_info, dict):
            logger.error("bazi_result['basic_info'] 不是字典类型: %s", type(basic_info))
            return []
        
        gender = basic_info.get('gender', 'male')

        temp_pillars = {'day': {'stem': day_stem, 'branch': day_branch}}
        try:
            analyzer = RizhuGenderAnalyzer(temp_pillars, gender)
            analysis_result = analyzer.analyze_rizhu_gender()
            if not analysis_result.get('has_data'):
                return []
            
            descriptions = analysis_result.get('descriptions', [])
            if not descriptions:
                return []
            return [{
                "rule_code": f"RZ_{day_stem}{day_branch}_{gender}",
                "rule_name": f"{day_stem}{day_branch}{'男' if gender == 'male' else '女'}命分析",
                "rule_type": "rizhu_gender",
                "priority": 100,
                "contents": [
                    {"type": "description", "text": desc}
                    for desc in descriptions
                ]
            }]
        except Exception as exc:
            logger.error("本地日柱分析失败: %s", exc)
            return []

