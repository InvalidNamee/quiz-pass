import json
import os
from pathlib import Path

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_quiz_pass.db"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["APP_ENV"] = "test"
Path("test_quiz_pass.db").unlink(missing_ok=True)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
command.upgrade(alembic_cfg, "head")

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import AuditEvent  # noqa: E402
from app.models.ai_workflow import AIGenerationDraft, AIGenerationWorkflow, AIGenerationWorkflowStep, AIGenerationDraftQuestion  # noqa: E402
from app.models.import_job import ImportJob  # noqa: E402
from app.models.practice import MistakeAttempt, MistakeRecord, PracticeAnswer, PracticeSession, PracticeSessionQuestion  # noqa: E402
from app.models.question import Question, QuestionOption  # noqa: E402
from app.models.question_bank import QuestionBank, QuestionBankFavorite, question_bank_tag_links  # noqa: E402
from app.models.user import EmailAuthToken, User  # noqa: E402
from app.core.config import get_settings  # noqa: E402
import app.infrastructure.email as email_delivery  # noqa: E402


def _register(client: TestClient, email: str, username: str) -> dict[str, str]:
    response = client.post("/api/v2/auth/register", json={"email": email, "username": username, "password": "password123"})
    assert response.status_code == 200, response.text
    token = response.json()["debug_token"]
    verified = client.get(f"/api/v2/auth/verify-email?token={token}")
    assert verified.status_code == 200, verified.text
    login = client.post("/api/v2/auth/login", json={"identifier": username, "password": "password123"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _login(client: TestClient, identifier: str, password: str = "password123") -> dict[str, str]:
    response = client.post("/api/v2/auth/login", json={"identifier": identifier, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _make_admin(username: str) -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None
        user.role = "admin"
        db.commit()
    finally:
        db.close()


def _sample_question_payload(stem: str = "示例题") -> dict:
    return {
        "type": "single",
        "stem": stem,
        "explanation": "解析",
        "options": [
            {"label": "A", "content": "正确", "is_correct": True},
            {"label": "B", "content": "错误", "is_correct": False},
        ],
    }


def _multiple_question_payload(stem: str = "多选示例题") -> dict:
    return {
        "type": "multiple",
        "stem": stem,
        "explanation": "解析",
        "options": [
            {"label": "A", "content": "正确 1", "is_correct": True},
            {"label": "B", "content": "正确 2", "is_correct": True},
            {"label": "C", "content": "错误", "is_correct": False},
        ],
    }


def _question_payload_with_option_count(count: int, stem: str = "多选项题") -> dict:
    return {
        "type": "single",
        "stem": stem,
        "options": [
            {
                "label": chr(65 + index) if index < 26 else f"X{index}",
                "content": f"选项 {index + 1}",
                "is_correct": index == 0,
            }
            for index in range(count)
        ],
    }


def _blank_question_payload(stem: str = "TCP 位于 OSI 的 {{1}} 层") -> dict:
    return {
        "type": "blank",
        "stem": stem,
        "options": [],
        "blanks": [{"label": "1", "answers": ["传输层", "Transport Layer"]}],
        "explanation": "TCP 属于传输层。",
    }


def _short_answer_question_payload(stem: str = "简述反向传播的核心思想") -> dict:
    return {
        "type": "short_answer",
        "stem": stem,
        "options": [],
        "blanks": [],
        "explanation": "给分点：链式法则、误差反向传播、参数更新。",
    }


def _create_shareable_bank(client: TestClient, headers: dict[str, str], title: str = "Share Source", tag_names: list[str] | None = None) -> dict:
    bank = client.post("/api/v2/banks", headers=headers, json={"title": title, "visibility": "private", "tag_names": tag_names or []})
    assert bank.status_code == 200, bank.text
    created = client.post(f"/api/v2/banks/{bank.json()['id']}/questions", headers=headers, json=_sample_question_payload(f"{title} Q"))
    assert created.status_code == 200, created.text
    return bank.json()


def _share_bank(client: TestClient, headers: dict[str, str], bank_id: int) -> dict:
    shared = client.post(f"/api/v2/banks/{bank_id}/share", headers=headers)
    assert shared.status_code == 200, shared.text
    return shared.json()


def _fk_ondelete(model, column_name: str) -> str | None:
    column = model.__table__.c[column_name]
    foreign_key = next(iter(column.foreign_keys))
    return foreign_key.ondelete


def test_database_model_removes_workflow_job_cycle_and_uses_cascades():
    assert "job_id" not in AIGenerationWorkflow.__table__.c
    assert "job_id" not in AIGenerationDraft.__table__.c
    assert "active_generation_job_id" not in QuestionBank.__table__.c

    assert _fk_ondelete(ImportJob, "workflow_id") == "CASCADE"
    assert _fk_ondelete(ImportJob, "bank_id") == "SET NULL"
    assert _fk_ondelete(Question, "bank_id") == "CASCADE"
    assert _fk_ondelete(QuestionOption, "question_id") == "CASCADE"
    assert _fk_ondelete(QuestionBankFavorite, "bank_id") == "CASCADE"
    assert next(iter(question_bank_tag_links.c.bank_id.foreign_keys)).ondelete == "CASCADE"
    assert _fk_ondelete(PracticeSession, "bank_id") == "CASCADE"
    assert _fk_ondelete(PracticeSessionQuestion, "session_id") == "CASCADE"
    assert _fk_ondelete(PracticeAnswer, "session_id") == "CASCADE"
    assert _fk_ondelete(MistakeRecord, "bank_id") == "CASCADE"
    assert _fk_ondelete(MistakeAttempt, "bank_id") == "CASCADE"
    assert _fk_ondelete(MistakeAttempt, "practice_session_id") == "CASCADE"
    assert _fk_ondelete(MistakeAttempt, "practice_answer_id") == "SET NULL"
    assert _fk_ondelete(AIGenerationWorkflow, "bank_id") == "SET NULL"
    assert AIGenerationWorkflow.__table__.c.bank_id.nullable is True
    assert "ai_context" in QuestionBank.__table__.c
    assert _fk_ondelete(AIGenerationWorkflowStep, "workflow_id") == "CASCADE"
    assert _fk_ondelete(AIGenerationDraft, "workflow_id") == "CASCADE"
    assert _fk_ondelete(AIGenerationDraftQuestion, "draft_id") == "CASCADE"
    assert _fk_ondelete(AIGenerationWorkflow, "ai_provider_config_id") == "SET NULL"
    assert _fk_ondelete(ImportJob, "ai_provider_config_id") == "SET NULL"
    assert "queue_job_id" in ImportJob.__table__.c
    assert "enqueued_at" in ImportJob.__table__.c
    assert "source_bank_id" in QuestionBank.__table__.c
    assert "is_shared_copy" in QuestionBank.__table__.c
    assert _fk_ondelete(QuestionBank, "source_bank_id") == "SET NULL"


def test_login_identifier_and_change_password():
    with TestClient(app) as client:
        headers = _register(client, "login@example.com", "loginuser")
        v2_headers = client.post(
            "/api/v2/auth/register",
            json={"email": "login-v2@example.com", "username": "loginuserv2", "password": "password123"},
        )
        assert v2_headers.status_code == 200, v2_headers.text
        assert client.get(f"/api/v2/auth/verify-email?token={v2_headers.json()['debug_token']}").status_code == 200
        assert client.post("/api/v2/auth/login", json={"identifier": "loginuserv2", "password": "password123"}).status_code == 200
        v2_token = client.post("/api/v2/auth/login", json={"identifier": "loginuserv2", "password": "password123"}).json()["access_token"]
        assert client.get("/api/v2/auth/me", headers={"Authorization": f"Bearer {v2_token}"}).json()["username"] == "loginuserv2"
        assert _login(client, "login@example.com")
        assert _login(client, "loginuser")
        bad = client.post("/api/v2/auth/login", json={"identifier": "loginuser", "password": "wrong"})
        assert bad.status_code == 401
        assert bad.json()["error"]["message"] == "用户名/邮箱或密码错误"

        wrong_old = client.post("/api/v2/users/me/change-password", headers=headers, json={"old_password": "wrong", "new_password": "newpass123"})
        assert wrong_old.status_code == 400
        ok = client.post("/api/v2/users/me/change-password", headers=headers, json={"old_password": "password123", "new_password": "newpass123"})
        assert ok.status_code == 200
        assert _login(client, "loginuser", "newpass123")


def test_v2_bank_author_filter_supports_owner_keyword_and_owner_id_priority():
    with TestClient(app) as client:
        alpha_headers = _register(client, "owner-alpha@example.com", "owneralpha")
        beta_headers = _register(client, "owner-beta@example.com", "ownerbeta")
        reader_headers = _register(client, "owner-reader@example.com", "ownerreader")
        alpha_me = client.get("/api/v2/users/me", headers=alpha_headers).json()
        beta_me = client.get("/api/v2/users/me", headers=beta_headers).json()
        client.patch("/api/v2/users/me", headers=alpha_headers, json={"display_name": "Alpha Display"})
        alpha_source = _create_shareable_bank(client, alpha_headers, "Alpha Public")
        beta_source = _create_shareable_bank(client, beta_headers, "Beta Public")
        alpha_bank = _share_bank(client, alpha_headers, alpha_source["id"])
        beta_bank = _share_bank(client, beta_headers, beta_source["id"])

        by_numeric_owner = client.get(f"/api/v2/banks?scope=public&owner={alpha_me['id']}", headers=reader_headers).json()["items"]
        assert [item["id"] for item in by_numeric_owner] == [alpha_bank["id"]]

        by_username = client.get("/api/v2/banks?scope=public&owner=ownerbeta", headers=reader_headers).json()["items"]
        assert [item["id"] for item in by_username] == [beta_bank["id"]]

        by_display_name = client.get("/api/v2/banks?scope=public&owner=Alpha", headers=reader_headers).json()["items"]
        assert [item["id"] for item in by_display_name] == [alpha_bank["id"]]

        owner_id_priority = client.get(f"/api/v2/banks?scope=public&owner_id={beta_me['id']}&owner=owneralpha", headers=reader_headers).json()["items"]
        assert [item["id"] for item in owner_id_priority] == [beta_bank["id"]]


def test_normal_users_cannot_directly_publish_banks_or_ai_jobs():
    with TestClient(app) as client:
        headers = _register(client, "publish-block@example.com", "publishblock")

        direct = client.post("/api/v2/banks", headers=headers, json={"title": "No Public", "visibility": "public"})
        assert direct.status_code == 403
        assert "分享" in direct.json()["error"]["message"]

        payload = {
            "bank": {"title": "Import Public"},
            "questions": [_sample_question_payload("导入题")],
        }
        imported = client.post(
            "/api/v2/banks/import-json",
            headers=headers,
            data={"visibility": "public"},
            files={"file": ("bank.json", json.dumps(payload).encode("utf-8"), "application/json")},
        )
        assert imported.status_code == 403


def test_sharing_bank_creates_static_public_copy_and_locks_normal_management():
    with TestClient(app) as client:
        owner_headers = _register(client, "share-owner@example.com", "shareowner")
        reader_headers = _register(client, "share-reader@example.com", "sharereader")
        source = _create_shareable_bank(client, owner_headers, "Private Source", ["共享标签"])

        source_detail = client.get(f"/api/v2/banks/{source['id']}", headers=owner_headers).json()
        assert source_detail["visibility"] == "private"
        assert source_detail["permissions"]["can_share"] is True

        shared = _share_bank(client, owner_headers, source["id"])
        assert shared["id"] != source["id"]
        assert shared["source_bank_id"] == source["id"]
        assert shared["is_shared_copy"] is True
        assert shared["visibility"] == "public"
        assert shared["permissions"]["can_manage"] is False
        assert shared["permissions"]["can_share"] is False
        assert shared["stats"]["question_count"] == 1
        assert shared["tags"][0]["name"] == "共享标签"

        reader_shared = client.get(f"/api/v2/banks/{shared['id']}", headers=reader_headers)
        assert reader_shared.status_code == 200, reader_shared.text
        assert reader_shared.json()["permissions"]["can_export"] is True
        assert reader_shared.json()["permissions"]["can_manage"] is False

        shared_questions = client.get(f"/api/v2/banks/{shared['id']}/questions", headers=reader_headers).json()["items"]
        assert shared_questions[0]["stem"] == "Private Source Q"
        assert shared_questions[0]["options"][0]["content"] == "正确"
        assert client.post(f"/api/v2/banks/{shared['id']}/questions", headers=owner_headers, json=_sample_question_payload("不允许")).status_code == 404

        source_question = client.get(f"/api/v2/banks/{source['id']}/questions", headers=owner_headers).json()["items"][0]
        source_update_payload = _sample_question_payload("源题已改")
        updated = client.patch(f"/api/v2/questions/{source_question['id']}", headers=owner_headers, json=source_update_payload)
        assert updated.status_code == 200, updated.text
        unchanged_shared = client.get(f"/api/v2/banks/{shared['id']}/questions", headers=reader_headers).json()["items"]
        assert unchanged_shared[0]["stem"] == "Private Source Q"

        deleted_source = client.delete(f"/api/v2/banks/{source['id']}", headers=owner_headers)
        assert deleted_source.status_code == 200, deleted_source.text
        after_delete = client.get(f"/api/v2/banks/{shared['id']}", headers=reader_headers)
        assert after_delete.status_code == 200, after_delete.text
        assert after_delete.json()["source_bank_id"] is None


def test_bank_resumable_session_api_and_list_dto_use_latest_in_progress_session():
    with TestClient(app) as client:
        owner_headers = _register(client, "resume-owner@example.com", "resumeowner")
        other_headers = _register(client, "resume-other@example.com", "resumeother")
        bank = client.post("/api/v2/banks", headers=owner_headers, json={"title": "Resume Bank", "visibility": "private"}).json()
        question = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=owner_headers, json=_sample_question_payload("继续练习题")).json()

        none_response = client.get(f"/api/v2/banks/{bank['id']}/practice/resumable-session", headers=owner_headers)
        assert none_response.status_code == 200
        assert none_response.json() is None

        practice = client.post("/api/v2/practice/sessions", headers=owner_headers, json={"bank_id": bank["id"], "mode": "practice"}).json()
        exam = client.post("/api/v2/practice/sessions", headers=owner_headers, json={"bank_id": bank["id"], "mode": "exam"}).json()
        client.post(
            f"/api/v2/practice/sessions/{exam['id']}/answers",
            headers=owner_headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][0]["id"]]},
        )

        latest = client.get(f"/api/v2/banks/{bank['id']}/practice/resumable-session", headers=owner_headers)
        assert latest.status_code == 200, latest.text
        assert latest.json()["id"] == exam["id"]
        assert latest.json()["mode"] == "exam"
        assert latest.json()["answered_count"] == 1

        mine = client.get("/api/v2/banks?scope=mine&keyword=Resume", headers=owner_headers).json()["items"][0]
        assert mine["resumable_session"]["id"] == exam["id"]
        assert client.get(f"/api/v2/banks/{bank['id']}/practice/resumable-session", headers=other_headers).status_code == 404

        submitted = client.post(f"/api/v2/practice/sessions/{exam['id']}/submit", headers=owner_headers)
        assert submitted.status_code == 200, submitted.text
        after_submit = client.get(f"/api/v2/banks/{bank['id']}/practice/resumable-session", headers=owner_headers).json()
        assert after_submit["id"] == practice["id"]


def test_bank_latest_practice_session_includes_submitted_sessions_without_replacing_resumable():
    with TestClient(app) as client:
        headers = _register(client, "latest-progress@example.com", "latestprogress")
        other_headers = _register(client, "latest-progress-other@example.com", "latestprogressother")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Latest Progress Bank", "visibility": "private"}).json()
        question = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_sample_question_payload("最近进度题")).json()

        in_progress = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice"}).json()
        submitted = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "exam"}).json()
        client.post(
            f"/api/v2/practice/sessions/{submitted['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][0]["id"]]},
        )
        submitted = client.post(f"/api/v2/practice/sessions/{submitted['id']}/submit", headers=headers).json()

        item = client.get("/api/v2/banks?scope=mine&keyword=Latest%20Progress", headers=headers).json()["items"][0]
        assert item["resumable_session"]["id"] == in_progress["id"]
        assert item["latest_practice_session"]["id"] == submitted["id"]
        assert item["latest_practice_session"]["status"] == "submitted"
        assert item["latest_practice_session"]["score"] == submitted["score"]
        assert item["latest_practice_session"]["correct_count"] == 1

        detail = client.get(f"/api/v2/banks/{bank['id']}", headers=headers).json()
        assert detail["latest_practice_session"]["id"] == submitted["id"]

        hidden = client.get("/api/v2/banks?scope=mine&keyword=Latest%20Progress", headers=other_headers).json()["items"]
        assert hidden == []


