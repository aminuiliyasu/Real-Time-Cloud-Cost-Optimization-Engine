from fastapi import FastAPI

app = FastAPI(title="Real-Time Cloud Cost Optimization Engine API")


@app.get("/health")
def health():
    return {"status": "ok", "service": "backend-api"}