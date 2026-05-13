import json
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from app.models.ai_provider_config import UserAIProviderConfig
from app.models.import_job import ImportJob
from app.models.question_bank import QuestionBank
from app.utils.crypto import decrypt_secret
from app.utils.json_io import create_question_from_payload


SYSTEM_PROMPT = """你是一个严谨的题库生成助手。只能输出 JSON，不要输出 Markdown。
JSON 格式必须是：
{"questions":[{"type":"single|multiple","stem":"题干","options":[{"label":"A","content":"选项","is_correct":true}],"explanation":"解析","difficulty":"easy|medium|hard"}]}
单选题必须且只能有一个正确选项；多选题至少两个正确选项；每题建议 4 个选项。"""


def _extract_json(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("AI 没有返回合法 JSON")
    return json.loads(stripped[start : end + 1])


def _build_user_prompt(text: str, requested_count: int | None) -> str:
    count_instruction = f"请根据以下材料生成 {requested_count} 道选择题。" if requested_count else "请根据材料长度和知识密度，自适应生成合理数量的选择题，最多 50 道。"
    return f"""{count_instruction}
要求覆盖材料中的关键事实和概念，避免题目重复。

材料：
{text}
"""


def _call_openai_compatible(config: UserAIProviderConfig, text: str, requested_count: int | None) -> dict:
    api_key = decrypt_secret(config.api_key_encrypted)
    base_url = config.api_base_url.rstrip("/")
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(text, requested_count)},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=90) as client:
        response = client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    content = data["choices"][0]["message"]["content"]
    return _extract_json(content)


def generate_questions_from_ai(db: Session, job_id: int, text: str, requested_count: int | None) -> None:
    job = db.get(ImportJob, job_id)
    if not job or not job.bank_id:
        return
    bank = db.get(QuestionBank, job.bank_id)
    config = db.get(UserAIProviderConfig, job.ai_provider_config_id) if job.ai_provider_config_id else None
    if not bank or not config:
        return

    try:
        job.status = "processing"
        bank.generation_status = "processing"
        job.started_at = datetime.now(UTC)
        db.commit()

        generated = _call_openai_compatible(config, text, requested_count)
        questions = generated.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError("AI 返回的 questions 不能为空")

        created_count = 0
        max_count = requested_count or 50
        for raw_question in questions[:max_count]:
            create_question_from_payload(db, bank.id, raw_question, source="ai_generated", generated_model=job.ai_model_snapshot)
            created_count += 1
        if created_count == 0:
            raise ValueError("没有可入库的题目")

        bank.question_count += created_count
        bank.generation_status = "succeeded"
        bank.visibility = bank.desired_visibility if bank.question_count > 0 else "private"
        bank.ai_model_name = job.ai_model_snapshot
        job.status = "succeeded"
        job.finished_at = datetime.now(UTC)
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(ImportJob, job_id)
        bank = db.get(QuestionBank, job.bank_id) if job and job.bank_id else None
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            job.finished_at = datetime.now(UTC)
        if bank:
            bank.generation_status = "failed"
            bank.visibility = "private"
        db.commit()
