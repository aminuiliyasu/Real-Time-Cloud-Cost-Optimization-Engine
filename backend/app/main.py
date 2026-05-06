from fastapi import FastAPI
import redis

from app.core.config import settings
from app.db.session import check_db_connection

app = FastAPI(title="Real-Time Cloud Cost Optimization Engine API")


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