def test_recent_practice_banks_returns_distinct_readable_banks_by_latest_activity():
    with TestClient(app) as client:
        headers = _register(client, "recent-banks@example.com", "recentbanks")
        other_headers = _register(client, "recent-banks-other@example.com", "recentbanksother")
        first_bank = client.post("/api/v2/banks", headers=headers, json={"title": "Recent First", "visibility": "private"}).json()
        second_bank = client.post("/api/v2/banks", headers=headers, json={"title": "Recent Second", "visibility": "private"}).json()
        first_question = client.post(f"/api/v2/banks/{first_bank['id']}/questions", headers=headers, json=_sample_question_payload("第一题库")).json()
        second_question = client.post(f"/api/v2/banks/{second_bank['id']}/questions", headers=headers, json=_sample_question_payload("第二题库")).json()

        first_old = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": first_bank["id"], "mode": "practice"}).json()
        client.post(
            f"/api/v2/practice/sessions/{first_old['id']}/answers",
            headers=headers,
            json={"question_id": first_question["id"], "selected_option_ids": [first_question["options"][0]["id"]]},
        )
        second_latest = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": second_bank["id"], "mode": "exam"}).json()
        client.post(
            f"/api/v2/practice/sessions/{second_latest['id']}/answers",
            headers=headers,
            json={"question_id": second_question["id"], "selected_option_ids": [second_question["options"][0]["id"]]},
        )
        client.post(f"/api/v2/practice/sessions/{second_latest['id']}/submit", headers=headers)
        first_latest = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": first_bank["id"], "mode": "exam"}).json()
        client.post(
            f"/api/v2/practice/sessions/{first_latest['id']}/answers",
            headers=headers,
            json={"question_id": first_question["id"], "selected_option_ids": [first_question["options"][0]["id"]]},
        )
        client.post(f"/api/v2/practice/sessions/{first_latest['id']}/submit", headers=headers)

        recent = client.get("/api/v2/banks/recent-practice?page_size=6", headers=headers)
        assert recent.status_code == 200, recent.text
        items = recent.json()
        assert [item["id"] for item in items[:2]] == [first_bank["id"], second_bank["id"]]
        assert items[0]["latest_practice_session"]["id"] == first_latest["id"]
        assert items[1]["latest_practice_session"]["id"] == second_latest["id"]

        limited = client.get("/api/v2/banks/recent-practice?page_size=1", headers=headers).json()
        assert [item["id"] for item in limited] == [first_bank["id"]]
        assert client.get("/api/v2/banks/recent-practice?page_size=6", headers=other_headers).json() == []


def test_bank_download_package_contains_full_readable_bank_content():
    with TestClient(app) as client:
        owner_headers = _register(client, "download-owner@example.com", "downloadowner")
        reader_headers = _register(client, "download-reader@example.com", "downloadreader")
        bank = client.post(
            "/api/v2/banks",
            headers=owner_headers,
            json={"title": "Download Bank", "description": "本地题库", "visibility": "private", "tag_names": ["离线"]},
        ).json()
        single = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=owner_headers, json=_sample_question_payload("下载单选")).json()
        blank = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=owner_headers, json=_blank_question_payload()).json()
        short = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=owner_headers, json=_short_answer_question_payload()).json()

        package = client.get(f"/api/v2/banks/{bank['id']}/download-package", headers=owner_headers)
        assert package.status_code == 200, package.text
        payload = package.json()
        assert payload["version"] == 1
        assert payload["bank"]["id"] == bank["id"]
        assert payload["bank"]["title"] == "Download Bank"
        assert payload["bank"]["description"] == "本地题库"
        assert payload["tags"] == [{"id": payload["tags"][0]["id"], "name": "离线"}]
        assert payload["content_hash"]
        assert payload["exported_at"]
        questions = {question["id"]: question for question in payload["questions"]}
        assert set(questions) == {single["id"], blank["id"], short["id"]}
        assert questions[single["id"]]["options"][0]["is_correct"] is True
        assert questions[blank["id"]]["blanks"][0]["answers"] == ["传输层", "Transport Layer"]
        assert questions[short["id"]]["type"] == "short_answer"

        hidden = client.get(f"/api/v2/banks/{bank['id']}/download-package", headers=reader_headers)
        assert hidden.status_code == 404


def test_offline_practice_sync_imports_full_session_and_is_idempotent():
    with TestClient(app) as client:
        headers = _register(client, "offline-sync@example.com", "offlinesync")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Offline Sync", "visibility": "private"}).json()
        single = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_sample_question_payload("离线单选")).json()
        blank = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_blank_question_payload()).json()

        payload = {
            "device_id": "device-a",
            "sessions": [
                {
                    "client_session_id": "local-session-1",
                    "remote_bank_id": bank["id"],
                    "mode": "practice",
                    "status": "submitted",
                    "question_order": [single["id"], blank["id"]],
                    "answers": [
                        {
                            "question_id": single["id"],
                            "selected_option_ids": [single["options"][1]["id"]],
                            "text_answers": [],
                            "is_submitted": True,
                            "answered_at": "2026-06-17T10:00:00Z",
                        },
                        {
                            "question_id": blank["id"],
                            "selected_option_ids": [],
                            "text_answers": ["传输层"],
                            "is_submitted": True,
                            "answered_at": "2026-06-17T10:01:00Z",
                        },
                    ],
                    "started_at": "2026-06-17T09:59:00Z",
                    "submitted_at": "2026-06-17T10:02:00Z",
                }
            ],
        }

        first_sync = client.post("/api/v2/offline/practice-sync", headers=headers, json=payload)
        assert first_sync.status_code == 200, first_sync.text
        first_body = first_sync.json()
        assert first_body["failed"] == []
        assert first_body["synced"][0]["client_session_id"] == "local-session-1"
        remote_session_id = first_body["synced"][0]["remote_session_id"]

        history = client.get("/api/v2/history/sessions", headers=headers).json()["items"]
        synced_history = next(item for item in history if item["id"] == remote_session_id)
        assert synced_history["status"] == "submitted"
        assert synced_history["correct_count"] == 1
        assert synced_history["score"] == 50

        result = client.get(f"/api/v2/practice/sessions/{remote_session_id}/result", headers=headers).json()
        assert [item["question_id"] for item in result] == [single["id"], blank["id"]]
        assert result[0]["selected_labels"] == ["B"]
        assert result[0]["is_correct"] is False
        assert result[1]["text_answers"] == ["传输层"]
        assert result[1]["is_correct"] is True

        mistakes = client.get(f"/api/v2/banks/{bank['id']}/mistake-attempts", headers=headers).json()
        assert mistakes["total"] == 1
        assert mistakes["items"][0]["practice_session_id"] == remote_session_id

        second_sync = client.post("/api/v2/offline/practice-sync", headers=headers, json=payload)
        assert second_sync.status_code == 200, second_sync.text
        assert second_sync.json()["synced"][0]["remote_session_id"] == remote_session_id
        assert client.get("/api/v2/history/sessions", headers=headers).json()["total"] == 1
        assert client.get(f"/api/v2/banks/{bank['id']}/mistake-attempts", headers=headers).json()["total"] == 1


def test_offline_practice_sync_updates_existing_in_progress_session():
    with TestClient(app) as client:
        headers = _register(client, "offline-sync-update@example.com", "offlinesyncupdate")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Offline Sync Update", "visibility": "private"}).json()
        single = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_sample_question_payload("离线更新单选")).json()
        blank = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_blank_question_payload()).json()

        draft_payload = {
            "device_id": "device-update",
            "sessions": [
                {
                    "client_session_id": "local-session-update",
                    "remote_bank_id": bank["id"],
                    "mode": "practice",
                    "status": "in_progress",
                    "question_order": [single["id"], blank["id"]],
                    "answers": [
                        {
                            "question_id": single["id"],
                            "selected_option_ids": [single["options"][1]["id"]],
                            "text_answers": [],
                            "is_submitted": True,
                            "answered_at": "2026-06-17T10:00:00Z",
                        }
                    ],
                    "started_at": "2026-06-17T09:59:00Z",
                    "submitted_at": None,
                }
            ],
        }
        first_sync = client.post("/api/v2/offline/practice-sync", headers=headers, json=draft_payload)
        assert first_sync.status_code == 200, first_sync.text
        remote_session_id = first_sync.json()["synced"][0]["remote_session_id"]
        assert client.get(f"/api/v2/banks/{bank['id']}/mistake-attempts", headers=headers).json()["total"] == 1

        submitted_payload = {
            **draft_payload,
            "sessions": [
                {
                    **draft_payload["sessions"][0],
                    "status": "submitted",
                    "answers": [
                        {
                            "question_id": single["id"],
                            "selected_option_ids": [single["options"][0]["id"]],
                            "text_answers": [],
                            "is_submitted": True,
                            "answered_at": "2026-06-17T10:03:00Z",
                        },
                        {
                            "question_id": blank["id"],
                            "selected_option_ids": [],
                            "text_answers": ["传输层"],
                            "is_submitted": True,
                            "answered_at": "2026-06-17T10:04:00Z",
                        },
                    ],
                    "submitted_at": "2026-06-17T10:05:00Z",
                }
            ],
        }
        second_sync = client.post("/api/v2/offline/practice-sync", headers=headers, json=submitted_payload)
        assert second_sync.status_code == 200, second_sync.text
        assert second_sync.json()["synced"][0]["remote_session_id"] == remote_session_id
        assert client.get("/api/v2/history/sessions", headers=headers).json()["total"] == 1

        synced_history = client.get("/api/v2/history/sessions", headers=headers).json()["items"][0]
        assert synced_history["id"] == remote_session_id
        assert synced_history["status"] == "submitted"
        assert synced_history["correct_count"] == 2
        assert synced_history["score"] == 100
        assert client.get(f"/api/v2/banks/{bank['id']}/mistake-attempts", headers=headers).json()["total"] == 0


def test_refresh_token_can_refresh_access_but_not_access_api():
    with TestClient(app) as client:
        response = client.post(
            "/api/v2/auth/register",
            json={"email": "refresh@example.com", "username": "refreshuser", "password": "password123"},
        )
        assert response.status_code == 200, response.text
        assert client.get(f"/api/v2/auth/verify-email?token={response.json()['debug_token']}").status_code == 200
        login = client.post("/api/v2/auth/login", json={"identifier": "refreshuser", "password": "password123"})
        assert login.status_code == 200, login.text
        data = login.json()
        assert data["access_token"]
        assert data["refresh_token"]

        refresh_headers = {"Authorization": f"Bearer {data['refresh_token']}"}
        assert client.get("/api/v2/users/me", headers=refresh_headers).status_code == 401

        refreshed = client.post("/api/v2/auth/refresh", json={"refresh_token": data["refresh_token"]})
        assert refreshed.status_code == 200, refreshed.text
        new_access_token = refreshed.json()["access_token"]
        assert new_access_token
        assert refreshed.json()["refresh_token"] == data["refresh_token"]
        me = client.get("/api/v2/users/me", headers={"Authorization": f"Bearer {new_access_token}"})
        assert me.status_code == 200
        assert me.json()["username"] == "refreshuser"


def test_email_verification_required_before_login():
    with TestClient(app) as client:
        registered = client.post(
            "/api/v2/auth/register",
            json={"email": "verify@example.com", "username": "verifyuser", "password": "password123"},
        )
        assert registered.status_code == 200, registered.text
        assert registered.json()["ok"] is True
        assert "access_token" not in registered.json()

        login = client.post("/api/v2/auth/login", json={"identifier": "verifyuser", "password": "password123"})
        assert login.status_code == 403
        assert login.json()["error"]["message"] == "请先验证邮箱"

        db = SessionLocal()
        try:
            user = db.scalar(select(User).where(User.username == "verifyuser"))
            assert user is not None
            assert user.email_verified_at is None
            token = db.scalar(select(EmailAuthToken).where(EmailAuthToken.user_id == user.id, EmailAuthToken.purpose == "email_verify"))
            assert token is not None
            assert token.token_hash
            assert len(token.token_hash) == 64
        finally:
            db.close()

        # Tests use the development outbox hook to retrieve the plaintext token.
        verify_token = registered.json()["debug_token"]
        verified = client.get(f"/api/v2/auth/verify-email?token={verify_token}")
        assert verified.status_code == 200, verified.text
        assert verified.json()["ok"] is True
        assert _login(client, "verifyuser")
        assert client.get(f"/api/v2/auth/verify-email?token={verify_token}").status_code == 400


def test_resend_verification_and_password_reset_flow():
    with TestClient(app) as client:
        registered = client.post(
            "/api/v2/auth/register",
            json={"email": "reset@example.com", "username": "resetuser", "password": "password123"},
        )
        assert registered.status_code == 200, registered.text

        resent = client.post("/api/v2/auth/resend-verification", json={"email": "reset@example.com"})
        assert resent.status_code == 200
        verify_token = resent.json()["debug_token"]
        assert verify_token != registered.json()["debug_token"]
        assert client.get(f"/api/v2/auth/verify-email?token={verify_token}").status_code == 200

        missing = client.post("/api/v2/auth/forgot-password", json={"email": "missing@example.com"})
        assert missing.status_code == 200
        assert missing.json()["ok"] is True

        forgot = client.post("/api/v2/auth/forgot-password", json={"email": "reset@example.com"})
        assert forgot.status_code == 200
        reset_token = forgot.json()["debug_token"]

        bad = client.post("/api/v2/auth/reset-password", json={"token": "bad-token", "new_password": "newpass123"})
        assert bad.status_code == 400
        ok = client.post("/api/v2/auth/reset-password", json={"token": reset_token, "new_password": "newpass123"})
        assert ok.status_code == 200
        assert client.post("/api/v2/auth/reset-password", json={"token": reset_token, "new_password": "another123"}).status_code == 400
        assert client.post("/api/v2/auth/login", json={"identifier": "resetuser", "password": "password123"}).status_code == 401
        assert _login(client, "resetuser", "newpass123")


def test_forgot_password_sends_reset_for_existing_unverified_user():
    with TestClient(app) as client:
        registered = client.post(
            "/api/v2/auth/register",
            json={"email": "legacy-reset@example.com", "username": "legacyreset", "password": "password123"},
        )
        assert registered.status_code == 200, registered.text

        forgot = client.post("/api/v2/auth/forgot-password", json={"email": "legacy-reset@example.com"})
        assert forgot.status_code == 200
        assert forgot.json()["debug_token"]


def test_forgot_password_reports_delivery_failure_for_existing_user(monkeypatch):
    with TestClient(app) as client:
        registered = client.post(
            "/api/v2/auth/register",
            json={"email": "delivery-fail@example.com", "username": "deliveryfail", "password": "password123"},
        )
        assert registered.status_code == 200, registered.text

        monkeypatch.setattr(email_delivery.EmailDeliveryService, "send", lambda *args, **kwargs: False)
        forgot = client.post("/api/v2/auth/forgot-password", json={"email": "delivery-fail@example.com"})
        assert forgot.status_code == 503
        assert forgot.json()["error"]["message"] == "重置密码邮件发送失败，请稍后重试"


def test_email_tokens_must_match_current_user_email():
    with TestClient(app) as client:
        registered = client.post(
            "/api/v2/auth/register",
            json={"email": "token-original@example.com", "username": "tokenuser", "password": "password123"},
        )
        assert registered.status_code == 200, registered.text
        verify_token = registered.json()["debug_token"]

        db = SessionLocal()
        try:
            user = db.scalar(select(User).where(User.username == "tokenuser"))
            assert user is not None
            user.email = "token-changed@example.com"
            db.commit()
        finally:
            db.close()

        assert client.get(f"/api/v2/auth/verify-email?token={verify_token}").status_code == 400


def test_email_delivery_uses_fastapi_mail_when_smtp_configured(monkeypatch):
    sent: list[tuple[str, list[str], str, str]] = []

    class FakeFastMail:
        def __init__(self, config):
            self.config = config

        async def send_message(self, message):
            sent.append((message.subject, message.recipients, message.body, message.subtype.value))

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    get_settings.cache_clear()
    monkeypatch.setattr(email_delivery, "FastMail", FakeFastMail)

    try:
        assert email_delivery.EmailDeliveryService().send("to@example.com", "Subject", "Body", "<strong>Body</strong>") is True
        assert sent == [("Subject", ["to@example.com"], "<strong>Body</strong>", "html")]
    finally:
        get_settings.cache_clear()


def test_v2_errors_use_unified_shape():
    with TestClient(app) as client:
        headers = _register(client, "errors@example.com", "errors")

        v2_missing = client.get("/api/v2/banks/999999", headers=headers)
        assert v2_missing.status_code == 404
        assert v2_missing.json()["error"]["code"] == "HTTP_404"
        assert v2_missing.json()["error"]["message"] == "Question bank not found"

        v2_validation = client.post("/api/v2/banks", headers=headers, json={})
        assert v2_validation.status_code == 422
        assert v2_validation.json()["error"]["code"] == "VALIDATION_ERROR"
        assert v2_validation.json()["error"]["message"] == "请求参数校验失败"

