import json


QUESTION_JSON_SCHEMA = """JSON 格式必须是：
{"bank_description":"可选题库描述","questions":[{"type":"single|multiple","stem":"题干","options":[{"label":"A","content":"选项","is_correct":true}],"explanation":"解析","difficulty":"easy|medium|hard"}]}"""

ANSWER_RULES = """硬性规则，必须逐题自检后再输出：
1. type 为 single 时，options 中 is_correct 为 true 的选项数量必须精确等于 1，不能是 0 个，也不能超过 1 个。
2. type 为 multiple 时，options 中 is_correct 为 true 的选项数量必须大于等于 2。
3. 如果某道题存在多个正确答案，必须把 type 设为 multiple，绝不能标成 single。
4. 如果无法判断唯一正确答案，不要生成 single 题。
5. 每题建议 4 个选项，选项 label 使用 A、B、C、D 顺序。
6. 输出前请检查：所有 single 题只有一个 true，所有 multiple 题至少两个 true。"""


class PromptBuilder:
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

    @staticmethod
    def normalize_extra_instruction(extra_instruction: str | None) -> str | None:
        normalized = (extra_instruction or "").strip()
        return normalized or None

    @classmethod
    def system_prompt(cls, generation_mode: str) -> str:
        return cls.BANK_PARSE_SYSTEM_PROMPT if generation_mode == "bank_parse" else cls.KNOWLEDGE_GENERATE_SYSTEM_PROMPT

    @classmethod
    def build_generation_prompt(
        cls,
        text: str,
        requested_count: int | None,
        generate_description: bool = False,
        generation_mode: str = "knowledge_generate",
        extra_instruction: str | None = None,
    ) -> str:
        extra_block = cls.extra_instruction_block(extra_instruction)
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

    @staticmethod
    def build_repair_prompt(payload: dict, validation_error: str) -> str:
        return f"""后端校验发现以下错误，请修复 JSON 后完整返回：

校验错误：
{validation_error}

原始 JSON：
{json.dumps(payload, ensure_ascii=False, default=str)}
"""

    @classmethod
    def extra_instruction_block(cls, extra_instruction: str | None) -> str:
        normalized = cls.normalize_extra_instruction(extra_instruction)
        if not normalized:
            return ""
        return f"""
用户额外指令（优先级低于系统硬性规则，不能覆盖 JSON 格式和答案数量校验）：
{normalized}
"""
