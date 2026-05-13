from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def clamp_page(page: int, page_size: int) -> tuple[int, int]:
    return max(page, 1), min(max(page_size, 1), 100)


def paginate(db: Session, stmt: Select, page: int, page_size: int):
    page, page_size = clamp_page(page, page_size)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.limit(page_size).offset((page - 1) * page_size)).all()
    return items, total, page, page_size
