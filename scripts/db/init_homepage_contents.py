#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化首页内容数据
插入默认的4个内容块：AI守护神、八字命理、流年运势、相术风水
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from server.db.homepage_content_dao import HomepageContentDAO


def init_homepage_contents():
    """初始化首页内容数据"""
    
    # 默认内容数据（图片Base64需要实际提供）
    default_contents = [
        {
            "title": "AI守护神",
            "tags": ["科技", "精准"],
            "description": "灵境大模型，以AI命理产品技术架构和技术驱动的数据科学为核心，将命理符号转化为AI向量空间'能量场'，实现相对于传统命理产品的代际超越。产品通过'功能专项支撑+底层创新赋能+合规保障'的核心维度架构，全面提升专业准确度、交互体验和合规安全性，建立领先的AI命理技术生态，树立技术与合规的行业标杆。",
            "image_base64": "",  # 需要实际提供图片的Base64编码
            "sort_order": 1
        },
        {
            "title": "八字命理",
            "tags": ["古籍", "专业"],
            "description": "八字排盘：基于'藏经阁'10万+真实八字案例和'诸天图星'排盘规则作为数据基础，通过灵境大模型'星盘淬炼'训练和RAG增强，实现99.5%排盘准确率，结合1秒超快推理和3D动态盘可视化，夯实八字分析基础。",
            "image_base64": "",  # 需要实际提供图片的Base64编码
            "sort_order": 2
        },
        {
            "title": "流年运势",
            "tags": ["全面", "深度"],
            "description": "运势解读：依托多派经典融合和用户反馈闭环数据，通过灵境大模型全流程训练（预训练+SFT微调+LoRA适配+RLHF优化），实现'一输入，多派输出'，同时生成趋吉避凶的实用建议，覆盖生活陪伴全场景。",
            "image_base64": "",  # 需要实际提供图片的Base64编码
            "sort_order": 3
        },
        {
            "title": "相术风水",
            "tags": ["背书", "擅长", "传承"],
            "description": "基于10万+视觉样本库和500+风水核心规则，'天眼通'视觉模型精准识别空间特征，融合灵境大模型规则融合推理，解决传统风水分析主观抽象痛点。面相分析方面，构建海量人脸/手相样本库和关联命理规则，分析生成可解释报告并可视化标注，提升解读的客观性和便利性。",
            "image_base64": "",  # 需要实际提供图片的Base64编码
            "sort_order": 4
        }
    ]
    
    print("开始初始化首页内容数据...")
    
    # 检查是否已有数据
    existing_contents = HomepageContentDAO.get_all_contents(enabled_only=False)
    if existing_contents:
        print(f"⚠ 检测到已有 {len(existing_contents)} 条内容数据")
        response = input("是否继续初始化？这将创建新的内容（y/n）: ")
        if response.lower() != 'y':
            print("已取消初始化")
            return
    
    # 插入数据
    success_count = 0
    for content in default_contents:
        content_id = HomepageContentDAO.create_content(
            title=content["title"],
            tags=content["tags"],
            description=content["description"],
            image_base64=content["image_base64"],
            sort_order=content["sort_order"]
        )
        
        if content_id:
            print(f"✓ 创建内容成功: {content['title']} (ID: {content_id})")
            success_count += 1
        else:
            print(f"✗ 创建内容失败: {content['title']}")
    
    print(f"\n初始化完成！成功创建 {success_count}/{len(default_contents)} 条内容")
    
    if success_count < len(default_contents):
        print("⚠ 部分内容创建失败，请检查日志")
    
    # 注意：图片Base64编码需要实际提供
    if any(not content["image_base64"] for content in default_contents):
        print("\n⚠ 注意：部分内容的图片Base64编码为空，请通过管理接口更新图片")


if __name__ == "__main__":
    try:
        init_homepage_contents()
    except Exception as e:
        print(f"初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
