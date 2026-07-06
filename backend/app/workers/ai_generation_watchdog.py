from app.db.session import SessionLocal
from app.domains.ai_generation.watchdog import fail_stale_workflows


def main() -> None:
    db = SessionLocal()
    try:
        count = fail_stale_workflows(db)
        print(f"Marked {count} stale AI workflows as failed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