def test_auth_bank_favorite_question_practice_and_mistake(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "demo@example.com", "demo")
        other_headers = _register(client, "other@example.com", "other")

        bank = client.post(
            "/api/v2/banks",
            headers=headers,
            json={"title": "Bank", "visibility": "private", "tag_names": [" 计算机组成原理 ", "", "深度学习基础", "计算机组成原理"]},
        ).json()
        assert [tag["name"] for tag in bank["tags"]] == ["深度学习基础", "计算机组成原理"]
        first_tag_id = bank["tags"][0]["id"]
        bank_detail = client.get(f"/api/v2/banks/{bank['id']}", headers=headers).json()
        assert bank_detail["owner_username"] == "demo"
        assert [tag["name"] for tag in bank_detail["tags"]] == ["深度学习基础", "计算机组成原理"]
        tag_search = client.get("/api/v2/banks/tags?keyword=深度", headers=headers).json()
        assert tag_search["total"] == 1
        assert tag_search["items"][0]["name"] == "深度学习基础"
        assert client.get(f"/api/v2/banks?tag_ids={first_tag_id}", headers=headers).json()["total"] == 1
        search_users = client.get("/api/v2/users/search?keyword=dem", headers=headers).json()
        assert search_users["total"] == 1
        assert search_users["items"][0]["username"] == "demo"
        assert "email" not in search_users["items"][0]
        assert client.get(f"/api/v2/banks/{bank['id']}", headers=other_headers).status_code == 404
        assert client.get(f"/api/v2/banks?tag_ids={first_tag_id}", headers=other_headers).json()["total"] == 0
        assert client.post(f"/api/v2/banks/{bank['id']}/favorites", headers=other_headers).status_code == 404
        assert client.post(f"/api/v2/banks/{bank['id']}/favorites", headers=headers).status_code == 200
        favorites_by_owner = client.get(f"/api/v2/banks?scope=favorites&owner_id={bank['owner_id']}", headers=headers).json()
        assert favorites_by_owner["total"] == 1

        question_payload = {
            "type": "single",
            "stem": "1+1=?",
            "options": [
                {"label": "A", "content": "2", "is_correct": True},
                {"label": "B", "content": "3", "is_correct": False},
            ],
            "explanation": "basic math",
        }
        question = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=question_payload).json()
        unanswered_question = client.post(
            f"/api/v2/banks/{bank['id']}/questions",
            headers=headers,
            json={
                "type": "multiple",
                "stem": "Select even numbers",
                "options": [
                    {"label": "A", "content": "2", "is_correct": True},
                    {"label": "B", "content": "3", "is_correct": False},
                    {"label": "C", "content": "4", "is_correct": True},
                ],
            },
        ).json()
        session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice"}).json()
        assert session["answered_count"] == 0
        assert session["bank_title"] == "Bank"
        assert session["bank_visibility"] == "private"
        assert session["bank_generation_status"] == "none"
        assert session["last_answered_at"] is None
        answer = client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][1]["id"]]},
        )
        assert answer.status_code == 200
        assert answer.json()["reveal"] is True
        assert answer.json()["is_correct"] is False
        assert answer.json()["correct_labels"] == ["A"]
        assert answer.json()["explanation"] == "basic math"
        question_states = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()
        answered_state = next(item for item in question_states if item["id"] == question["id"])["answer_state"]
        assert answered_state["is_answered"] is True
        assert answered_state["selected_option_ids"] == [question["options"][1]["id"]]
        assert answered_state["reveal"] is True
        assert answered_state["correct_labels"] == ["A"]
        repeat = client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][0]["id"]]},
        )
        assert repeat.status_code == 400
        assert "不能重复" in repeat.json()["error"]["message"]
        updated_session = client.get(f"/api/v2/practice/sessions/{session['id']}", headers=headers).json()
        assert updated_session["answered_count"] == 1
        assert updated_session["last_answered_at"] is not None
        history = client.get("/api/v2/history/sessions", headers=headers).json()
        history_item = history["items"][0]
        assert history_item["bank_title"] == "Bank"
        assert history_item["started_at"] is not None
        assert history_item["last_answered_at"] == updated_session["last_answered_at"]
        v2_history = client.get("/api/v2/history/sessions", headers=headers).json()
        assert v2_history["items"][0]["bank_title"] == "Bank"
        assert v2_history["items"][0]["last_answered_at"] == updated_session["last_answered_at"]
        submitted = client.post(f"/api/v2/practice/sessions/{session['id']}/submit", headers=headers).json()
        assert submitted["answered_count"] == 1
        assert submitted["submitted_at"] is not None
        result = client.get(f"/api/v2/practice/sessions/{session['id']}/result", headers=headers).json()
        answered = next(item for item in result if item["question_id"] == question["id"])
        unanswered = next(item for item in result if item["question_id"] == unanswered_question["id"])
        assert answered["stem"] == "1+1=?"
        assert answered["selected_labels"] == ["B"]
        assert answered["correct_labels"] == ["A"]
        assert unanswered["is_unanswered"] is True
        assert unanswered["selected_labels"] == []
        assert unanswered["correct_labels"] == ["A", "C"]
        mistakes = client.get(f"/api/v2/banks/{bank['id']}/mistakes", headers=headers).json()
        assert mistakes["total"] == 1
        mistake = mistakes["items"][0]
        assert mistake["stem"] == "1+1=?"
        assert mistake["type"] == "single"
        assert mistake["options"][0]["label"] == "A"
        assert mistake["correct_labels"] == ["A"]
        assert mistake["correct_option_ids"] == [question["options"][0]["id"]]
        assert mistake["explanation"] == "basic math"
        assert mistake["wrong_count"] == 1
        exported = client.get(f"/api/v2/banks/{bank['id']}/export-json", headers=headers).json()
        assert exported["bank"]["tags"] == ["深度学习基础", "计算机组成原理"]
        imported = client.post(
            "/api/v2/banks/import-json",
            headers=headers,
            data={"visibility": "private", "tag_names": '["手动导入标签"]'},
            files={"file": ("bank.json", json.dumps(exported).encode("utf-8"), "application/json")},
        )
        assert imported.status_code == 200
        imported_tag_names = [tag["name"] for tag in imported.json()["tags"]]
        assert "深度学习基础" in imported_tag_names
        assert "手动导入标签" in imported_tag_names
        patched_tags = client.patch(f"/api/v2/banks/{bank['id']}", headers=headers, json={"tag_names": ["操作系统"]})
        assert patched_tags.status_code == 200
        assert [tag["name"] for tag in patched_tags.json()["tags"]] == ["操作系统"]
        too_many_tags = client.patch(f"/api/v2/banks/{bank['id']}", headers=headers, json={"tag_names": [f"tag-{index}" for index in range(21)]})
        assert too_many_tags.status_code == 422


def test_register_validation_and_exam_hides_answer_until_submit():
    with TestClient(app) as client:
        invalid = client.post("/api/v2/auth/register", json={"email": "bad", "username": "ab", "password": "short"})
        assert invalid.status_code == 422
        headers = _register(client, "exam@example.com", "examuser")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Exam Bank", "visibility": "private"}).json()
        question = client.post(
            f"/api/v2/banks/{bank['id']}/questions",
            headers=headers,
            json={
                "type": "single",
                "stem": "2+2=?",
                "options": [
                    {"label": "A", "content": "3", "is_correct": False},
                    {"label": "B", "content": "4", "is_correct": True},
                ],
                "explanation": "basic arithmetic",
            },
        ).json()
        session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "exam"}).json()
        answer = client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][0]["id"]]},
        )
        assert answer.status_code == 200
        assert answer.json()["reveal"] is False
        assert answer.json()["is_correct"] is None
        assert answer.json()["correct_labels"] == []
        state = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()[0]["answer_state"]
        assert state["is_answered"] is True
        assert state["reveal"] is False
        changed = client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][1]["id"]]},
        )
        assert changed.status_code == 200
        assert changed.json()["reveal"] is False
        state = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()[0]["answer_state"]
        assert state["selected_option_ids"] == [question["options"][1]["id"]]
        client.post(f"/api/v2/practice/sessions/{session['id']}/submit", headers=headers)
        revealed = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()[0]["answer_state"]
        assert revealed["reveal"] is True
        assert revealed["is_correct"] is True
        assert revealed["correct_labels"] == ["B"]
        result = client.get(f"/api/v2/practice/sessions/{session['id']}/result", headers=headers).json()[0]
        assert result["correct_labels"] == ["B"]
        assert result["selected_labels"] == ["B"]
        assert result["explanation"] == "basic arithmetic"


def test_practice_answer_draft_saves_without_locking_normal_practice():
    with TestClient(app) as client:
        headers = _register(client, "draft-practice@example.com", "draftpractice")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Draft Practice", "visibility": "private"}).json()
        question = client.post(
            f"/api/v2/banks/{bank['id']}/questions",
            headers=headers,
            json={
                "type": "multiple",
                "stem": "Pick letters",
                "options": [
                    {"label": "A", "content": "A", "is_correct": True},
                    {"label": "B", "content": "B", "is_correct": True},
                    {"label": "C", "content": "C", "is_correct": False},
                ],
                "explanation": "A and B",
            },
        ).json()
        session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice"}).json()
        draft = client.put(
            f"/api/v2/practice/sessions/{session['id']}/answers/{question['id']}/draft",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][0]["id"]]},
        )
        assert draft.status_code == 200, draft.text
        state = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()[0]["answer_state"]
        assert state["selected_option_ids"] == [question["options"][0]["id"]]
        assert state["is_answered"] is False
        assert state["reveal"] is False
        progress = client.get(f"/api/v2/practice/sessions/{session['id']}", headers=headers).json()
        assert progress["answered_count"] == 0

        submitted = client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][0]["id"], question["options"][1]["id"]]},
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["reveal"] is True
        duplicate_draft = client.put(
            f"/api/v2/practice/sessions/{session['id']}/answers/{question['id']}/draft",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][2]["id"]]},
        )
        assert duplicate_draft.status_code == 200
        state_after = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()[0]["answer_state"]
        assert set(state_after["selected_option_ids"]) == {question["options"][0]["id"], question["options"][1]["id"]}
        assert state_after["is_answered"] is True
        progress_after = client.get(f"/api/v2/practice/sessions/{session['id']}", headers=headers).json()
        assert progress_after["answered_count"] == 1


def test_exam_empty_answer_draft_clears_saved_choice_and_counts_unanswered():
    with TestClient(app) as client:
        headers = _register(client, "exam-clear@example.com", "examclear")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Exam Clear", "visibility": "private"}).json()
        question = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_sample_question_payload("考试可清空题")).json()
        session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "exam"}).json()

        saved = client.put(
            f"/api/v2/practice/sessions/{session['id']}/answers/{question['id']}/draft",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][0]["id"]]},
        )
        assert saved.status_code == 200, saved.text
        assert client.get(f"/api/v2/practice/sessions/{session['id']}", headers=headers).json()["answered_count"] == 1

        cleared = client.put(
            f"/api/v2/practice/sessions/{session['id']}/answers/{question['id']}/draft",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": []},
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["changed"] is True
        restored = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()[0]["answer_state"]
        assert restored["selected_option_ids"] == []
        assert restored["is_answered"] is False
        assert client.get(f"/api/v2/practice/sessions/{session['id']}", headers=headers).json()["answered_count"] == 0

        submitted = client.post(f"/api/v2/practice/sessions/{session['id']}/submit", headers=headers)
        assert submitted.status_code == 200, submitted.text
        result = client.get(f"/api/v2/practice/sessions/{session['id']}/result", headers=headers).json()[0]
        assert result["is_unanswered"] is True
        assert result["selected_option_ids"] == []
        assert result["selected_labels"] == []


def test_ai_config_api_key_cannot_be_updated_and_list_has_only_real_configs():
    with TestClient(app) as client:
        headers = _register(client, "config@example.com", "configuser")
        created = client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True, "response_format_type": "json_schema"},
        )
        assert created.status_code == 200
        assert created.json()["response_format_type"] == "json_schema"
        configs = client.get("/api/v2/users/me/ai-provider-configs", headers=headers).json()
        assert len(configs) == 1
        assert configs[0]["name"] == ""
        assert configs[0]["response_format_type"] == "json_schema"
        assert configs[0]["has_api_key"] is True
        updated = client.patch(
            f"/api/v2/users/me/ai-provider-configs/{created.json()['id']}",
            headers=headers,
            json={"response_format_type": "json_object"},
        )
        assert updated.status_code == 200
        assert updated.json()["response_format_type"] == "json_object"
        blocked = client.patch(
            f"/api/v2/users/me/ai-provider-configs/{created.json()['id']}",
            headers=headers,
            json={"api_key": "sk-new"},
        )
        assert blocked.status_code == 400
        assert "不可修改" in blocked.json()["error"]["message"]


def test_admin_user_management_and_bank_permissions():
    with TestClient(app) as client:
        admin_headers = _register(client, "admin@example.com", "adminuser")
        _make_admin("adminuser")
        admin_headers = _login(client, "adminuser")
        admin_id = client.get("/api/v2/auth/me", headers=admin_headers).json()["id"]
        owner_headers = _register(client, "owner@example.com", "owneruser")
        other_headers = _register(client, "visitor@example.com", "visitoruser")

        users = client.get("/api/v2/admin/users?keyword=visitor", headers=admin_headers).json()
        visitor_id = users["items"][0]["id"]
        patched = client.patch(
            f"/api/v2/admin/users/{visitor_id}",
            headers=admin_headers,
            json={"display_name": "Visitor", "bio": "bio", "is_active": False},
        )
        assert patched.status_code == 200
        assert patched.json()["display_name"] == "Visitor"
        assert patched.json()["is_active"] is False
        assert client.post("/api/v2/auth/login", json={"identifier": "visitoruser", "password": "password123"}).status_code == 401
        client.patch(f"/api/v2/admin/users/{visitor_id}", headers=admin_headers, json={"is_active": True})
        role_patch = client.patch(f"/api/v2/admin/users/{visitor_id}", headers=admin_headers, json={"role": "admin"})
        assert role_patch.status_code == 422
        reset = client.post(f"/api/v2/admin/users/{visitor_id}/reset-password", headers=admin_headers)
        assert reset.status_code == 200
        temporary_password = reset.json()["temporary_password"]
        assert client.post("/api/v2/auth/login", json={"identifier": "visitoruser", "password": "password123"}).status_code == 401
        assert _login(client, "visitoruser", temporary_password)
        assert client.post(f"/api/v2/admin/users/{admin_id}/reset-password", headers=admin_headers).status_code == 400
        assert client.patch(f"/api/v2/admin/users/{visitor_id}", headers=other_headers, json={"is_active": False}).status_code == 403

        private_bank = client.post("/api/v2/banks", headers=owner_headers, json={"title": "Private", "visibility": "private"}).json()
        public_source = client.post("/api/v2/banks", headers=owner_headers, json={"title": "Public", "visibility": "private"}).json()
        source_question = client.post(
            f"/api/v2/banks/{public_source['id']}/questions",
            headers=owner_headers,
            json={
                "type": "single",
                "stem": "Public Q",
                "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
            },
        ).json()
        public_bank = client.post(f"/api/v2/banks/{public_source['id']}/share", headers=owner_headers).json()
        question = client.get(f"/api/v2/banks/{public_bank['id']}/questions", headers=owner_headers).json()["items"][0]

        assert client.get(f"/api/v2/banks/{private_bank['id']}", headers=other_headers).status_code == 404
        assert client.get(f"/api/v2/banks/{public_bank['id']}/export-json", headers=other_headers).status_code == 200
        other_public_mistakes = client.get(f"/api/v2/banks/{public_bank['id']}/mistakes", headers=other_headers)
        assert other_public_mistakes.status_code == 200
        assert other_public_mistakes.json()["total"] == 0
        assert client.patch(f"/api/v2/banks/{public_bank['id']}", headers=other_headers, json={"title": "Nope"}).status_code == 404
        assert client.post(
            f"/api/v2/banks/{public_bank['id']}/questions",
            headers=other_headers,
            json={
                "type": "single",
                "stem": "Nope",
                "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
            },
        ).status_code == 404
        assert client.delete(f"/api/v2/questions/{source_question['id']}", headers=other_headers).status_code == 404

        other_session = client.post("/api/v2/practice/sessions", headers=other_headers, json={"bank_id": public_bank["id"], "mode": "practice"}).json()
        other_answer = client.post(
            f"/api/v2/practice/sessions/{other_session['id']}/answers",
            headers=other_headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][1]["id"]]},
        )
        assert other_answer.status_code == 200
        other_public_mistakes = client.get(f"/api/v2/banks/{public_bank['id']}/mistakes", headers=other_headers).json()
        owner_public_mistakes = client.get(f"/api/v2/banks/{public_bank['id']}/mistakes", headers=owner_headers).json()
        assert other_public_mistakes["total"] == 1
        assert other_public_mistakes["items"][0]["stem"] == "Public Q"
        assert other_public_mistakes["items"][0]["correct_labels"] == ["A"]
        assert owner_public_mistakes["total"] == 0
        other_patch_tags = client.patch(f"/api/v2/banks/{public_bank['id']}", headers=other_headers, json={"tag_names": ["Nope"]})
        assert other_patch_tags.status_code == 404

        assert client.get(f"/api/v2/banks/{private_bank['id']}", headers=admin_headers).status_code == 200
        admin_update = client.patch(f"/api/v2/banks/{private_bank['id']}", headers=admin_headers, json={"title": "Admin Edited"})
        assert admin_update.status_code == 200
        assert admin_update.json()["title"] == "Admin Edited"
        admin_tag_update = client.patch(f"/api/v2/banks/{private_bank['id']}", headers=admin_headers, json={"tag_names": ["管理员标签"]})
        assert admin_tag_update.status_code == 200
        assert admin_tag_update.json()["tags"][0]["name"] == "管理员标签"
        admin_question = client.post(
            f"/api/v2/banks/{private_bank['id']}/questions",
            headers=admin_headers,
            json={
                "type": "single",
                "stem": "Admin Q",
                "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
            },
        )
        assert admin_question.status_code == 200


