# -*- coding: utf-8 -*-
"""
分析器 - 分析反馈数据，识别错误模式
"""
from typing import Dict, Any, List
from collections import Counter, defaultdict
from services.prompt_optimizer.logger import logger


class FeedbackAnalyzer:
    """反馈分析器"""
    
    def __init__(self):
        logger.info("FeedbackAnalyzer initialized")
    
    def analyze_accuracy(self, feedbacks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析准确率
        
        Args:
            feedbacks: 反馈列表
        
        Returns:
            分析结果
        """
        if not feedbacks:
            return {
                "total_requests": 0,
                "accuracy": 0.0,
                "common_errors": [],
                "accuracy_by_intent": {}
            }
        
        total = len(feedbacks)
        correct = 0
        intent_stats = defaultdict(lambda: {"total": 0, "correct": 0})
        errors = []
        
        for feedback in feedbacks:
            predicted = set(feedback.get("predicted_intents", []))
            correct_intents = set(feedback.get("correct_intents", []))
            
            # 计算是否正确
            is_correct = predicted == correct_intents or feedback.get("satisfied", False)
            if is_correct:
                correct += 1
            else:
                # 记录错误
                errors.append({
                    "question": feedback.get("question", ""),
                    "predicted": list(predicted),
                    "should_be": list(correct_intents),
                    "confidence": feedback.get("confidence", 0.0)
                })
            
            # 统计每个意图的准确率
            for intent in predicted:
                intent_stats[intent]["total"] += 1
                if is_correct:
                    intent_stats[intent]["correct"] += 1
        
        # 计算总准确率
        accuracy = correct / total if total > 0 else 0.0
        
        # 分析常见错误模式
        common_errors = self._identify_error_patterns(errors)
        
        # 计算每个意图的准确率
        accuracy_by_intent = {
            intent: stats["correct"] / stats["total"]
            for intent, stats in intent_stats.items()
            if stats["total"] > 0
        }
        
        result = {
            "total_requests": total,
            "accuracy": accuracy,
            "common_errors": common_errors,
            "accuracy_by_intent": accuracy_by_intent
        }
        
        logger.info(f"Analysis complete: accuracy={accuracy:.2%}, total={total}")
        return result
    
    def _identify_error_patterns(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别常见错误模式"""
        if not errors:
            return []
        
        # 按 predicted -> should_be 分组
        error_groups = defaultdict(list)
        for error in errors:
            predicted_str = ",".join(sorted(error["predicted"]))
            should_be_str = ",".join(sorted(error["should_be"]))
            key = f"{predicted_str} -> {should_be_str}"
            error_groups[key].append(error["question"])
        
        # 找出最常见的错误
        common_errors = []
        for key, questions in sorted(error_groups.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            predicted, should_be = key.split(" -> ")
            common_errors.append({
                "pattern": key,
                "count": len(questions),
                "predicted": predicted,
                "should_be": should_be,
                "examples": questions[:3]
            })
        
        return common_errors
    
    def generate_weekly_report(self, feedbacks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成周报"""
        analysis = self.analyze_accuracy(feedbacks)
        
        report = {
            "period": "Last 7 days",
            "total_requests": analysis["total_requests"],
            "overall_accuracy": analysis["accuracy"],
            "accuracy_by_intent": analysis["accuracy_by_intent"],
            "top_errors": analysis["common_errors"][:5],
            "recommendations": self._generate_recommendations(analysis)
        }
        
        logger.info(f"Weekly report generated: accuracy={report['overall_accuracy']:.2%}")
        return report
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """根据分析结果生成优化建议"""
        recommendations = []
        
        accuracy = analysis["accuracy"]
        
        if accuracy < 0.85:
            recommendations.append("准确率较低，建议全面优化Prompt，增加Few-shot示例")
        elif accuracy < 0.95:
            recommendations.append("准确率接近目标，建议针对常见错误进行优化")
        else:
            recommendations.append("准确率良好，建议继续监控和小幅优化")
        
        # 针对特定意图的建议
        for intent, acc in analysis["accuracy_by_intent"].items():
            if acc < 0.80:
                recommendations.append(f"{intent} 意图准确率偏低（{acc:.1%}），建议增加该类别的示例")
        
        # 针对常见错误的建议
        if analysis["common_errors"]:
            top_error = analysis["common_errors"][0]
            recommendations.append(f"最常见错误：{top_error['pattern']}，出现{top_error['count']}次，建议添加相关训练样本")
        
        return recommendations

