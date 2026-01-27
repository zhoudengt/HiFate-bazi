#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试报告辅助工具
用于生成和导出测试报告
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class ReportHelper:
    """测试报告辅助工具类"""
    
    def __init__(self, reports_dir: str = "reports"):
        """
        初始化报告助手
        
        Args:
            reports_dir: 报告输出目录
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)
    
    def generate_report_filename(self, prefix: str = "stress_test") -> str:
        """
        生成报告文件名（带时间戳）
        
        Args:
            prefix: 文件名前缀
            
        Returns:
            文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.json"
    
    def save_json_report(self, data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        保存 JSON 格式报告
        
        Args:
            data: 报告数据
            filename: 文件名（可选，默认自动生成）
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            filename = self.generate_report_filename()
        
        filepath = self.reports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def format_statistics(self, stats: Dict[str, Any]) -> str:
        """
        格式化统计信息为可读字符串
        
        Args:
            stats: 统计信息字典
            
        Returns:
            格式化后的字符串
        """
        lines = []
        lines.append("=" * 60)
        lines.append("压力测试统计报告")
        lines.append("=" * 60)
        lines.append(f"测试时间: {stats.get('timestamp', 'N/A')}")
        lines.append(f"目标服务器: {stats.get('host', 'N/A')}")
        lines.append("")
        lines.append("请求统计:")
        lines.append(f"  总请求数: {stats.get('total_requests', 0)}")
        lines.append(f"  成功请求: {stats.get('successful_requests', 0)}")
        lines.append(f"  失败请求: {stats.get('failed_requests', 0)}")
        lines.append(f"  错误率: {stats.get('error_rate', 0):.2%}")
        lines.append("")
        lines.append("性能指标:")
        lines.append(f"  平均响应时间: {stats.get('avg_response_time', 0):.2f}ms")
        lines.append(f"  P50 响应时间: {stats.get('p50_response_time', 0):.2f}ms")
        lines.append(f"  P95 响应时间: {stats.get('p95_response_time', 0):.2f}ms")
        lines.append(f"  P99 响应时间: {stats.get('p99_response_time', 0):.2f}ms")
        lines.append(f"  最小响应时间: {stats.get('min_response_time', 0):.2f}ms")
        lines.append(f"  最大响应时间: {stats.get('max_response_time', 0):.2f}ms")
        lines.append("")
        lines.append("吞吐量:")
        lines.append(f"  平均 QPS: {stats.get('avg_rps', 0):.2f}")
        lines.append(f"  峰值 QPS: {stats.get('peak_rps', 0):.2f}")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def check_performance_thresholds(self, stats: Dict[str, Any], 
                                     thresholds: Dict[str, float]) -> Dict[str, bool]:
        """
        检查性能指标是否满足阈值要求
        
        Args:
            stats: 统计信息
            thresholds: 阈值配置
            
        Returns:
            检查结果字典 {指标名: 是否通过}
        """
        results = {}
        
        # 检查响应时间
        p50 = stats.get('p50_response_time', 0)
        p95 = stats.get('p95_response_time', 0)
        p99 = stats.get('p99_response_time', 0)
        
        results['p50_ok'] = p50 <= thresholds.get('max_response_time_p50', 1000)
        results['p95_ok'] = p95 <= thresholds.get('max_response_time_p95', 2000)
        results['p99_ok'] = p99 <= thresholds.get('max_response_time_p99', 5000)
        
        # 检查错误率
        error_rate = stats.get('error_rate', 1.0)
        results['error_rate_ok'] = error_rate <= thresholds.get('max_error_rate', 0.01)
        
        # 检查 QPS
        avg_rps = stats.get('avg_rps', 0)
        results['rps_ok'] = avg_rps >= thresholds.get('min_rps', 10)
        
        return results
