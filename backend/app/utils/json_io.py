import json
import re

from app.models.question import Question, QuestionBlank, QuestionOption


CHOICE_TYPES = {"single", "multiple"}
TEXT_TYPES = {"blank", "short_answer"}
QUESTION_TYPES = CHOICE_TYPES | TEXT_TYPES


def normalize_blank_answers(raw_answers) -> list[str]:
    if not isinstance(raw_answers, list):
        raise ValueError("填空答案必须是数组")
    answers: list[str] = []
    seen: set[str] = set()
    for answer in raw_answers:
        normalized = str(answer or "").strip()
        if normalized and normalized not in seen:
            answers.append(normalized)
            seen.add(normalized)
    if not answers:
        raise ValueError("每个空至少需要一个答案")
    return answers


def normalize_blanks(raw_blanks, stem: str) -> list[dict]:
    if not isinstance(raw_blanks, list) or not raw_blanks:
        raise ValueError("填空题至少需要一个空")
    normalized: list[dict] = []
    seen: set[str] = set()
    for index, blank in enumerate(raw_blanks, start=1):
        if not isinstance(blank, dict):
            raise ValueError("填空项必须是对象")
        label = str(blank.get("label") or index).strip()
        if not label:
            raise ValueError("填空 label 不能为空")
        if label in seen:
            raise ValueError("填空 label 不能重复")
        seen.add(label)
        normalized.append({"label": label, "answers": normalize_blank_answers(blank.get("answers"))})
    placeholders = set(re.findall(r"\{\{([^{}]+)\}\}", stem))
    labels = {blank["label"] for blank in normalized}
    if not placeholders:
        raise ValueError("填空题题干必须包含 {{1}} 形式的占位符")
    if placeholders != labels:
        raise ValueError("填空题题干占位符必须与 blanks 一一对应")
    return normalized


def normalize_question_payload(raw: dict) -> dict:
    question_type = raw.get("type")
    if question_type not in QUESTION_TYPES:
        raise ValueError("题目类型必须是 single、multiple、blank 或 short_answer")
    stem = str(raw.get("stem") or "").strip()
    if not stem:
        raise ValueError("题干不能为空")
    options = raw.get("options") or []
    blanks = raw.get("blanks") or []
    if question_type in TEXT_TYPES and options:
        raise ValueError("填空和简答题不能包含选项")
    if question_type != "blank" and blanks:
        raise ValueError("只有填空题可以包含 blanks")
    normalized_options = []
    normalized_blanks = []
    if question_type in CHOICE_TYPES:
        if not isinstance(options, list) or len(options) < 2:
            raise ValueError("选择题至少需要两个选项")
        if len(options) > 26:
            raise ValueError("每题最多 26 个选项")
        for index, option in enumerate(options):
            if not isinstance(option, dict):
                raise ValueError("选项必须是对象")
            content = str(option.get("content") or "").strip()
            if not content:
                raise ValueError("选项内容不能为空")
            normalized_options.append(
                {
                    "label": str(option.get("label") or chr(65 + index))[:8],
                    "content": content,
                    "is_correct": bool(option.get("is_correct")),
                }
            )
        correct_count = sum(1 for option in normalized_options if option["is_correct"])
        if question_type == "single" and correct_count != 1:
            raise ValueError("单选题必须且只能有一个正确答案")
        if question_type == "multiple" and correct_count < 2:
            raise ValueError("多选题至少需要两个正确答案")
    elif question_type == "blank":
        normalized_blanks = normalize_blanks(blanks, stem)
    elif not str(raw.get("explanation") or "").strip():
        raise ValueError("简答题必须在解析中填写给分点")
    return {
        "type": question_type,
        "stem": stem,
        "options": normalized_options,
        "blanks": normalized_blanks,
        "explanation": str(raw.get("explanation") or "").strip() or None,
        "difficulty": raw.get("difficulty") if raw.get("difficulty") in {"easy", "medium", "hard"} else None,
    }


def create_question_from_payload(db, bank_id: int, payload: dict, source: str, generated_model: str | None = None) -> Question:
    data = normalize_question_payload(payload)
    question = Question(
        bank_id=bank_id,
        type=data["type"],
        stem=data["stem"],
        explanation=data["explanation"],
        difficulty=data["difficulty"],
        source=source,
        generated_model=generated_model,
    )
    db.add(question)
    db.flush()
    for index, option in enumerate(data["options"]):
        db.add(
            QuestionOption(
                question_id=question.id,
                label=option["label"],
                content=option["content"],
                is_correct=option["is_correct"],
                sort_order=index,
            )
        )
    for index, blank in enumerate(data["blanks"]):
        db.add(
            QuestionBlank(
                question_id=question.id,
                label=blank["label"],
                answers_json=json.dumps(blank["answers"], ensure_ascii=False),
                sort_order=index,
            )
        )
    return question


def question_to_json(question: Question) -> dict:
    options = sorted(question.options, key=lambda item: item.sort_order)
    blanks = sorted(question.blanks, key=lambda item: item.sort_order)
    return {
        "type": question.type,
        "stem": question.stem,
        "options": [
            {"label": option.label, "content": option.content, "is_correct": option.is_correct}
            for option in options
        ],
        "blanks": [
            {"label": blank.label, "answers": json.loads(blank.answers_json)}
            for blank in blanks
        ],
        "explanation": question.explanation,
        "difficulty": question.difficulty,
    }
