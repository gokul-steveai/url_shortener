from fastapi import FastAPI
from app.api.v1.endpoints import router as api_v1_router

app = FastAPI(
    title="Scalable URL Shortener",
    description="A production-grade URL shortening service.",
    version="1.0.0",
)

# Include our versioned routes
app.include_router(api_v1_router)


@app.get("/health")
async def health_check():
    """Service health check for Load Balancers."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)