def test_ai_generation_validation_failure(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "ai@example.com", "aiuser")
        config = client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )
        assert config.status_code == 200

        from app.domains.ai_generation import facade as ai_generation

        def bad_ai(*args, **kwargs):
            return {"questions": [{"type": "single", "stem": "bad", "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": True}]}]}

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", bad_ai)
        response = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "AI Bank", "desired_visibility": "private", "question_count": "1", "tag_names": '["AI标签"]'},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert response.status_code == 200
        bank = client.get(f"/api/v2/banks/{response.json()['bank_id']}", headers=headers).json()
        assert bank["tags"][0]["name"] == "AI标签"
        job = client.get(f"/api/v2/ai/workflows/{response.json()['workflow_id']}", headers=headers).json()
        assert job["status"] == "failed"
        assert job["workflow_id"] is not None
        assert job["workflow_status"] == "failed"
        assert job["repair_attempts"] == 2
        assert job["can_confirm"] is False
        assert "知识库生成失败" in job["error_message"]
        assert "已自动修复 2 次仍失败" in job["error_message"]
        assert "第 1 题" in job["error_message"]
        assert "题干：bad" in job["error_message"]
        assert "题型：single" in job["error_message"]
        assert "single 有 2 个正确答案" in job["error_message"]
        steps = client.get(f"/api/v2/ai/workflows/{job['workflow_id']}/steps", headers=headers).json()
        assert any(step["step_name"] == "validate_payload" and step["status"] == "failed" for step in steps)


def test_ai_generation_repair_draft_confirm_and_extend(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "workflow@example.com", "workflowuser")
        _make_admin("workflowuser")
        headers = _login(client, "workflowuser")
        other_headers = _register(client, "workflow-other@example.com", "workflowother")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        calls = []
        outputs = [
            {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Broken question",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": True}],
                    }
                ]
            },
            {
                "bank_description": "Draft description",
                "questions": [
                    {
                        "type": "single",
                        "stem": "Fixed question",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                        "explanation": "Fixed explanation",
                    }
                ],
            },
            {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Extended question",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            },
        ]

        def workflow_ai(*args, **kwargs):
            calls.append(args)
            return outputs.pop(0)

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", workflow_ai)
        response = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Workflow Bank", "desired_visibility": "public", "question_count": "1", "generate_description": "true"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert response.status_code == 200
        bank = client.get(f"/api/v2/banks/{response.json()['bank_id']}", headers=headers).json()
        assert bank["generation_status"] == "processing"
        assert bank["visibility"] == "private"
        assert bank["question_count"] == 0
        job = client.get(f"/api/v2/ai/workflows/{response.json()['workflow_id']}", headers=headers).json()
        assert job["status"] == "draft_ready"
        assert job["workflow_status"] == "draft_ready"
        assert job["draft_question_count"] == 1
        assert job["repair_attempts"] == 1
        assert job["can_confirm"] is True
        draft = client.get(f"/api/v2/ai/workflows/{job['id']}/draft", headers=headers).json()
        assert draft["bank_description"] == "Draft description"
        assert draft["questions"][0]["stem"] == "Fixed question"
        assert client.get(f"/api/v2/ai/workflows/{job['id']}/draft", headers=other_headers).status_code == 404

        edited = draft.copy()
        edited["bank_description"] = "Edited description"
        edited["questions"][0]["stem"] = "Edited fixed question"
        patch = client.patch(f"/api/v2/ai/workflows/{job['id']}/draft", headers=headers, json=edited)
        assert patch.status_code == 200
        confirmed = client.post(f"/api/v2/ai/workflows/{job['id']}/draft/confirm", headers=headers)
        assert confirmed.status_code == 200
        bank_after_confirm = client.get(f"/api/v2/banks/{bank['id']}", headers=headers).json()
        assert bank_after_confirm["generation_status"] == "succeeded"
        assert bank_after_confirm["visibility"] == "public"
        assert bank_after_confirm["description"] == "Edited description"
        assert bank_after_confirm["question_count"] == 1
        questions = client.get(f"/api/v2/banks/{bank['id']}/questions", headers=headers).json()
        assert questions["items"][0]["stem"] == "Edited fixed question"

        extend = client.post(
            f"/api/v2/banks/{bank['id']}/ai-workflows",
            headers=headers,
            data={"generation_mode": "knowledge_generate", "question_count": "1", "extra_instruction": "避免重复", "include_existing_questions": "true"},
            files={"file": ("more.txt", b"more content", "text/plain")},
        )
        assert extend.status_code == 200
        bank_during_extend = client.get(f"/api/v2/banks/{bank['id']}", headers=other_headers)
        assert bank_during_extend.status_code == 200, bank_during_extend.text
        assert bank_during_extend.json()["generation_status"] == "succeeded"
        logs_during_extend = client.get(f"/api/v2/banks/{bank['id']}/ai-workflows", headers=other_headers)
        assert logs_during_extend.status_code == 200, logs_during_extend.text
        extend_job = client.get(f"/api/v2/ai/workflows/{extend.json()['workflow_id']}", headers=headers).json()
        assert extend_job["status"] == "draft_ready"
        assert extend_job["draft_question_count"] == 1
        assert any("Edited fixed question" in str(call) for call in calls)
        assert client.post(f"/api/v2/ai/workflows/{extend_job['id']}/draft/confirm", headers=headers).status_code == 200
        bank_after_extend = client.get(f"/api/v2/banks/{bank['id']}", headers=headers).json()
        assert bank_after_extend["question_count"] == 2
        assert bank_after_extend["visibility"] == "public"
        public_logs = client.get(f"/api/v2/banks/{bank['id']}/ai-workflows", headers=other_headers)
        assert public_logs.status_code == 200, public_logs.text
        imported_log = next(item for item in public_logs.json()["items"] if item["id"] == extend_job["id"])
        assert imported_log["question_delta"] == 1
        assert imported_log["imported_question_count"] == 1
        assert imported_log["source_text_snapshot"] is None
        assert imported_log["extra_instruction"] is None
        assert imported_log["error_message"] is None

        forbidden = client.post(
            f"/api/v2/banks/{bank['id']}/ai-workflows",
            headers=other_headers,
            data={"generation_mode": "knowledge_generate", "question_count": "1"},
            files={"file": ("more.txt", b"more content", "text/plain")},
        )
        assert forbidden.status_code == 404


def test_bank_workflow_logs_redact_failed_error_for_readers(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "workflow-log-owner@example.com", "workflowlogowner")
        _make_admin("workflowlogowner")
        headers = _login(client, "workflowlogowner")
        reader_headers = _register(client, "workflow-log-reader@example.com", "workflowlogreader")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Workflow Log", "visibility": "public"}).json()

        from app.domains.ai_generation import facade as ai_generation

        def bad_ai(*args, **kwargs):
            return {"questions": []}

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", bad_ai)
        created = client.post(
            f"/api/v2/banks/{bank['id']}/ai-workflows",
            headers=headers,
            data={"question_count": "1", "extra_instruction": "sensitive extra instruction"},
            files={"file": ("bad.txt", b"sensitive source text", "text/plain")},
        )
        assert created.status_code == 200, created.text
        owner_workflow = client.get(f"/api/v2/ai/workflows/{created.json()['workflow_id']}", headers=headers).json()
        assert owner_workflow["status"] == "failed"
        assert owner_workflow["error_message"]

        owner_logs = client.get(f"/api/v2/banks/{bank['id']}/ai-workflows", headers=headers)
        assert owner_logs.status_code == 200, owner_logs.text
        owner_item = owner_logs.json()["items"][0]
        assert owner_item["error_message"] == owner_workflow["error_message"]
        assert owner_item["source_file_name"] == "bad.txt"
        assert owner_item["source_text_snapshot"] == "sensitive source text"
        assert owner_item["extra_instruction"] == "sensitive extra instruction"
        assert owner_item["can_retry"] is True

        logs = client.get(f"/api/v2/banks/{bank['id']}/ai-workflows", headers=reader_headers)
        assert logs.status_code == 200, logs.text
        item = logs.json()["items"][0]
        assert item["status"] == "failed"
        assert item["error_summary"]
        assert item["error_message"] is None
        assert item["source_file_name"] is None
        assert item["source_text_snapshot"] is None
        assert item["extra_instruction"] is None
        assert item["ai_provider_config_id"] is None
        assert item["can_retry"] is False
        assert item["can_cancel"] is False
        assert "sensitive source text" not in str(item)
        assert "sensitive extra instruction" not in str(item)


def test_public_bank_workflow_logs_cover_extension_states_and_redaction():
    with TestClient(app) as client:
        headers = _register(client, "workflow-state-owner@example.com", "workflowstateowner")
        _make_admin("workflowstateowner")
        headers = _login(client, "workflowstateowner")
        reader_headers = _register(client, "workflow-state-reader@example.com", "workflowstatereader")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Workflow States", "visibility": "public"}).json()

        db = SessionLocal()
        try:
            owner = db.scalar(select(User).where(User.username == "workflowstateowner"))
            assert owner is not None
            workflows = []
            for status in ["pending", "draft_ready", "failed", "cancelled", "imported"]:
                workflow = AIGenerationWorkflow(
                    bank_id=bank["id"],
                    user_id=owner.id,
                    purpose="extend_bank",
                    generation_mode="knowledge_generate",
                    status=status,
                    source_file_name=f"{status}.txt",
                    source_text_snapshot=f"{status} sensitive source",
                    extra_instruction=f"{status} sensitive instruction",
                    error_message=f"{status} sensitive error detail",
                    ai_provider_config_id=None,
                    ai_model_snapshot="mock",
                    ai_base_url_snapshot="example.test",
                )
                db.add(workflow)
                db.flush()
                db.add(
                    ImportJob(
                        user_id=owner.id,
                        bank_id=bank["id"],
                        workflow_id=workflow.id,
                        status=status,
                        desired_visibility="public",
                        type="document_ai",
                    )
                )
                if status == "draft_ready":
                    draft = AIGenerationDraft(workflow_id=workflow.id, bank_id=bank["id"], user_id=owner.id, status="ready")
                    db.add(draft)
                    db.flush()
                    db.add(
                        AIGenerationDraftQuestion(
                            draft_id=draft.id,
                            sort_order=0,
                            type="single",
                            stem="Draft pending question",
                            options_json='[{"label":"A","content":"A","is_correct":true},{"label":"B","content":"B","is_correct":false}]',
                            validation_status="valid",
                        )
                    )
                if status == "imported":
                    db.add(
                        AIGenerationWorkflowStep(
                            workflow_id=workflow.id,
                            step_name="confirm_draft",
                            status="succeeded",
                            output_json='{"question_count": 3}',
                        )
                    )
                workflows.append(workflow)
            db.commit()
            workflow_ids = {workflow.status: workflow.id for workflow in workflows}
        finally:
            db.close()

        logs = client.get(f"/api/v2/banks/{bank['id']}/ai-workflows?page_size=20", headers=reader_headers)
        assert logs.status_code == 200, logs.text
        items = {item["id"]: item for item in logs.json()["items"]}
        for status, workflow_id in workflow_ids.items():
            item = items[workflow_id]
            assert item["status"] == status
            assert item["source_file_name"] is None
            assert item["source_text_snapshot"] is None
            assert item["extra_instruction"] is None
            assert item["error_message"] is None
            assert item["ai_provider_config_id"] is None
            assert item["can_confirm"] is False
            assert item["can_retry"] is False
            assert item["can_cancel"] is False
        assert items[workflow_ids["draft_ready"]]["draft_question_count"] == 1
        assert items[workflow_ids["imported"]]["imported_question_count"] == 3
        assert items[workflow_ids["imported"]]["question_delta"] == 3

        owner_queue = client.get("/api/v2/ai/workflows?page_size=20", headers=headers)
        assert owner_queue.status_code == 200, owner_queue.text
        owner_items = {item["id"]: item for item in owner_queue.json()["items"]}
        failed_owner_item = owner_items[workflow_ids["failed"]]
        assert failed_owner_item["error_message"] == "failed sensitive error detail"
        assert failed_owner_item["source_file_name"] == "failed.txt"


def test_delete_bank_cleans_generation_and_practice_records(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "delete-bank@example.com", "deletebank")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation.client import OpenAICompatibleClient

        def good_ai(*args, **kwargs):
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Delete me",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(OpenAICompatibleClient, "generate_json", lambda self, *args, **kwargs: good_ai(*args, **kwargs))
        response = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Delete Workflow Bank", "desired_visibility": "private", "question_count": "1"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert response.status_code == 200
        bank_id = response.json()["bank_id"]
        workflow_id = response.json()["workflow_id"]
        assert client.post(f"/api/v2/ai/workflows/{workflow_id}/draft/confirm", headers=headers).status_code == 200
        questions = client.get(f"/api/v2/banks/{bank_id}/questions", headers=headers).json()
        question = questions["items"][0]
        session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank_id, "mode": "practice"}).json()
        client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][1]["id"]]},
        )
        assert client.get(f"/api/v2/banks/{bank_id}/mistakes", headers=headers).json()["total"] == 1

        deleted = client.delete(f"/api/v2/banks/{bank_id}", headers=headers)
        assert deleted.status_code == 200, deleted.text
        assert client.get(f"/api/v2/banks/{bank_id}", headers=headers).status_code == 404
        workflow_after_delete = client.get(f"/api/v2/ai/workflows/{workflow_id}", headers=headers)
        assert workflow_after_delete.status_code == 200
        assert workflow_after_delete.json()["bank_id"] is None


def test_v2_banks_returns_domain_shaped_bank_permissions_and_stats():
    with TestClient(app) as client:
        owner_headers = _register(client, "v2-owner@example.com", "v2owner")
        _make_admin("v2owner")
        owner_headers = _login(client, "v2owner")
        visitor_headers = _register(client, "v2-visitor@example.com", "v2visitor")
        admin_headers = _register(client, "v2-admin@example.com", "v2admin")
        _make_admin("v2admin")
        admin_headers = _login(client, "v2admin")

        private_bank = client.post("/api/v2/banks", headers=owner_headers, json={"title": "V2 Private", "visibility": "private"}).json()
        public_bank = client.post("/api/v2/banks", headers=owner_headers, json={"title": "V2 Public", "visibility": "public", "tag_names": ["体系结构"]}).json()
        question = client.post(
            f"/api/v2/banks/{public_bank['id']}/questions",
            headers=owner_headers,
            json={
                "type": "single",
                "stem": "V2 Q",
                "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
            },
        ).json()
        client.post(f"/api/v2/banks/{public_bank['id']}/favorites", headers=visitor_headers)

        public_list = client.get("/api/v2/banks?scope=public&keyword=V2", headers=visitor_headers)
        assert public_list.status_code == 200, public_list.text
        public_item = next(item for item in public_list.json()["items"] if item["id"] == public_bank["id"])
        assert public_item["owner"]["username"] == "v2owner"
        assert public_item["stats"] == {"question_count": 1, "favorite_count": 1}
        assert public_item["permissions"]["can_read"] is True
        assert public_item["permissions"]["can_manage"] is False
        assert public_item["permissions"]["can_export"] is True
        assert public_item["permissions"]["can_view_mistakes"] is True
        assert public_item["permissions"]["can_extend_ai"] is False
        assert public_item["active_workflow"] is None
        assert public_item["tags"][0]["name"] == "体系结构"

        private_for_visitor = client.get(f"/api/v2/banks/{private_bank['id']}", headers=visitor_headers)
        assert private_for_visitor.status_code == 404

        admin_private = client.get(f"/api/v2/banks/{private_bank['id']}", headers=admin_headers)
        assert admin_private.status_code == 200, admin_private.text
        assert admin_private.json()["permissions"]["can_manage"] is True
        assert admin_private.json()["permissions"]["can_extend_ai"] is True

        deleted = client.delete(f"/api/v2/banks/{public_bank['id']}", headers=owner_headers)
        assert deleted.status_code == 200, deleted.text
        assert client.get(f"/api/v2/questions/{question['id']}", headers=owner_headers).status_code == 404


def test_v2_practice_session_answers_results_and_mistakes_use_domain_services():
    with TestClient(app) as client:
        headers = _register(client, "v2-practice@example.com", "v2practice")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "V2 Practice", "visibility": "private"}).json()
        question = client.post(
            f"/api/v2/banks/{bank['id']}/questions",
            headers=headers,
            json={
                "type": "single",
                "stem": "Domain answer?",
                "options": [{"label": "A", "content": "yes", "is_correct": True}, {"label": "B", "content": "no", "is_correct": False}],
                "explanation": "domain service",
            },
        ).json()

        session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice"}).json()
        assert session["bank_title"] == "V2 Practice"
        assert session["answered_count"] == 0

        questions = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()
        assert questions[0]["answer_state"]["is_answered"] is False
        answer = client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][1]["id"]]},
        )
        assert answer.status_code == 200, answer.text
        assert answer.json()["reveal"] is True
        assert answer.json()["correct_labels"] == ["A"]
        assert answer.json()["is_correct"] is False

        restored = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()[0]
        assert restored["answer_state"]["is_answered"] is True
        assert restored["answer_state"]["selected_option_ids"] == [question["options"][1]["id"]]
        assert restored["answer_state"]["correct_labels"] == ["A"]

        result = client.get(f"/api/v2/practice/sessions/{session['id']}/result", headers=headers).json()[0]
        assert result["stem"] == "Domain answer?"
        assert result["selected_labels"] == ["B"]
        assert result["correct_labels"] == ["A"]
        mistakes = client.get(f"/api/v2/banks/{bank['id']}/mistakes", headers=headers).json()
        assert mistakes["total"] == 1
        assert mistakes["items"][0]["stem"] == "Domain answer?"


