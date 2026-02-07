#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量润色 rizhu_liujiazi 表 analysis 中的【深度解读】段落：
- 命理术语 → 小白可读表述
- 单条净增 50～70 字
输出：rizhu_shendu_polished_update.sql
"""
import re
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SQL_FILE = os.path.join(PROJECT_ROOT, 'scripts', 'migration', 'rizhu_update_production.sql')
OUT_SQL = os.path.join(PROJECT_ROOT, 'scripts', 'migration', 'rizhu_shendu_polished_update.sql')

# 术语 → 小白话（按长度从长到短替换，避免子串误替换）
REPLACEMENTS = [
    ("干支相生之贵格", "日干与日支五行相生，属于命理中较有利的一种组合"),
    ("坐财库之象", "日支为“财库”，象征善于积累与守成"),
    ("木火通明之象", "木生火、火得木助，属于“木火通明”的有利组合"),
    ("木火相生之象", "木生火、火得木助，属于较有利的组合"),
    ("金水相生之智格", "金生水、水得金助，属于智慧与灵活兼具的组合"),
    ("金水相生之象", "金生水、水得金助，属于较有利的组合"),
    ("水火既济之象", "水与火既济，象征平衡与成事之象"),
    ("水火既济", "水与火既济，象征平衡与成事"),
    ("土金相生之象", "土生金、金得土助，属于较有利的组合"),
    ("火土相生之象", "火生土、土得火助，属于较有利的组合"),
    ("火土相生", "火生土、土得火助"),
    ("木水相生之慈航格", "木水相生，即智慧与仁德相辅相成"),
    ("官印相生", "官与印相生，利于名誉与自律"),
    ("财官双美", "财与官俱佳，易得名得利"),
    ("土重木抑", "土多会压抑木气"),
    ("水旺木浮", "水旺则木易浮"),
    ("火旺金熔", "火旺则金易熔"),
    ("木多火塞", "木多则火易塞"),
    ("甲木得子水贴身滋养", "日干得日支相生滋养，好比身边常有精神支持与贵人缘"),
    ("乙木得子水贴身滋养", "日干得日支相生滋养，好比身边常有精神支持与贵人缘"),
    ("丙火得寅木长生之地", "丙火得寅木长生之地，能量有源"),
    ("丁火得卯木相生", "日干得日支相生，能量有源"),
    ("子午冲象", "子午相冲，与“午”相关年份易有变动，可提前留意"),
    ("子午相冲", "子午相冲，与“午”相关年份易有变动"),
    ("寅申冲", "寅申相冲，与“申”相关年份易有变动"),
    ("卯酉冲", "卯酉相冲，与“酉”相关年份易有变动"),
    ("辰戌冲", "辰戌相冲，相关年份易有变动"),
    ("巳亥冲", "巳亥相冲，相关年份易有变动"),
    ("木克土为财", "木克土在命理中代表“财”"),
    ("火克金为财", "火克金在命理中代表“财”"),
    ("土克水为财", "土克水在命理中代表“财”"),
    ("金克木为财", "金克木在命理中代表“财”"),
    ("水克火为财", "水克火在命理中代表“财”"),
    ("木水相生", "木水相生，即智慧与仁德相辅相成"),
    ("金水相生", "金水相生，即智慧与灵活相辅相成"),
    ("火土相生", "火生土、土得火助"),
    ("木火相生", "木生火、火得木助"),
    ("土金相生", "土生金、金得土助"),
    ("之贵格", "，属于命理中较有利的一种组合"),
    ("之象。", "之象。"),
    ("意味着内在有强大的精神支持与贵人缘分", "好比身边常有精神支持与贵人缘"),
    ("然水旺木浮，", "然水旺则木易浮，"),
    ("寅为驿马，多动少静，宜向外发展。", "寅为驿马，多动少静，宜向外发展、多走动更利发挥。"),
    ("丑为金库，与金属、金融有缘。", "丑为金库，与金属、金融有缘。"),
    ("巳为火库", "巳为火库"),
    ("午为火旺", "午为火旺"),
    ("亥为水库", "亥为水库"),
    ("辰戌丑未为四库", "辰戌丑未为四库，与积累、收藏有关"),
]

# 能量解析末尾可加的短句（约 15～25 字），用于补足 50～70 字
# 已确认的 3 条润色全文（与 rizhu_shendu_polish_samples.md 一致）
CONFIRMED_SHENDU = {
    "甲子": """【深度解读】
基础性格： 甲子日柱，日干与日支五行相生，属于命理中较有利的一种组合。甲木如参天大树，子水为智慧深泉。命主通常正直仁厚，富有同情心与学习能力。为人聪慧清雅，有上进心，但内心标准较高，易有完美主义倾向，不喜苟且。
内在特质： 日干得日支相生滋养，好比身边常有精神支持与贵人缘。家庭、长辈或内在信念常能给予其力量。然水旺则木易浮，有时思虑过深，行动力稍显不足，需防范依赖心与优柔寡断的一面。
能量解析： 木水相生，即智慧与仁德相辅相成；子午相冲，与"午"相关的年份易有变动，可提前留意。""",
    "乙丑": """【深度解读】
