# -*- coding: utf-8 -*-
"""
性能监控工具 - 端到端日志和性能分析
用于记录每个阶段的响应时间和问题分析
"""
import time
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器 - 记录端到端流程的每个阶段"""
    
    def __init__(self, request_id: Optional[str] = None):
        """
        初始化性能监控器
        
        Args:
            request_id: 请求ID（用于追踪）
        """
        self.request_id = request_id or f"req_{int(time.time() * 1000)}"
        self.stages: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.current_stage = None
        self.stage_start_time = None
        
        logger.info(f"[PerformanceMonitor] 开始监控请求: {self.request_id}")
    
    @contextmanager
    def stage(self, stage_name: str, stage_description: str = "", **kwargs):
        """
        阶段上下文管理器
        
        Usage:
            with monitor.stage("intent_recognition", "意图识别"):
                # 执行意图识别代码
                result = intent_client.classify(question)
        """
        self.start_stage(stage_name, stage_description, **kwargs)
        try:
            yield
        except Exception as e:
            self.end_stage(stage_name, success=False, error=str(e))
            raise
        else:
            self.end_stage(stage_name, success=True)
    
    def start_stage(self, stage_name: str, stage_description: str = "", **kwargs):
        """
        开始一个阶段
        
        Args:
            stage_name: 阶段名称
            stage_description: 阶段描述
            **kwargs: 额外信息
        """
        if self.current_stage:
            # 如果上一个阶段未结束，先结束它
            self.end_stage(self.current_stage, success=False, error="阶段被新阶段中断")
        
        self.current_stage = stage_name
        self.stage_start_time = time.time()
        
        stage_info = {
            "stage": stage_name,
            "description": stage_description,
            "start_time": self.stage_start_time,
            "start_time_iso": datetime.now().isoformat(),
            **kwargs
        }
        
        logger.info(
            f"[PerformanceMonitor] [{self.request_id}] 开始阶段: {stage_name} - {stage_description}",
            extra={"stage": stage_name, "request_id": self.request_id}
        )
        
        return stage_info
    
    def end_stage(
        self,
        stage_name: str,
        success: bool = True,
        error: Optional[str] = None,
        **kwargs
    ):
        """
        结束一个阶段
        
        Args:
            stage_name: 阶段名称
            success: 是否成功
            error: 错误信息（如果有）
            **kwargs: 额外信息（如结果数量、数据大小等）
        """
        if not self.stage_start_time:
            logger.warning(f"[PerformanceMonitor] 阶段 {stage_name} 未开始，无法结束")
            return
        
        end_time = time.time()
        duration = end_time - self.stage_start_time
        duration_ms = int(duration * 1000)
        
        stage_info = {
            "stage": stage_name,
            "start_time": self.stage_start_time,
            "end_time": end_time,
            "duration_ms": duration_ms,
            "duration_sec": round(duration, 3),
            "success": success,
            "error": error,
            **kwargs
        }
        
        self.stages.append(stage_info)
        
        # 日志输出
        status = "✅" if success else "❌"
        error_msg = f" - 错误: {error}" if error else ""
        logger.info(
            f"[PerformanceMonitor] [{self.request_id}] {status} 阶段完成: {stage_name} - "
            f"耗时: {duration_ms}ms ({duration:.3f}s){error_msg}",
            extra={
                "stage": stage_name,
                "duration_ms": duration_ms,
                "success": success,
                "request_id": self.request_id
            }
        )
        
        # 如果耗时过长，记录警告
        if duration > 1.0:  # 超过1秒
            logger.warning(
                f"[PerformanceMonitor] ⚠️ 阶段 {stage_name} 耗时过长: {duration_ms}ms",
                extra={
                    "stage": stage_name,
                    "duration_ms": duration_ms,
                    "request_id": self.request_id
                }
            )
        
        self.current_stage = None
        self.stage_start_time = None
        
        return stage_info
    
    def add_metric(self, stage_name: str, metric_name: str, value: Any):
        """
        添加指标
        
        Args:
            stage_name: 阶段名称
            metric_name: 指标名称
            value: 指标值
        """
        # 找到对应的阶段并添加指标
        for stage in self.stages:
            if stage.get("stage") == stage_name:
                stage[f"metric_{metric_name}"] = value
                break
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取性能摘要
        
        Returns:
            包含总耗时、各阶段耗时、问题分析等的摘要
        """
        total_duration = time.time() - self.start_time
        total_duration_ms = int(total_duration * 1000)
        
        # 计算各阶段耗时
        stage_times = {}
        for stage in self.stages:
            stage_name = stage.get("stage")
            duration_ms = stage.get("duration_ms", 0)
            stage_times[stage_name] = duration_ms
        
        # 识别性能瓶颈
        bottlenecks = []
        for stage in self.stages:
            duration_ms = stage.get("duration_ms", 0)
            if duration_ms > 1000:  # 超过1秒
                bottlenecks.append({
                    "stage": stage.get("stage"),
                    "duration_ms": duration_ms,
                    "description": stage.get("description", "")
                })
        
        # 识别失败的阶段
        failed_stages = [
            {
                "stage": stage.get("stage"),
                "error": stage.get("error"),
                "description": stage.get("description", "")
            }
            for stage in self.stages
            if not stage.get("success", True)
        ]
        
        summary = {
            "request_id": self.request_id,
            "total_duration_ms": total_duration_ms,
            "total_duration_sec": round(total_duration, 3),
            "stages": self.stages,
            "stage_times": stage_times,
            "bottlenecks": bottlenecks,
            "failed_stages": failed_stages,
            "success": len(failed_stages) == 0,
            "timestamp": datetime.now().isoformat()
        }
        
        return summary
    
    def log_summary(self):
        """输出性能摘要到日志"""
        summary = self.get_summary()
        
        logger.info("=" * 80)
        logger.info(f"[PerformanceMonitor] [{self.request_id}] 性能摘要")
        logger.info("=" * 80)
        logger.info(f"总耗时: {summary['total_duration_ms']}ms ({summary['total_duration_sec']}s)")
        logger.info(f"阶段数: {len(summary['stages'])}")
        logger.info("")
        
        logger.info("各阶段耗时:")
        for stage in summary['stages']:
            stage_name = stage.get("stage")
            duration_ms = stage.get("duration_ms", 0)
            success = stage.get("success", True)
            status = "✅" if success else "❌"
            logger.info(f"  {status} {stage_name}: {duration_ms}ms")
        
        if summary['bottlenecks']:
            logger.info("")
            logger.warning("⚠️ 性能瓶颈（>1秒）:")
            for bottleneck in summary['bottlenecks']:
                logger.warning(
                    f"  - {bottleneck['stage']}: {bottleneck['duration_ms']}ms - {bottleneck['description']}"
                )
        
        if summary['failed_stages']:
            logger.info("")
            logger.error("❌ 失败的阶段:")
            for failed in summary['failed_stages']:
                logger.error(
                    f"  - {failed['stage']}: {failed['error']} - {failed['description']}"
                )
        
        logger.info("=" * 80)
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        return self.get_summary()
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

