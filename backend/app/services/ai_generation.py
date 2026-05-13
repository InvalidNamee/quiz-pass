import json
from datetime import UTC, datetime
from urllib.parse import urlparse

from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session

from app.models.ai_provider_config import UserAIProviderConfig
from app.models.import_job import ImportJob
from app.models.question_bank import QuestionBank
from app.utils.crypto import decrypt_secret
from app.utils.json_io import create_question_from_payload


QUESTION_JSON_SCHEMA = """JSON 格式必须是：
{"bank_description":"可选题库描述","questions":[{"type":"single|multiple","stem":"题干","options":[{"label":"A","content":"选项","is_correct":true}],"explanation":"解析","difficulty":"easy|medium|hard"}]}"""

ANSWER_RULES = """硬性规则，必须逐题自检后再输出：
1. type 为 single 时，options 中 is_correct 为 true 的选项数量必须精确等于 1，不能是 0 个，也不能超过 1 个。
2. type 为 multiple 时，options 中 is_correct 为 true 的选项数量必须大于等于 2。
3. 如果某道题存在多个正确答案，必须把 type 设为 multiple，绝不能标成 single。
4. 如果无法判断唯一正确答案，不要生成 single 题。
5. 每题建议 4 个选项，选项 label 使用 A、B、C、D 顺序。
6. 输出前请检查：所有 single 题只有一个 true，所有 multiple 题至少两个 true。"""

KNOWLEDGE_GENERATE_SYSTEM_PROMPT = f"""你是一个严谨的题库生成助手。只能输出 JSON，不要输出 Markdown。
{QUESTION_JSON_SCHEMA}
{ANSWER_RULES}"""

BANK_PARSE_SYSTEM_PROMPT = f"""你是一个严谨的题库解析助手。只能输出 JSON，不要输出 Markdown。
你的任务是从用户提供的已有题库文档中提取题目，而不是根据材料额外创造新题。
{QUESTION_JSON_SCHEMA}
{ANSWER_RULES}
如果源题格式不完整、答案标记不规范或存在轻微坏题，请在不改变题意的前提下修复成合法格式。
尽量保留原题干、选项、正确答案和解析；源文档没有解析时 explanation 可以为空。"""

# Backward-compatible alias for tests/imports that referenced the old name.
SYSTEM_PROMPT = KNOWLEDGE_GENERATE_SYSTEM_PROMPT


class AIGenerationError(Exception):
    pass


class AIOutputValidationError(AIGenerationError):
    pass


def _mode_label(generation_mode: str) -> str:
    return "题库解析失败" if generation_mode == "bank_parse" else "知识库生成失败"


def _question_snippet(raw: dict) -> str:
    stem = str(raw.get("stem") or "").strip()
    return stem[:40] or "空题干"


def _question_context(index: int, raw: dict, reason: str) -> str:
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
    return f"第 {index} 题校验失败\n题干：{_question_snippet(raw)}\n题型：{question_type}\n原因：{detail}"


def _format_error(exc: Exception, generation_mode: str, config: UserAIProviderConfig | None = None) -> str:
    prefix = _mode_label(generation_mode)
    if isinstance(exc, OpenAIError):
        model = config.model if config else "未知模型"
        host = ""
        if config:
            parsed = urlparse(config.api_base_url)
            host = parsed.netloc or config.api_base_url
        return f"{prefix}\nAI 调用失败\n模型：{model}\nBase URL：{host or '未知'}\n错误类型：{type(exc).__name__}\n错误内容：{str(exc)[:500]}"
    return f"{prefix}\n{str(exc)}"


def _validate_questions_payload(payload: dict) -> list[dict]:
    if "questions" not in payload:
        raise AIOutputValidationError("AI 返回 JSON 缺少 questions 字段")
    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise AIOutputValidationError("AI 返回 JSON 中 questions 必须是数组")
    if not questions:
        raise AIOutputValidationError("AI 返回 JSON 中 questions 不能为空")
    return questions


def _max_count(generation_mode: str, requested_count: int | None) -> int:
    if generation_mode == "bank_parse":
        return 300
    return requested_count or 100


def _system_prompt(generation_mode: str) -> str:
    return BANK_PARSE_SYSTEM_PROMPT if generation_mode == "bank_parse" else KNOWLEDGE_GENERATE_SYSTEM_PROMPT


