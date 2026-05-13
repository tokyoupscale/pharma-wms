import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn as uv

from routers import auth, references, supply as supply_router, expense as expense_router
from routers import limit_card as limit_card_router, request as request_router, reports as reports_router
from routers import operations_log as operations_log_router

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app = FastAPI(
    title="АО «Фармцентр ВИЛАР» — Система складского учёта МТЗ",
    description="Информационная система учёта складских операций с материально-техническими запасами и сырьём",
    version="1.0.0",
    docs_url=None if ENVIRONMENT == "production" else "/docs",
    redoc_url=None if ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if ENVIRONMENT == "production" else "/openapi.json",
)

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security headers ─────────────────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(references.router)
app.include_router(supply_router.router)
app.include_router(expense_router.router)
app.include_router(limit_card_router.router)
app.include_router(request_router.router)
app.include_router(reports_router.router)
app.include_router(operations_log_router.router)

@app.get("/", tags=["Status"])
def root():
    return {"status": "ok"}

if __name__ == "__main__":
    uv.run(app, host="localhost", port=8000)
