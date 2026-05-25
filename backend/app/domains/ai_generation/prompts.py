import json


QUESTION_JSON_SCHEMA = """JSON 格式必须是：
{"bank_description":"可选题库描述","questions":[{"type":"single|multiple|blank|short_answer","stem":"题干","options":[{"label":"A","content":"选项","is_correct":true}],"blanks":[{"label":"1","answers":["答案1","答案2"]}],"explanation":"解析或给分点","difficulty":"easy|medium|hard"}]}
所有题目都必须包含 options 和 blanks 字段；不用的字段输出空数组。"""

ANSWER_RULES = """硬性规则，必须逐题自检后再输出：
1. type 为 single 时，options 中 is_correct 为 true 的选项数量必须精确等于 1，不能是 0 个，也不能超过 1 个。
2. type 为 multiple 时，options 中 is_correct 为 true 的选项数量必须大于等于 2。
3. 如果某道题存在多个正确答案，必须把 type 设为 multiple，绝不能标成 single。
4. type 为 blank 时，题干必须使用 {{1}}、{{2}} 这类占位符标出每个空；blanks 必须和占位符一一对应；每个空 answers 至少一个可接受答案。
5. type 为 short_answer 时，不要生成标准答案；options 和 blanks 必须为空数组；必须在 explanation 中写清楚给分点。
6. 如果无法判断唯一正确答案，不要生成 single 题。
7. 选择题建议 4 个选项，选项 label 使用 A、B、C、D 顺序。
8. 输出前请检查：所有 single 题只有一个 true，所有 multiple 题至少两个 true，所有 blank 题占位符和 blanks 匹配。"""

QUESTION_TYPE_LABELS = {
    "single": "单选",
    "multiple": "多选",
    "blank": "填空",
    "short_answer": "简答",
}

FORMULA_RULES = """公式规则：
1. 题干、选项和解析中的公式必须保留为纯文本 LaTeX。
2. 行内公式必须使用 \\(...\\)，块级公式必须使用 \\[...\\]。
3. 禁止输出 Markdown 公式围栏，禁止把公式转成图片、HTML、MathML 或自然语言替代。
4. JSON 字符串中的反斜杠必须按 JSON 规则正确转义，不能吞掉反斜杠。"""


class PromptBuilder:
    KNOWLEDGE_GENERATE_SYSTEM_PROMPT = f"""你是一个严谨的题库生成助手。只能输出 JSON，不要输出 Markdown。
{QUESTION_JSON_SCHEMA}
{ANSWER_RULES}
{FORMULA_RULES}"""

    BANK_PARSE_SYSTEM_PROMPT = f"""你是一个严谨的题库解析助手。只能输出 JSON，不要输出 Markdown。
你的任务是从用户提供的已有题库文档中提取题目，而不是根据材料额外创造新题。
{QUESTION_JSON_SCHEMA}
{ANSWER_RULES}
{FORMULA_RULES}
如果源题格式不完整、答案标记不规范或存在轻微坏题，请在不改变题意的前提下修复成合法格式。
尽量保留原题干、选项、正确答案和解析；源文档没有解析时 explanation 可以为空。"""

    REPAIR_SYSTEM_PROMPT = f"""你是题库 JSON 修复助手。只能输出完整 JSON，不要输出 Markdown。
根据后端校验错误修复用户给出的 JSON。不要解释，不要新增无关题目。
{QUESTION_JSON_SCHEMA}
{ANSWER_RULES}
{FORMULA_RULES}"""

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
        question_type_settings: dict | None = None,
    ) -> str:
        extra_block = cls.extra_instruction_block(extra_instruction)
        type_instruction = cls.question_type_instruction(generation_mode, question_type_settings)
        if generation_mode == "bank_parse":
            description_instruction = "如果文档中有题库描述可以提取到 bank_description；没有就不要生成 bank_description 字段。" if generate_description else "不要生成 bank_description 字段。"
            return f"""请解析以下已有题库文档，提取其中实际存在的全部选择题、填空题和简答题。
不需要按指定题数生成，题数以文档中实际题目为准。
如果存在坏题、答案标记不规范、选项编号混乱，请先修复为合法 JSON 题目格式。
特别注意：单选题 single 的正确答案必须且只能有一个；只要有两个或更多正确选项，就必须使用 multiple。
{type_instruction}
{description_instruction}
{extra_block}

题库文档：
{text}
"""
        count_instruction = f"请根据以下材料生成 {requested_count} 道选择题、填空题或简答题。" if requested_count else "请根据材料长度和知识密度，自适应生成合理数量的选择题、填空题或简答题，最多 100 道。"
        description_instruction = "请同时生成一段 30-120 字的题库描述，放在 bank_description 字段。" if generate_description else "不要生成 bank_description 字段。"
        return f"""{count_instruction}
要求覆盖材料中的关键事实和概念，避免题目重复。
特别注意：单选题 single 的正确答案必须且只能有一个；只要有两个或更多正确选项，就必须使用 multiple。
输出前必须逐题检查 is_correct 数量，不能把多答案题标成 single。
{type_instruction}
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

    @staticmethod
    def question_type_instruction(generation_mode: str, question_type_settings: dict | None) -> str:
        if not question_type_settings:
            return "允许题型：single 单选、multiple 多选、blank 填空、short_answer 简答。"
        enabled: list[str] = []
        fixed: list[str] = []
        adaptive: list[str] = []
        for key, label in QUESTION_TYPE_LABELS.items():
            config = question_type_settings.get(key) if isinstance(question_type_settings, dict) else None
            if not isinstance(config, dict) or not config.get("enabled"):
                continue
            enabled.append(f"{key}（{label}）")
            count = config.get("count")
            if generation_mode == "knowledge_generate" and isinstance(count, int) and count > 0:
                fixed.append(f"{label} {count} 道")
            elif generation_mode == "knowledge_generate":
                adaptive.append(label)
        if generation_mode == "bank_parse":
            return f"只解析以下题型：{'、'.join(enabled)}；文档中的其他题型请忽略。"
        parts = [f"只生成以下题型：{'、'.join(enabled)}。"]
        if fixed:
            parts.append(f"固定数量：{'、'.join(fixed)}。")
        if adaptive:
            parts.append(f"以下题型数量由 AI 自适应：{'、'.join(adaptive)}。")
        return "\n".join(parts)
