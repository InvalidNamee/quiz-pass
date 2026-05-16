import json
from datetime import UTC, datetime
from typing import Literal, TypedDict
from urllib.parse import urlparse

from langgraph.graph import END, START, StateGraph
from openai import OpenAI, OpenAIError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.ai_provider_config import UserAIProviderConfig
from app.models.ai_workflow import AIGenerationDraft, AIGenerationDraftQuestion, AIGenerationWorkflow, AIGenerationWorkflowStep
from app.models.import_job import ImportJob
from app.models.question import Question
from app.models.question_bank import QuestionBank
from app.utils.crypto import decrypt_secret
from app.utils.json_io import create_question_from_payload, normalize_question_payload


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

REPAIR_SYSTEM_PROMPT = f"""你是题库 JSON 修复助手。只能输出完整 JSON，不要输出 Markdown。
根据后端校验错误修复用户给出的 JSON。不要解释，不要新增无关题目。
{QUESTION_JSON_SCHEMA}
{ANSWER_RULES}"""

SYSTEM_PROMPT = KNOWLEDGE_GENERATE_SYSTEM_PROMPT
MAX_REPAIR_ATTEMPTS = 2


class AIGenerationError(Exception):
    pass


class AIOutputValidationError(AIGenerationError):
    pass


class AIGenerationState(TypedDict, total=False):
    db: Session
    job_id: int
    workflow_id: int
    bank_id: int
    user_id: int
    config_id: int
    text: str
    context_text: str
    requested_count: int | None
    generate_description: bool
    generation_mode: str
    extra_instruction: str | None
    raw_payload: dict
    repaired_payload: dict
    payload: dict
    questions: list[dict]
    bank_description: str | None
    validation_summary: str
    validation_error: str | None
    repair_attempts: int
    error_message: str | None
    route: str


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _now() -> datetime:
    return datetime.now(UTC)


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


def _format_error(exc: Exception | str, generation_mode: str, config: UserAIProviderConfig | None = None, repair_attempts: int = 0) -> str:
    prefix = _mode_label(generation_mode)
    if isinstance(exc, OpenAIError):
        model = config.model if config else "未知模型"
        host = ""
        if config:
            parsed = urlparse(config.api_base_url)
            host = parsed.netloc or config.api_base_url
        return f"{prefix}\nAI 调用失败\n模型：{model}\nBase URL：{host or '未知'}\n错误类型：{type(exc).__name__}\n错误内容：{str(exc)[:500]}"
    retry_line = f"\n已自动修复 {repair_attempts} 次仍失败" if repair_attempts else ""
    return f"{prefix}{retry_line}\n{str(exc)}"


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


def _build_repair_prompt(payload: dict, validation_error: str) -> str:
    return f"""后端校验发现以下错误，请修复 JSON 后完整返回：

校验错误：
{validation_error}

原始 JSON：
{_json_dumps(payload)}
"""


