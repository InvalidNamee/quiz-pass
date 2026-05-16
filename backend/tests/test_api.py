import json
import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_quiz_pass.db"
os.environ["JWT_SECRET_KEY"] = "test-secret"
Path("test_quiz_pass.db").unlink(missing_ok=True)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


def _register(client: TestClient, email: str, username: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": "password123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _login(client: TestClient, identifier: str, password: str = "password123") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
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


def test_login_identifier_and_change_password():
    with TestClient(app) as client:
        headers = _register(client, "login@example.com", "loginuser")
        assert _login(client, "login@example.com")
        assert _login(client, "loginuser")
        bad = client.post("/api/v1/auth/login", json={"identifier": "loginuser", "password": "wrong"})
        assert bad.status_code == 401
        assert bad.json()["detail"] == "用户名/邮箱或密码错误"

        wrong_old = client.post("/api/v1/users/me/change-password", headers=headers, json={"old_password": "wrong", "new_password": "newpass123"})
        assert wrong_old.status_code == 400
        ok = client.post("/api/v1/users/me/change-password", headers=headers, json={"old_password": "password123", "new_password": "newpass123"})
        assert ok.status_code == 200
        assert _login(client, "loginuser", "newpass123")


def test_auth_bank_favorite_question_practice_and_mistake(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "demo@example.com", "demo")
        other_headers = _register(client, "other@example.com", "other")

        bank = client.post(
            "/api/v1/question-banks",
            headers=headers,
            json={"title": "Bank", "visibility": "private", "tag_names": [" 计算机组成原理 ", "", "深度学习基础", "计算机组成原理"]},
        ).json()
        assert [tag["name"] for tag in bank["tags"]] == ["深度学习基础", "计算机组成原理"]
        first_tag_id = bank["tags"][0]["id"]
        bank_detail = client.get(f"/api/v1/question-banks/{bank['id']}", headers=headers).json()
        assert bank_detail["owner_username"] == "demo"
        assert [tag["name"] for tag in bank_detail["tags"]] == ["深度学习基础", "计算机组成原理"]
        tag_search = client.get("/api/v1/question-banks/tags?keyword=深度", headers=headers).json()
        assert tag_search["total"] == 1
        assert tag_search["items"][0]["name"] == "深度学习基础"
        assert client.get(f"/api/v1/question-banks?tag_ids={first_tag_id}", headers=headers).json()["total"] == 1
        search_users = client.get("/api/v1/users/search?keyword=dem", headers=headers).json()
        assert search_users["total"] == 1
        assert search_users["items"][0]["username"] == "demo"
        assert "email" not in search_users["items"][0]
        assert client.get(f"/api/v1/question-banks/{bank['id']}", headers=other_headers).status_code == 404
        assert client.get(f"/api/v1/question-banks?tag_ids={first_tag_id}", headers=other_headers).json()["total"] == 0
        assert client.post(f"/api/v1/question-banks/{bank['id']}/favorite", headers=other_headers).status_code == 404
        assert client.post(f"/api/v1/question-banks/{bank['id']}/favorite", headers=headers).status_code == 200
        favorites_by_owner = client.get(f"/api/v1/question-banks/favorites?owner_id={bank['owner_id']}", headers=headers).json()
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
        question = client.post(f"/api/v1/question-banks/{bank['id']}/questions", headers=headers, json=question_payload).json()
        unanswered_question = client.post(
            f"/api/v1/question-banks/{bank['id']}/questions",
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
        session = client.post("/api/v1/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "practice"}).json()
        assert session["answered_count"] == 0
        assert session["bank_title"] == "Bank"
        assert session["bank_visibility"] == "private"
        assert session["bank_generation_status"] == "none"
        assert session["last_answered_at"] is None
        answer = client.post(
            f"/api/v1/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][1]["id"]]},
        )
        assert answer.status_code == 200
        assert answer.json()["reveal"] is True
        assert answer.json()["is_correct"] is False
        assert answer.json()["correct_labels"] == ["A"]
        assert answer.json()["explanation"] == "basic math"
        question_states = client.get(f"/api/v1/practice/sessions/{session['id']}/questions", headers=headers).json()
        answered_state = next(item for item in question_states if item["id"] == question["id"])["answer_state"]
        assert answered_state["is_answered"] is True
        assert answered_state["selected_option_ids"] == [question["options"][1]["id"]]
        assert answered_state["reveal"] is True
        assert answered_state["correct_labels"] == ["A"]
        repeat = client.post(
            f"/api/v1/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][0]["id"]]},
        )
        assert repeat.status_code == 400
        assert "不能重复" in repeat.json()["detail"]
        updated_session = client.get(f"/api/v1/practice/sessions/{session['id']}", headers=headers).json()
        assert updated_session["answered_count"] == 1
        assert updated_session["last_answered_at"] is not None
        history = client.get("/api/v1/history/sessions", headers=headers).json()
        history_item = history["items"][0]
        assert history_item["bank_title"] == "Bank"
        assert history_item["started_at"] is not None
        assert history_item["last_answered_at"] == updated_session["last_answered_at"]
        submitted = client.post(f"/api/v1/practice/sessions/{session['id']}/submit", headers=headers).json()
        assert submitted["answered_count"] == 1
        assert submitted["submitted_at"] is not None
        result = client.get(f"/api/v1/practice/sessions/{session['id']}/result", headers=headers).json()
        answered = next(item for item in result if item["question_id"] == question["id"])
        unanswered = next(item for item in result if item["question_id"] == unanswered_question["id"])
        assert answered["stem"] == "1+1=?"
        assert answered["selected_labels"] == ["B"]
        assert answered["correct_labels"] == ["A"]
        assert unanswered["is_unanswered"] is True
        assert unanswered["selected_labels"] == []
        assert unanswered["correct_labels"] == ["A", "C"]
        mistakes = client.get(f"/api/v1/question-banks/{bank['id']}/mistakes", headers=headers).json()
        assert mistakes["total"] == 1
        mistake = mistakes["items"][0]
        assert mistake["stem"] == "1+1=?"
        assert mistake["type"] == "single"
        assert mistake["options"][0]["label"] == "A"
        assert mistake["correct_labels"] == ["A"]
        assert mistake["correct_option_ids"] == [question["options"][0]["id"]]
        assert mistake["explanation"] == "basic math"
        assert mistake["wrong_count"] == 1
        exported = client.get(f"/api/v1/question-banks/{bank['id']}/export", headers=headers).json()
        assert exported["bank"]["tags"] == ["深度学习基础", "计算机组成原理"]
        imported = client.post(
            "/api/v1/question-banks/import-json",
            headers=headers,
            data={"visibility": "private", "tag_names": '["手动导入标签"]'},
            files={"file": ("bank.json", json.dumps(exported).encode("utf-8"), "application/json")},
        )
        assert imported.status_code == 200
        imported_tag_names = [tag["name"] for tag in imported.json()["tags"]]
        assert "深度学习基础" in imported_tag_names
        assert "手动导入标签" in imported_tag_names
        patched_tags = client.patch(f"/api/v1/question-banks/{bank['id']}", headers=headers, json={"tag_names": ["操作系统"]})
        assert patched_tags.status_code == 200
        assert [tag["name"] for tag in patched_tags.json()["tags"]] == ["操作系统"]
        too_many_tags = client.patch(f"/api/v1/question-banks/{bank['id']}", headers=headers, json={"tag_names": [f"tag-{index}" for index in range(21)]})
        assert too_many_tags.status_code == 422


def test_register_validation_and_exam_hides_answer_until_submit():
    with TestClient(app) as client:
        invalid = client.post("/api/v1/auth/register", json={"email": "bad", "username": "ab", "password": "short"})
        assert invalid.status_code == 422
        headers = _register(client, "exam@example.com", "examuser")
        bank = client.post("/api/v1/question-banks", headers=headers, json={"title": "Exam Bank", "visibility": "private"}).json()
        question = client.post(
            f"/api/v1/question-banks/{bank['id']}/questions",
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
        session = client.post("/api/v1/practice/sessions", headers=headers, json={"bank_id": bank["id"], "mode": "exam"}).json()
        answer = client.post(
            f"/api/v1/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][0]["id"]]},
        )
        assert answer.status_code == 200
        assert answer.json()["reveal"] is False
        assert answer.json()["is_correct"] is None
        assert answer.json()["correct_labels"] == []
        state = client.get(f"/api/v1/practice/sessions/{session['id']}/questions", headers=headers).json()[0]["answer_state"]
        assert state["is_answered"] is True
        assert state["reveal"] is False
        client.post(f"/api/v1/practice/sessions/{session['id']}/submit", headers=headers)
        revealed = client.get(f"/api/v1/practice/sessions/{session['id']}/questions", headers=headers).json()[0]["answer_state"]
        assert revealed["reveal"] is True
        assert revealed["correct_labels"] == ["B"]
        result = client.get(f"/api/v1/practice/sessions/{session['id']}/result", headers=headers).json()[0]
        assert result["correct_labels"] == ["B"]
        assert result["explanation"] == "basic arithmetic"


def test_ai_config_api_key_cannot_be_updated_and_list_has_only_real_configs():
    with TestClient(app) as client:
        headers = _register(client, "config@example.com", "configuser")
        created = client.post(
            "/api/v1/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )
        assert created.status_code == 200
        configs = client.get("/api/v1/users/me/ai-provider-configs", headers=headers).json()
        assert len(configs) == 1
        assert configs[0]["name"] == ""
        assert configs[0]["has_api_key"] is True
        blocked = client.patch(
            f"/api/v1/users/me/ai-provider-configs/{created.json()['id']}",
            headers=headers,
            json={"api_key": "sk-new"},
        )
        assert blocked.status_code == 400
        assert "不可修改" in blocked.json()["detail"]


def test_admin_user_management_and_bank_permissions():
    with TestClient(app) as client:
        admin_headers = _register(client, "admin@example.com", "adminuser")
        _make_admin("adminuser")
        admin_headers = _login(client, "adminuser")
        admin_id = client.get("/api/v1/auth/me", headers=admin_headers).json()["id"]
        owner_headers = _register(client, "owner@example.com", "owneruser")
        other_headers = _register(client, "visitor@example.com", "visitoruser")

        users = client.get("/api/v1/admin/users?keyword=visitor", headers=admin_headers).json()
        visitor_id = users["items"][0]["id"]
        patched = client.patch(
            f"/api/v1/admin/users/{visitor_id}",
            headers=admin_headers,
            json={"display_name": "Visitor", "bio": "bio", "is_active": False},
        )
        assert patched.status_code == 200
        assert patched.json()["display_name"] == "Visitor"
        assert patched.json()["is_active"] is False
        assert client.post("/api/v1/auth/login", json={"identifier": "visitoruser", "password": "password123"}).status_code == 401
        client.patch(f"/api/v1/admin/users/{visitor_id}", headers=admin_headers, json={"is_active": True})
        role_patch = client.patch(f"/api/v1/admin/users/{visitor_id}", headers=admin_headers, json={"role": "admin"})
        assert role_patch.status_code == 422
        reset = client.post(f"/api/v1/admin/users/{visitor_id}/reset-password", headers=admin_headers)
        assert reset.status_code == 200
        temporary_password = reset.json()["temporary_password"]
        assert client.post("/api/v1/auth/login", json={"identifier": "visitoruser", "password": "password123"}).status_code == 401
        assert _login(client, "visitoruser", temporary_password)
        assert client.post(f"/api/v1/admin/users/{admin_id}/reset-password", headers=admin_headers).status_code == 400
        assert client.patch(f"/api/v1/admin/users/{visitor_id}", headers=other_headers, json={"is_active": False}).status_code == 403

        private_bank = client.post("/api/v1/question-banks", headers=owner_headers, json={"title": "Private", "visibility": "private"}).json()
        public_bank = client.post("/api/v1/question-banks", headers=owner_headers, json={"title": "Public", "visibility": "public"}).json()
        question = client.post(
            f"/api/v1/question-banks/{public_bank['id']}/questions",
            headers=owner_headers,
            json={
                "type": "single",
                "stem": "Public Q",
                "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
            },
        ).json()

        assert client.get(f"/api/v1/question-banks/{private_bank['id']}", headers=other_headers).status_code == 404
        assert client.get(f"/api/v1/question-banks/{public_bank['id']}/export", headers=other_headers).status_code == 200
        other_public_mistakes = client.get(f"/api/v1/question-banks/{public_bank['id']}/mistakes", headers=other_headers)
        assert other_public_mistakes.status_code == 200
        assert other_public_mistakes.json()["total"] == 0
        assert client.patch(f"/api/v1/question-banks/{public_bank['id']}", headers=other_headers, json={"title": "Nope"}).status_code == 404
        assert client.post(
            f"/api/v1/question-banks/{public_bank['id']}/questions",
            headers=other_headers,
            json={
                "type": "single",
                "stem": "Nope",
                "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": False}],
            },
        ).status_code == 404
        assert client.delete(f"/api/v1/questions/{question['id']}", headers=other_headers).status_code == 404

        other_session = client.post("/api/v1/practice/sessions", headers=other_headers, json={"bank_id": public_bank["id"], "mode": "practice"}).json()
        other_answer = client.post(
            f"/api/v1/practice/sessions/{other_session['id']}/answers",
            headers=other_headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][1]["id"]]},
        )
        assert other_answer.status_code == 200
        other_public_mistakes = client.get(f"/api/v1/question-banks/{public_bank['id']}/mistakes", headers=other_headers).json()
        owner_public_mistakes = client.get(f"/api/v1/question-banks/{public_bank['id']}/mistakes", headers=owner_headers).json()
        assert other_public_mistakes["total"] == 1
        assert other_public_mistakes["items"][0]["stem"] == "Public Q"
        assert other_public_mistakes["items"][0]["correct_labels"] == ["A"]
        assert owner_public_mistakes["total"] == 0
        other_patch_tags = client.patch(f"/api/v1/question-banks/{public_bank['id']}", headers=other_headers, json={"tag_names": ["Nope"]})
        assert other_patch_tags.status_code == 404

        assert client.get(f"/api/v1/question-banks/{private_bank['id']}", headers=admin_headers).status_code == 200
        admin_update = client.patch(f"/api/v1/question-banks/{private_bank['id']}", headers=admin_headers, json={"title": "Admin Edited"})
        assert admin_update.status_code == 200
        assert admin_update.json()["title"] == "Admin Edited"
        admin_tag_update = client.patch(f"/api/v1/question-banks/{private_bank['id']}", headers=admin_headers, json={"tag_names": ["管理员标签"]})
        assert admin_tag_update.status_code == 200
        assert admin_tag_update.json()["tags"][0]["name"] == "管理员标签"
        admin_question = client.post(
            f"/api/v1/question-banks/{private_bank['id']}/questions",
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
            "/api/v1/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )
        assert config.status_code == 200

        from app.services import ai_generation

        def bad_ai(*args, **kwargs):
            return {"questions": [{"type": "single", "stem": "bad", "options": [{"label": "A", "content": "A", "is_correct": True}, {"label": "B", "content": "B", "is_correct": True}]}]}

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", bad_ai)
        response = client.post(
            "/api/v1/ai-generation/question-bank-jobs",
            headers=headers,
            data={"title": "AI Bank", "desired_visibility": "public", "question_count": "1", "tag_names": '["AI标签"]'},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert response.status_code == 200
        bank = client.get(f"/api/v1/question-banks/{response.json()['bank_id']}", headers=headers).json()
        assert bank["tags"][0]["name"] == "AI标签"
        job = client.get(f"/api/v1/ai-generation/jobs/{response.json()['job_id']}", headers=headers).json()
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
        steps = client.get(f"/api/v1/ai-generation/workflows/{job['workflow_id']}/steps", headers=headers).json()
        assert any(step["step_name"] == "validate_payload" and step["status"] == "failed" for step in steps)


def test_ai_generation_repair_draft_confirm_and_extend(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "workflow@example.com", "workflowuser")
        other_headers = _register(client, "workflow-other@example.com", "workflowother")
        client.post(
            "/api/v1/users/me/ai-provider-configs",
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
            "/api/v1/ai-generation/question-bank-jobs",
            headers=headers,
            data={"title": "Workflow Bank", "desired_visibility": "public", "question_count": "1", "generate_description": "true"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert response.status_code == 200
        bank = client.get(f"/api/v1/question-banks/{response.json()['bank_id']}", headers=headers).json()
        assert bank["generation_status"] == "processing"
        assert bank["visibility"] == "private"
        assert bank["question_count"] == 0
        job = client.get(f"/api/v1/ai-generation/jobs/{response.json()['job_id']}", headers=headers).json()
        assert job["status"] == "draft_ready"
        assert job["workflow_status"] == "draft_ready"
        assert job["draft_question_count"] == 1
        assert job["repair_attempts"] == 1
        assert job["can_confirm"] is True
        draft = client.get(f"/api/v1/ai-generation/jobs/{job['id']}/draft", headers=headers).json()
        assert draft["bank_description"] == "Draft description"
        assert draft["questions"][0]["stem"] == "Fixed question"
        assert client.get(f"/api/v1/ai-generation/jobs/{job['id']}/draft", headers=other_headers).status_code == 404

        edited = draft.copy()
        edited["bank_description"] = "Edited description"
        edited["questions"][0]["stem"] = "Edited fixed question"
        patch = client.patch(f"/api/v1/ai-generation/jobs/{job['id']}/draft", headers=headers, json=edited)
        assert patch.status_code == 200
        confirmed = client.post(f"/api/v1/ai-generation/jobs/{job['id']}/confirm", headers=headers)
        assert confirmed.status_code == 200
        bank_after_confirm = client.get(f"/api/v1/question-banks/{bank['id']}", headers=headers).json()
        assert bank_after_confirm["generation_status"] == "succeeded"
        assert bank_after_confirm["visibility"] == "public"
        assert bank_after_confirm["description"] == "Edited description"
        assert bank_after_confirm["question_count"] == 1
        questions = client.get(f"/api/v1/question-banks/{bank['id']}/questions", headers=headers).json()
        assert questions["items"][0]["stem"] == "Edited fixed question"

        extend = client.post(
            f"/api/v1/question-banks/{bank['id']}/ai-generation/extend-jobs",
            headers=headers,
            data={"generation_mode": "knowledge_generate", "question_count": "1", "extra_instruction": "避免重复"},
            files={"file": ("more.txt", b"more content", "text/plain")},
        )
        assert extend.status_code == 200
        extend_job = client.get(f"/api/v1/ai-generation/jobs/{extend.json()['job_id']}", headers=headers).json()
        assert extend_job["status"] == "draft_ready"
        assert extend_job["draft_question_count"] == 1
        assert any("Edited fixed question" in str(call) for call in calls)
        assert client.post(f"/api/v1/ai-generation/jobs/{extend_job['id']}/confirm", headers=headers).status_code == 200
        bank_after_extend = client.get(f"/api/v1/question-banks/{bank['id']}", headers=headers).json()
        assert bank_after_extend["question_count"] == 2
        assert bank_after_extend["visibility"] == "public"

        forbidden = client.post(
            f"/api/v1/question-banks/{bank['id']}/ai-generation/extend-jobs",
            headers=other_headers,
            data={"generation_mode": "knowledge_generate", "question_count": "1"},
            files={"file": ("more.txt", b"more content", "text/plain")},
        )
        assert forbidden.status_code == 404


def test_delete_bank_cleans_generation_and_practice_records(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "delete-bank@example.com", "deletebank")
        client.post(
            "/api/v1/users/me/ai-provider-configs",
            headers=headers,
            json={"name": "mock", "api_base_url": "https://example.test/v1", "api_key": "sk-test", "model": "mock", "is_default": True},
        )

        from app.services import ai_generation

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

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", good_ai)
        response = client.post(
            "/api/v1/ai-generation/question-bank-jobs",
            headers=headers,
            data={"title": "Delete Workflow Bank", "desired_visibility": "private", "question_count": "1"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert response.status_code == 200
        bank_id = response.json()["bank_id"]
        job_id = response.json()["job_id"]
        assert client.post(f"/api/v1/ai-generation/jobs/{job_id}/confirm", headers=headers).status_code == 200
        questions = client.get(f"/api/v1/question-banks/{bank_id}/questions", headers=headers).json()
        question = questions["items"][0]
        session = client.post("/api/v1/practice/sessions", headers=headers, json={"bank_id": bank_id, "mode": "practice"}).json()
        client.post(
            f"/api/v1/practice/sessions/{session['id']}/answers",
            headers=headers,
            json={"question_id": question["id"], "selected_option_ids": [question["options"][1]["id"]]},
        )
        assert client.get(f"/api/v1/question-banks/{bank_id}/mistakes", headers=headers).json()["total"] == 1

        deleted = client.delete(f"/api/v1/question-banks/{bank_id}", headers=headers)
        assert deleted.status_code == 200, deleted.text
        assert client.get(f"/api/v1/question-banks/{bank_id}", headers=headers).status_code == 404
        assert client.get(f"/api/v1/ai-generation/jobs/{job_id}", headers=headers).status_code == 404


def test_bank_parse_mode_without_question_count_and_detailed_errors(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "parse@example.com", "parseuser")
        client.post(
            "/api/v1/users/me/ai-provider-configs",
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
            "/api/v1/ai-generation/question-bank-jobs",
            headers=headers,
            data={"title": "Parsed Bank", "desired_visibility": "private", "generation_mode": "bank_parse", "extra_instruction": "保留原题编号"},
            files={"file": ("bank.txt", b"Q1 Parsed question", "text/plain")},
        )
        assert response.status_code == 200
        assert seen_modes == ["bank_parse"]
        assert seen_extra == ["保留原题编号"]
        job = client.get(f"/api/v1/ai-generation/jobs/{response.json()['job_id']}", headers=headers).json()
        assert job["type"] == "bank_parse_ai"
        assert job["status"] == "draft_ready"
        assert job["draft_question_count"] == 1
        bank = client.get(f"/api/v1/question-banks/{response.json()['bank_id']}", headers=headers).json()
        assert bank["question_count"] == 0
        draft = client.get(f"/api/v1/ai-generation/jobs/{job['id']}/draft", headers=headers).json()
        assert draft["questions"][0]["stem"] == "Parsed question"
        assert client.post(f"/api/v1/ai-generation/jobs/{job['id']}/confirm", headers=headers).status_code == 200
        questions = client.get(f"/api/v1/question-banks/{bank['id']}/questions", headers=headers).json()
        assert questions["items"][0]["source"] == "ai_generated"
        assert questions["items"][0]["generated_model"] == "mock"

        def bad_json(*args, **kwargs):
            return {}

        monkeypatch.setattr(ai_generation, "_call_openai_compatible", bad_json)
        bad_response = client.post(
            "/api/v1/ai-generation/question-bank-jobs",
            headers=headers,
            data={"title": "Bad Parsed Bank", "desired_visibility": "private", "generation_mode": "bank_parse"},
            files={"file": ("bank.txt", b"bad", "text/plain")},
        )
        bad_job = client.get(f"/api/v1/ai-generation/jobs/{bad_response.json()['job_id']}", headers=headers).json()
        assert bad_job["status"] == "failed"
        assert "题库解析失败" in bad_job["error_message"]
        assert "缺少 questions" in bad_job["error_message"]

        too_long = client.post(
            "/api/v1/ai-generation/question-bank-jobs",
            headers=headers,
            data={"title": "Too Long", "desired_visibility": "private", "generation_mode": "bank_parse", "extra_instruction": "x" * 2001},
            files={"file": ("bank.txt", b"bad", "text/plain")},
        )
        assert too_long.status_code == 422
        assert "额外指令" in too_long.json()["detail"]


def test_ai_generation_success_public_after_write(monkeypatch):
    with TestClient(app) as client:
        headers = _register(client, "ok@example.com", "okuser")
        client.post(
            "/api/v1/users/me/ai-provider-configs",
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
            "/api/v1/ai-generation/question-bank-jobs",
            headers=headers,
            data={"title": "AI Bank", "desired_visibility": "public", "question_count": "1"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        bank = client.get(f"/api/v1/question-banks/{response.json()['bank_id']}", headers=headers).json()
        assert bank["generation_status"] == "processing"
        assert bank["visibility"] == "private"
        assert bank["question_count"] == 0
        assert bank["description"] is None
        assert client.post(f"/api/v1/ai-generation/jobs/{response.json()['job_id']}/confirm", headers=headers).status_code == 200
        imported_bank = client.get(f"/api/v1/question-banks/{response.json()['bank_id']}", headers=headers).json()
        assert imported_bank["generation_status"] == "succeeded"
        assert imported_bank["visibility"] == "public"
        assert imported_bank["question_count"] == 1

        response_with_description = client.post(
            "/api/v1/ai-generation/question-bank-jobs",
            headers=headers,
            data={"title": "AI Bank With Description", "desired_visibility": "private", "question_count": "1", "generate_description": "true"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert client.post(f"/api/v1/ai-generation/jobs/{response_with_description.json()['job_id']}/confirm", headers=headers).status_code == 200
        described = client.get(f"/api/v1/question-banks/{response_with_description.json()['bank_id']}", headers=headers).json()
        assert described["description"] == "AI generated description"