def test_mistake_attempts_are_concrete_and_resolve_individually():
    with TestClient(app) as client:
        headers = _register(client, "attempts@example.com", "attempts")
        other_headers = _register(client, "attempts-other@example.com", "attemptsother")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Attempt Bank", "visibility": "private"}).json()
        question = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_sample_question_payload("Concrete wrong?")).json()

        for _ in range(2):
            session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice"}).json()
            answer = client.post(
                f"/api/v2/practice/sessions/{session['id']}/answers",
                headers=headers,
                json={"question_id": question["id"], "selected_option_ids": [question["options"][1]["id"]]},
            )
            assert answer.status_code == 200, answer.text

        attempts = client.get(f"/api/v2/banks/{bank['id']}/mistake-attempts", headers=headers).json()
        assert attempts["total"] == 2
        first_attempt = attempts["items"][0]
        assert first_attempt["question_id"] == question["id"]
        assert first_attempt["stem"] == "Concrete wrong?"
        assert first_attempt["selected_labels"] == ["B"]
        assert first_attempt["correct_labels"] == ["A"]
        assert first_attempt["wrong_at"] is not None
        assert client.get(f"/api/v2/banks/{bank['id']}/mistake-attempts", headers=other_headers).status_code == 404

        summary = client.get(f"/api/v2/banks/{bank['id']}/mistakes", headers=headers).json()
        assert summary["total"] == 1
        assert summary["items"][0]["wrong_count"] == 2

        legacy_resolve = client.post(f"/api/v2/banks/{bank['id']}/mistakes/{question['id']}/resolve", headers=headers)
        assert legacy_resolve.status_code == 410, legacy_resolve.text
        assert client.get(f"/api/v2/banks/{bank['id']}/mistake-attempts", headers=headers).json()["total"] == 2

        resolved = client.post(f"/api/v2/banks/{bank['id']}/mistake-attempts/{first_attempt['id']}/resolve", headers=headers)
        assert resolved.status_code == 200, resolved.text
        unresolved = client.get(f"/api/v2/banks/{bank['id']}/mistake-attempts", headers=headers).json()
        assert unresolved["total"] == 1
        assert unresolved["items"][0]["id"] != first_attempt["id"]

        second_attempt_id = unresolved["items"][0]["id"]
        assert client.post(f"/api/v2/banks/{bank['id']}/mistake-attempts/{second_attempt_id}/resolve", headers=headers).status_code == 200
        assert client.get(f"/api/v2/banks/{bank['id']}/mistake-attempts", headers=headers).json()["total"] == 0
        assert client.get(f"/api/v2/banks/{bank['id']}/mistakes?resolved=false", headers=headers).json()["total"] == 0


def test_mistake_practice_sessions_are_source_scoped_and_resumable():
    with TestClient(app) as client:
        headers = _register(client, "attempt-practice@example.com", "attemptpractice")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Attempt Practice", "visibility": "private"}).json()
        first = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_sample_question_payload("Wrong one?")).json()
        second = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_sample_question_payload("Wrong two?")).json()

        first_session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice", "shuffle_questions": False}).json()
        client.post(
            f"/api/v2/practice/sessions/{first_session['id']}/answers",
            headers=headers,
            json={"question_id": first["id"], "selected_option_ids": [first["options"][1]["id"]]},
        )

        second_session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice", "shuffle_questions": False}).json()
        client.post(
            f"/api/v2/practice/sessions/{second_session['id']}/answers",
            headers=headers,
            json={"question_id": second["id"], "selected_option_ids": [second["options"][1]["id"]]},
        )

        bank_review = client.post(f"/api/v2/banks/{bank['id']}/mistakes/practice-sessions", headers=headers)
        assert bank_review.status_code == 200, bank_review.text
        bank_review_data = bank_review.json()
        assert bank_review_data["mode"] == "mistake_review"
        assert bank_review_data["mistake_source_type"] == "bank"
        assert bank_review_data["mistake_source_id"] == bank["id"]
        assert bank_review_data["total_questions"] == 2

        same_bank_review = client.post(f"/api/v2/banks/{bank['id']}/mistakes/practice-sessions", headers=headers).json()
        assert same_bank_review["id"] == bank_review_data["id"]

        record_review = client.post(f"/api/v2/practice/sessions/{first_session['id']}/mistake-practice-sessions", headers=headers)
        assert record_review.status_code == 200, record_review.text
        record_review_data = record_review.json()
        assert record_review_data["mistake_source_type"] == "practice_session"
        assert record_review_data["mistake_source_id"] == first_session["id"]
        assert record_review_data["total_questions"] == 1
        record_questions = client.get(f"/api/v2/practice/sessions/{record_review_data['id']}/questions", headers=headers).json()
        assert [item["id"] for item in record_questions] == [first["id"]]

        same_record_review = client.post(f"/api/v2/practice/sessions/{first_session['id']}/mistake-practice-sessions", headers=headers).json()
        assert same_record_review["id"] == record_review_data["id"]


def test_delete_session_removes_attempts_and_rebuilds_mistake_summary():
    with TestClient(app) as client:
        headers = _register(client, "delete-attempts@example.com", "deleteattempts")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Delete Attempts", "visibility": "private"}).json()
        question = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_sample_question_payload("Delete wrong?")).json()
        sessions = []
        for _ in range(2):
            session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice"}).json()
            sessions.append(session)
            client.post(
                f"/api/v2/practice/sessions/{session['id']}/answers",
                headers=headers,
                json={"question_id": question["id"], "selected_option_ids": [question["options"][1]["id"]]},
            )

        assert client.get(f"/api/v2/banks/{bank['id']}/mistake-attempts", headers=headers).json()["total"] == 2
        assert client.delete(f"/api/v2/practice/sessions/{sessions[0]['id']}", headers=headers).status_code == 200
        attempts_after_delete = client.get(f"/api/v2/banks/{bank['id']}/mistake-attempts", headers=headers).json()
        assert attempts_after_delete["total"] == 1
        summary = client.get(f"/api/v2/banks/{bank['id']}/mistakes", headers=headers).json()
        assert summary["total"] == 1
        assert summary["items"][0]["wrong_count"] == 1


def test_v2_ai_workflow_create_draft_confirm_is_workflow_centred(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "v2-ai@example.com", "v2ai")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation.client import OpenAICompatibleClient

        def good_ai(*args, **kwargs):
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Workflow v2 question",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(OpenAICompatibleClient, "generate_json", lambda self, *args, **kwargs: good_ai(*args, **kwargs))
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "V2 Workflow", "desired_visibility": "private", "question_count": "1"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert created.status_code == 200, created.text
        payload = created.json()
        assert payload["workflow_id"] is not None
        assert payload["job_id"] is not None

        workflows = client.get("/api/v2/ai/workflows", headers=headers).json()
        assert workflows["items"][0]["id"] == payload["workflow_id"]
        assert workflows["items"][0]["status"] == "draft_ready"
        draft = client.get(f"/api/v2/ai/workflows/{payload['workflow_id']}/draft", headers=headers).json()
        assert draft["questions"][0]["stem"] == "Workflow v2 question"

        confirmed = client.post(f"/api/v2/ai/workflows/{payload['workflow_id']}/draft/confirm", headers=headers)
        assert confirmed.status_code == 200, confirmed.text
        bank = client.get(f"/api/v2/banks/{payload['bank_id']}", headers=headers).json()
        assert bank["stats"]["question_count"] == 1
        assert bank["generation_status"] == "succeeded"


def test_ai_workflow_accepts_multiple_source_files_and_preserves_section_markers(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "multi-file-ai@example.com", "multifileai")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        seen_texts = []

        def good_ai(*args, **kwargs):
            seen_texts.append(args[1])
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Multi file question",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", good_ai)
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Multi File AI", "question_count": "1"},
            files=[
                ("files", ("alpha.txt", b"alpha content", "text/plain")),
                ("files", ("beta.txt", b"beta content", "text/plain")),
            ],
        )
        assert created.status_code == 200, created.text
        workflow = client.get(f"/api/v2/ai/workflows/{created.json()['workflow_id']}", headers=headers).json()
        assert workflow["source_file_name"] == "alpha.txt 等 2 个文件"
        assert "===== 文件: alpha.txt =====" in workflow["source_text_snapshot"]
        assert "alpha content" in workflow["source_text_snapshot"]
        assert "===== 文件: beta.txt =====" in workflow["source_text_snapshot"]
        assert "beta content" in workflow["source_text_snapshot"]
        assert workflow["source_text_snapshot"] == seen_texts[-1]


def test_ai_workflow_multi_file_source_name_is_bounded(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "long-files-ai@example.com", "longfilesai")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", lambda *args, **kwargs: {"questions": [_sample_question_payload("长文件名题")]})
        long_alpha = f"{'a' * 240}.txt"
        long_beta = f"{'b' * 240}.txt"
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Long File Names", "question_count": "1"},
            files=[
                ("files", (long_alpha, b"alpha long content", "text/plain")),
                ("files", (long_beta, b"beta long content", "text/plain")),
            ],
        )
        assert created.status_code == 200, created.text
        workflow = client.get(f"/api/v2/ai/workflows/{created.json()['workflow_id']}", headers=headers).json()
        assert workflow["source_file_name"].endswith(" 等 2 个文件")
        assert len(workflow["source_file_name"]) <= 255
        assert f"===== 文件: {long_alpha} =====" in workflow["source_text_snapshot"]
        assert f"===== 文件: {long_beta} =====" in workflow["source_text_snapshot"]


def test_confirm_draft_imports_latest_edited_persisted_questions(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "draft-edit-confirm@example.com", "drafteditconfirm")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        def two_questions(*args, **kwargs):
            return {
                "questions": [
                    _sample_question_payload("原始第一题"),
                    {
                        **_sample_question_payload("原始第二题"),
                        "options": [{"label": "A", "content": "旧正确", "is_correct": True}, {"label": "B", "content": "旧错误", "is_correct": False}],
                    },
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", two_questions)
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Draft Edit Confirm", "question_count": "2"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert created.status_code == 200, created.text
        workflow_id = created.json()["workflow_id"]
        draft = client.get(f"/api/v2/ai/workflows/{workflow_id}/draft", headers=headers).json()
        assert len(draft["questions"]) == 2
        edited_question = draft["questions"][1]
        edited_question["stem"] = "编辑后的唯一题"
        edited_question["options"] = [{"label": "A", "content": "新正确", "is_correct": True}, {"label": "B", "content": "新错误", "is_correct": False}]
        draft["questions"] = [edited_question]

        saved = client.patch(f"/api/v2/ai/workflows/{workflow_id}/draft", headers=headers, json=draft)
        assert saved.status_code == 200, saved.text
        assert len(saved.json()["questions"]) == 1
        assert saved.json()["questions"][0]["stem"] == "编辑后的唯一题"

        confirmed = client.post(f"/api/v2/ai/workflows/{workflow_id}/draft/confirm", headers=headers)
        assert confirmed.status_code == 200, confirmed.text
        questions = client.get(f"/api/v2/banks/{created.json()['bank_id']}/questions?all=true", headers=headers).json()["items"]
        assert len(questions) == 1
        assert questions[0]["stem"] == "编辑后的唯一题"
        assert questions[0]["options"][0]["content"] == "新正确"


def test_v2_ai_workflow_cancel_create_bank_preserves_audit_and_deletes_shell(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "cancel-workflow@example.com", "cancelworkflow")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        def good_ai(*args, **kwargs):
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Draft before cancel",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", good_ai)
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Cancel Shell", "desired_visibility": "private", "question_count": "1"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert created.status_code == 200, created.text
        payload = created.json()
        assert client.get(f"/api/v2/banks/{payload['bank_id']}", headers=headers).status_code == 200

        cancelled = client.post(
            f"/api/v2/ai/workflows/{payload['workflow_id']}/cancel",
            headers=headers,
            data={"cancel_reason": "不需要了"},
        )
        assert cancelled.status_code == 200, cancelled.text
        workflow = client.get(f"/api/v2/ai/workflows/{payload['workflow_id']}", headers=headers).json()
        assert workflow["status"] == "cancelled"
        assert workflow["bank_id"] is None
        assert workflow["bank_title_snapshot"] == "Cancel Shell"
        assert workflow["cancel_reason"] == "不需要了"
        assert client.get(f"/api/v2/banks/{payload['bank_id']}", headers=headers).status_code == 404
        db = SessionLocal()
        try:
            assert db.scalar(select(AuditEvent).where(AuditEvent.action == "workflow.cancel", AuditEvent.target_id == payload["workflow_id"])) is not None
        finally:
            db.close()


def test_v2_ai_workflow_retry_failed_creates_new_workflow(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "retry-workflow@example.com", "retryworkflow")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        mode = {"ok": False}

        def ai(*args, **kwargs):
            if not mode["ok"]:
                return {"questions": []}
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Retry success",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", ai)
        failed = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Retry Bank", "question_count": "1"},
            files={"file": ("bad.txt", b"bad source", "text/plain")},
        )
        assert failed.status_code == 200, failed.text
        failed_workflow = client.get(f"/api/v2/ai/workflows/{failed.json()['workflow_id']}", headers=headers).json()
        assert failed_workflow["status"] == "failed"
        original_bank_id = failed_workflow["bank_id"]

        mode["ok"] = True
        retried = client.post(
            f"/api/v2/ai/workflows/{failed_workflow['id']}/retry",
            headers=headers,
            data={
                "source_text": "edited source",
                "question_count_mode": "fixed",
                "question_count": "1",
                "title": "Retry Bank 2",
                "description": "retry description",
                    "desired_visibility": "private",
            },
        )
        assert retried.status_code == 200, retried.text
        new_workflow = client.get(f"/api/v2/ai/workflows/{retried.json()['workflow_id']}", headers=headers).json()
        assert new_workflow["status"] == "draft_ready"
        assert new_workflow["retry_of_workflow_id"] == failed_workflow["id"]
        assert new_workflow["bank_id"] == original_bank_id
        assert new_workflow["source_text_snapshot"] == "edited source"
        assert new_workflow["bank_title_snapshot"] == "Retry Bank 2"
        assert new_workflow["draft_question_count"] == 1
        reused_bank = client.get(f"/api/v2/banks/{original_bank_id}", headers=headers).json()
        assert reused_bank["title"] == "Retry Bank 2"
        assert reused_bank["description"] == "retry description"
        assert reused_bank["desired_visibility"] == "private"
        mine = client.get("/api/v2/banks?scope=mine&page_size=50", headers=headers).json()["items"]
        matching_ids = [item["id"] for item in mine if item["title"] in {"Retry Bank", "Retry Bank 2"}]
        assert matching_ids == [original_bank_id]
        old_after_retry = client.get(f"/api/v2/ai/workflows/{failed_workflow['id']}", headers=headers).json()
        assert old_after_retry["retried_by_workflow_id"] == new_workflow["id"]

        second_retry = client.post(
            f"/api/v2/ai/workflows/{failed_workflow['id']}/retry",
            headers=headers,
            data={"source_text": "another source", "question_count_mode": "fixed", "question_count": "1", "title": "Retry Bank 3"},
        )
        assert second_retry.status_code == 400
        cancelled_old = client.post(
            f"/api/v2/ai/workflows/{failed_workflow['id']}/cancel",
            headers=headers,
            data={"cancel_reason": "too late"},
        )
        assert cancelled_old.status_code == 400
        db = SessionLocal()
        try:
            assert db.scalar(select(AuditEvent).where(AuditEvent.action == "workflow.retry", AuditEvent.target_id == failed_workflow["id"])) is not None
        finally:
            db.close()


def test_v2_ai_workflow_retry_cancelled_create_bank_creates_new_shell(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "retry-cancelled-shell@example.com", "retrycancelledshell")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        def good_ai(*args, **kwargs):
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Retry cancelled shell",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", good_ai)
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Cancelled Shell", "question_count": "1"},
            files={"file": ("material.txt", b"source", "text/plain")},
        )
        payload = created.json()
        assert client.post(f"/api/v2/ai/workflows/{payload['workflow_id']}/cancel", headers=headers).status_code == 200
        cancelled = client.get(f"/api/v2/ai/workflows/{payload['workflow_id']}", headers=headers).json()
        assert cancelled["bank_id"] is None

        retried = client.post(
            f"/api/v2/ai/workflows/{payload['workflow_id']}/retry",
            headers=headers,
            data={"source_text": "retry source", "question_count_mode": "fixed", "question_count": "1", "title": "New Shell"},
        )
        assert retried.status_code == 200, retried.text
        new_payload = retried.json()
        assert new_payload["bank_id"] is not None
        new_workflow = client.get(f"/api/v2/ai/workflows/{new_payload['workflow_id']}", headers=headers).json()
        assert new_workflow["retry_of_workflow_id"] == payload["workflow_id"]
        assert new_workflow["bank_title_snapshot"] == "New Shell"


