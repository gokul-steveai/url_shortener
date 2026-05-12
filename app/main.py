import logging
import uuid

from fastapi import FastAPI, Request
from app.api.v1.endpoints import router as api_v1_router
from app.core.config import settings
from app.core.logging import setup_logging, request_id_ctx

# Boot logging before anything else
setup_logging(level=settings.LOG_LEVEL, fmt=settings.LOG_FORMAT)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Scalable URL Shortener",
    description="A production-grade URL shortening service.",
    version="1.0.0",
)

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Stamp every request with a unique ID and surface it in logs + response headers."""
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(rid)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        request_id_ctx.reset(token)


app.include_router(api_v1_router)


@app.get("/health")
async def health_check():
    """Service health check for Load Balancers."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)