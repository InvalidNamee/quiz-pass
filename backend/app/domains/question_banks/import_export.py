import json

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domains.question_banks.permissions import QuestionBankPermissionService
from app.domains.question_banks.queries import QuestionBankQueryService
from app.domains.question_banks.stats import QuestionBankStatsService
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.domains.question_banks.tags import merge_tag_names, normalize_tag_names, set_bank_tags
from app.utils.json_io import create_question_from_payload, question_to_json


class QuestionBankImportExportService:
    def __init__(self, db: Session):
        self.db = db
        self.query = QuestionBankQueryService(db)

    def export_payload(self, bank_id: int, user: User) -> dict:
        bank = self.db.scalar(select(QuestionBank).options(selectinload(QuestionBank.questions)).where(QuestionBank.id == bank_id))
        if not bank or not QuestionBankPermissionService.can_read(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        for question in bank.questions:
            _ = question.options
        return {
            "version": 1,
            "bank": {
                "title": bank.title,
                "description": bank.description,
                "tags": [tag.name for tag in sorted(bank.tags, key=lambda item: item.name)],
            },
            "questions": [question_to_json(question) for question in bank.questions],
        }

    def export_response(self, bank_id: int, user: User) -> JSONResponse:
        payload = self.export_payload(bank_id, user)
        return JSONResponse(payload, headers={"Content-Disposition": f'attachment; filename="question-bank-{bank_id}.json"'})

    def import_to_existing(self, bank_id: int, payload: dict, user: User):
        bank = self.db.get(QuestionBank, bank_id)
        if not QuestionBankPermissionService.can_manage(bank, user):
            raise HTTPException(status_code=404, detail="Question bank not found")
        try:
            questions = self.extract_questions(payload)
            for raw_question in questions:
                create_question_from_payload(self.db, bank.id, raw_question, source="json_import")
            QuestionBankStatsService.increment_questions(self.db, bank, len(questions))
            self.db.commit()
            self.db.refresh(bank)
            return self.query.to_out(bank, user)
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=f"JSON 导入失败: {exc}") from exc

    def import_new_bank(
        self,
        payload: dict,
        user: User,
        visibility: str = "private",
        form_tag_names: list[object] | None = None,
        file_stem: str | None = None,
    ):
        try:
            raw_bank_info = payload.get("bank") or {}
            bank_info = raw_bank_info if isinstance(raw_bank_info, dict) else {}
            title = str(bank_info.get("title") or "").strip()
            if not title:
                title = (file_stem or "").strip() or "导入题库"
            raw_description = bank_info.get("description")
            description = raw_description.strip() or None if isinstance(raw_description, str) else None
            file_tag_names = bank_info.get("tags") if isinstance(bank_info.get("tags"), list) else []
            questions = self.extract_questions(payload)
            bank = QuestionBank(owner_id=user.id, title=title, description=description, visibility=visibility, desired_visibility=visibility)
            self.db.add(bank)
            self.db.flush()
            set_bank_tags(self.db, bank, merge_tag_names(file_tag_names, form_tag_names or []))
            for raw_question in questions:
                create_question_from_payload(self.db, bank.id, raw_question, source="json_import")
            QuestionBankStatsService.rebuild_bank_stats(self.db, bank.id)
            self.db.commit()
            self.db.refresh(bank)
            return self.query.to_out(bank, user)
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=f"JSON 导入失败: {exc}") from exc

    @staticmethod
    def parse_upload(content: bytes) -> dict:
        try:
            payload = json.loads(content.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"JSON 导入失败: {exc}") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON 导入失败: 顶层必须是对象")
        return payload

    @staticmethod
    def parse_tag_names(raw: str | None) -> list[str]:
        if not raw:
            return []
        try:
            tag_names = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="tag_names 必须是字符串数组") from exc
        if not isinstance(tag_names, list):
            raise HTTPException(status_code=422, detail="tag_names 必须是字符串数组")
        try:
            return normalize_tag_names(tag_names)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @staticmethod
    def extract_questions(payload: dict) -> list[dict]:
        questions = payload.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError("questions 不能为空")
        return questions