def test_v2_ai_workflow_detail_owner_only_and_rq_enqueue(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_workflow_execution_mode", "rq")

    from app.domains.ai_generation import facade as ai_generation
    from app.domains.ai_generation.workflow_state import now_utc
    import app.domains.ai_generation.queue as workflow_queue

    def should_not_run(*args, **kwargs):
        raise AssertionError("RQ mode should enqueue instead of running synchronously")

    def fake_enqueue(workflow_id, job):
        job.queue_job_id = f"rq-{workflow_id}"
        job.enqueued_at = now_utc()

    monkeypatch.setattr(ai_generation, "_call_openai_compatible", should_not_run)
    monkeypatch.setattr(workflow_queue, "enqueue_workflow", fake_enqueue)

    with TestClient(app) as client:
        headers = _register(client, "rq-workflow@example.com", "rqworkflow")
        other_headers = _register(client, "rq-workflow-other@example.com", "rqworkflowother")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "RQ Bank", "question_count": "1", "extra_instruction": "owner only instruction"},
            files={"file": ("rq.txt", b"owner only source", "text/plain")},
        )
        assert created.status_code == 200, created.text
        workflow_id = created.json()["workflow_id"]
        workflow = client.get(f"/api/v2/ai/workflows/{workflow_id}", headers=headers).json()
        assert workflow["status"] == "pending"
        assert workflow["queue_job_id"] == f"rq-{workflow_id}"
        assert workflow["enqueued_at"] is not None

        detail = client.get(f"/api/v2/ai/workflows/{workflow_id}/detail", headers=headers)
        assert detail.status_code == 200, detail.text
        detail_payload = detail.json()
        assert detail_payload["source_text_snapshot"] == "owner only source"
        assert detail_payload["extra_instruction"] == "owner only instruction"
        assert detail_payload["queue_job_id"] == f"rq-{workflow_id}"
        assert detail_payload["steps"] == []
        assert client.get(f"/api/v2/ai/workflows/{workflow_id}/detail", headers=other_headers).status_code == 404


def test_v2_rq_enqueue_failure_marks_create_workflow_failed(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_workflow_execution_mode", "rq")

    import app.domains.ai_generation.queue as workflow_queue

    def broken_enqueue(*args, **kwargs):
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(workflow_queue, "enqueue_workflow", broken_enqueue)

    with TestClient(app) as client:
        headers = _register(client, "rq-fail-create@example.com", "rqfailcreate")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "RQ Failure Bank", "desired_visibility": "private", "question_count": "1"},
            files={"file": ("rq-fail.txt", b"source", "text/plain")},
        )
        assert created.status_code == 200, created.text
        payload = created.json()
        workflow = client.get(f"/api/v2/ai/workflows/{payload['workflow_id']}", headers=headers).json()
        assert workflow["status"] == "failed"
        assert "队列入队失败" in workflow["error_message"]
        assert "redis unavailable" in workflow["error_message"]
        bank = client.get(f"/api/v2/banks/{payload['bank_id']}", headers=headers).json()
        assert bank["generation_status"] == "failed"
        assert bank["visibility"] == "private"


def test_v2_rq_enqueue_failure_does_not_pollute_extend_bank(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_workflow_execution_mode", "rq")

    import app.domains.ai_generation.queue as workflow_queue

    def broken_enqueue(*args, **kwargs):
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(workflow_queue, "enqueue_workflow", broken_enqueue)

    with TestClient(app) as client:
        headers = _register(client, "rq-fail-extend@example.com", "rqfailextend")
        _make_admin("rqfailextend")
        headers = _login(client, "rqfailextend")
        reader_headers = _register(client, "rq-fail-reader@example.com", "rqfailreader")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Extend RQ Failure", "visibility": "public"}).json()
        before = client.get(f"/api/v2/banks/{bank['id']}", headers=reader_headers).json()

        created = client.post(
            f"/api/v2/banks/{bank['id']}/ai-workflows",
            headers=headers,
            data={"question_count": "1"},
            files={"file": ("extend-rq-fail.txt", b"source", "text/plain")},
        )
        assert created.status_code == 200, created.text
        workflow = client.get(f"/api/v2/ai/workflows/{created.json()['workflow_id']}", headers=headers).json()
        assert workflow["status"] == "failed"
        assert "队列入队失败" in workflow["error_message"]
        after = client.get(f"/api/v2/banks/{bank['id']}", headers=reader_headers)
        assert after.status_code == 200, after.text
        assert after.json()["generation_status"] == before["generation_status"]


def test_cancelled_create_workflow_worker_stops_after_shell_deleted(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "cancel-worker@example.com", "cancelworker")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        def good_ai(*args, **kwargs):
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Cancel worker",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", good_ai)
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Cancel Worker Shell", "question_count": "1"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert created.status_code == 200, created.text
        payload = created.json()
        config_id = client.get(f"/api/v2/ai/workflows/{payload['workflow_id']}", headers=headers).json()["ai_provider_config_id"]
        assert client.post(f"/api/v2/ai/workflows/{payload['workflow_id']}/cancel", headers=headers).status_code == 200

        from app.domains.ai_generation.workflow_runtime import WorkflowCancelled, WorkflowRuntime

        db = SessionLocal()
        try:
            with pytest.raises(WorkflowCancelled):
                WorkflowRuntime(db).load_objects(
                    {
                        "db": db,
                        "workflow_id": payload["workflow_id"],
                        "bank_id": payload["bank_id"],
                        "config_id": config_id,
                    }
                )
        finally:
            db.close()


def test_v2_ai_workflow_retry_draft_ready_head_only(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "retry-draft@example.com", "retrydraft")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        def good_ai(*args, **kwargs):
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Draft retry success",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", good_ai)
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Draft Retry", "question_count": "1"},
            files={"file": ("material.txt", b"original source", "text/plain")},
        )
        assert created.status_code == 200, created.text
        original = client.get(f"/api/v2/ai/workflows/{created.json()['workflow_id']}", headers=headers).json()
        assert original["status"] == "draft_ready"
        assert original["can_retry"] is True

        retried = client.post(
            f"/api/v2/ai/workflows/{original['id']}/retry",
            headers=headers,
            data={"source_text": "retry from draft", "question_count_mode": "fixed", "question_count": "1", "title": "Draft Retry 2"},
        )
        assert retried.status_code == 200, retried.text
        old_after_retry = client.get(f"/api/v2/ai/workflows/{original['id']}", headers=headers).json()
        assert old_after_retry["retried_by_workflow_id"] == retried.json()["workflow_id"]
        assert old_after_retry["can_retry"] is False
        assert old_after_retry["can_confirm"] is False
        old_confirm = client.post(f"/api/v2/ai/workflows/{original['id']}/draft/confirm", headers=headers)
        assert old_confirm.status_code == 400
        assert "重新生成" in old_confirm.json()["error"]["message"]
        assert client.post(f"/api/v2/ai/workflows/{original['id']}/cancel", headers=headers).status_code == 400

        new_workflow = client.get(f"/api/v2/ai/workflows/{retried.json()['workflow_id']}", headers=headers).json()
        assert new_workflow["status"] == "draft_ready"
        assert new_workflow["can_confirm"] is True
        new_confirm = client.post(f"/api/v2/ai/workflows/{new_workflow['id']}/draft/confirm", headers=headers)
        assert new_confirm.status_code == 200, new_confirm.text


def test_v2_ai_workflow_extends_existing_bank(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "v2-extend@example.com", "v2extend")
        _make_admin("v2extend")
        headers = _login(client, "v2extend")
        visitor_headers = _register(client, "v2-extend-visitor@example.com", "v2extendvisitor")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Extend V2", "visibility": "public"}).json()
        client.post(
            f"/api/v2/banks/{bank['id']}/questions",
            headers=headers,
            json={
                "type": "single",
                "stem": "Existing",
                "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
            },
        )

        from app.domains.ai_generation.client import OpenAICompatibleClient

        def good_ai(*args, **kwargs):
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Extended via v2",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(OpenAICompatibleClient, "generate_json", lambda self, *args, **kwargs: good_ai(*args, **kwargs))
        forbidden = client.post(
            f"/api/v2/banks/{bank['id']}/ai-workflows",
            headers=visitor_headers,
            data={"question_count": "1"},
            files={"file": ("more.txt", b"more", "text/plain")},
        )
        assert forbidden.status_code == 404

        created = client.post(
            f"/api/v2/banks/{bank['id']}/ai-workflows",
            headers=headers,
            data={"question_count": "1", "extra_instruction": "避免和 Existing 重复"},
            files={"file": ("more.txt", b"more", "text/plain")},
        )
        assert created.status_code == 200, created.text
        payload = created.json()
        draft = client.get(f"/api/v2/ai/workflows/{payload['workflow_id']}/draft", headers=headers).json()
        assert draft["questions"][0]["stem"] == "Extended via v2"
        assert client.post(f"/api/v2/ai/workflows/{payload['workflow_id']}/draft/confirm", headers=headers).status_code == 200
        after = client.get(f"/api/v2/banks/{bank['id']}", headers=headers).json()
        assert after["stats"]["question_count"] == 2
        assert after["visibility"] == "public"


def test_v2_extend_workflow_inherit_context_toggle(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "context-toggle@example.com", "contexttoggle")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Context Bank", "visibility": "private"}).json()
        assert client.patch(f"/api/v2/banks/{bank['id']}/ai-context", headers=headers, json={"ai_context": "题库上下文：偏工程应用"}).status_code == 200
        client.post(
            f"/api/v2/banks/{bank['id']}/questions",
            headers=headers,
            json={
                "type": "single",
                "stem": "已有题目摘要",
                "options": [{"label": "A", "content": "SECRET_OPTION", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
            },
        )

        from app.domains.ai_generation import facade as ai_generation

        seen_texts = []

        def good_ai(*args, **kwargs):
            seen_texts.append(args[1])
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Context generated",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", good_ai)
        no_context = client.post(
            f"/api/v2/banks/{bank['id']}/ai-workflows",
            headers=headers,
            data={"question_count": "1", "inherit_context": "false"},
            files={"file": ("more.txt", b"fresh source", "text/plain")},
        )
        assert no_context.status_code == 200, no_context.text
        assert "题库上下文：偏工程应用" not in seen_texts[-1]
        assert "已有题目摘要" not in seen_texts[-1]

        with_context = client.post(
            f"/api/v2/banks/{bank['id']}/ai-workflows",
            headers=headers,
            data={"question_count": "1", "inherit_context": "true"},
            files={"file": ("more.txt", b"fresh source", "text/plain")},
        )
        assert with_context.status_code == 200, with_context.text
        assert "题库上下文：偏工程应用" in seen_texts[-1]
        assert "已有题目摘要" not in seen_texts[-1]

        with_questions = client.post(
            f"/api/v2/banks/{bank['id']}/ai-workflows",
            headers=headers,
            data={"question_count": "1", "inherit_context": "false", "include_existing_questions": "true"},
            files={"file": ("more.txt", b"fresh source", "text/plain")},
        )
        assert with_questions.status_code == 200, with_questions.text
        assert "题库上下文：偏工程应用" not in seen_texts[-1]
        assert "已有题目摘要" in seen_texts[-1]
        assert "[单选] 已有题目摘要" in seen_texts[-1]
        assert "SECRET_OPTION" not in seen_texts[-1]
        assert "最近成功 workflow" not in seen_texts[-1]


def test_v2_extend_workflow_existing_question_context_truncates(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "context-truncate@example.com", "contexttruncate")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Large Context", "visibility": "private"}).json()
        for index in range(4):
            client.post(
                f"/api/v2/banks/{bank['id']}/questions",
                headers=headers,
                json={
                    "type": "single",
                    "stem": f"长题干 {index} " + ("上下文" * 30),
                    "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                },
            )

        from app.domains.ai_generation import facade as ai_generation
        from app.domains.ai_generation import context as context_module

        seen_texts = []

        def good_ai(*args, **kwargs):
            seen_texts.append(args[1])
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Context truncated generated",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(context_module, "EXISTING_QUESTION_CONTEXT_CHAR_BUDGET", 90)
        monkeypatch.setattr(ai_generation, "_call_openai_compatible", good_ai)
        created = client.post(
            f"/api/v2/banks/{bank['id']}/ai-workflows",
            headers=headers,
            data={"question_count": "1", "include_existing_questions": "true"},
            files={"file": ("more.txt", b"fresh source", "text/plain")},
        )
        assert created.status_code == 200, created.text
        assert "已有题目摘要因长度限制已截断" in seen_texts[-1]


def test_bank_parse_mode_without_question_count_and_detailed_errors(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "parse@example.com", "parseuser")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        seen_modes = []
        seen_extra = []

        def parsed_ai(*args, **kwargs):
            seen_modes.append(args[4])
            seen_extra.append(args[5])
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "Parsed question",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", parsed_ai)
        response = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Parsed Bank", "desired_visibility": "private", "generation_mode": "bank_parse", "extra_instruction": "保留原题编号"},
            files={"file": ("bank.txt", b"Q1 Parsed question", "text/plain")},
        )
        assert response.status_code == 200
        assert seen_modes == ["bank_parse"]
        assert seen_extra == ["保留原题编号"]
        job = client.get(f"/api/v2/ai/workflows/{response.json()['workflow_id']}", headers=headers).json()
        assert job["type"] == "bank_parse_ai"
        assert job["status"] == "draft_ready"
        assert job["draft_question_count"] == 1
        bank = client.get(f"/api/v2/banks/{response.json()['bank_id']}", headers=headers).json()
        assert bank["question_count"] == 0
        draft = client.get(f"/api/v2/ai/workflows/{job['id']}/draft", headers=headers).json()
        assert draft["questions"][0]["stem"] == "Parsed question"
        assert client.post(f"/api/v2/ai/workflows/{job['id']}/draft/confirm", headers=headers).status_code == 200
        questions = client.get(f"/api/v2/banks/{bank['id']}/questions", headers=headers).json()
        assert questions["items"][0]["source"] == "ai_generated"
        assert questions["items"][0]["generated_model"] == "mock"

        def bad_json(*args, **kwargs):
            return {}

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", bad_json)
        bad_response = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Bad Parsed Bank", "desired_visibility": "private", "generation_mode": "bank_parse"},
            files={"file": ("bank.txt", b"bad", "text/plain")},
        )
        bad_job = client.get(f"/api/v2/ai/workflows/{bad_response.json()['workflow_id']}", headers=headers).json()
        assert bad_job["status"] == "failed"
        assert "题库解析失败" in bad_job["error_message"]
        assert "缺少 questions" in bad_job["error_message"]

        too_long = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Too Long", "desired_visibility": "private", "generation_mode": "bank_parse", "extra_instruction": "x" * 2001},
            files={"file": ("bank.txt", b"bad", "text/plain")},
        )
        assert too_long.status_code == 422
        assert "额外指令" in too_long.json()["error"]["message"]