def _call_openai_compatible(
    config: UserAIProviderConfig,
    text: str,
    requested_count: int | None,
    generate_description: bool = False,
    generation_mode: str = "knowledge_generate",
    extra_instruction: str | None = None,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
) -> dict:
    api_key = decrypt_secret(config.api_key_encrypted)
    base_url = config.api_base_url.rstrip("/")
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=90)
    response = client.chat.completions.create(
        model=config.model,
        messages=[
            {"role": "system", "content": system_prompt or _system_prompt(generation_mode)},
            {"role": "user", "content": user_prompt or _build_user_prompt(text, requested_count, generate_description, generation_mode, extra_instruction)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""
    return _extract_json(content)


def validate_generated_payload(payload: dict, generation_mode: str, requested_count: int | None) -> tuple[list[dict], str]:
    questions = _validate_questions_payload(payload)
    max_count = _max_count(generation_mode, requested_count)
    normalized: list[dict] = []
    for index, raw_question in enumerate(questions[:max_count], start=1):
        try:
            if not isinstance(raw_question, dict):
                raise ValueError("题目必须是对象")
            normalized.append(normalize_question_payload(raw_question))
        except ValueError as exc:
            raise AIOutputValidationError(_question_context(index, raw_question if isinstance(raw_question, dict) else {}, str(exc))) from exc
    if not normalized:
        raise AIOutputValidationError("没有可入库的题目")
    return normalized, f"校验通过，共 {len(normalized)} 道题"


def _set_status(db: Session, workflow: AIGenerationWorkflow, job: ImportJob, bank: QuestionBank, status: str) -> None:
    workflow.status = status
    job.status = status
    if status in {"pending", "extracting_document", "calling_model", "validating", "repairing", "draft_ready"}:
        bank.generation_status = "processing"
    elif status == "imported":
        bank.generation_status = "succeeded"
    elif status in {"failed", "cancelled"}:
        bank.generation_status = "failed"
    db.flush()


def _record_step(db: Session, workflow_id: int, step_name: str, status: str, input_data=None, output_data=None, error_message: str | None = None) -> None:
    now = _now()
    db.add(
        AIGenerationWorkflowStep(
            workflow_id=workflow_id,
            step_name=step_name,
            status=status,
            input_json=_json_dumps(input_data) if input_data is not None else None,
            output_json=_json_dumps(output_data) if output_data is not None else None,
            error_message=error_message,
            started_at=now,
            finished_at=now,
        )
    )
    db.flush()


def _existing_bank_context(db: Session, bank: QuestionBank, workflow: AIGenerationWorkflow) -> str:
    if workflow.purpose != "extend_bank":
        return ""
    stems = db.scalars(select(Question.stem).where(Question.bank_id == bank.id).limit(80)).all()
    previous = db.scalars(
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
题库标签：{', '.join(tag_names) or '无'}
当前模型：{bank.ai_model_name or '无'}
最近成功 workflow：
{chr(10).join(previous_lines) or '无'}
已有题目摘要：
{chr(10).join(stem_lines) or '无'}
"""


def _load_objects(state: AIGenerationState):
    db = state["db"]
    job = db.get(ImportJob, state["job_id"])
    workflow = db.get(AIGenerationWorkflow, state["workflow_id"])
    bank = db.get(QuestionBank, state["bank_id"])
    config = db.get(UserAIProviderConfig, state["config_id"])
    if not job or not workflow or not bank or not config:
        raise AIGenerationError("生成任务、workflow、题库或 AI 配置不存在")
    return db, job, workflow, bank, config


def _extract_document_node(state: AIGenerationState) -> AIGenerationState:
    db, job, workflow, bank, _ = _load_objects(state)
    _set_status(db, workflow, job, bank, "extracting_document")
    _record_step(db, workflow.id, "extract_document", "succeeded", {"file_name": workflow.source_file_name}, {"text_length": len(state["text"])})
    db.commit()
    return {"text": state["text"], "route": "ok"}


def _build_context_node(state: AIGenerationState) -> AIGenerationState:
    db, _, workflow, bank, _ = _load_objects(state)
    context = _existing_bank_context(db, bank, workflow)
    context_text = f"{context}\n\n{state['text']}" if context else state["text"]
    _record_step(db, workflow.id, "build_context", "succeeded", {"purpose": workflow.purpose}, {"context_length": len(context_text)})
    db.commit()
    return {"context_text": context_text}


def _generate_or_parse_node(state: AIGenerationState) -> AIGenerationState:
    db, job, workflow, bank, config = _load_objects(state)
    try:
        _set_status(db, workflow, job, bank, "calling_model")
        db.commit()
        payload = _call_openai_compatible(
            config,
            state.get("context_text") or state["text"],
            state.get("requested_count"),
            state.get("generate_description", False),
            state.get("generation_mode", "knowledge_generate"),
            state.get("extra_instruction"),
        )
        _record_step(db, workflow.id, "generate_or_parse", "succeeded", {"mode": workflow.generation_mode}, {"payload": payload})
        db.commit()
        return {"raw_payload": payload, "payload": payload, "route": "ok"}
    except Exception as exc:
        message = _format_error(exc, workflow.generation_mode, config)
        _record_step(db, workflow.id, "generate_or_parse", "failed", {"mode": workflow.generation_mode}, error_message=message)
        db.commit()
        return {"validation_error": message, "error_message": message, "route": "fail"}


def _validate_payload_node(state: AIGenerationState) -> AIGenerationState:
    db, job, workflow, bank, _ = _load_objects(state)
    payload = state.get("payload") or {}
    try:
        _set_status(db, workflow, job, bank, "validating")
        questions, summary = validate_generated_payload(payload, workflow.generation_mode, workflow.requested_count)
        bank_description = payload.get("bank_description")
        _record_step(db, workflow.id, "validate_payload", "succeeded", {"payload": payload}, {"summary": summary})
        db.commit()
        return {
            "questions": questions,
            "bank_description": bank_description.strip() if isinstance(bank_description, str) and bank_description.strip() else None,
            "validation_summary": summary,
            "validation_error": None,
            "route": "draft",
        }
    except Exception as exc:
        message = str(exc)
        attempts = state.get("repair_attempts", 0)
        _record_step(db, workflow.id, "validate_payload", "failed", {"payload": payload}, error_message=message)
        db.commit()
        return {"validation_error": message, "route": "repair" if attempts < MAX_REPAIR_ATTEMPTS else "fail"}


def _repair_payload_node(state: AIGenerationState) -> AIGenerationState:
    db, job, workflow, bank, config = _load_objects(state)
    attempts = state.get("repair_attempts", 0) + 1
    payload = state.get("payload") or state.get("raw_payload") or {}
    try:
        _set_status(db, workflow, job, bank, "repairing")
        workflow.repair_attempts = attempts
        job.error_message = f"正在自动修复第 {attempts} 次：{state.get('validation_error')}"
        db.commit()
        repaired = _call_openai_compatible(
            config,
            state.get("context_text") or state["text"],
            state.get("requested_count"),
            state.get("generate_description", False),
            workflow.generation_mode,
            state.get("extra_instruction"),
            system_prompt=REPAIR_SYSTEM_PROMPT,
            user_prompt=_build_repair_prompt(payload, state.get("validation_error") or "未知错误"),
        )
        _record_step(db, workflow.id, "repair_payload", "succeeded", {"attempt": attempts, "error": state.get("validation_error")}, {"payload": repaired})
        db.commit()
        return {"payload": repaired, "repaired_payload": repaired, "repair_attempts": attempts, "route": "ok"}
    except Exception as exc:
        message = _format_error(exc, workflow.generation_mode, config)
        _record_step(db, workflow.id, "repair_payload", "failed", {"attempt": attempts}, error_message=message)
        db.commit()
        return {"validation_error": message, "error_message": message, "repair_attempts": attempts, "route": "fail"}


def _write_draft_node(state: AIGenerationState) -> AIGenerationState:
    db, job, workflow, bank, _ = _load_objects(state)
    raw_payload = state.get("raw_payload") or state.get("payload") or {}
    repaired_payload = state.get("repaired_payload") or state.get("payload") or {}
    db.execute(delete(AIGenerationDraft).where(AIGenerationDraft.job_id == job.id))
    draft = AIGenerationDraft(
        workflow_id=workflow.id,
        job_id=job.id,
        bank_id=bank.id,
        user_id=workflow.user_id,
        bank_description=state.get("bank_description") if state.get("generate_description") else None,
        raw_payload_json=_json_dumps(raw_payload),
        repaired_payload_json=_json_dumps(repaired_payload),
        validation_summary=state.get("validation_summary"),
        status="ready",
    )
    db.add(draft)
    db.flush()
    for index, question in enumerate(state.get("questions") or [], start=1):
        db.add(
            AIGenerationDraftQuestion(
                draft_id=draft.id,
                sort_order=index,
                type=question["type"],
                stem=question["stem"],
                explanation=question.get("explanation"),
                difficulty=question.get("difficulty"),
                options_json=_json_dumps(question["options"]),
                validation_status="valid",
            )
        )
    _set_status(db, workflow, job, bank, "draft_ready")
    workflow.error_message = None
    job.error_message = None
    workflow.finished_at = _now()
    job.finished_at = _now()
    _record_step(db, workflow.id, "write_draft", "succeeded", output_data={"draft_id": draft.id, "question_count": len(state.get("questions") or [])})
    db.commit()
    return {"route": "done"}


def _fail_node(state: AIGenerationState) -> AIGenerationState:
    db, job, workflow, bank, config = _load_objects(state)
    attempts = state.get("repair_attempts", workflow.repair_attempts)
    message = state.get("error_message") or _format_error(state.get("validation_error") or "生成失败", workflow.generation_mode, config, attempts)
    if state.get("validation_error") and attempts >= MAX_REPAIR_ATTEMPTS:
        message = _format_error(state["validation_error"], workflow.generation_mode, config, attempts)
    workflow.status = "failed"
    workflow.repair_attempts = attempts
    workflow.error_message = message
    workflow.finished_at = _now()
    job.status = "failed"
    job.error_message = message
    job.finished_at = _now()
    bank.generation_status = "failed"
    if workflow.purpose == "create_bank":
        bank.visibility = "private"
    _record_step(db, workflow.id, "fail", "failed", error_message=message)
    db.commit()
    return {"error_message": message, "route": "done"}


def _route_after_generation(state: AIGenerationState) -> Literal["validate_payload", "fail"]:
    return "fail" if state.get("route") == "fail" else "validate_payload"


def _route_after_validate(state: AIGenerationState) -> Literal["repair_payload", "write_draft", "fail"]:
    if state.get("route") == "draft":
        return "write_draft"
    if state.get("route") == "repair":
        return "repair_payload"
    return "fail"


def _route_after_repair(state: AIGenerationState) -> Literal["validate_payload", "fail"]:
    return "fail" if state.get("route") == "fail" else "validate_payload"


def _build_graph():
    graph = StateGraph(AIGenerationState)
    graph.add_node("extract_document", _extract_document_node)
    graph.add_node("build_context", _build_context_node)
    graph.add_node("generate_or_parse", _generate_or_parse_node)
    graph.add_node("validate_payload", _validate_payload_node)
    graph.add_node("repair_payload", _repair_payload_node)
    graph.add_node("write_draft", _write_draft_node)
    graph.add_node("fail", _fail_node)
    graph.add_edge(START, "extract_document")
    graph.add_edge("extract_document", "build_context")
    graph.add_edge("build_context", "generate_or_parse")
    graph.add_conditional_edges("generate_or_parse", _route_after_generation)
    graph.add_conditional_edges("validate_payload", _route_after_validate)
    graph.add_conditional_edges("repair_payload", _route_after_repair)
    graph.add_edge("write_draft", END)
    graph.add_edge("fail", END)
    return graph.compile()


AI_GENERATION_GRAPH = _build_graph()


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
    workflow = db.get(AIGenerationWorkflow, job.workflow_id) if job.workflow_id else None
    config = db.get(UserAIProviderConfig, job.ai_provider_config_id) if job.ai_provider_config_id else None
    if not bank or not workflow or not config:
        return
    if job.status == "cancelled":
        return
    job.started_at = _now()
    workflow.source_text_snapshot = workflow.source_text_snapshot or text
    db.commit()
    AI_GENERATION_GRAPH.invoke(
        {
            "db": db,
            "job_id": job.id,
            "workflow_id": workflow.id,
            "bank_id": bank.id,
            "user_id": workflow.user_id,
            "config_id": config.id,
            "text": workflow.source_text_snapshot or text,
            "requested_count": requested_count,
            "generate_description": generate_description,
            "generation_mode": generation_mode,
            "extra_instruction": _normalize_extra_instruction(extra_instruction),
            "repair_attempts": 0,
        }
    )


def draft_to_payload(draft: AIGenerationDraft) -> dict:
    questions = []
    for question in sorted(draft.questions, key=lambda item: item.sort_order):
        questions.append(
            {
                "id": question.id,
                "type": question.type,
                "stem": question.stem,
                "explanation": question.explanation,
                "difficulty": question.difficulty,
                "options": json.loads(question.options_json),
                "validation_status": question.validation_status,
                "validation_message": question.validation_message,
            }
        )
    return {
        "id": draft.id,
        "workflow_id": draft.workflow_id,
        "job_id": draft.job_id,
        "bank_id": draft.bank_id,
        "bank_description": draft.bank_description,
        "validation_summary": draft.validation_summary,
        "status": draft.status,
        "questions": questions,
    }


def replace_draft_questions(db: Session, draft: AIGenerationDraft, bank_description: str | None, questions: list[dict]) -> None:
    normalized_questions = []
    for index, raw_question in enumerate(questions, start=1):
        try:
            normalized_questions.append(normalize_question_payload(raw_question))
        except ValueError as exc:
            raise AIOutputValidationError(_question_context(index, raw_question if isinstance(raw_question, dict) else {}, str(exc))) from exc
    if not normalized_questions:
        raise AIOutputValidationError("草稿题目不能为空")
    draft.bank_description = (bank_description or "").strip() or None
    draft.validation_summary = f"校验通过，共 {len(normalized_questions)} 道题"
    db.execute(delete(AIGenerationDraftQuestion).where(AIGenerationDraftQuestion.draft_id == draft.id))
    db.flush()
    for index, question in enumerate(normalized_questions, start=1):
        db.add(
            AIGenerationDraftQuestion(
                draft_id=draft.id,
                sort_order=index,
                type=question["type"],
                stem=question["stem"],
                explanation=question.get("explanation"),
                difficulty=question.get("difficulty"),
                options_json=_json_dumps(question["options"]),
                validation_status="valid",
            )
        )


def confirm_draft(db: Session, job: ImportJob, draft: AIGenerationDraft) -> QuestionBank:
    workflow = db.get(AIGenerationWorkflow, draft.workflow_id)
    bank = db.get(QuestionBank, draft.bank_id)
    if not workflow or not bank:
        raise AIGenerationError("草稿关联的 workflow 或题库不存在")
    payload = draft_to_payload(draft)
    questions, _ = validate_generated_payload({"questions": payload["questions"]}, workflow.generation_mode, workflow.requested_count)
    for question in questions:
        create_question_from_payload(db, bank.id, question, source="ai_generated", generated_model=job.ai_model_snapshot)
    bank.question_count += len(questions)
    if draft.bank_description:
        bank.description = draft.bank_description
    bank.generation_status = "succeeded"
    if workflow.purpose == "create_bank":
        bank.visibility = bank.desired_visibility if bank.question_count > 0 else "private"
    bank.ai_model_name = job.ai_model_snapshot
    workflow.status = "imported"
    workflow.finished_at = _now()
    job.status = "imported"
    job.finished_at = _now()
    draft.status = "imported"
    _record_step(db, workflow.id, "confirm_draft", "succeeded", output_data={"question_count": len(questions)})
    return bank
