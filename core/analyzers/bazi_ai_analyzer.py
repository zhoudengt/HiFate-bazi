#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字AI分析器 - 基于 Coze API
将八字计算结果传递给 Coze 服务进行分析
支持用户在 Coze 平台可视化配置服务
"""

import sys
import os
import json
import requests
from typing import Dict, Any, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class BaziAIAnalyzer:
    """八字AI分析器 - 基于 Coze API"""
    
    def __init__(self, access_token: Optional[str] = None, bot_id: Optional[str] = None,
                 api_base: str = "https://api.coze.cn"):
        """
        初始化Coze AI分析器
        
        Args:
            access_token: Coze Access Token，如果为None则从环境变量获取
            bot_id: Coze Bot ID，如果为None则从环境变量获取
            api_base: Coze API 基础URL，默认为 https://api.coze.cn（不包含版本号）
        """
        self.access_token = access_token or os.getenv("COZE_ACCESS_TOKEN")
        self.bot_id = bot_id or os.getenv("COZE_BOT_ID")
        self.api_base = api_base.rstrip('/')
        
        if not self.access_token:
            raise ValueError("需要提供 Coze Access Token 或设置环境变量 COZE_ACCESS_TOKEN")
        
        if not self.bot_id:
            raise ValueError("需要提供 Coze Bot ID 或设置环境变量 COZE_BOT_ID")
        
        # 设置请求头
        # Coze API 可能使用不同的认证方式
        # 尝试多种可能的认证格式
        if self.access_token.startswith("pat_"):
            # 如果 token 以 pat_ 开头，可能需要不同的格式
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        else:
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        
        # 也准备一个使用 PAT 前缀的认证头（某些 API 可能需要）
        self.headers_pat = {
            "Authorization": f"PAT {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _prepare_bazi_data(self, bazi_data: Dict[str, Any]) -> str:
        """
        准备八字数据，格式化为文本供AI分析
        
        Args:
            bazi_data: 八字接口返回的数据
            
        Returns:
            str: 格式化后的八字文本信息
        """
        lines = []
        
        # 基本信息
        basic_info = bazi_data.get('basic_info', {})
        lines.append("【基本信息】")
        lines.append(f"出生日期: {basic_info.get('solar_date', '')} {basic_info.get('solar_time', '')}")
        lines.append(f"性别: {'男' if basic_info.get('gender') == 'male' else '女'}")
        
        lunar_date = basic_info.get('lunar_date', {})
        if isinstance(lunar_date, dict):
            lines.append(f"农历: {lunar_date.get('year', '')}年{lunar_date.get('month_name', '')}{lunar_date.get('day_name', '')}")
        lines.append("")
        
        # 四柱信息
        bazi_pillars = bazi_data.get('bazi_pillars', {})
        lines.append("【四柱八字】")
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar = bazi_pillars.get(pillar_type, {})
            pillar_name = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}.get(pillar_type, pillar_type)
            lines.append(f"{pillar_name}: {pillar.get('stem', '')}{pillar.get('branch', '')}")
        lines.append("")
        
        # 日柱信息（用于分析）
        day_pillar = bazi_pillars.get('day', {})
        day_stem = day_pillar.get('stem', '')
        day_branch = day_pillar.get('branch', '')
        rizhu = f"{day_stem}{day_branch}"
        
        # 获取日柱性别分析结果
        from core.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
        analyzer = RizhuGenderAnalyzer(bazi_pillars, basic_info.get('gender', 'male'))
        rizhu_analysis = analyzer.analyze_rizhu_gender()
        
        lines.append("【日柱性别分析】")
        lines.append(f"日柱: {rizhu}")
        lines.append(f"性别: {'男' if basic_info.get('gender') == 'male' else '女'}")
        if rizhu_analysis.get('has_data'):
            lines.append("分析结果:")
            for desc in rizhu_analysis.get('descriptions', []):
                lines.append(f"  - {desc}")
        lines.append("")
        
        # 详细四柱信息
        details = bazi_data.get('details', {})
        if details:
            lines.append("【详细四柱信息】")
            for pillar_type in ['year', 'month', 'day', 'hour']:
                pillar_details = details.get(pillar_type, {})
                pillar_name = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}.get(pillar_type, pillar_type)
                lines.append(f"{pillar_name}:")
                lines.append(f"  主星: {pillar_details.get('main_star', '')}")
                lines.append(f"  纳音: {pillar_details.get('nayin', '')}")
                lines.append(f"  空亡: {pillar_details.get('kongwang', '')}")
                if pillar_details.get('deities'):
                    lines.append(f"  神煞: {', '.join(pillar_details.get('deities', []))}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _call_coze_api(self, user_message: str, bazi_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 Coze API
        
        Args:
            user_message: 用户消息内容
            bazi_data: 八字数据
            
        Returns:
            dict: 包含AI分析结果
        """
        try:
            # Coze API 调用方式
            # 根据 Coze 官方文档，正确的端点路径应该是 /open_api/v2/chat
            # 如果 api_base 已经包含 /v1，需要调整
            if "/v1" in self.api_base:
                # 如果 api_base 是 https://api.coze.cn/v1，需要改为 https://api.coze.cn
                self.api_base = self.api_base.replace("/v1", "").rstrip('/')
            
            # 尝试多个可能的端点路径
            # 根据 Coze API 文档，正确的端点应该是 /open_api/v2/chat
            possible_paths = [
                "/open_api/v2/chat",  # Coze v2 格式（最可能正确）
                "/open_api/v2/chat/completions",  # 类似 OpenAI 格式
                "/v2/chat",  # 简化 v2 格式
                "/open_api/v1/chat",  # Coze v1 格式
                "/api/v1/chat",  # API v1 格式
                "/v1/chat",  # 简化格式
                "/chat",  # 最简格式
            ]
            
            url = None
            last_error = None
            
            # 直接尝试使用实际消息，而不是测试请求
            for path in possible_paths:
                test_url = f"{self.api_base}{path}"
                print(f"🔍 尝试端点: {test_url}")
                
                # 使用第一个请求格式进行尝试
                # 尝试最简格式，只包含必需字段
                test_payload = {
                    "bot_id": str(self.bot_id),
                    "query": user_message
                }
                
                try:
                    # 打印调试信息
                    print(f"📤 发送请求体: {json.dumps(test_payload, ensure_ascii=False, indent=2)[:500]}")
                    # 尝试两种认证方式
                    for headers_to_use, header_name in [(self.headers, "Bearer"), (self.headers_pat, "PAT")]:
                        try:
                            test_response = requests.post(test_url, headers=headers_to_use, json=test_payload, timeout=60)
                            if test_response.status_code in [200, 400]:  # 400 也可能表示端点存在但格式不对
                                break
                        except:
                            continue
                    else:
                        # 如果两种认证方式都失败，使用默认的
                        test_response = requests.post(test_url, headers=self.headers, json=test_payload, timeout=60)
                    
                    if test_response.status_code == 200:
                        # 检查响应内容，确认是否真的成功
                        try:
                            test_result = test_response.json()
                            # 检查是否包含错误信息
                            if "code" in test_result and test_result.get("code") != 0:
                                # 有错误码，不是真正的成功
                                error_msg = test_result.get("msg", str(test_result))
                                print(f"⚠ 端点返回200但包含错误: {error_msg[:200]}")
                                # 端点存在，但需要调整参数格式
                                url = test_url
                                last_error = f"端点 {path} 存在但参数格式需要调整: {error_msg[:200]}"
                                break
                            else:
                                # 真正的成功
                                url = test_url
                                result = test_result
                                print(f"✓ 找到可用端点: {url}")
                                break
                        except:
                            # 响应不是JSON，可能是文本，也认为是成功
                            url = test_url
                            result = {"content": test_response.text}
                            print(f"✓ 找到可用端点: {url}")
                            break
                    elif test_response.status_code == 404:
                        # 端点不存在，尝试下一个
                        try:
                            error_detail = test_response.json()
                            error_msg = json.dumps(error_detail, ensure_ascii=False)
                            print(f"✗ 端点不存在 (404): {error_msg[:200]}")
                        except:
                            print(f"✗ 端点不存在 (404): {path}")
                        last_error = f"端点 {path} 不存在 (404)"
                        continue
                    else:
                        # 其他错误，可能是参数问题，但端点存在
                        # 记录错误但继续尝试其他格式
                        try:
                            error_detail = test_response.json()
                            error_msg = json.dumps(error_detail, ensure_ascii=False)
                            print(f"⚠ 端点存在但参数错误 ({test_response.status_code}): {error_msg[:200]}")
                        except:
                            print(f"⚠ 端点存在但参数错误 ({test_response.status_code}): {path}")
                        # 端点存在，但需要调整参数格式
                        url = test_url
                        last_error = f"端点 {path} 存在但参数格式需要调整"
                        break
                except Exception as e:
                    print(f"✗ 端点调用异常: {path} - {str(e)}")
                    last_error = f"端点 {path} 调用异常: {str(e)}"
                    continue
            
            if not url:
                return {
                    "success": False,
                    "error": f"无法找到可用的 Coze API 端点。最后错误: {last_error}。请检查 Coze API 文档: https://www.coze.cn/docs/developer_guides/api_overview",
                    "analysis": None
                }
            
            # 如果端点已成功（200），直接处理结果
            if 'result' in locals() and url:
                # 端点已成功，直接处理结果
                pass
            else:
                # 端点存在但参数格式需要调整，尝试其他参数格式
                # 根据 Coze API 官方文档，正确的格式应该是：
                # {
                #   "conversation_id": "...",
                #   "bot_id": "...",
                #   "user": "...",
                #   "query": "...",
                #   "stream": false
                # }
                # 根据 Coze API 文档，尝试最可能的格式
                # 注意：可能需要先创建 conversation，或者 conversation_id 不能是空字符串
                payload_formats = [
                    # 格式1: 不包含 conversation_id（让 API 自动创建新会话）
                    {
                        "bot_id": str(self.bot_id),
                        "user": "bazi_user",
                        "query": user_message,
                        "stream": False
                    },
                    # 格式2: 包含 conversation_id 但使用 None（让 API 处理）
                    {
                        "bot_id": str(self.bot_id),
                        "user": "bazi_user",
                        "conversation_id": None,
                        "query": user_message,
                        "stream": False
                    },
                    # 格式3: 不包含 stream 字段
                    {
                        "bot_id": str(self.bot_id),
                        "user": "bazi_user",
                        "query": user_message
                    },
                    # 格式4: 最简格式（只有 bot_id 和 query）
                    {
                        "bot_id": str(self.bot_id),
                        "query": user_message
                    },
                    # 格式5: 使用 user_id（某些版本可能支持）
                    {
                        "bot_id": str(self.bot_id),
                        "user_id": "bazi_user",
                        "query": user_message,
                        "stream": False
                    },
                    # 格式6: 包含 conversation_id 为空字符串
                    {
                        "conversation_id": "",
                        "bot_id": str(self.bot_id),
                        "user": "bazi_user",
                        "query": user_message,
                        "stream": False
                    }
                ]
                
                found_format = False
                for i, payload in enumerate(payload_formats):
                    try:
                        print(f"🔍 尝试格式 {i+1}: {url}")
                        # 清理 payload，移除 None 值（某些 API 不接受 None）
                        clean_payload = {k: v for k, v in payload.items() if v is not None}
                        print(f"📤 请求体: {json.dumps(clean_payload, ensure_ascii=False, indent=2)[:500]}")
                        # 尝试两种认证方式
                        response = None
                        for headers_to_use in [self.headers, self.headers_pat]:
                            try:
                                response = requests.post(url, headers=headers_to_use, json=clean_payload, timeout=60)
                                if response.status_code in [200, 400]:  # 400 也可能表示端点存在但格式不对
                                    break
                            except:
                                continue
                        if response is None:
                            response = requests.post(url, headers=self.headers, json=clean_payload, timeout=60)
                        
                        if response.status_code == 200:
                            # 检查响应内容，确认是否真的成功
                            try:
                                response_data = response.json()
                                # 检查是否包含错误信息
                                if "code" in response_data and response_data.get("code") != 0:
                                    # 有错误码，不是真正的成功
                                    error_msg = response_data.get("msg", str(response_data))
                                    print(f"✗ 格式 {i+1} 返回错误: {error_msg[:200]}")
                                    last_error = f"格式{i+1}返回错误: {error_msg[:200]}"
                                    continue
                                else:
                                    # 真正的成功
                                    print(f"✓ 格式 {i+1} 成功")
                                    result = response_data
                                    found_format = True
                                    break
                            except:
                                # 响应不是JSON，可能是文本，也认为是成功
                                print(f"✓ 格式 {i+1} 成功（文本响应）")
                                result = {"content": response.text}
                                found_format = True
                                break
                        else:
                            # 其他错误，尝试下一个格式
                            try:
                                error_detail = response.json()
                                error_msg = json.dumps(error_detail, ensure_ascii=False)
                                print(f"✗ 格式 {i+1} 返回错误 {response.status_code}: {error_msg[:200]}")
                                last_error = f"格式{i+1}返回错误 {response.status_code}: {error_msg[:200]}"
                            except:
                                error_msg = response.text[:200]
                                print(f"✗ 格式 {i+1} 返回错误 {response.status_code}: {error_msg}")
                                last_error = f"格式{i+1}返回错误 {response.status_code}: {error_msg}"
                            continue
                    except Exception as e:
                        print(f"✗ 格式 {i+1} 调用异常: {str(e)}")
                        last_error = f"格式{i+1}调用异常: {str(e)}"
                        continue
                
                if not found_format:
                    return {
                        "success": False,
                        "error": f"所有参数格式都失败。最后错误: {last_error}。请检查 Coze API 文档: https://www.coze.cn/docs/developer_guides/api_overview",
                        "analysis": None
                    }
            
            # 如果到这里，说明找到了可用的端点和格式（response.status_code == 200）
            # result 应该已经存在
            if 'result' not in locals():
                return {
                    "success": False,
                    "error": "无法获取 Coze API 响应结果",
                    "analysis": None
                }
            
            # 处理成功响应（response.status_code == 200）
            # 解析 Coze 响应（根据实际返回格式调整）
            # Coze 返回格式可能因配置而异，这里做通用处理
            ai_content = ""
            
            # 尝试多种可能的响应格式
            if "data" in result:
                data = result.get("data", {})
                # 格式1: data.messages
                if "messages" in data:
                    messages = data.get("messages", [])
                    if messages:
                        # 获取最后一条AI消息
                        ai_message = messages[-1]
                        if isinstance(ai_message, dict):
                            ai_content = ai_message.get("content", "") or ai_message.get("text", "") or str(ai_message)
                        else:
                            ai_content = str(ai_message)
                # 格式2: data.content
                elif "content" in data:
                    ai_content = data["content"]
                # 格式3: data 直接是内容
                else:
                    ai_content = json.dumps(data, ensure_ascii=False, indent=2)
            elif "content" in result:
                ai_content = result["content"]
            elif "message" in result:
                ai_content = result["message"]
            elif "text" in result:
                ai_content = result["text"]
            elif "answer" in result:
                ai_content = result["answer"]
            else:
                # 如果格式不匹配，返回整个响应的JSON
                ai_content = json.dumps(result, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "analysis": ai_content,
                "raw_response": result  # 保留原始响应供调试
            }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Coze API 调用超时",
                "analysis": None
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"网络请求失败: {str(e)}",
                "analysis": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Coze API 调用异常: {str(e)}",
                "analysis": None
            }
    
    def analyze_rizhu_gender_only(self, rizhu_analysis_text: str, user_question: Optional[str] = None) -> Dict[str, Any]:
        """
        只传递日柱性别分析内容给AI（不传递其他八字信息）
        
        Args:
            rizhu_analysis_text: 日柱性别分析文本（get_formatted_output() 的输出）
            user_question: 用户的问题或分析需求，可选
            
        Returns:
            dict: 包含AI分析结果
        """
        # 只使用日柱性别分析文本，不传递其他八字数据
        if user_question:
            user_message = f"""请根据以下内容进行分析，并回答用户的问题：

{rizhu_analysis_text}

用户问题：{user_question}

请提供专业的分析。"""
        else:
            user_message = f"""请根据以下内容进行分析：

{rizhu_analysis_text}

请提供专业的分析和建议。"""
        
        # 调用 Coze API（不传递 bazi_data）
        return self._call_coze_api(user_message, {})
    
    def _normalize_line(self, line: str) -> str:
        """
        标准化行内容，用于对比（去除首尾空格，统一空白字符）
        """
        return line.strip()
    
    def _find_similar_line(self, target_line: str, search_lines: list, threshold: float = 0.6) -> int:
        """
        在搜索列表中查找与目标行相似的行
        
        Args:
            target_line: 目标行
            search_lines: 搜索列表
            threshold: 相似度阈值（0-1）
            
        Returns:
            int: 找到的行的索引，如果没找到返回-1
        """
        import difflib
        
        target_normalized = self._normalize_line(target_line)
        if not target_normalized:
            return -1
        
        for idx, search_line in enumerate(search_lines):
            search_normalized = self._normalize_line(search_line)
            if not search_normalized:
                continue
            
            # 计算相似度
            similarity = difflib.SequenceMatcher(None, target_normalized, search_normalized).ratio()
            if similarity >= threshold:
                return idx
        
        return -1
    
    def _compare_texts(self, original: str, polished: str) -> list:
        """
        对比原始文本和润色后的文本，找出修改的地方
        使用更智能的方式识别修改的内容块
        
        Args:
            original: 原始文本
            polished: 润色后的文本
            
        Returns:
            list: 修改列表，每个元素包含修改位置和内容
        """
        import difflib
        
        changes = []
        original_lines = original.split('\n')
        polished_lines = polished.split('\n')
        
        # 使用 difflib 进行智能对比
        differ = difflib.SequenceMatcher(None, original_lines, polished_lines)
        
        # 找出所有不同的块
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == 'replace':
                # 修改：原始内容和润色后的内容都不同
                orig_block = '\n'.join(original_lines[i1:i2])
                polish_block = '\n'.join(polished_lines[j1:j2])
                
                # 检查是否是真正的修改还是位置移动
                # 如果原始块中的每一行都能在润色后的块中找到相似内容，可能是位置移动
                orig_block_lines = [l for l in orig_block.split('\n') if l.strip()]
                polish_block_lines = [l for l in polish_block.split('\n') if l.strip()]
                
                # 如果两个块都有内容，且行数相同或接近，更可能是修改而不是删除+新增
                if orig_block_lines and polish_block_lines:
                    changes.append({
                        "line_number": i1 + 1,
                        "original": orig_block,
                        "polished": polish_block,
                        "type": "modified"
                    })
                elif orig_block_lines and not polish_block_lines:
                    # 原始有内容，润色后没有，但需要检查是否在其他位置
                    found_elsewhere = False
                    for orig_line in orig_block_lines:
                        if self._find_similar_line(orig_line, polished_lines) >= 0:
                            found_elsewhere = True
                            break
                    
                    if not found_elsewhere:
                        changes.append({
                            "line_number": i1 + 1,
                            "original": orig_block,
                            "polished": "",
                            "type": "deleted"
                        })
                elif not orig_block_lines and polish_block_lines:
                    # 润色后有新内容，检查是否在原始内容中存在
                    found_in_original = False
                    for polish_line in polish_block_lines:
                        if self._find_similar_line(polish_line, original_lines) >= 0:
                            found_in_original = True
                            break
                    
                    if not found_in_original:
                        changes.append({
                            "line_number": i1 + 1,
                            "original": "",
                            "polished": polish_block,
                            "type": "added"
                        })
            elif tag == 'delete':
                # 删除：原始内容在润色后不存在
                orig_block = '\n'.join(original_lines[i1:i2])
                orig_block_lines = [l for l in orig_block.split('\n') if l.strip()]
                
                if not orig_block_lines:
                    # 跳过空白行
                    continue
                
                # 检查原始内容是否在润色后的文本中的其他位置存在（可能是位置移动）
                found_elsewhere = False
                for orig_line in orig_block_lines:
                    if self._find_similar_line(orig_line, polished_lines) >= 0:
                        found_elsewhere = True
                        break
                
                # 只有在润色后的文本中完全找不到相似内容时，才认为是删除
                if not found_elsewhere:
                    changes.append({
                        "line_number": i1 + 1,
                        "original": orig_block,
                        "polished": "",
                        "type": "deleted"
                    })
            elif tag == 'insert':
                # 新增：润色后新增的内容
                polish_block = '\n'.join(polished_lines[j1:j2])
                polish_block_lines = [l for l in polish_block.split('\n') if l.strip()]
                
                if not polish_block_lines:
                    # 跳过空白行
                    continue
                
                # 检查润色后的内容是否在原始文本中的其他位置存在（可能是位置移动）
                found_in_original = False
                for polish_line in polish_block_lines:
                    if self._find_similar_line(polish_line, original_lines) >= 0:
                        found_in_original = True
                        break
                
                # 只有在原始文本中完全找不到相似内容时，才认为是新增
                if not found_in_original:
                    changes.append({
                        "line_number": i1 + 1,
                        "original": "",
                        "polished": polish_block,
                        "type": "added"
                    })
        
        return changes
    
    def polish_character_analysis(self, analysis_text: str, user_instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        将【性格与命运解析】格式的内容传递给大模型进行处理
        
        Args:
            analysis_text: 包含【性格与命运解析】的文本内容
            user_instruction: 用户指令，例如"请润色文字"、"请优化表达"等，可选
            
        Returns:
            dict: 包含处理后的结果和对比信息
        """
        # 检查是否包含【性格与命运解析】
        if "【性格与命运解析】" not in analysis_text:
            return {
                "success": False,
                "error": "内容中未找到【性格与命运解析】格式",
                "polished_content": None,
                "original_content": None,
                "changes": []
            }
        
        # 提取【性格与命运解析】部分的内容
        lines = analysis_text.split('\n')
        start_idx = -1
        for i, line in enumerate(lines):
            if "【性格与命运解析】" in line:
                start_idx = i
                break
        
        if start_idx == -1:
            return {
                "success": False,
                "error": "无法定位【性格与命运解析】内容",
                "polished_content": None,
                "original_content": None,
                "changes": []
            }
        
        # 提取从【性格与命运解析】开始的所有内容（保留原始格式）
        character_analysis = '\n'.join(lines[start_idx:])
        
        # 提取纯文本内容（去掉格式，只保留文字）
        # 跳过标题行和分隔线，只提取编号和内容
        text_lines = []
        for line in lines[start_idx:]:
            line = line.strip()
            # 跳过标题和分隔线
            if "【性格与命运解析】" in line or line.startswith("=") or not line:
                continue
            # 保留编号和内容行
            if line:
                text_lines.append(line)
        
        # 纯文本内容（不带格式）
        plain_text = '\n'.join(text_lines)
        
        # 构建用户消息，只发送纯文本，要求返回纯文本
        if user_instruction:
            user_message = f"""请根据以下要求处理以下内容：

{user_instruction}

{plain_text}

要求：
1. 只润色文字内容，使其更加流畅、自然、易读
2. 必须保留所有原始内容，不能删除任何一条
3. 保持原有的编号格式（如 "1. xxx"）
4. 只返回润色后的文字内容，不要添加任何标题或格式"""
        else:
            user_message = f"""请对以下内容进行润色，使其更加流畅、自然、易读：

{plain_text}

要求：
1. 只润色文字内容，使其更加流畅、自然、易读
2. 必须保留所有原始内容，不能删除任何一条
3. 保持原有的编号格式（如 "1. xxx"）
4. 只返回润色后的文字内容，不要添加任何标题或格式"""
        
        # 调用 Coze API
        result = self._call_coze_api(user_message, {})
        
        if result.get('success'):
            polished_plain_text = result.get('analysis', '').strip()
            
            # 检查返回的内容是否是错误信息
            if polished_plain_text:
                polished_str = str(polished_plain_text).strip()
                # 检查是否是 JSON 格式的错误信息
                if polished_str.startswith('{') and ('"code"' in polished_str or '"error"' in polished_str or '"msg"' in polished_str):
                    # 这是错误信息，不是润色后的内容
                    try:
                        import json
                        error_data = json.loads(polished_str)
                        error_msg = error_data.get('msg', error_data.get('error', polished_str))
                        return {
                            "success": False,
                            "error": f"Coze API 返回错误: {error_msg}",
                            "polished_content": None,
                            "original_content": character_analysis,
                            "changes": []
                        }
                    except:
                        return {
                            "success": False,
                            "error": f"Coze API 返回了错误信息: {polished_str[:200]}",
                            "polished_content": None,
                            "original_content": character_analysis,
                            "changes": []
                        }
            
            # 将润色后的纯文本重新包装成原格式
            # 添加标题和分隔线
            polished_text = "【性格与命运解析】\n"
            polished_text += "=" * 60 + "\n"
            polished_text += polished_plain_text
            
            # 对比原始内容和润色后的内容（使用纯文本对比）
            changes = self._compare_texts(plain_text, polished_plain_text)
            
            return {
                "success": True,
                "analysis": polished_text,  # 润色后的完整内容（带格式）
                "original_content": character_analysis,  # 原始完整内容（带格式）
                "polished_content": polished_text,  # 润色后的完整内容（带格式）
                "polished_plain_text": polished_plain_text,  # 润色后的纯文本（不带格式）
                "original_plain_text": plain_text,  # 原始纯文本（不带格式）
                "changes": changes,  # 修改列表（基于纯文本对比）
                "changes_count": len(changes),  # 修改数量
                "raw_response": result.get('raw_response')
            }
        else:
            return {
                "success": False,
                "error": result.get('error'),
                "polished_content": None,
                "original_content": character_analysis,
                "changes": []
            }
    
    def analyze_with_rizhu_gender(self, bazi_data: Dict[str, Any], rizhu_analysis_text: str, 
                                   user_question: Optional[str] = None) -> Dict[str, Any]:
        """
        使用Coze AI分析，只传递日柱性别分析结果（不传递其他八字信息）
        
        Args:
            bazi_data: 八字接口返回的数据（保留参数以兼容，但不使用）
            rizhu_analysis_text: print_rizhu_gender_analysis() 输出的文本内容
            user_question: 用户的问题或分析需求，可选
            
        Returns:
            dict: 包含AI分析结果
        """
        # 只使用日柱性别分析文本，不传递其他八字数据
        if user_question:
            user_message = f"""请根据以下内容进行分析，并回答用户的问题：

{rizhu_analysis_text}

用户问题：{user_question}

请提供专业的分析。"""
        else:
            user_message = f"""请根据以下内容进行分析：

{rizhu_analysis_text}

请提供专业的分析和建议。"""
        
        # 调用 Coze API（不传递 bazi_data）
        return self._call_coze_api(user_message, {})
    
