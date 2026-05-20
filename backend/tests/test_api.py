import json
import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_quiz_pass.db"
os.environ["JWT_SECRET_KEY"] = "test-secret"
Path("test_quiz_pass.db").unlink(missing_ok=True)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
command.upgrade(alembic_cfg, "head")

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.ai_workflow import AIGenerationDraft, AIGenerationWorkflow, AIGenerationWorkflowStep, AIGenerationDraftQuestion  # noqa: E402
from app.models.import_job import ImportJob  # noqa: E402
from app.models.practice import MistakeRecord, PracticeAnswer, PracticeSession, PracticeSessionQuestion  # noqa: E402
from app.models.question import Question, QuestionOption  # noqa: E402
from app.models.question_bank import QuestionBank, QuestionBankFavorite, question_bank_tag_links  # noqa: E402
from app.models.user import User  # noqa: E402


def _register(client: TestClient, email: str, username: str) -> dict[str, str]:
    response = client.post("/api/v2/auth/register", json={"email": email, "username": username, "password": "password123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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


def _fk_ondelete(model, column_name: str) -> str | None:
    column = model.__table__.c[column_name]
    foreign_key = next(iter(column.foreign_keys))
    return foreign_key.ondelete


def test_database_model_removes_workflow_job_cycle_and_uses_cascades():
    assert "job_id" not in AIGenerationWorkflow.__table__.c
    assert "job_id" not in AIGenerationDraft.__table__.c
    assert "active_generation_job_id" not in QuestionBank.__table__.c

    assert _fk_ondelete(ImportJob, "workflow_id") == "CASCADE"
    assert _fk_ondelete(ImportJob, "bank_id") == "CASCADE"
    assert _fk_ondelete(Question, "bank_id") == "CASCADE"
    assert _fk_ondelete(QuestionOption, "question_id") == "CASCADE"
    assert _fk_ondelete(QuestionBankFavorite, "bank_id") == "CASCADE"
    assert next(iter(question_bank_tag_links.c.bank_id.foreign_keys)).ondelete == "CASCADE"
    assert _fk_ondelete(PracticeSession, "bank_id") == "CASCADE"
    assert _fk_ondelete(PracticeSessionQuestion, "session_id") == "CASCADE"
    assert _fk_ondelete(PracticeAnswer, "session_id") == "CASCADE"
    assert _fk_ondelete(MistakeRecord, "bank_id") == "CASCADE"
    assert _fk_ondelete(AIGenerationWorkflow, "bank_id") == "CASCADE"
    assert _fk_ondelete(AIGenerationWorkflowStep, "workflow_id") == "CASCADE"
    assert _fk_ondelete(AIGenerationDraft, "workflow_id") == "CASCADE"
    assert _fk_ondelete(AIGenerationDraftQuestion, "draft_id") == "CASCADE"
    assert _fk_ondelete(AIGenerationWorkflow, "ai_provider_config_id") == "SET NULL"
    assert _fk_ondelete(ImportJob, "ai_provider_config_id") == "SET NULL"


def test_login_identifier_and_change_password():
    with TestClient(app) as client:
        headers = _register(client, "login@example.com", "loginuser")
        v2_headers = client.post(
            "/api/v2/auth/register",
            json={"email": "login-v2@example.com", "username": "loginuserv2", "password": "password123"},
        )
        assert v2_headers.status_code == 200, v2_headers.text
        assert client.post("/api/v2/auth/login", json={"identifier": "loginuserv2", "password": "password123"}).status_code == 200
        v2_token = v2_headers.json()["access_token"]
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
        client.post(f"/api/v2/practice/sessions/{session['id']}/submit", headers=headers)
        revealed = client.get(f"/api/v2/practice/sessions/{session['id']}/questions", headers=headers).json()[0]["answer_state"]
        assert revealed["reveal"] is True
        assert revealed["correct_labels"] == ["B"]
        result = client.get(f"/api/v2/practice/sessions/{session['id']}/result", headers=headers).json()[0]
        assert result["correct_labels"] == ["B"]
        assert result["explanation"] == "basic arithmetic"


def test_ai_config_api_key_cannot_be_updated_and_list_has_only_real_configs():
    with TestClient(app) as client:
        headers = _register(client, "config@example.com", "configuser")
        created = client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )
        assert created.status_code == 200
        configs = client.get("/api/v2/users/me/ai-provider-configs", headers=headers).json()
        assert len(configs) == 1
        assert configs[0]["name"] == ""
        assert configs[0]["has_api_key"] is True
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
        public_bank = client.post("/api/v2/banks", headers=owner_headers, json={"title": "Public", "visibility": "public"}).json()
        question = client.post(
            f"/api/v2/banks/{public_bank['id']}/questions",
            headers=owner_headers,
            json={
                "type": "single",
                "stem": "Public Q",
                "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
            },
        ).json()

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
        assert client.delete(f"/api/v2/questions/{question['id']}", headers=other_headers).status_code == 404

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

        from app.services import ai_generation

        def bad_ai(*args, **kwargs):
            return {"questions": [{"type": "single", "stem": "bad", "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": True}]}]}

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", bad_ai)
        response = client.post(
            "/api/v2/ai/workflows",
            headers=headers,
            data={"title": "AI Bank", "desired_visibility": "public", "question_count": "1", "tag_names": '["AI标签"]'},
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
        other_headers = _register(client, "workflow-other@example.com", "workflowother")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.services import ai_generation

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
            data={"generation_mode": "knowledge_generate", "question_count": "1", "extra_instruction": "避免重复"},
            files={"file": ("more.txt", b"more content", "text/plain")},
        )
        assert extend.status_code == 200
        extend_job = client.get(f"/api/v2/ai/workflows/{extend.json()['workflow_id']}", headers=headers).json()
        assert extend_job["status"] == "draft_ready"
        assert extend_job["draft_question_count"] == 1
        assert any("Edited fixed question" in str(call) for call in calls)
        assert client.post(f"/api/v2/ai/workflows/{extend_job['id']}/draft/confirm", headers=headers).status_code == 200
        bank_after_extend = client.get(f"/api/v2/banks/{bank['id']}", headers=headers).json()
        assert bank_after_extend["question_count"] == 2
        assert bank_after_extend["visibility"] == "public"

        forbidden = client.post(
            f"/api/v2/banks/{bank['id']}/ai-workflows",
            headers=other_headers,
            data={"generation_mode": "knowledge_generate", "question_count": "1"},
            files={"file": ("more.txt", b"more content", "text/plain")},
        )
        assert forbidden.status_code == 404


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
        assert client.get(f"/api/v2/ai/workflows/{workflow_id}", headers=headers).status_code == 404


def test_v2_banks_returns_domain_shaped_bank_permissions_and_stats():
    with TestClient(app) as client:
        owner_headers = _register(client, "v2-owner@example.com", "v2owner")
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


def test_v2_ai_workflow_extends_existing_bank(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "v2-extend@example.com", "v2extend")
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


def test_bank_parse_mode_without_question_count_and_detailed_errors(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "parse@example.com", "parseuser")
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.services import ai_generation

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
        client.post(
            "/api/v2/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.services import ai_generation

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

        from app.services import ai_generation

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
