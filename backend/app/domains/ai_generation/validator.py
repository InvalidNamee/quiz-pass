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
    def validate(cls, payload: dict, generation_mode: str, requested_count: int | None, question_type_settings: dict | None = None) -> tuple[list[dict], str]:
        questions = cls.validate_questions_payload(payload)
        max_count = cls.max_count(generation_mode, requested_count)
        allowed_types = cls.allowed_types(question_type_settings)
        fixed_quotas = cls.fixed_type_quotas(generation_mode, question_type_settings)
        type_counts = {question_type: 0 for question_type in fixed_quotas}
        normalized: list[dict] = []
        for index, raw_question in enumerate(questions, start=1):
            try:
                if not isinstance(raw_question, dict):
                    raise ValueError("题目必须是对象")
                question_type = raw_question.get("type")
                if allowed_types and question_type not in allowed_types:
                    if generation_mode == "bank_parse":
                        continue
                    raise ValueError(f"题型 {question_type} 未启用")
                if question_type in fixed_quotas and type_counts[question_type] >= fixed_quotas[question_type]:
                    continue
                normalized.append(normalize_question_payload(raw_question))
                if question_type in type_counts:
                    type_counts[question_type] += 1
                if len(normalized) >= max_count:
                    break
            except ValueError as exc:
                raise AIOutputValidationError(question_context(index, raw_question if isinstance(raw_question, dict) else {}, str(exc))) from exc
        missing = [
            f"{question_type} 需要 {expected} 道，实际 {type_counts.get(question_type, 0)} 道"
            for question_type, expected in fixed_quotas.items()
            if type_counts.get(question_type, 0) < expected
        ]
        if missing:
            raise AIOutputValidationError("题型数量不足：" + "；".join(missing))
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

    @staticmethod
    def allowed_types(question_type_settings: dict | None) -> set[str] | None:
        if not question_type_settings:
            return None
        enabled = {
            question_type
            for question_type, config in question_type_settings.items()
            if isinstance(config, dict) and config.get("enabled")
        }
        return enabled or None

    @staticmethod
    def fixed_type_quotas(generation_mode: str, question_type_settings: dict | None) -> dict[str, int]:
        if generation_mode != "knowledge_generate" or not question_type_settings:
            return {}
        return {
            question_type: config["count"]
            for question_type, config in question_type_settings.items()
            if isinstance(config, dict)
            and config.get("enabled")
            and isinstance(config.get("count"), int)
            and not isinstance(config.get("count"), bool)
        }
