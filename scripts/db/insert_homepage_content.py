#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插入首页内容到数据库（包含图片）

使用方法:
    python scripts/db/insert_homepage_content.py --title "AI守护神" --image path/to/image.jpg --description "描述" --tags "科技,精准" --sort 1
"""

import sys
import os
import argparse
import base64

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.db.homepage_content_dao import HomepageContentDAO


def image_to_base64(image_path):
    """将图片文件转换为Base64编码"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    
    # 判断图片类型
    ext = os.path.splitext(image_path)[1].lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    mime_type = mime_types.get(ext, 'image/jpeg')
    
    # 读取图片并转换为Base64
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # 返回完整的Base64字符串（包含前缀）
    return f"data:{mime_type};base64,{image_data}"


def main():
    parser = argparse.ArgumentParser(description='插入首页内容到数据库')
    parser.add_argument('--title', required=True, help='标题')
    parser.add_argument('--image', required=True, help='图片文件路径')
    parser.add_argument('--description', required=True, help='详细描述')
    parser.add_argument('--tags', default='', help='标签，用逗号分隔，如：科技,精准')
    parser.add_argument('--sort', type=int, default=0, help='排序值（默认0）')
    
    args = parser.parse_args()
    
    try:
        # 转换图片
        print(f"正在读取图片: {args.image}")
        image_base64 = image_to_base64(args.image)
        image_size = len(image_base64)
        print(f"✅ 图片转换成功，Base64大小: {image_size:,} 字符 ({image_size/1024:.1f} KB)")
        
        # 解析标签
        tags = [tag.strip() for tag in args.tags.split(',') if tag.strip()] if args.tags else []
        
        # 插入数据库
        print(f"\n正在插入数据库...")
        print(f"  标题: {args.title}")
        print(f"  标签: {tags}")
        print(f"  排序: {args.sort}")
        
        content_id = HomepageContentDAO.create_content(
            title=args.title,
            tags=tags,
            description=args.description,
            image_base64=image_base64,
            sort_order=args.sort
        )
        
        if content_id:
            print(f"\n✅ 插入成功！内容ID: {content_id}")
            return 0
        else:
            print("\n❌ 插入失败")
            return 1
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