def test_ai_generation_success_public_after_write(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "ok@example.com", "okuser")
        _make_admin("okuser")
        headers = _login(client, "okuser")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        def good_ai(*args, **kwargs):
            return {
                "bank_description": "AI generated description",
                "questions": [
                    {
                        "type": "single",
                        "stem": "Q",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                        "explanation": "E",
                    }
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", good_ai)
        response = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "AI Bank", "desired_visibility": "public", "question_count": "1"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        bank = client.get(f"/api/v2/banks/{response.json()['bank_id']}", headers=headers).json()
        assert bank["generation_status"] == "processing"
        assert bank["visibility"] == "private"
        assert bank["question_count"] == 0
        assert bank["description"] is None
        assert client.post(f"/api/v2/ai/workflows/{response.json()['workflow_id']}/draft/confirm", headers=headers).status_code == 200
        imported_bank = client.get(f"/api/v2/banks/{response.json()['bank_id']}", headers=headers).json()
        assert imported_bank["generation_status"] == "succeeded"
        assert imported_bank["visibility"] == "public"
        assert imported_bank["question_count"] == 1

        response_with_description = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "AI Bank With Description", "desired_visibility": "private", "question_count": "1", "generate_description": "true"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert client.post(f"/api/v2/ai/workflows/{response_with_description.json()['workflow_id']}/draft/confirm", headers=headers).status_code == 200
        described = client.get(f"/api/v2/banks/{response_with_description.json()['bank_id']}", headers=headers).json()
        assert described["description"] == "AI generated description"


def test_v2_users_profile_ai_provider_and_admin_management():
    with TestClient(app) as client:
        user_headers = _register(client, "100200300@qq.com", "v2user")
        admin_headers = _register(client, "v2-users-admin@example.com", "v2usersadmin")
        _make_admin("v2usersadmin")
        admin_headers = _login(client, "v2usersadmin")

        me = client.get("/api/v2/users/me", headers=user_headers)
        assert me.status_code == 200, me.text
        assert me.json()["username"] == "v2user"

        updated = client.patch(
            "/api/v2/users/me",
            headers=user_headers,
            json={"display_name": "V2 User", "bio": "bio", "avatar_source": "qq_email"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["display_name"] == "V2 User"
        assert updated.json()["avatar_url"]

        assert client.post("/api/v2/users/me/change-password", headers=user_headers, json={"old_password": "bad", "new_password": "newpass123"}).status_code == 400
        assert client.post("/api/v2/users/me/change-password", headers=user_headers, json={"old_password": "password123", "new_password": "newpass123"}).status_code == 200
        assert _login(client, "v2user", "newpass123")

        config = client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=user_headers,
            json={"name": "", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "v2-model", "is_default": True},
        )
        assert config.status_code == 200, config.text
        assert config.json()["name"] == ""
        configs = client.get("/api/v2/users/me/ai-provider-configs", headers=user_headers).json()
        assert len(configs) == 1
        assert "api_key" not in configs[0]
        assert configs[0]["has_api_key"] is True
        patch_key = client.patch(f"/api/v2/users/me/ai-provider-configs/{config.json()['id']}", headers=user_headers, json={"api_key": "new"})
        assert patch_key.status_code == 400
        renamed = client.patch(f"/api/v2/users/me/ai-provider-configs/{config.json()['id']}", headers=user_headers, json={"name": "renamed"})
        assert renamed.status_code == 200
        assert renamed.json()["name"] == "renamed"

        public = client.get(f"/api/v2/users/{me.json()['id']}", headers=user_headers)
        assert public.status_code == 200, public.text
        assert public.json()["username"] == "v2user"
        search = client.get("/api/v2/users/search?keyword=v2user", headers=user_headers).json()
        assert search["total"] >= 1

        users = client.get("/api/v2/admin/users?keyword=v2user", headers=admin_headers)
        assert users.status_code == 200, users.text
        target_id = next(item["id"] for item in users.json()["items"] if item["username"] == "v2user")
        admin_update = client.patch(f"/api/v2/admin/users/{target_id}", headers=admin_headers, json={"display_name": "Admin Edited", "is_active": False})
        assert admin_update.status_code == 200, admin_update.text
        assert admin_update.json()["display_name"] == "Admin Edited"
        assert admin_update.json()["is_active"] is False
        assert client.patch(f"/api/v2/admin/users/{target_id}", headers=admin_headers, json={"role": "admin"}).status_code == 422

        client.patch(f"/api/v2/admin/users/{target_id}", headers=admin_headers, json={"is_active": True})
        reset = client.post(f"/api/v2/admin/users/{target_id}/reset-password", headers=admin_headers)
        assert reset.status_code == 200, reset.text
        assert _login(client, "v2user", reset.json()["temporary_password"])
        admin_id = client.get("/api/v2/users/me", headers=admin_headers).json()["id"]
        assert client.post(f"/api/v2/admin/users/{admin_id}/reset-password", headers=admin_headers).status_code == 400
        assert client.get("/api/v2/admin/users", headers=user_headers).status_code == 403


def test_deleting_ai_provider_preserves_workflow_history_and_snapshots(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "provider-history@example.com", "providerhistory")
        config = client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "history", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "history-model", "is_default": True},
        ).json()

        from app.domains.ai_generation import facade as ai_generation

        def good_ai(*args, **kwargs):
            return {
                "questions": [
                    {
                        "type": "single",
                        "stem": "History Q",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", good_ai)
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Provider History", "desired_visibility": "private", "question_count": "1"},
            files={"file": ("material.txt", b"content", "text/plain")},
        ).json()
        assert client.delete(f"/api/v2/users/me/ai-provider-configs/{config['id']}", headers=headers).status_code == 200

        workflow = client.get(f"/api/v2/ai/workflows/{created['workflow_id']}", headers=headers)
        assert workflow.status_code == 200, workflow.text
        assert workflow.json()["ai_model_snapshot"] == "history-model"
        job = client.get(f"/api/v2/ai/workflows/{created['workflow_id']}", headers=headers)
        assert job.status_code == 200, job.text
        assert job.json()["ai_model_snapshot"] == "history-model"

        db = SessionLocal()
        try:
            stored_workflow = db.get(AIGenerationWorkflow, created["workflow_id"])
            stored_job = db.get(ImportJob, created["job_id"])
            assert stored_workflow.ai_provider_config_id is None
            assert stored_job.ai_provider_config_id is None
        finally:
            db.close()


def test_v2_question_crud_permissions_and_json_import_export():
    with TestClient(app) as client:
        owner_headers = _register(client, "v2-q-owner@example.com", "v2qowner")
        _make_admin("v2qowner")
        owner_headers = _login(client, "v2qowner")
        visitor_headers = _register(client, "v2-q-visitor@example.com", "v2qvisitor")
        admin_headers = _register(client, "v2-q-admin@example.com", "v2qadmin")
        _make_admin("v2qadmin")
        admin_headers = _login(client, "v2qadmin")

        private_bank = client.post("/api/v2/banks", headers=owner_headers, json={"title": "Private Q", "visibility": "private"}).json()
        public_bank = client.post("/api/v2/banks", headers=owner_headers, json={"title": "Public Q", "visibility": "public", "tag_names": ["原标签"]}).json()
        question_payload = {
            "type": "single",
            "stem": "Original stem",
            "options": [{"label": "A", "content": "Right", "is_correct": True}, {"label": "B", "content": "Wrong", "is_correct": False}],
            "explanation": "Because",
        }

        created = client.post(f"/api/v2/banks/{public_bank['id']}/questions", headers=owner_headers, json=question_payload)
        assert created.status_code == 200, created.text
        question_id = created.json()["id"]
        assert client.get(f"/api/v2/banks/{public_bank['id']}", headers=owner_headers).json()["stats"]["question_count"] == 1

        visitor_list = client.get(f"/api/v2/banks/{public_bank['id']}/questions", headers=visitor_headers)
        assert visitor_list.status_code == 200, visitor_list.text
        assert visitor_list.json()["items"][0]["stem"] == "Original stem"
        assert client.get(f"/api/v2/banks/{private_bank['id']}/questions", headers=visitor_headers).status_code == 404
        assert client.post(f"/api/v2/banks/{public_bank['id']}/questions", headers=visitor_headers, json=question_payload).status_code == 404

        patched = client.patch(
            f"/api/v2/questions/{question_id}",
            headers=admin_headers,
            json={**question_payload, "stem": "Admin edited stem"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["stem"] == "Admin edited stem"

        exported = client.get(f"/api/v2/banks/{public_bank['id']}/export-json", headers=visitor_headers)
        assert exported.status_code == 200, exported.text
        assert exported.json()["bank"]["tags"] == ["原标签"]
        assert exported.json()["questions"][0]["stem"] == "Admin edited stem"

        append_payload = {
            "version": 1,
            "bank": {"title": "Ignored", "tags": ["不应覆盖"]},
            "questions": [
                {
                    "type": "single",
                    "stem": "Appended",
                    "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                }
            ],
        }
        forbidden_append = client.post(
            f"/api/v2/banks/{public_bank['id']}/import-json",
            headers=visitor_headers,
            files={"file": ("append.json", json.dumps(append_payload).encode("utf-8"), "application/json")},
        )
        assert forbidden_append.status_code == 404
        appended = client.post(
            f"/api/v2/banks/{public_bank['id']}/import-json",
            headers=owner_headers,
            files={"file": ("append.json", json.dumps(append_payload).encode("utf-8"), "application/json")},
        )
        assert appended.status_code == 200, appended.text
        assert appended.json()["stats"]["question_count"] == 2
        assert [tag["name"] for tag in appended.json()["tags"]] == ["原标签"]

        imported_payload = {
            "version": 1,
            "bank": {"title": "Imported Bank", "description": "Imported description", "tags": ["导入标签"]},
            "questions": [
                {
                    "type": "multiple",
                    "stem": "Imported multiple",
                    "options": [
                        {"label": "A", "content": "A", "is_correct": True},
                        {"label": "B", "content": "B", "is_correct": True},
                        {"label": "C", "content": "C", "is_correct": False},
                    ],
                }
            ],
        }
        imported = client.post(
            "/api/v2/banks/import-json",
            headers=owner_headers,
            data={"visibility": "private", "tag_names": '["表单标签", null, "", 42, "None"]'},
            files={"file": ("bank.json", json.dumps(imported_payload).encode("utf-8"), "application/json")},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["title"] == "Imported Bank"
        assert imported.json()["description"] == "Imported description"
        assert imported.json()["stats"]["question_count"] == 1
        assert [tag["name"] for tag in imported.json()["tags"]] == ["导入标签", "表单标签"]

        fallback_payload = {
            "version": 1,
            "bank": {"description": "Fallback description", "tags": ["JSON 标签", None, ""]},
            "questions": [
                {
                    "type": "single",
                    "stem": "Fallback title question",
                    "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                }
            ],
        }
        fallback_import = client.post(
            "/api/v2/banks/import-json",
            headers=owner_headers,
            data={"visibility": "private", "file_stem": "fallback-title", "tag_names": '["表单兜底标签", null]'},
            files={"file": ("fallback.json", json.dumps(fallback_payload).encode("utf-8"), "application/json")},
        )
        assert fallback_import.status_code == 200, fallback_import.text
        assert fallback_import.json()["title"] == "fallback-title"
        assert fallback_import.json()["description"] == "Fallback description"
        assert [tag["name"] for tag in fallback_import.json()["tags"]] == ["JSON 标签", "表单兜底标签"]

        bad_import = client.post(
            "/api/v2/banks/import-json",
            headers=owner_headers,
            files={"file": ("bad.json", json.dumps({"questions": []}).encode("utf-8"), "application/json")},
        )
        assert bad_import.status_code == 400
        assert "questions 不能为空" in bad_import.json()["error"]["message"]

        deleted = client.delete(f"/api/v2/questions/{question_id}", headers=owner_headers)
        assert deleted.status_code == 200, deleted.text
        assert client.get(f"/api/v2/banks/{public_bank['id']}", headers=owner_headers).json()["stats"]["question_count"] == 1


def test_question_management_all_true_returns_full_list_for_managers_only():
    with TestClient(app) as client:
        owner_headers = _register(client, "all-q-owner@example.com", "allqowner")
        visitor_headers = _register(client, "all-q-visitor@example.com", "allqvisitor")
        bank = client.post("/api/v2/banks", headers=owner_headers, json={"title": "All Questions", "visibility": "private"}).json()
        for index in range(25):
            created = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=owner_headers, json=_sample_question_payload(f"题目 {index:02d}"))
            assert created.status_code == 200, created.text

        default_page = client.get(f"/api/v2/banks/{bank['id']}/questions", headers=owner_headers)
        assert default_page.status_code == 200, default_page.text
        assert len(default_page.json()["items"]) == 20
        assert default_page.json()["total"] == 25

        full = client.get(f"/api/v2/banks/{bank['id']}/questions?all=true", headers=owner_headers)
        assert full.status_code == 200, full.text
        assert len(full.json()["items"]) == 25
        assert full.json()["page_size"] == 25
        assert client.get(f"/api/v2/banks/{bank['id']}/questions?all=true", headers=visitor_headers).status_code == 404


def test_blank_and_short_answer_crud_json_and_practice_flow():
    with TestClient(app) as client:
        headers = _register(client, "text-types@example.com", "texttypes")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Text Types", "visibility": "private"}).json()

        blank = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_blank_question_payload())
        assert blank.status_code == 200, blank.text
        assert blank.json()["type"] == "blank"
        assert blank.json()["options"] == []
        assert blank.json()["blanks"] == [{"id": blank.json()["blanks"][0]["id"], "label": "1", "answers": ["传输层", "Transport Layer"], "sort_order": 0}]

        short = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_short_answer_question_payload())
        assert short.status_code == 200, short.text
        assert short.json()["type"] == "short_answer"
        assert short.json()["options"] == []
        assert short.json()["blanks"] == []

        invalid_blank = client.post(
            f"/api/v2/banks/{bank['id']}/questions",
            headers=headers,
            json={**_blank_question_payload("题干没有占位符"), "blanks": [{"label": "1", "answers": ["答案"]}]},
        )
        assert invalid_blank.status_code == 422

        exported = client.get(f"/api/v2/banks/{bank['id']}/export-json", headers=headers)
        assert exported.status_code == 200, exported.text
        exported_questions = {item["type"]: item for item in exported.json()["questions"]}
        assert exported_questions["blank"]["blanks"][0]["answers"] == ["传输层", "Transport Layer"]
        assert exported_questions["short_answer"]["blanks"] == []

        imported = client.post(
            "/api/v2/banks/import-json",
            headers=headers,
            data={"visibility": "private"},
            files={"file": ("text-types.json", json.dumps(exported.json()).encode("utf-8"), "application/json")},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["stats"]["question_count"] == 2

        session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice", "shuffle_questions": False}).json()
        questions = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()
        blank_question = next(item for item in questions if item["type"] == "blank")
        short_question = next(item for item in questions if item["type"] == "short_answer")
        assert blank_question["blanks"][0]["label"] == "1"
        assert blank_question["answer_state"]["text_answers"] == []

        blank_answer = client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": blank_question["id"], "text_answers": [" 传输层 "]},
        )
        assert blank_answer.status_code == 200, blank_answer.text
        assert blank_answer.json()["is_correct"] is True
        assert blank_answer.json()["correct_text_answers"] == [["传输层", "Transport Layer"]]

        short_answer = client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": short_question["id"], "text_answers": ["利用链式法则反向传播误差"]},
        )
        assert short_answer.status_code == 200, short_answer.text
        assert short_answer.json()["is_correct"] is False
        assert short_answer.json()["correct_text_answers"] == []

        result = client.get(f"/api/v2/practice/sessions/{session['id']}/result", headers=headers).json()
        blank_result = next(item for item in result if item["type"] == "blank")
        short_result = next(item for item in result if item["type"] == "short_answer")
        assert blank_result["text_answers"] == [" 传输层 "]
        assert blank_result["correct_text_answers"] == [["传输层", "Transport Layer"]]
        assert blank_result["is_correct"] is True
        assert short_result["text_answers"] == ["利用链式法则反向传播误差"]
        assert short_result["is_correct"] is False


def test_practice_session_can_select_counts_per_question_type():
    with TestClient(app) as client:
        headers = _register(client, "type-counts@example.com", "typecounts")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Type Count Bank", "visibility": "private"}).json()
        for index in range(3):
            client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_sample_question_payload(f"单选 {index}"))
        for index in range(2):
            client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_multiple_question_payload(f"多选 {index}"))
        for index in range(2):
            client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_blank_question_payload(f"填空 {index} {{{{1}}}}"))
        client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_short_answer_question_payload("简答 0"))

        created = client.post(
            "/api/v2/practice/sessions",
            headers=headers,
            json={
                "bank_id": bank["id"],
                "mode": "practice",
                "shuffle_questions": False,
                "question_type_settings": {
                    "single": {"enabled": True, "count": 2},
                    "multiple": {"enabled": True, "count": 1},
                    "blank": {"enabled": False, "count": None},
                    "short_answer": {"enabled": True, "count": None},
                },
            },
        )
        assert created.status_code == 200, created.text
        session = created.json()
        assert session["total_questions"] == 4
        questions = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()
        types = [question["type"] for question in questions]
        assert types.count("single") == 2
        assert types.count("multiple") == 1
        assert types.count("blank") == 0
        assert types.count("short_answer") == 1


def test_practice_session_rejects_zero_question_type_count():
    with TestClient(app) as client:
        headers = _register(client, "type-count-zero@example.com", "typecountzero")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Type Count Zero", "visibility": "private"}).json()
        client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_sample_question_payload("单选"))

        created = client.post(
            "/api/v2/practice/sessions",
            headers=headers,
            json={
                "bank_id": bank["id"],
                "mode": "practice",
                "question_type_settings": {
                    "single": {"enabled": True, "count": 0},
                    "multiple": {"enabled": False, "count": None},
                    "blank": {"enabled": False, "count": None},
                    "short_answer": {"enabled": False, "count": None},
                },
            },
        )
        assert created.status_code == 422
        assert "题型数量必须是 1-200" in created.json()["error"]["message"]


def test_blank_wrong_answer_records_mistake_and_exam_text_answers_can_change():
    with TestClient(app) as client:
        headers = _register(client, "text-exam@example.com", "textexam")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Text Exam", "visibility": "private"}).json()
        blank = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_blank_question_payload()).json()

        practice = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice"}).json()
        wrong = client.post(
            f"/api/v2/practice/sessions/{practice['id']}/answers",
            headers=headers,
            json={"question_id": blank["id"], "text_answers": ["网络层"]},
        )
        assert wrong.status_code == 200, wrong.text
        assert wrong.json()["is_correct"] is False
        mistakes = client.get(f"/api/v2/banks/{bank['id']}/mistakes", headers=headers).json()
        assert mistakes["total"] == 1
        assert mistakes["items"][0]["type"] == "blank"
        assert mistakes["items"][0]["correct_text_answers"] == [["传输层", "Transport Layer"]]

        exam = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "exam"}).json()
        draft = client.put(
            f"/api/v2/practice/sessions/{exam['id']}/answers/{blank['id']}/draft",
            headers=headers,
            json={"question_id": blank["id"], "text_answers": ["网络层"]},
        )
        assert draft.status_code == 200, draft.text
        changed = client.put(
            f"/api/v2/practice/sessions/{exam['id']}/answers/{blank['id']}/draft",
            headers=headers,
            json={"question_id": blank["id"], "text_answers": ["Transport Layer"]},
        )
        assert changed.status_code == 200, changed.text
        state = client.get(f"/api/v2/practice/sessions/{exam['id']}/questions", headers=headers).json()[0]["answer_state"]
        assert state["is_answered"] is True
        assert state["text_answers"] == ["Transport Layer"]
        assert state["reveal"] is False
        submitted = client.post(f"/api/v2/practice/sessions/{exam['id']}/submit", headers=headers)
        assert submitted.status_code == 200, submitted.text
        exam_result = client.get(f"/api/v2/practice/sessions/{exam['id']}/result", headers=headers).json()[0]
        assert exam_result["is_correct"] is True
        assert exam_result["text_answers"] == ["Transport Layer"]


