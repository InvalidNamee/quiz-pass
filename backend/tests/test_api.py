import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_quiz_pass.db"
os.environ["JWT_SECRET_KEY"] = "test-secret"
Path("test_quiz_pass.db").unlink(missing_ok=True)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _register(client: TestClient, email: str, username: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": "password123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _login(client: TestClient, identifier: str, password: str = "password123") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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

        bank = client.post("/api/v1/question-banks", headers=headers, json={"title": "Bank", "visibility": "private"}).json()
        bank_detail = client.get(f"/api/v1/question-banks/{bank['id']}", headers=headers).json()
        assert bank_detail["owner_username"] == "demo"
        assert client.get(f"/api/v1/question-banks/{bank['id']}", headers=other_headers).status_code == 404
        assert client.post(f"/api/v1/question-banks/{bank['id']}/favorite", headers=other_headers).status_code == 404
        assert client.post(f"/api/v1/question-banks/{bank['id']}/favorite", headers=headers).status_code == 200

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
        submitted = client.post(f"/api/v1/practice/sessions/{session['id']}/submit", headers=headers).json()
        assert submitted["answered_count"] == 1
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
            data={"title": "AI Bank", "desired_visibility": "public", "question_count": "1"},
            files={"file": ("material.txt", b"content", "text/plain")},
        )
        assert response.status_code == 200
        job = client.get(f"/api/v1/ai-generation/jobs/{response.json()['job_id']}", headers=headers).json()
        assert job["status"] == "failed"
        assert "单选题" in job["error_message"]


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
        assert bank["generation_status"] == "succeeded"
        assert bank["visibility"] == "public"
        assert bank["question_count"] == 1
