#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日运势日历API接口
基于万年历接口，提供完整的每日运势信息
"""

import sys
import os
import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.services.daily_fortune_calendar_service import DailyFortuneCalendarService
from server.services.coze_stream_service import CozeStreamService
from server.utils.bazi_input_processor import BaziInputProcessor
from server.api.v1.models.bazi_base_models import BaziBaseRequest

# 导入配置加载器（从数据库读取配置）
try:
    from server.config.config_loader import get_config_from_db_only
except ImportError:
    # 如果导入失败，抛出错误（不允许降级）
    def get_config_from_db_only(key: str) -> Optional[str]:
        raise ImportError("无法导入配置加载器，请确保 server.config.config_loader 模块可用")

router = APIRouter()


class DailyFortuneCalendarRequest(BaseModel):
    """每日运势日历请求模型（所有参数都是可选的，未登录时只需要date）"""
    date: Optional[str] = Field(None, description="日期（可选，默认为今天），格式：YYYY-MM-DD", example="2025-01-15")
    # 用户生辰信息（可选，用于十神提示）
    solar_date: Optional[str] = Field(None, description="用户生辰阳历日期（可选），格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: Optional[str] = Field(None, description="用户生辰时间（可选），格式：HH:MM", example="14:30")
    gender: Optional[str] = Field(None, description="用户性别（可选），male/female", example="male")
    calendar_type: Optional[str] = Field("solar", description="历法类型：solar(阳历) 或 lunar(农历)，默认solar", example="solar")
    location: Optional[str] = Field(None, description="出生地点（用于时区转换，优先级1）", example="北京")
    latitude: Optional[float] = Field(None, description="纬度（用于时区转换，优先级2）", example=39.90)
    longitude: Optional[float] = Field(None, description="经度（用于时区转换和真太阳时计算，优先级2）", example=116.40)
    
    @validator('date')
    def validate_date(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式错误，应为 YYYY-MM-DD')
        return v
    
    @validator('solar_date')
    def validate_solar_date(cls, v):
        if v is None:
            return v
        # 允许任何格式通过（包括农历日期字符串）
        return v
    
    @validator('solar_time')
    def validate_solar_time(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError('时间格式错误，应为 HH:MM')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        if v is None:
            return v
        if v not in ['male', 'female']:
            raise ValueError('性别必须为 male 或 female')
        return v
    
    @validator('calendar_type')
    def validate_calendar_type(cls, v):
        if v and v not in ['solar', 'lunar']:
            raise ValueError('历法类型必须为 solar 或 lunar')
        return v or "solar"


class JianchuInfo(BaseModel):
    """建除信息模型"""
    name: Optional[str] = None  # 建除名称（如：危）
    energy: Optional[int] = None  # 能量（如：90）
    summary: Optional[str] = None  # 能量小结内容


class MasterInfo(BaseModel):
    """命主信息模型"""
    rizhu: Optional[str] = None  # 日主（如：甲木）
    today_shishen: Optional[str] = None  # 今日十神（如：比肩）


class DailyFortuneCalendarResponse(BaseModel):
    """每日运势日历响应模型"""
    success: bool
    # 基础万年历信息
    solar_date: Optional[str] = None  # 当前阳历日期
    lunar_date: Optional[str] = None  # 当前阴历日期
    weekday: Optional[str] = None  # 星期几（中文）
    weekday_en: Optional[str] = None  # 星期几（英文）
    # 万年历信息
    yi: Optional[List[str]] = None  # 宜
    ji: Optional[List[str]] = None  # 忌
    luck_level: Optional[str] = None  # 吉凶等级
    deities: Optional[Dict[str, Any]] = None  # 神煞方位（喜神、财神、福神、胎神）
    chong_he_sha: Optional[Dict[str, Any]] = None  # 冲合煞（冲、合、煞）
    jianchu: Optional[JianchuInfo] = None  # 建除信息（包含名称、分数、小结）
    # 胎神信息
    taishen: Optional[str] = None  # 胎神方位（如：占门厕外正东）
    taishen_explanation: Optional[str] = None  # 胎神解释
    # 运势内容
    jiazi_fortune: Optional[str] = None  # 整体运势（六十甲子）
    shishen_hint: Optional[str] = None  # 十神提示（需要用户生辰）
    zodiac_relations: Optional[str] = None  # 生肖简运
    # 新增功能
    master_info: Optional[MasterInfo] = None  # 命主信息（日主、今日十神）
    wuxing_wear: Optional[str] = None  # 五行穿搭（逗号分隔）
    guiren_fangwei: Optional[str] = None  # 贵人方位（逗号分隔）
    wenshen_directions: Optional[str] = None  # 瘟神方位（逗号分隔）
    error: Optional[str] = None


@router.post("/daily-fortune-calendar/query", response_model=DailyFortuneCalendarResponse, summary="查询每日运势日历")
async def query_daily_fortune_calendar(request: DailyFortuneCalendarRequest):
    """
    查询每日运势日历信息
    
    基于万年历接口，提供完整的每日运势信息，包括：
    - 基础万年历信息（阳历、阴历、星期、宜忌、吉凶等级、神煞方位、冲合煞、建除）
    - 胎神信息（胎神方位和解释）
    - 整体运势（根据甲子日匹配六十甲子运势）
    - 十神提示（根据日干与用户生辰日干计算，需要用户生辰信息）
    - 生肖简运（根据日支匹配生肖刑冲破害）
    - 命主信息（日主、今日十神）
    - 五行穿搭（万年历方位颜色+十神颜色）
    - 贵人方位（喜神、福神方位+日干方位）
    - 瘟神方位（万年历煞方位+日支方位）
    
    **参数说明**：
    - **date**: 查询日期（可选，默认为今天），格式：YYYY-MM-DD
    - **solar_date**: 用户生辰阳历日期（可选，用于十神提示），格式：YYYY-MM-DD
    - **solar_time**: 用户生辰时间（可选），格式：HH:MM
    - **gender**: 用户性别（可选），male/female
    
    **注意**：
    - 如果未提供用户生辰信息，十神提示将为空
    - 所有运势数据从数据库读取，不直接读取Excel文件
    
    返回完整的每日运势信息
    """
    try:
        # 处理用户生辰的农历输入和时区转换（如果提供了生辰信息）
        user_final_solar_date = request.solar_date
        user_final_solar_time = request.solar_time
        conversion_info = None
        
        if request.solar_date and request.solar_time and request.gender:
            try:
                user_final_solar_date, user_final_solar_time, conversion_info = BaziInputProcessor.process_input(
                    request.solar_date,
                    request.solar_time,
                    request.calendar_type or "solar",
                    request.location,
                    request.latitude,
                    request.longitude
                )
            except Exception as e:
                # 转换失败不影响主流程，使用原始值
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"用户生辰转换失败，使用原始值: {e}")
        
        # 使用模块级别的导入（已在文件顶部导入）
        result = DailyFortuneCalendarService.get_daily_fortune_calendar(
            date_str=request.date,
            user_solar_date=user_final_solar_date,
            user_solar_time=user_final_solar_time,
            user_gender=request.gender
        )
        
        if result.get('success'):
            # 处理建除信息
            jianchu_info = result.get('jianchu')
            jianchu_model = None
            # 兼容处理：如果jianchu是字符串，尝试从数据库查询
            if isinstance(jianchu_info, str) and jianchu_info:
                jianchu_dict = DailyFortuneCalendarService.get_jianchu_info(jianchu_info)
                if jianchu_dict:
                    jianchu_info = jianchu_dict
            if jianchu_info and isinstance(jianchu_info, dict):
                jianchu_model = JianchuInfo(
                    name=jianchu_info.get('name'),
                    energy=jianchu_info.get('energy'),
                    summary=jianchu_info.get('summary')
                )
            
            # 处理命主信息
            master_info = result.get('master_info')
            master_info_model = None
            if master_info and isinstance(master_info, dict):
                master_info_model = MasterInfo(
                    rizhu=master_info.get('rizhu'),
                    today_shishen=master_info.get('today_shishen')
                )
            
            # 构建响应数据
            response_dict = {
                'success': True,
                'solar_date': result.get('solar_date'),
                'lunar_date': result.get('lunar_date'),
                'weekday': result.get('weekday'),
                'weekday_en': result.get('weekday_en'),
                'yi': result.get('yi', []),
                'ji': result.get('ji', []),
                'luck_level': result.get('luck_level'),
                'deities': result.get('deities', {}),
                'chong_he_sha': result.get('chong_he_sha', {}),
                'jianchu': jianchu_model,
                'taishen': result.get('taishen'),
                'taishen_explanation': result.get('taishen_explanation'),
                'jiazi_fortune': result.get('jiazi_fortune'),
                'shishen_hint': result.get('shishen_hint'),
                'zodiac_relations': result.get('zodiac_relations'),
                'master_info': master_info_model,
                'wuxing_wear': result.get('wuxing_wear') if result.get('wuxing_wear') else None,  # 空字符串转为None
                'guiren_fangwei': result.get('guiren_fangwei'),
                'wenshen_directions': result.get('wenshen_directions')
            }
            
            # 添加转换信息到结果（如果进行了转换）
            if conversion_info and (conversion_info.get('converted') or conversion_info.get('timezone_info')):
                response_dict['conversion_info'] = conversion_info
            
            return DailyFortuneCalendarResponse(**response_dict)
        else:
            return DailyFortuneCalendarResponse(
                success=False,
                error=result.get('error', '获取每日运势失败')
            )
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"查询每日运势异常: {str(e)}\n{traceback.format_exc()}"
        )


class ActionSuggestionsRequest(BaseModel):
    """行动建议请求模型"""
    yi: List[str] = Field(..., description="宜事项列表", example=["解除", "扫舍", "馀事勿取"])
    ji: List[str] = Field(..., description="忌事项列表", example=["诸事不宜"])
    bot_id: Optional[str] = Field(None, description="Coze Bot ID（可选，优先级：参数 > DAILY_FORTUNE_ACTION_BOT_ID 环境变量）", example="7584766797639958555")


async def action_suggestions_stream_generator(
    yi_list: List[str],
    ji_list: List[str],
    bot_id: Optional[str] = None
):
    """
    流式生成行动建议的生成器
    
    Args:
        yi_list: 宜事项列表
        ji_list: 忌事项列表
        bot_id: Coze Bot ID（可选，优先级：参数 > DAILY_FORTUNE_ACTION_BOT_ID > 默认值）
    """
    try:
        # 确定使用的 bot_id（优先级：参数 > 数据库配置）
        if not bot_id:
            # 只从数据库读取，不降级到环境变量
            bot_id = get_config_from_db_only("DAILY_FORTUNE_ACTION_BOT_ID")
            if not bot_id:
                error_msg = {
                    'type': 'error',
                    'content': "数据库配置缺失: DAILY_FORTUNE_ACTION_BOT_ID，请在 service_configs 表中配置，或在请求参数中提供 bot_id。"
                }
                yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
                return
        
        # 创建Coze流式服务（捕获初始化错误）
        try:
            coze_service = CozeStreamService(bot_id=bot_id)
        except ValueError as e:
            # 数据库配置缺失
            error_msg = {
                'type': 'error',
                'content': f"Coze API 配置缺失: {str(e)}。请在 service_configs 表中配置 COZE_ACCESS_TOKEN 和 COZE_BOT_ID。"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        except Exception as e:
            error_msg = {
                'type': 'error',
                'content': f"初始化 Coze 服务失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            return
        
        # 流式生成
        async for result in coze_service.stream_action_suggestions(yi_list, ji_list, bot_id):
            # 转换为SSE格式
            if result.get('type') == 'progress':
                # 进度消息
                msg = {
                    'type': 'progress',
                    'content': result.get('content', '')
                }
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)
            elif result.get('type') == 'complete':
                # 完成消息
                msg = {
                    'type': 'complete',
                    'content': result.get('content', '')
                }
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                return
            elif result.get('type') == 'error':
                # 错误消息
                msg = {
                    'type': 'error',
                    'content': result.get('content', '生成失败')
                }
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                return
    except Exception as e:
        import traceback
        error_msg = {
            'type': 'error',
            'content': f"生成行动建议失败: {str(e)}\n{traceback.format_exc()}"
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"


@router.post("/daily-fortune-calendar/action-suggestions/stream", summary="流式生成行动建议")
async def action_suggestions_stream(request: ActionSuggestionsRequest):
    """
    流式生成行动建议
    
    使用Coze大模型美化宜忌内容，返回SSE流式响应。
    
    **参数说明**：
    - **yi**: 宜事项列表（必填）
    - **ji**: 忌事项列表（必填）
    - **bot_id**: Coze Bot ID（可选，优先级：参数 > DAILY_FORTUNE_ACTION_BOT_ID 环境变量）
    
    **返回格式**：
    SSE流式响应，每行格式：`data: {"type": "progress|complete|error", "content": "..."}`
    
    **示例**：
    ```
    data: {"type": "progress", "content": "宜："}
    data: {"type": "progress", "content": "今日"}
    data: {"type": "complete", "content": "宜：今日适合解除束缚，清扫环境，其他事项暂缓。忌：今日不宜进行重大决策或重要活动。"}
    ```
    """
    try:
        return StreamingResponse(
            action_suggestions_stream_generator(
                request.yi,
                request.ji,
                request.bot_id  # bot_id 在 generator 中处理默认值
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"流式生成行动建议异常: {str(e)}\n{traceback.format_exc()}"
        )

