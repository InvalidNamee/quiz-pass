from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_workflow import AIGenerationWorkflow
from app.models.question import Question
from app.models.question_bank import QuestionBank


class WorkflowContextBuilder:
    def __init__(self, db: Session):
        self.db = db

    def build(self, bank: QuestionBank, workflow: AIGenerationWorkflow) -> str:
        if workflow.purpose != "extend_bank" or not workflow.inherit_context:
            return ""
        stems = self.db.scalars(select(Question.stem).where(Question.bank_id == bank.id).limit(80)).all()
        previous = self.db.scalars(
            select(AIGenerationWorkflow)
            .where(AIGenerationWorkflow.bank_id == bank.id, AIGenerationWorkflow.status == "imported", AIGenerationWorkflow.id != workflow.id)
            .order_by(AIGenerationWorkflow.updated_at.desc())
            .limit(3)
        ).all()
        previous_lines = [f"- {item.generation_mode} / 额外指令：{item.extra_instruction or '无'} / 修复 {item.repair_attempts} 次" for item in previous]
        stem_lines = [f"- {stem[:80]}" for stem in stems]
        tag_names = [tag.name for tag in sorted(bank.tags, key=lambda item: item.name)]
        return f"""
这是对已有题库的扩展，请延续题库风格并避免和已有题目重复。
题库标题：{bank.title}
题库描述：{bank.description or '无'}
题库级上下文：
{bank.ai_context or '无'}
题库标签：{', '.join(tag_names) or '无'}
当前模型：{bank.ai_model_name or '无'}
最近成功 workflow：
{chr(10).join(previous_lines) or '无'}
已有题目摘要：
{chr(10).join(stem_lines) or '无'}
"""
