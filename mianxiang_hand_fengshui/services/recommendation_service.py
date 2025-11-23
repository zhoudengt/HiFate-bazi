from __future__ import annotations

import json
from typing import Any, Iterable

from fastapi import UploadFile

from .report_service import ReportAssembler


class FengshuiRecommendationService:
    """
    根据面相、手相与八字结果给出办公室摆件建议。
    """

    def __init__(self) -> None:
        self.report_assembler = ReportAssembler()

    async def generate_response(
        self,
        workspace_image: UploadFile | None,
        face_profile: dict[str, Any] | None,
        hand_profile: dict[str, Any] | None,
        bazi_profile: dict[str, Any] | None,
    ) -> dict[str, Any]:
        workspace_analysis: dict[str, Any] | None = None
        if workspace_image:
            workspace_analysis = await self.analyze_workspace_image(workspace_image)

        suggestions = self._compose_suggestions(
            workspace=workspace_analysis,
            face_profile=face_profile,
            hand_profile=hand_profile,
            bazi_profile=bazi_profile,
        )

        face_section = (
            self.report_assembler.render_face_section(face_profile)
            if face_profile
            else None
        )
        hand_section = (
            self.report_assembler.render_hand_section(hand_profile)
            if hand_profile
            else None
        )
        bazi_section = (
            self.report_assembler.render_bazi_section(bazi_profile)
            if bazi_profile
            else None
        )
        workspace_section = (
            self.report_assembler.render_workspace_section(workspace_analysis)
            if workspace_analysis
            else None
        )

        report = self.report_assembler.compile_full_report(
            face_section=face_section,
            hand_section=hand_section,
            bazi_section=bazi_section,
            fengshui_suggestions={"recommendations": suggestions},
            workspace_section=workspace_section,
        )

        return {
            "recommendations": suggestions,
            "workspace_analysis": workspace_analysis,
            "report": report,
        }

    async def analyze_workspace_image(self, workspace_image: UploadFile) -> dict[str, Any]:
        """
        TODO: 在此集成实际的图像识别逻辑（例如检测光照、杂物、植物摆放）。
        """
        # 基于文件名输出示例数据；真正实现应解析图片内容
        fake_insights = [
            "整体光线均衡，适合放置能够聚财的水晶类摆件。",
            "桌面偏左区域较为空旷，可布置文昌方向的摆件提升学习与专注。",
        ]
        return {
            "meta": {"filename": workspace_image.filename},
            "insights": fake_insights,
        }

    def _compose_suggestions(
        self,
        workspace: dict[str, Any] | None,
        face_profile: dict[str, Any] | None,
        hand_profile: dict[str, Any] | None,
        bazi_profile: dict[str, Any] | None,
    ) -> list[str]:
        suggestions: list[str] = []

        if workspace:
            suggestions.append(
                "根据上传照片，建议在桌面左前方摆放文昌塔或书卷摆件，平衡空间并提升专注度。"
            )

        if face_profile:
            suggestions.extend(self._face_based_suggestions(face_profile))

        if hand_profile:
            suggestions.extend(self._hand_based_suggestions(hand_profile))

        if bazi_profile:
            suggestions.extend(self._bazi_based_suggestions(bazi_profile))

        if not suggestions:
            suggestions.append("未提供分析数据，建议任选绿植、黄水晶等通用聚气摆件。")

        return suggestions

    @staticmethod
    def _face_based_suggestions(face_profile: dict[str, Any]) -> list[str]:
        results: list[str] = []
        attributes = face_profile.get("features", {}).get("facial_attributes", {})
        emotion = attributes.get("emotion")
        if emotion == "neutral":
            results.append("面相情绪稳定，可配置水晶球与罗盘类摆件巩固决策能量。")
        if face_profile.get("features", {}).get("san_ting_ratio", {}).get("upper", 0) > 0.34:
            results.append("上停较长，适合在办公桌北方位放置葫芦或灯具，强化思考力。")
        results.append("结合面相财运特征，可考虑貔貅、黄水晶摆件强化财富磁场。")
        return results

    @staticmethod
    def _hand_based_suggestions(hand_profile: dict[str, Any]) -> list[str]:
        results: list[str] = []
        hand_shape = hand_profile.get("features", {}).get("hand_shape")
        if hand_shape == "方形手":
            results.append("手型偏务实，可在东南位放置文昌塔或铜制笔筒，提升执行力。")
        heart_line = hand_profile.get("features", {}).get("palm_lines", {}).get("heart_line")
        if heart_line and "向下弯" in heart_line:
            results.append("感情线偏向下，建议摆放薰衣草香薰或疗愈水晶，缓和情绪波动。")
        return results

    @staticmethod
    def _bazi_based_suggestions(bazi_profile: dict[str, Any]) -> list[str]:
        results: list[str] = []
        favorable = set(bazi_profile.get("favorable_elements", []))
        if "木" in favorable:
            results.append("八字喜木，可摆放常青植物、文昌竹等木质摆件增强运势。")
        if "火" in favorable:
            results.append("八字喜火，可在南方位摆放红色或灯饰类摆件，激发活力。")
        if not results:
            results.append("结合八字，优先选择五行平衡的铜、木、水元素摆件。")
        return results

