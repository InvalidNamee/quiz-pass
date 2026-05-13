from fastapi import APIRouter

from app.api.v1 import admin, ai_generation, auth, practice, question_banks, questions, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(question_banks.router, prefix="/question-banks", tags=["question-banks"])
api_router.include_router(questions.router, tags=["questions"])
api_router.include_router(ai_generation.router, prefix="/ai-generation", tags=["ai-generation"])
api_router.include_router(practice.router, tags=["practice"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
