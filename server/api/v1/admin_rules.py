#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则管理API接口（管理员接口）
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, project_root)

from server.db.rule_content_dao import RuleContentDAO

router = APIRouter()


class RizhuGenderContentRequest(BaseModel):
    """日柱性别内容请求模型"""
    rizhu: str = Field(..., description="日柱，如：甲子", example="甲子")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    descriptions: List[str] = Field(..., description="描述列表", example=["描述1", "描述2"])


class BatchContentRequest(BaseModel):
    """批量内容请求模型"""
    contents: List[RizhuGenderContentRequest] = Field(..., description="内容列表")


@router.post("/admin/rule-contents/rizhu-gender", summary="创建/更新日柱性别内容")
async def create_rizhu_gender_content(request: RizhuGenderContentRequest):
    """
    创建/更新日柱性别内容
    
    - **rizhu**: 日柱（如：甲子）
    - **gender**: 性别（male/female）
    - **descriptions**: 描述列表
    
    更新后会自动增加版本号，触发热加载
    """
    try:
        success = RuleContentDAO.save_rizhu_gender_content(
            request.rizhu,
            request.gender,
            request.descriptions
        )
        
        if success:
            return {
                "success": True,
                "message": f"日柱{request.rizhu}{'男' if request.gender == 'male' else '女'}命内容已更新",
                "rizhu": request.rizhu,
                "gender": request.gender,
                "description_count": len(request.descriptions)
            }
        else:
            raise HTTPException(status_code=500, detail="保存失败")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.post("/admin/rule-contents/batch-import", summary="批量导入日柱性别内容")
async def batch_import_contents(request: BatchContentRequest):
    """
    批量导入日柱性别内容
    
    - **contents**: 内容列表
    
    更新后会自动增加版本号，触发热加载
    """
    try:
        contents = [
            {
                'rizhu': item.rizhu,
                'gender': item.gender,
                'descriptions': item.descriptions
            }
            for item in request.contents
        ]
        
        success_count = RuleContentDAO.batch_save_rizhu_gender_contents(contents)
        
        return {
            "success": True,
            "message": f"批量导入完成",
            "total": len(contents),
            "success_count": success_count,
            "failed_count": len(contents) - success_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量导入失败: {str(e)}")


@router.get("/admin/rule-contents/rizhu-gender", summary="获取所有日柱性别内容")
async def get_all_rizhu_gender_contents():
    """
    获取所有日柱性别内容
    """
    try:
        contents = RuleContentDAO.get_all_rizhu_gender_contents()
        
        return {
            "success": True,
            "total": len(contents),
            "contents": contents
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.get("/admin/rule-contents/rizhu-gender/{rizhu}/{gender}", summary="获取指定日柱性别内容")
async def get_rizhu_gender_content(rizhu: str, gender: str):
    """
    获取指定日柱性别内容
    
    - **rizhu**: 日柱
    - **gender**: 性别
    """
    try:
        descriptions = RuleContentDAO.get_rizhu_gender_content(rizhu, gender)
        
        return {
            "success": True,
            "rizhu": rizhu,
            "gender": gender,
            "descriptions": descriptions,
            "count": len(descriptions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.put("/admin/rule-contents/rizhu-gender/{rizhu}/{gender}/enable", summary="启用日柱性别内容")
async def enable_rizhu_gender_content(rizhu: str, gender: str):
    """启用日柱性别内容"""
    try:
        success = RuleContentDAO.enable_rizhu_gender_content(rizhu, gender)
        if success:
            return {
                "success": True,
                "message": f"日柱{rizhu}{'男' if gender == 'male' else '女'}命内容已启用"
            }
        else:
            raise HTTPException(status_code=500, detail="启用失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启用失败: {str(e)}")


@router.put("/admin/rule-contents/rizhu-gender/{rizhu}/{gender}/disable", summary="禁用日柱性别内容")
async def disable_rizhu_gender_content(rizhu: str, gender: str):
    """禁用日柱性别内容"""
    try:
        success = RuleContentDAO.disable_rizhu_gender_content(rizhu, gender)
        if success:
            return {
                "success": True,
                "message": f"日柱{rizhu}{'男' if gender == 'male' else '女'}命内容已禁用"
            }
        else:
            raise HTTPException(status_code=500, detail="禁用失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"禁用失败: {str(e)}")


@router.get("/admin/rule-contents/version", summary="获取版本号")
async def get_version():
    """获取规则和内容版本号"""
    try:
        content_version = RuleContentDAO.get_content_version()
        rule_version = RuleContentDAO.get_rule_version()
        
        return {
            "success": True,
            "content_version": content_version,
            "rule_version": rule_version
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本号失败: {str(e)}")








































