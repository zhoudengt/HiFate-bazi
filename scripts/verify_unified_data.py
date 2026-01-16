#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据验证脚本

验证 UnifiedBaziDataProvider 的数据与排盘接口完全一致

用法：
    python3 scripts/verify_unified_data.py
    
    # 指定测试用例
    python3 scripts/verify_unified_data.py --date 1985-11-21 --time 06:30 --gender female
"""

import sys
import os
import asyncio
import argparse
import logging

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.services.unified_bazi_data_provider import UnifiedBaziDataProvider, DataInconsistencyError
from server.services.bazi_display_service import BaziDisplayService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 测试用例（用户提供的关键测试数据）
TEST_CASES = [
    {
        "name": "用户测试用例1",
        "solar_date": "1985-11-21",
        "solar_time": "06:30",
        "gender": "female",
        "expected_special_years": [1990, 2009, 2013, 2022, 2038, 2058, 2069, 2073, 2076],
        "expected_relations": {
            1990: ["岁运并临"],
            2009: ["岁运并临", "日柱天合地合"],
            2013: ["月柱天克地冲"],
            2022: ["月柱天合地合"],
            2038: ["日柱天克地冲"],
            2058: ["日柱天克地冲"],
            2069: ["日柱天合地合"],
            2073: ["月柱天克地冲"],
            2076: ["岁运并临"]
        }
    }
]


async def verify_single_case(
    solar_date: str,
    solar_time: str,
    gender: str,
    expected_special_years: list = None,
    expected_relations: dict = None
) -> bool:
    """
    验证单个测试用例
    
    Returns:
        bool: 验证是否通过
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"验证: {solar_date} {solar_time} {gender}")
    logger.info(f"{'='*60}")
    
    all_passed = True
    
    try:
        # 1. 获取统一数据
        logger.info("1. 获取统一数据...")
        unified_data = await UnifiedBaziDataProvider.get_unified_data(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender
        )
        logger.info(f"   ✅ 统一数据获取成功")
        
        # 2. 获取排盘数据（基准）
        logger.info("2. 获取排盘数据（基准）...")
        display_result = BaziDisplayService.get_fortune_display(
            solar_date=solar_date,
            solar_time=solar_time,
            gender=gender,
            quick_mode=False
        )
        logger.info(f"   ✅ 排盘数据获取成功")
        
        # 3. 验证四柱
        logger.info("3. 验证四柱...")
        pillars_raw = display_result.get('pillars', {})
        
        for pillar_type in ['year', 'month', 'day', 'hour']:
            display_pillar = pillars_raw.get(pillar_type, {})
            unified_pillar = getattr(unified_data.bazi_pillars, pillar_type, {})
            
            display_stem = display_pillar.get('stem', '')
            unified_stem = unified_pillar.get('stem', '')
            
            if display_stem != unified_stem:
                logger.error(f"   ❌ {pillar_type}柱天干不一致: 排盘={display_stem}, 统一={unified_stem}")
                all_passed = False
            else:
                logger.info(f"   ✅ {pillar_type}柱天干一致: {display_stem}")
        
        # 4. 验证大运数量
        logger.info("4. 验证大运序列...")
        display_dayun_list = display_result.get('dayun', {}).get('list', [])
        unified_dayun_count = len(unified_data.dayun_sequence)
        
        if len(display_dayun_list) != unified_dayun_count:
            logger.error(f"   ❌ 大运数量不一致: 排盘={len(display_dayun_list)}, 统一={unified_dayun_count}")
            all_passed = False
        else:
            logger.info(f"   ✅ 大运数量一致: {unified_dayun_count}个")
        
        # 5. 验证特殊年份（关键！）
        logger.info("5. 验证特殊年份（关键）...")
        
        # 从排盘提取特殊年份
        display_liunian_list = display_result.get('liunian', {}).get('list', [])
        display_special = [
            ln for ln in display_liunian_list 
            if ln.get('relations') and len(ln.get('relations', [])) > 0
        ]
        display_special_years = [ln['year'] for ln in display_special]
        
        # 从统一数据提取特殊年份
        unified_special_years = [sl.year for sl in unified_data.special_liunians]
        
        logger.info(f"   排盘特殊年份: {sorted(display_special_years)}")
        logger.info(f"   统一特殊年份: {sorted(unified_special_years)}")
        
        if set(display_special_years) != set(unified_special_years):
            logger.error(f"   ❌ 特殊年份不一致!")
            all_passed = False
        else:
            logger.info(f"   ✅ 特殊年份数量一致: {len(unified_special_years)}个")
        
        # 6. 验证每个特殊年份的 relations
        logger.info("6. 验证特殊年份的 relations...")
        display_relations_map = {
            ln['year']: ln.get('relations', [])
            for ln in display_special
        }
        
        for sl in unified_data.special_liunians:
            display_relations = display_relations_map.get(sl.year, [])
            
            # 比较 relations
            if sl.relations != display_relations:
                logger.error(f"   ❌ {sl.year}年 relations 不一致:")
                logger.error(f"      排盘: {display_relations}")
                logger.error(f"      统一: {sl.relations}")
                all_passed = False
            else:
                # 提取 relations 类型用于显示
                relation_types = []
                for r in sl.relations:
                    if isinstance(r, dict):
                        relation_types.append(r.get('type', str(r)))
                    else:
                        relation_types.append(str(r))
                logger.info(f"   ✅ {sl.year}年 relations 一致: {relation_types}")
        
        # 7. 与预期数据比对（如果提供）
        if expected_special_years:
            logger.info("7. 与预期数据比对...")
            
            if set(unified_special_years) != set(expected_special_years):
                logger.error(f"   ❌ 与预期特殊年份不一致!")
                logger.error(f"      预期: {sorted(expected_special_years)}")
                logger.error(f"      实际: {sorted(unified_special_years)}")
                
                # 找出差异
                missing = set(expected_special_years) - set(unified_special_years)
                extra = set(unified_special_years) - set(expected_special_years)
                if missing:
                    logger.error(f"      缺少: {sorted(missing)}")
                if extra:
                    logger.error(f"      多余: {sorted(extra)}")
                
                all_passed = False
            else:
                logger.info(f"   ✅ 与预期特殊年份一致")
        
        # 8. 验证旺衰数据
        logger.info("8. 验证旺衰数据...")
        logger.info(f"   旺衰: {unified_data.wangshuai.wangshuai}")
        logger.info(f"   喜神五行: {unified_data.wangshuai.xi_shen_elements}")
        logger.info(f"   忌神五行: {unified_data.wangshuai.ji_shen_elements}")
        
        if not unified_data.wangshuai.wangshuai:
            logger.warning(f"   ⚠️ 旺衰数据为空")
        if not unified_data.wangshuai.xi_shen_elements:
            logger.warning(f"   ⚠️ 喜神五行为空")
        if not unified_data.wangshuai.ji_shen_elements:
            logger.warning(f"   ⚠️ 忌神五行为空")
        
    except DataInconsistencyError as e:
        logger.error(f"❌ 数据一致性验证失败: {e}")
        all_passed = False
    except Exception as e:
        logger.error(f"❌ 验证过程出错: {e}", exc_info=True)
        all_passed = False
    
    # 总结
    logger.info(f"\n{'='*60}")
    if all_passed:
        logger.info(f"✅ 验证通过: {solar_date} {solar_time} {gender}")
    else:
        logger.error(f"❌ 验证失败: {solar_date} {solar_time} {gender}")
    logger.info(f"{'='*60}\n")
    
    return all_passed


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='验证统一数据与排盘一致性')
    parser.add_argument('--date', type=str, help='阳历日期 (如 1985-11-21)')
    parser.add_argument('--time', type=str, help='出生时间 (如 06:30)')
    parser.add_argument('--gender', type=str, choices=['male', 'female'], help='性别')
    parser.add_argument('--all', action='store_true', help='运行所有测试用例')
    
    args = parser.parse_args()
    
    all_passed = True
    
    if args.date and args.time and args.gender:
        # 运行指定的测试用例
        passed = await verify_single_case(
            solar_date=args.date,
            solar_time=args.time,
            gender=args.gender
        )
        all_passed = passed
    elif args.all or (not args.date and not args.time and not args.gender):
        # 运行所有预定义的测试用例
        logger.info(f"运行 {len(TEST_CASES)} 个测试用例...\n")
        
        for i, case in enumerate(TEST_CASES, 1):
            logger.info(f"[{i}/{len(TEST_CASES)}] {case['name']}")
            passed = await verify_single_case(
                solar_date=case['solar_date'],
                solar_time=case['solar_time'],
                gender=case['gender'],
                expected_special_years=case.get('expected_special_years'),
                expected_relations=case.get('expected_relations')
            )
            if not passed:
                all_passed = False
    else:
        parser.print_help()
        return
    
    # 最终结果
    print("\n" + "="*60)
    if all_passed:
        print("✅ 所有验证通过！统一数据与排盘完全一致。")
    else:
        print("❌ 验证失败！存在数据不一致问题。")
    print("="*60)
    
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    asyncio.run(main())
