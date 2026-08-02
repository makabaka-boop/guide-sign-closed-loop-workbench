from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine, SessionLocal, ensure_columns
from models import *
from auth import init_default_user
from routers.auth_router import router as auth_router
from routers.sign_router import router as sign_router
from routers.stats_router import router as stats_router
from routers.anomaly_router import router as anomaly_router

Base.metadata.create_all(bind=engine)
ensure_columns()

app = FastAPI(title="试听现场导引位标防错闭环工作台", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(sign_router)
app.include_router(stats_router)
app.include_router(anomaly_router)


@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        init_default_user(db)
    finally:
        db.close()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "导引位标防错闭环服务运行中"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8130)
