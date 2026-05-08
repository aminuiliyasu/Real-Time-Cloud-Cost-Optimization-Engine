from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis
from app.api.dashboard import router as dashboard_router
from app.api.ingestion import router as ingestion_router
from app.api.resources import router as resources_router
from app.api.recommendations import router as recommendations_router

from app.core.config import settings
from app.db.session import check_db_connection

app = FastAPI(title="Real-Time Cloud Cost Optimization Engine API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev-friendly; restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(resources_router)
app.include_router(recommendations_router)
app.include_router(ingestion_router)
app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "backend-api", "env": settings.app_env}


@app.get("/db-check")
def db_check():
    ok = check_db_connection()
    return {"database": "ok" if ok else "error"}


@app.get("/redis-check")
def redis_check():
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        pong = client.ping()
        return {"redis": "ok" if pong else "error"}
    except Exception:
        return {"redis": "error"}