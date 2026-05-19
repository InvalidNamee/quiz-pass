from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v2.router import api_router as api_v2_router
from app.core.config import get_settings
from app import models  # noqa: F401

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Quiz Pass API", version="0.1.0", lifespan=lifespan)


def _is_v2_request(request: Request) -> bool:
    return request.url.path.startswith("/api/v2")


@app.exception_handler(HTTPException)
async def quiz_pass_http_exception_handler(request: Request, exc: HTTPException):
    if not _is_v2_request(request):
        return await http_exception_handler(request, exc)
    message = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": message,
                "details": exc.detail if not isinstance(exc.detail, str) else {},
            }
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def quiz_pass_validation_exception_handler(request: Request, exc: RequestValidationError):
    if not _is_v2_request(request):
        return await request_validation_exception_handler(request, exc)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数校验失败",
                "details": exc.errors(),
            }
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api_v2_router, prefix="/api/v2")
