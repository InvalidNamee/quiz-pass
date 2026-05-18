from fastapi import APIRouter

from app.domains.ai_generation.router import router as ai_generation_router
from app.domains.practice.router import router as practice_router
from app.domains.question_banks.router import router as question_banks_router
from app.domains.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(users_router, tags=["v2-users"])
api_router.include_router(question_banks_router, tags=["v2-question-banks"])
api_router.include_router(practice_router, tags=["v2-practice"])
api_router.include_router(ai_generation_router, tags=["v2-ai-generation"])