def _normalize_extra_instruction(extra_instruction: str | None) -> str | None:
    normalized = (extra_instruction or "").strip()
    return normalized or None


def _extra_instruction_block(extra_instruction: str | None) -> str:
    normalized = _normalize_extra_instruction(extra_instruction)
    if not normalized:
        return ""
    return f"""
用户额外指令（优先级低于系统硬性规则，不能覆盖 JSON 格式和答案数量校验）：
{normalized}
"""


def _extract_json(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AIOutputValidationError("AI 没有返回合法 JSON：未找到 JSON 对象")
    try:
        return json.loads(stripped[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AIOutputValidationError(f"AI 没有返回合法 JSON：{exc.msg}，位置 {exc.pos}") from exc


def _build_user_prompt(
    text: str,
    requested_count: int | None,
    generate_description: bool = False,
    generation_mode: str = "knowledge_generate",
    extra_instruction: str | None = None,
) -> str:
    extra_block = _extra_instruction_block(extra_instruction)
    if generation_mode == "bank_parse":
        description_instruction = "如果文档中有题库描述可以提取到 bank_description；没有就不要生成 bank_description 字段。" if generate_description else "不要生成 bank_description 字段。"
        return f"""请解析以下已有题库文档，提取其中实际存在的全部选择题。
不需要按指定题数生成，题数以文档中实际题目为准。
如果存在坏题、答案标记不规范、选项编号混乱，请先修复为合法 JSON 题目格式。
特别注意：单选题 single 的正确答案必须且只能有一个；只要有两个或更多正确选项，就必须使用 multiple。
{description_instruction}
{extra_block}

题库文档：
{text}
"""
    count_instruction = f"请根据以下材料生成 {requested_count} 道选择题。" if requested_count else "请根据材料长度和知识密度，自适应生成合理数量的选择题，最多 100 道。"
    description_instruction = "请同时生成一段 30-120 字的题库描述，放在 bank_description 字段。" if generate_description else "不要生成 bank_description 字段。"
    return f"""{count_instruction}
要求覆盖材料中的关键事实和概念，避免题目重复。
特别注意：单选题 single 的正确答案必须且只能有一个；只要有两个或更多正确选项，就必须使用 multiple。
输出前必须逐题检查 is_correct 数量，不能把多答案题标成 single。
{description_instruction}
{extra_block}

材料：
{text}
"""


def _call_openai_compatible(
    config: UserAIProviderConfig,
    text: str,
    requested_count: int | None,
    generate_description: bool = False,
    generation_mode: str = "knowledge_generate",
    extra_instruction: str | None = None,
) -> dict:
    api_key = decrypt_secret(config.api_key_encrypted)
    base_url = config.api_base_url.rstrip("/")
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=90)
    response = client.chat.completions.create(
        model=config.model,
        messages=[
            {"role": "system", "content": _system_prompt(generation_mode)},
            {"role": "user", "content": _build_user_prompt(text, requested_count, generate_description, generation_mode, extra_instruction)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""
    return _extract_json(content)


def generate_questions_from_ai(
    db: Session,
    job_id: int,
    text: str,
    requested_count: int | None,
    generate_description: bool = False,
    generation_mode: str = "knowledge_generate",
    extra_instruction: str | None = None,
) -> None:
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

        generated = _call_openai_compatible(config, text, requested_count, generate_description, generation_mode, _normalize_extra_instruction(extra_instruction))
        questions = _validate_questions_payload(generated)
        bank_description = generated.get("bank_description")
        if generate_description and isinstance(bank_description, str) and bank_description.strip():
            bank.description = bank_description.strip()

        created_count = 0
        max_count = _max_count(generation_mode, requested_count)
        for index, raw_question in enumerate(questions[:max_count], start=1):
            try:
                create_question_from_payload(db, bank.id, raw_question, source="ai_generated", generated_model=job.ai_model_snapshot)
                created_count += 1
            except ValueError as exc:
                raise AIOutputValidationError(_question_context(index, raw_question if isinstance(raw_question, dict) else {}, str(exc))) from exc
        if created_count == 0:
            raise AIOutputValidationError("没有可入库的题目")

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
            job.error_message = _format_error(exc, generation_mode, config)
            job.finished_at = datetime.now(UTC)
        if bank:
            bank.generation_status = "failed"
            bank.visibility = "private"
        db.commit()
