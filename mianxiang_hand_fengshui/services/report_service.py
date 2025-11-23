from typing import Any


class ReportAssembler:
    """
    负责将各模块结果转换为统一的报告结构。
    """

    def render_workspace_section(self, workspace_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "section": "办公环境分析",
            "source": "workspace",
            "content": workspace_result,
            "summary": workspace_result.get("insights", []),
        }

    def render_face_section(self, face_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "section": "面相分析",
            "source": "face",
            "content": face_result,
            "summary": face_result.get("inferences", []),
        }

    def render_hand_section(self, hand_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "section": "手相分析",
            "source": "hand",
            "content": hand_result,
            "summary": hand_result.get("inferences", []),
        }

    def render_bazi_section(self, bazi_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "section": "八字分析",
            "source": "bazi",
            "content": bazi_result,
            "summary": bazi_result.get("summary", []),
        }

    def compile_full_report(
        self,
        face_section: dict[str, Any] | None,
        hand_section: dict[str, Any] | None,
        bazi_section: dict[str, Any] | None,
        fengshui_suggestions: dict[str, Any] | None,
        workspace_section: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sections = list(
            filter(None, [face_section, hand_section, bazi_section, workspace_section])
        )
        return {
            "title": "面相手相八字综合报告",
            "sections": sections,
            "fengshui_recommendations": fengshui_suggestions,
        }

