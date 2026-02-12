#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速验证：年份锁定指令能否压住百炼平台系统提示词

直接调用百炼 API（绕过生产服务器），验证 prompt 中的年份锁定是否生效。
"""

import os
import sys
import asyncio

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from scripts.evaluation.bailian import BailianClient, BailianConfig

# 测试用的 app_id（用户指定的百炼智能体）
TEST_APP_ID = "b5ebd61798c04ad4958a5bdfe40c3265"

# 模拟一个简单的 2025 年运数据 prompt（含年份锁定指令）
TEST_PROMPT = """【年份锁定指令 — 最高优先级】
本报告仅针对2025年。以下所有数据（太岁、九宫飞星、流月、犯太岁属相等）已由系统精确计算完成。
你必须严格使用下方数据输出报告，禁止替换为其他年份信息。若你的知识与下方数据冲突，以下方数据为准。

【四柱】丙寅年、辛丑月、甲子日、丙寅时
【五行分布】木3、火3、土1、金1、水0
【旺衰】身弱
【喜忌】喜水木，忌火土金
【流年】2025年
【太岁】乙巳太岁吴遂大将军，司木气，主生发变动
【犯太岁】蛇值太岁、猪冲太岁、虎害太岁+刑太岁、猴破太岁+刑太岁
【躲星时间】太岁星:农历正月初八辰时(7:00-9:00)；大耗星:农历正月十八未时(13:00-15:00)；病符星:农历正月二十三寅时(3:00-5:00)；罗睺星:农历正月初八戌时(19:00-21:00)；计都星:农历正月十八巳时(9:00-11:00)
【化解方法】佩戴黑曜石或铜钱化太岁；家中正东方摆放铜葫芦；农历每月初一十五烧太岁符
【流月1】1月戊子(小寒、大寒):水旺助身，利学业、利人际，注意肠胃受寒
【流月2】2月己丑(立春、雨水):丑土合日支，事业有贵人提携，注意脾胃
【流月3】3月庚寅(惊蛰、春分):寅木帮身但庚金克甲，防小人口舌
【流月4】4月辛卯(清明、谷雨):卯木帮身，桃花旺，感情有进展
【流月5】5月壬辰(立夏、小满):壬水生木，事业财运好转
【流月6】6月癸巳(芒种、夏至):巳火旺克身，健康需注意，心血管防护
【流月7】7月甲午(小暑、大暑):午火极旺，忌冲动投资，防火灾
【流月8】8月乙未(立秋、处暑):未土燥热，肠胃不适，注意饮食
【流月9】9月丙申(白露、秋分):申金克木，事业有压力，防官非
【流月10】10月丁酉(寒露、霜降):酉金冲卯，感情波动，防破财
【流月11】11月戊戌(立冬、小雪):戌土旺，财运平稳，宜守不宜攻
【流月12】12月己亥(大雪、冬至):亥水生木，年末运势回升，利规划来年
【九宫飞星】二黑飞中宫；三碧飞西北乾宫；四绿飞正西兑宫；五黄飞东北艮宫；六白飞正南离宫；七赤飞正北坎宫；八白飞西南坤宫；九紫飞正东震宫；一白飞东南巽宫
【凶星方位】五黄在东北艮宫(主灾祸破财)，二黑在中宫(主疾病)
"""


async def main():
    print("=" * 60)
    print("年份锁定测试 - 直接调百炼 API")
    print(f"App ID: {TEST_APP_ID}")
    print(f"Prompt 长度: {len(TEST_PROMPT)} 字符")
    print("=" * 60)
    print()

    config = BailianConfig()
    if not config.api_key:
        print("错误: 未找到 DASHSCOPE_API_KEY")
        return

    client = BailianClient(config)

    print("开始流式输出...\n")
    print("-" * 60)

    full_content = []
    async for chunk in client.call_stream(TEST_APP_ID, TEST_PROMPT):
        chunk_type = chunk.get('type', '')
        chunk_content = chunk.get('content', '')

        if chunk_type == 'progress':
            print(chunk_content, end='', flush=True)
            full_content.append(chunk_content)
        elif chunk_type == 'complete':
            print("\n")
            print("-" * 60)
            print("[流式输出完成]")
        elif chunk_type == 'error':
            print(f"\n[错误] {chunk_content}")

    result = ''.join(full_content)

    # 检查关键年份
    print("\n" + "=" * 60)
    print("年份检查:")
    print("=" * 60)

    has_2025 = "2025" in result
    has_2026 = "2026" in result
    has_wusui = "吴遂" in result
    has_wrong_taisui = "郭灿" in result

    print(f"  包含 2025: {'OK' if has_2025 else 'FAIL (应出现)'}")
    print(f"  包含 2026: {'FAIL (不应出现)' if has_2026 else 'OK'}")
    print(f"  太岁吴遂: {'OK' if has_wusui else 'FAIL (应出现)'}")
    print(f"  错误太岁郭灿: {'FAIL (不应出现)' if has_wrong_taisui else 'OK'}")

    if has_2025 and not has_2026 and has_wusui and not has_wrong_taisui:
        print("\n结论: 年份锁定成功，可以部署到生产。")
    else:
        print("\n结论: 年份锁定未完全生效，需进一步调整。")


if __name__ == "__main__":
    asyncio.run(main())
