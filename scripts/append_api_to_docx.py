#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""追加六爻和办公桌风水接口到 66666.docx"""

import os
import sys

# 确保用 python3.13（有 docx）
if sys.version_info < (3, 10):
    py313 = os.path.join(os.path.dirname(__file__), '..', '.venv', 'bin', 'python3.13')
    if os.path.exists(py313):
        os.execv(py313, [py313] + sys.argv)

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

DOC_PATH = "/Users/zhoudt/Desktop/公司/other/66666.docx"

LIUYAO_DIVINATE = """
接口详情6.
/api/v1/liuyao/divinate
(六爻起卦-仅卦象)

接口路径
/api/v1/liuyao/divinate

接口别名
六爻起卦（仅卦象）

请求方法
POST

接口描述
根据占卜问题与起卦方式（铜钱/数字/时间）计算卦象，仅返回卦象数据，不调用大模型。

请求参数
字段名	类型	必填	描述	示例
question	str	是	占卜问题	这次投资能成功吗？
method	str	是	起卦方式：coin(铜钱)/number(数字)/time(时间)	coin
coin_results	list[int]	method=coin 时必填	6 个数字，每项 2/3/6/9	[2,3,6,3,2,9]
number	list[int]	method=number 时必填	3 个数字	[12,34,56]
divination_time	str	method=time 时必填	占卜时间，格式 YYYY-MM-DD HH:mm	2025-03-06 14:30

响应格式
字段名	类型	描述
success	bool	是否成功
data	object	卦象数据
data.question	str	占卜问题
data.method	str	起卦方式
data.ben_gua	object	本卦
data.ben_gua.name	str	卦名
data.ben_gua.lines	list	六爻列表（含 position、yin_yang、yao_ci、liu_qin、liu_shen、is_dong）
data.bian_gua	object	变卦
data.gua_ci	str	卦辞
data.shi_ying	object	世应，含 shi_yao、ying_yao
"""

LIUYAO_STREAM = """
==================================================================
接口详情7.
/api/v1/liuyao/stream
(六爻占卜-流式解读)

接口路径
/api/v1/liuyao/stream

接口别名
六爻占卜流式解读

请求方法
POST

接口描述
根据占卜问题与起卦方式计算卦象，先返回完整卦象数据，再流式返回大模型解读。使用 Server-Sent Events (SSE) 格式。

备注
流式接口，响应格式为 text/event-stream。先返回 type: data（完整卦象），再流式返回 type: progress（AI 解读片段），最后 type: complete。

请求参数
字段名	类型	必填	描述	示例
question	str	是	占卜问题	这次投资能成功吗？
method	str	是	起卦方式：coin/number/time	coin
coin_results	list[int]	method=coin 时必填	6 个 2/3/6/9	[2,3,6,3,2,9]
number	list[int]	method=number 时必填	3 个数字	[12,34,56]
divination_time	str	method=time 时必填	YYYY-MM-DD HH:mm	2025-03-06 14:30
bot_id	str	否	Bot ID（可选）

响应说明
本接口使用 SSE 格式，响应类型为 text/event-stream。

响应格式
字段名	类型	描述
type: data	object	完整卦象数据（首条）
type: data.content.success	bool	是否成功
type: data.content.data	object	卦象结构同 /liuyao/divinate
type: progress	object	流式 AI 解读片段
type: progress.content	str	增量文本
type: complete	object	完成信号
type: complete.content	str	完整解读内容（可选）
type: error	object	错误信息
type: error.content	str	错误描述
"""

DESK_FENGSHUI_STREAM = """
==================================================================
接口详情8.
/api/v2/desk-fengshui/analyze/stream
(办公桌风水分析-流式)

接口路径
/api/v2/desk-fengshui/analyze/stream

接口别名
办公桌风水分析-流式

请求方法
POST

接口描述
上传办公桌照片，先返回基础风水分析数据（物品识别、规则匹配等），再流式返回大模型整合分析结果。使用 Server-Sent Events (SSE) 格式。

备注
流式接口，multipart/form-data 上传图片。先返回 type: request_id，再 type: data（基础分析），再 type: progress（AI 解读），最后 type: complete。

请求参数
字段名	类型	必填	描述	示例
image	File(multipart/form-data)	是	办公桌照片，支持 JPG、PNG	desk.jpg
bot_id	str	否	Bot ID（可选）

响应说明
本接口使用 SSE 格式，响应类型为 text/event-stream。

响应格式
字段名	类型	描述
type: request_id	object	首条事件，含 request_id
type: data	object	基础风水分析数据
type: data.content	object	分析结果（vision_items、rules、scene_info 等）
type: progress	object	流式 AI 整合分析片段
type: progress.content	str	增量文本
type: complete	object	完成信号
type: complete.content	str	完整分析内容（可选）
type: error	object	错误信息
"""


def main():
    doc = Document(DOC_PATH)
    # 追加三个接口，按文档既有格式用段落
    for block in [LIUYAO_DIVINATE, LIUYAO_STREAM, DESK_FENGSHUI_STREAM]:
        for line in block.strip().split("\n"):
            p = doc.add_paragraph(line.strip())
            p.paragraph_format.space_after = Pt(0)
    doc.save(DOC_PATH)
    print(f"已追加六爻与办公桌风水接口到 {DOC_PATH}")


if __name__ == "__main__":
    main()