def test_blank_draft_can_save_partial_answers_without_locking_question():
    with TestClient(app) as client:
        headers = _register(client, "partial-blank@example.com", "partialblank")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Partial Blank", "visibility": "private"}).json()
        blank = client.post(
            f"/api/v2/banks/{bank['id']}/questions",
            headers=headers,
            json={
                "type": "blank",
                "stem": "TCP 位于 {{1}} 层，HTTP 默认端口是 {{2}}。",
                "options": [],
                "blanks": [
                    {"label": "1", "answers": ["传输层"]},
                    {"label": "2", "answers": ["80"]},
                ],
                "explanation": "TCP 属于传输层，HTTP 默认端口为 80。",
            },
        ).json()
        session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice"}).json()

        partial = client.put(
            f"/api/v2/practice/sessions/{session['id']}/answers/{blank['id']}/draft",
            headers=headers,
            json={"question_id": blank["id"], "text_answers": ["传输层"]},
        )
        assert partial.status_code == 200, partial.text
        assert partial.json() == {"ok": True, "changed": True}

        restored = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()[0]
        assert restored["answer_state"]["is_answered"] is False
        assert restored["answer_state"]["text_answers"] == ["传输层", ""]

        submitted = client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": blank["id"], "text_answers": ["传输层"]},
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["is_correct"] is False
        result = client.get(f"/api/v2/practice/sessions/{session['id']}/result", headers=headers).json()[0]
        assert result["text_answers"] == ["传输层", ""]
        assert result["is_correct"] is False


def test_blank_and_short_answer_can_submit_empty_as_wrong_answers():
    with TestClient(app) as client:
        headers = _register(client, "empty-text-answer@example.com", "emptytextanswer")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Empty Text Answers", "visibility": "private"}).json()
        blank = client.post(
            f"/api/v2/banks/{bank['id']}/questions",
            headers=headers,
            json={
                "type": "blank",
                "stem": "{{1}} 使用 {{2}} 端口。",
                "options": [],
                "blanks": [
                    {"label": "1", "answers": ["HTTP"]},
                    {"label": "2", "answers": ["80"]},
                ],
                "explanation": "HTTP 默认 80 端口。",
            },
        ).json()
        short = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_short_answer_question_payload()).json()
        session = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice", "shuffle_questions": False}).json()

        blank_answer = client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": blank["id"], "text_answers": ["", ""]},
        )
        assert blank_answer.status_code == 200, blank_answer.text
        assert blank_answer.json()["is_correct"] is False

        short_answer = client.post(
            f"/api/v2/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": short["id"], "text_answers": []},
        )
        assert short_answer.status_code == 200, short_answer.text
        assert short_answer.json()["is_correct"] is False

        result = client.get(f"/api/v2/practice/sessions/{session['id']}/result", headers=headers).json()
        blank_result = next(item for item in result if item["question_id"] == blank["id"])
        short_result = next(item for item in result if item["question_id"] == short["id"])
        assert blank_result["text_answers"] == ["", ""]
        assert blank_result["is_unanswered"] is False
        assert short_result["text_answers"] == [""]
        assert short_result["is_unanswered"] is False


def test_exam_submit_can_ignore_unlocked_drafts_and_user_can_delete_session():
    with TestClient(app) as client:
        headers = _register(client, "commit-drafts@example.com", "commitdrafts")
        other_headers = _register(client, "commit-drafts-other@example.com", "commitdraftsother")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Commit Drafts", "visibility": "private"}).json()
        question = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=_sample_question_payload("考试缓存题")).json()

        ignored = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "exam"}).json()
        saved = client.put(
            f"/api/v2/practice/sessions/{ignored['id']}/answers/{question['id']}/draft",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][0]["id"]]},
        )
        assert saved.status_code == 200, saved.text
        submitted = client.post(f"/api/v2/practice/sessions/{ignored['id']}/submit", headers=headers, json={"commit_drafts": False})
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["answered_count"] == 0
        ignored_result = client.get(f"/api/v2/practice/sessions/{ignored['id']}/result", headers=headers).json()[0]
        assert ignored_result["is_unanswered"] is True
        assert ignored_result["selected_option_ids"] == []

        counted = client.post("/api/v2/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "exam"}).json()
        client.put(
            f"/api/v2/practice/sessions/{counted['id']}/answers/{question['id']}/draft",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][0]["id"]]},
        )
        counted_submit = client.post(f"/api/v2/practice/sessions/{counted['id']}/submit", headers=headers, json={"commit_drafts": True})
        assert counted_submit.status_code == 200, counted_submit.text
        assert counted_submit.json()["answered_count"] == 1

        assert client.delete(f"/api/v2/practice/sessions/{counted['id']}", headers=other_headers).status_code == 404
        deleted = client.delete(f"/api/v2/practice/sessions/{counted['id']}", headers=headers)
        assert deleted.status_code == 200, deleted.text
        assert deleted.json() == {"ok": True}
        assert client.get(f"/api/v2/practice/sessions/{counted['id']}", headers=headers).status_code == 404


def test_ai_generation_accepts_blank_and_short_answer_with_type_settings(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "ai-text-types@example.com", "aitexttypes")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True, "response_format_type": "json_schema"},
        )

        from app.domains.ai_generation import facade as ai_generation

        observed = {}

        def good_ai(*args, **kwargs):
            observed["user_prompt"] = kwargs.get("user_prompt") or ""
            return {
                "questions": [
                    _blank_question_payload("HTTP 状态码 200 表示 {{1}}"),
                    _short_answer_question_payload("解释梯度下降的核心思想"),
                ]
            }

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", good_ai)
        type_settings = {
            "single": {"enabled": False, "count": 0},
            "multiple": {"enabled": False, "count": 0},
            "blank": {"enabled": True, "count": 1},
            "short_answer": {"enabled": True, "count": 1},
        }
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={
                "title": "AI Text Types",
                "generation_mode": "knowledge_generate",
                "question_type_settings": json.dumps(type_settings),
            },
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert created.status_code == 200, created.text
        assert "填空" in observed["user_prompt"]
        assert "简答" in observed["user_prompt"]
        workflow = client.get(f"/api/v2/ai/workflows/{created.json()['workflow_id']}", headers=headers).json()
        assert workflow["question_type_settings"]["blank"] == {"enabled": True, "count": 1}
        assert workflow["question_type_settings"]["short_answer"] == {"enabled": True, "count": 1}
        draft = client.get(f"/api/v2/ai/workflows/{created.json()['workflow_id']}/draft", headers=headers).json()
        assert [question["type"] for question in draft["questions"]] == ["blank", "short_answer"]
        confirmed = client.post(f"/api/v2/ai/workflows/{created.json()['workflow_id']}/draft/confirm", headers=headers)
        assert confirmed.status_code == 200, confirmed.text
        questions = client.get(f"/api/v2/banks/{created.json()['bank_id']}/questions?all=true", headers=headers).json()["items"]
        assert {question["type"] for question in questions} == {"blank", "short_answer"}


def test_question_options_are_limited_to_26_across_manual_json_and_draft_confirm(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "option-cap@example.com", "optioncap")
        bank = client.post("/api/v2/banks", headers=headers, json={"title": "Option Cap", "visibility": "private"}).json()
        too_many = _question_payload_with_option_count(27)

        manual = client.post(f"/api/v2/banks/{bank['id']}/questions", headers=headers, json=too_many)
        assert manual.status_code == 422

        json_payload = {"bank": {"title": "Too Many Options"}, "questions": [too_many]}
        imported = client.post(
            "/api/v2/banks/import-json",
            headers=headers,
            data={"visibility": "private"},
            files={"file": ("too-many.json", json.dumps(json_payload).encode("utf-8"), "application/json")},
        )
        assert imported.status_code == 400
        assert "26" in imported.json()["error"]["message"]

        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.domains.ai_generation import facade as ai_generation

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", lambda *args, **kwargs: {"questions": [_sample_question_payload("合法草稿")]})
        created = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "Draft Option Cap", "question_count": "1"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert created.status_code == 200, created.text
        workflow_id = created.json()["workflow_id"]
        db = SessionLocal()
        try:
            draft = db.scalar(select(AIGenerationDraft).where(AIGenerationDraft.workflow_id == workflow_id))
            assert draft is not None
            question = db.scalar(select(AIGenerationDraftQuestion).where(AIGenerationDraftQuestion.draft_id == draft.id))
            assert question is not None
            question.options_json = json.dumps(too_many["options"], ensure_ascii=False)
            db.commit()
        finally:
            db.close()

        confirmed = client.post(f"/api/v2/ai/workflows/{workflow_id}/draft/confirm", headers=headers)
        assert confirmed.status_code == 422
        assert "26" in confirmed.json()["error"]["message"]


def test_ai_generation_prompt_builder_and_validator_components():
    from app.domains.ai_generation.prompts import ANSWER_RULES, FORMULA_RULES, PromptBuilder
    from app.domains.ai_generation.validator import AIPayloadValidator, AIOutputValidationError

    knowledge_prompt = PromptBuilder.build_generation_prompt("material", 3, True, "knowledge_generate", "偏难")
    parse_prompt = PromptBuilder.build_generation_prompt("bank text", None, False, "bank_parse", "保留编号")
    repair_prompt = PromptBuilder.build_repair_prompt({"questions": []}, "缺少题目")

    assert "生成 3 道选择题" in knowledge_prompt
    assert "偏难" in knowledge_prompt
    assert "提取其中实际存在的全部选择题" in parse_prompt
    assert "保留编号" in parse_prompt
    assert ANSWER_RULES in PromptBuilder.system_prompt("knowledge_generate")
    assert ANSWER_RULES in PromptBuilder.system_prompt("bank_parse")
    assert ANSWER_RULES in PromptBuilder.REPAIR_SYSTEM_PROMPT
    assert FORMULA_RULES in PromptBuilder.system_prompt("knowledge_generate")
    assert FORMULA_RULES in PromptBuilder.system_prompt("bank_parse")
    assert FORMULA_RULES in PromptBuilder.REPAIR_SYSTEM_PROMPT
    assert "\\(...\\)" in FORMULA_RULES
    assert "\\[...\\]" in FORMULA_RULES
    assert "缺少题目" in repair_prompt

    questions, summary = AIPayloadValidator.validate(
        {
            "questions": [
                {
                    "type": "single",
                    "stem": "ok",
                    "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                }
            ]
        },
        "knowledge_generate",
        1,
    )
    assert questions[0]["stem"] == "ok"
    assert summary == "校验通过，共 1 道题"

    quota_questions, quota_summary = AIPayloadValidator.validate(
        {
            "questions": [
                _sample_question_payload("单选 1"),
                _sample_question_payload("单选 2"),
                _blank_question_payload("填空 {{1}}"),
            ]
        },
        "knowledge_generate",
        2,
        {
            "single": {"enabled": True, "count": 1},
            "multiple": {"enabled": False, "count": None},
            "blank": {"enabled": True, "count": 1},
            "short_answer": {"enabled": False, "count": None},
        },
    )
    assert [question["stem"] for question in quota_questions] == ["单选 1", "填空 {{1}}"]
    assert quota_summary == "校验通过，共 2 道题"

    try:
        AIPayloadValidator.validate(
            {"questions": [_sample_question_payload("单选 1"), _sample_question_payload("单选 2")]},
            "knowledge_generate",
            2,
            {
                "single": {"enabled": True, "count": 1},
                "multiple": {"enabled": False, "count": None},
                "blank": {"enabled": True, "count": 1},
                "short_answer": {"enabled": False, "count": None},
            },
        )
    except AIOutputValidationError as exc:
        assert "blank 需要 1 道，实际 0 道" in str(exc)
    else:
        raise AssertionError("validator should reject missing fixed type quota")

    for payload, expected in [
        ({}, "缺少 questions"),
        ({"questions": []}, "questions 不能为空"),
        (
            {
                "questions": [
                    {
                        "type": "single",
                        "stem": "bad single",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": True}],
                    }
                ]
            },
            "single 有 2 个正确答案",
        ),
        (
            {
                "questions": [
                    {
                        "type": "multiple",
                        "stem": "bad multiple",
                        "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
                    }
                ]
            },
            "multiple 有 1 个正确答案",
        ),
    ]:
        try:
            AIPayloadValidator.validate(payload, "knowledge_generate", None)
        except AIOutputValidationError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("validator should reject invalid payload")


def test_ai_generation_rejects_zero_and_boolean_question_type_counts():
    with TestClient(app) as client:
        headers = _register(client, "ai-count-zero@example.com", "aicountzero")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        for count in (0, True):
            created = client.post(
                "/api/v2/ai/workflows",
                headers=headers,
                data={
                    "title": "Bad Type Count",
                    "generation_mode": "knowledge_generate",
                    "question_type_settings": json.dumps(
                        {
                            "single": {"enabled": True, "count": count},
                            "multiple": {"enabled": False, "count": None},
                            "blank": {"enabled": False, "count": None},
                            "short_answer": {"enabled": False, "count": None},
                        }
                    ),
                },
                files={"file": ("material.txt", b"content", "text/plain")},
            )
            assert created.status_code == 422
            assert "题型数量必须是 1-100" in created.json()["error"]["message"]


def test_ai_generation_worker_spawns_configured_worker_processes(monkeypatch):
    from app.workers import ai_generation_worker

    started: list[tuple[int, str]] = []
    joined: list[int] = []

    class FakeProcess:
        def __init__(self, target, args):
            self.target = target
            self.args = args

        def start(self):
            started.append(self.args)

        def join(self):
            joined.append(self.args[0])

    settings = get_settings()
    monkeypatch.setattr(settings, "ai_workflow_worker_count", 3)
    monkeypatch.setattr(ai_generation_worker.multiprocessing, "Process", FakeProcess)

    ai_generation_worker.run_configured_workers(settings)

    assert started == [(1, "ai-generation"), (2, "ai-generation"), (3, "ai-generation")]
    assert joined == [1, 2, 3]


def test_ai_generation_worker_name_is_unique_per_process(monkeypatch):
    from app.workers import ai_generation_worker

    monkeypatch.setattr(ai_generation_worker.socket, "gethostname", lambda: "worker-host")
    monkeypatch.setattr(ai_generation_worker.os, "getpid", lambda: 4242)

    assert ai_generation_worker.worker_name("ai-generation", 2) == "ai-generation-2-worker-host-4242"


def test_ai_generation_state_and_draft_services_keep_transactions_safe():
    from app.domains.ai_generation.drafts import DraftService
    from app.domains.ai_generation.validator import AIOutputValidationError
    from app.domains.ai_generation.workflow_state import WorkflowStateService

    db = SessionLocal()
    try:
        user = User(email="ai-state@example.com", username="aistate", display_name="aistate", password_hash="hash")
        db.add(user)
        db.flush()
        bank = QuestionBank(owner_id=user.id, title="AI State", visibility="private", desired_visibility="public", generation_status="pending")
        db.add(bank)
        db.flush()
        workflow = AIGenerationWorkflow(bank_id=bank.id, user_id=user.id, purpose="create_bank", generation_mode="knowledge_generate", status="pending")
        db.add(workflow)
        db.flush()
        job = ImportJob(user_id=user.id, bank_id=bank.id, workflow_id=workflow.id, status="pending", desired_visibility="public", type="document_ai")
        db.add(job)
        db.flush()

        state = WorkflowStateService(db)
        state.set_status(workflow, job, bank, "validating")
        state.record_step(workflow.id, "validate_payload", "failed", error_message="bad")
        db.commit()

        assert workflow.status == "validating"
        assert job.status == "validating"
        assert bank.generation_status == "processing"
        assert db.scalar(select(AIGenerationWorkflowStep).where(AIGenerationWorkflowStep.workflow_id == workflow.id)).error_message == "bad"

        draft = AIGenerationDraft(workflow_id=workflow.id, bank_id=bank.id, user_id=user.id, status="ready")
        db.add(draft)
        db.flush()
        db.add(
            AIGenerationDraftQuestion(
                draft_id=draft.id,
                sort_order=1,
                type="single",
                stem="invalid",
                options_json=json.dumps(
                    [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": True}],
                    ensure_ascii=False,
                ),
            )
        )
        db.commit()

        try:
            DraftService(db).confirm(job, draft)
            db.commit()
        except AIOutputValidationError:
            db.rollback()
        else:
            raise AssertionError("invalid draft should not confirm")

        db.refresh(bank)
        assert bank.question_count == 0
        assert db.scalar(select(Question).where(Question.bank_id == bank.id)) is None
    finally:
        db.close()
