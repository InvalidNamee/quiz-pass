from app.models.question import Question, QuestionOption


def normalize_question_payload(raw: dict) -> dict:
    question_type = raw.get("type")
    if question_type not in {"single", "multiple"}:
        raise ValueError("题目类型必须是 single 或 multiple")
    stem = str(raw.get("stem") or "").strip()
    if not stem:
        raise ValueError("题干不能为空")
    options = raw.get("options")
    if not isinstance(options, list) or len(options) < 2:
        raise ValueError("每题至少需要两个选项")
    if len(options) > 26:
        raise ValueError("每题最多 26 个选项")
    normalized_options = []
    for index, option in enumerate(options):
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
    return {
        "type": question_type,
        "stem": stem,
        "options": normalized_options,
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
    return question


def question_to_json(question: Question) -> dict:
    return {
        "type": question.type,
        "stem": question.stem,
        "options": [
            {"label": option.label, "content": option.content, "is_correct": option.is_correct}
            for option in sorted(question.options, key=lambda item: item.sort_order)
        ],
        "explanation": question.explanation,
        "difficulty": question.difficulty,
    }
