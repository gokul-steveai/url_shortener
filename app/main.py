import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from app.api.v1.router import router as api_router
from app.core.config import settings
from app.core.logging import setup_logging, request_id_ctx

setup_logging(level=settings.LOG_LEVEL, fmt=settings.LOG_FORMAT)

logger = logging.getLogger(__name__)

_TAGS = [
    {
        "name": "Authentication",
        "description": "Registration, login, token refresh, password reset. **No token required.**",
    },
    {
        "name": "Links",
        "description": "Create, list, delete short URLs and fetch AI summaries. 🔒 **JWT required.**",
    },
    {
        "name": "Admin",
        "description": "Admin-only operations — user management. 🔒 **Admin JWT required.**",
    },
    {
        "name": "Public Endpoints",
        "description": "Public redirect endpoint. **No token required.**",
    },
    {
        "name": "System Endpoints",
        "description": "Health check and aggregate stats.",
    },
]

app = FastAPI(
    title="BoltLink API",
    description=(
        "## ⚡ BoltLink — Production-Grade URL Shortener\n\n"
        "A high-performance URL shortening service with AI-powered summaries, "
        "Redis caching, JWT authentication, and role-based access control.\n\n"
        "### Authentication\n"
        "1. `POST /auth/register` or `POST /auth/login` to get tokens\n"
        "2. Click **Authorize** and enter: `Bearer <access_token>`\n"
        "3. All 🔒 endpoints will use it automatically\n\n"
        "### Roles\n"
        "- `user` — default role, can manage own links\n"
        "- `admin` — can access admin endpoints\n"
    ),
    version="1.0.0",
    openapi_tags=_TAGS,
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        tags=_TAGS,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Paste your access token from `/auth/login` or `/auth/register`",
        }
    }
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(rid)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        request_id_ctx.reset(token)


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