基础性格： 乙丑日柱，日支为"财库"，象征善于积累与守成。乙木如藤萝花草，丑土为湿土金库。命主通常外柔内刚，心思细腻，务实节俭。为人稳重，有责任感，但有时固执己见，容易因小事钻牛角尖。
内在特质： 乙木生于丑月寒冬，看似柔弱实则坚韧。内在有强烈的物质安全感和积累欲望，懂得未雨绸缪。土多会压抑木气，有时会压抑真实情感，显得沉闷或过于谨慎。
能量解析： 木克土在命理中代表"财"，理财能力佳；丑为金库，与金属、金融有缘。""",
    "丙寅": """【深度解读】
基础性格： 丙寅日柱，木生火、火得木助，属于"木火通明"的有利组合。丙火如太阳，寅木为参天大树。命主通常热情开朗，积极进取，有领导才能。为人光明磊落，慷慨大方，但有时急躁冲动，好面子，缺乏耐心。
内在特质： 丙火得寅木长生之地，能量源源不断。内在充满活力和创造力，天生具有感染他人的魅力。然火势过旺，需注意情绪管理，避免因一时热情而虎头蛇尾。
能量解析： 木生火旺，才华易显；寅为驿马，多动少静，宜向外发展、多走动更利发挥。""",
}

ENERGY_SUFFIX_OPTIONS = [
    "可多留意流年与自身状态。",
    "宜顺势而为，不必强求。",
    "关键年份可提前规划。",
]


def decode_hex(s: str) -> str:
    return bytes.fromhex(s).decode("utf-8")


def encode_hex(s: str) -> str:
    return s.encode("utf-8").hex().upper()


def extract_shendu(analysis: str) -> str:
    start = analysis.find("【深度解读】")
    end = analysis.find("【断语展示】")
    if start == -1:
        return ""
    if end == -1:
        return analysis[start:]
    return analysis[start:end].strip()


def polish_shendu(shendu: str, rizhu: str) -> str:
    """对【深度解读】段落做术语替换与小幅拓展，净增约 50～70 字。"""
    if rizhu in CONFIRMED_SHENDU:
        return CONFIRMED_SHENDU[rizhu]
    text = shendu
    for old, new in REPLACEMENTS:
        if old in text:
            text = text.replace(old, new, 1)
    # 若“能量解析”末句以句号结尾且无拓展，可补一句（控制总增 50～70 字）
    if "能量解析：" in text and not any(s in text for s in ENERGY_SUFFIX_OPTIONS):
        last_line = text.split("能量解析：")[-1].strip()
        if last_line.endswith("。") and len(last_line) < 80:
            add = ENERGY_SUFFIX_OPTIONS[0]
            text = text.rstrip()
            if not text.endswith("。"):
                text += "。"
            text += add
    return text


def replace_shendu_in_analysis(analysis: str, new_shendu: str) -> str:
    start = analysis.find("【深度解读】")
    end = analysis.find("【断语展示】")
    if start == -1 or end == -1:
        return analysis
    return analysis[:start] + new_shendu + "\n" + analysis[end:]


def main():
    if not os.path.exists(SQL_FILE):
        print(f"File not found: {SQL_FILE}")
        return
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r"UPDATE rizhu_liujiazi SET analysis=UNHEX\('([A-F0-9]+)'\) WHERE BINARY rizhu=UNHEX\('([A-F0-9]+)'\)"
    matches = list(re.finditer(pattern, content))
    if len(matches) != 60:
        print(f"Warning: expected 60 rows, got {len(matches)}")
    out_lines = [
        "-- 批量润色【深度解读】后生成的 UPDATE（术语→小白话，单条净增约50～70字）",
        f"-- 记录数: {len(matches)}",
        "",
    ]
    for m in matches:
        hex_analysis = m.group(1)
        hex_rizhu = m.group(2)
        rizhu = decode_hex(hex_rizhu)
        full = decode_hex(hex_analysis)
        shendu = extract_shendu(full)
        if not shendu:
            out_lines.append(f"-- skip {rizhu}: no 深度解读")
            new_full = full
        else:
            new_shendu = polish_shendu(shendu, rizhu)
            new_full = replace_shendu_in_analysis(full, new_shendu)
        new_hex = encode_hex(new_full)
        out_lines.append(f"UPDATE rizhu_liujiazi SET analysis=UNHEX('{new_hex}') WHERE BINARY rizhu=UNHEX('{hex_rizhu}');")
    os.makedirs(os.path.dirname(OUT_SQL), exist_ok=True)
    with open(OUT_SQL, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))
    print(f"Done. Wrote {len(matches)} UPDATEs to {OUT_SQL}")


if __name__ == "__main__":
    main()
