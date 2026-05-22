import json
from urllib.parse import urlparse

from openai import OpenAI, OpenAIError

from app.domains.ai_generation.errors import AIOutputValidationError
from app.domains.ai_generation.prompts import PromptBuilder
from app.models.ai_provider_config import UserAIProviderConfig
from app.utils.crypto import decrypt_secret


AI_RESPONSE_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "bank_description": {"type": ["string", "null"]},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "type": {"type": "string", "enum": ["single", "multiple"]},
                    "stem": {"type": "string"},
                    "explanation": {"type": ["string", "null"]},
                    "difficulty": {"type": ["string", "null"]},
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "label": {"type": "string"},
                                "content": {"type": "string"},
                                "is_correct": {"type": "boolean"},
                            },
                            "required": ["label", "content", "is_correct"],
                        },
                    },
                },
                "required": ["type", "stem", "explanation", "difficulty", "options"],
            },
        },
    },
    "required": ["bank_description", "questions"],
}


def build_response_format(config: UserAIProviderConfig) -> dict:
    if config.response_format_type == "json_schema":
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "quiz_pass_question_bank",
                "strict": True,
                "schema": AI_RESPONSE_JSON_SCHEMA,
            },
        }
    return {"type": "json_object"}


class OpenAICompatibleClient:
    def generate_json(
        self,
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
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=1200)
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system_prompt or PromptBuilder.system_prompt(generation_mode)},
                {
                    "role": "user",
                    "content": user_prompt
                    or PromptBuilder.build_generation_prompt(text, requested_count, generate_description, generation_mode, extra_instruction),
                },
            ],
            temperature=0.2,
            response_format=build_response_format(config),
        )
        content = response.choices[0].message.content or ""
        return extract_json(content)


def extract_json(text: str) -> dict:
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


def format_ai_error(exc: Exception | str, generation_mode: str, config: UserAIProviderConfig | None = None, repair_attempts: int = 0) -> str:
    prefix = "题库解析失败" if generation_mode == "bank_parse" else "知识库生成失败"
    if isinstance(exc, OpenAIError):
        model = config.model if config else "未知模型"
        host = ""
        if config:
            parsed = urlparse(config.api_base_url)
            host = parsed.netloc or config.api_base_url
        return f"{prefix}\nAI 调用失败\n模型：{model}\nBase URL：{host or '未知'}\n错误类型：{type(exc).__name__}\n错误内容：{str(exc)[:500]}"
    retry_line = f"\n已自动修复 {repair_attempts} 次仍失败" if repair_attempts else ""
    return f"{prefix}{retry_line}\n{str(exc)}"
