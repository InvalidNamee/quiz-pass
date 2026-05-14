from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.question_bank import QuestionBank, QuestionBankTag

MAX_TAGS_PER_BANK = 20
MAX_TAG_NAME_LENGTH = 32


def normalize_tag_names(tag_names: list[str] | None) -> list[str]:
    if not tag_names:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_name in tag_names:
        name = str(raw_name).strip()
        if not name:
            continue
        if len(name) > MAX_TAG_NAME_LENGTH:
            raise ValueError(f"标签不能超过 {MAX_TAG_NAME_LENGTH} 个字符")
        if name not in seen:
            normalized.append(name)
            seen.add(name)
    if len(normalized) > MAX_TAGS_PER_BANK:
        raise ValueError(f"单个题库最多 {MAX_TAGS_PER_BANK} 个标签")
    return normalized


def get_or_create_tags(db: Session, tag_names: list[str] | None) -> list[QuestionBankTag]:
    names = normalize_tag_names(tag_names)
    if not names:
        return []
    existing = db.scalars(select(QuestionBankTag).where(QuestionBankTag.name.in_(names))).all()
    by_name = {tag.name: tag for tag in existing}
    tags: list[QuestionBankTag] = []
    for name in names:
        tag = by_name.get(name)
        if not tag:
            tag = QuestionBankTag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def set_bank_tags(db: Session, bank: QuestionBank, tag_names: list[str] | None) -> None:
    bank.tags = get_or_create_tags(db, tag_names)


def merge_tag_names(*tag_name_groups: list[str] | None) -> list[str]:
    merged: list[str] = []
    for tag_names in tag_name_groups:
        merged.extend(tag_names or [])
    return normalize_tag_names(merged)
