from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_workflow import AIGenerationWorkflow
from app.models.question import Question
from app.models.question_bank import QuestionBank

EXISTING_QUESTION_CONTEXT_CHAR_BUDGET = 24000


class WorkflowContextBuilder:
    def __init__(self, db: Session):
        self.db = db

    def build(self, bank: QuestionBank, workflow: AIGenerationWorkflow) -> str:
        if workflow.purpose != "extend_bank":
            return ""
        tag_names = [tag.name for tag in sorted(bank.tags, key=lambda item: item.name)]
        context_lines = [
            "这是对已有题库的扩展，请延续题库风格并避免和已有题目重复。",
            f"题库标题：{bank.title}",
            f"题库描述：{bank.description or '无'}",
            f"题库标签：{', '.join(tag_names) or '无'}",
            f"当前模型：{bank.ai_model_name or '无'}",
        ]
        if workflow.inherit_context:
            context_lines.extend(["题库 AI 描述：", bank.ai_context or "无"])
        if workflow.include_existing_questions:
            question_lines, truncated = self._existing_question_lines(bank.id)
            context_lines.append("已有题目题干摘要：")
            context_lines.append("\n".join(question_lines) or "无")
            if truncated:
                context_lines.append("已有题目摘要因长度限制已截断。")
        return "\n".join(context_lines)

    def _existing_question_lines(self, bank_id: int) -> tuple[list[str], bool]:
        rows = self.db.execute(
            select(Question.type, Question.stem).where(Question.bank_id == bank_id).order_by(Question.id.asc())
        ).all()
        lines: list[str] = []
        used = 0
        for question_type, stem in rows:
            label = "单选" if question_type == "single" else "多选" if question_type == "multiple" else question_type
            line = f"- [{label}] {(stem or '').strip()}"
            line_len = len(line) + 1
            if lines and used + line_len > EXISTING_QUESTION_CONTEXT_CHAR_BUDGET:
                return lines, True
            if not lines and line_len > EXISTING_QUESTION_CONTEXT_CHAR_BUDGET:
                return [line[:EXISTING_QUESTION_CONTEXT_CHAR_BUDGET]], True
            lines.append(line)
            used += line_len
        return lines, False
