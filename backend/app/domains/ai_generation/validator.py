from app.domains.ai_generation.errors import AIOutputValidationError
from app.utils.json_io import normalize_question_payload


def question_snippet(raw: dict) -> str:
    stem = str(raw.get("stem") or "").strip()
    return stem[:40] or "空题干"


def question_context(index: int, raw: dict, reason: str) -> str:
    question_type = raw.get("type") or "未知类型"
    correct_count = 0
    options = raw.get("options")
    if isinstance(options, list):
        correct_count = sum(1 for option in options if bool(option.get("is_correct")))
    detail = reason
    if question_type == "single":
        detail = f"single 有 {correct_count} 个正确答案；{reason}"
    elif question_type == "multiple":
        detail = f"multiple 有 {correct_count} 个正确答案；{reason}"
    return f"第 {index} 题校验失败\n题干：{question_snippet(raw)}\n题型：{question_type}\n原因：{detail}"


class AIPayloadValidator:
    @classmethod
    def validate(cls, payload: dict, generation_mode: str, requested_count: int | None) -> tuple[list[dict], str]:
        questions = cls.validate_questions_payload(payload)
        max_count = cls.max_count(generation_mode, requested_count)
        normalized: list[dict] = []
        for index, raw_question in enumerate(questions[:max_count], start=1):
            try:
                if not isinstance(raw_question, dict):
                    raise ValueError("题目必须是对象")
                normalized.append(normalize_question_payload(raw_question))
            except ValueError as exc:
                raise AIOutputValidationError(question_context(index, raw_question if isinstance(raw_question, dict) else {}, str(exc))) from exc
        if not normalized:
            raise AIOutputValidationError("没有可入库的题目")
        return normalized, f"校验通过，共 {len(normalized)} 道题"

    @staticmethod
    def validate_questions_payload(payload: dict) -> list[dict]:
        if "questions" not in payload:
            raise AIOutputValidationError("AI 返回 JSON 缺少 questions 字段")
        questions = payload.get("questions")
        if not isinstance(questions, list):
            raise AIOutputValidationError("AI 返回 JSON 中 questions 必须是数组")
        if not questions:
            raise AIOutputValidationError("AI 返回 JSON 中 questions 不能为空")
        return questions

    @staticmethod
    def max_count(generation_mode: str, requested_count: int | None) -> int:
        if generation_mode == "bank_parse":
            return 300
        return requested_count or 100
