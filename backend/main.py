from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from database import Base, engine, SessionLocal
from models import *
from auth import init_default_user
from routers.auth_router import router as auth_router
from routers.sign_router import router as sign_router
from routers.stats_router import router as stats_router
from routers.anomaly_router import router as anomaly_router

Base.metadata.create_all(bind=engine)


GUIDE_SIGN_NEW_COLUMNS = [
    ("trace_code", "VARCHAR(100) DEFAULT ''"),
    ("scene_scope", "VARCHAR(30) DEFAULT 'private'"),
    ("risk_level", "VARCHAR(20) DEFAULT 'green'"),
    ("handover_note", "TEXT DEFAULT ''"),
    ("consistency_state", "VARCHAR(20) DEFAULT 'ok'"),
    ("summary_meta", "TEXT DEFAULT ''"),
    ("flow_digest", "TEXT DEFAULT ''"),
]

ANOMALY_NEW_COLUMNS = [
    ("trace_code", "VARCHAR(100) DEFAULT ''"),
    ("scene_scope", "VARCHAR(30) DEFAULT 'private'"),
    ("risk_level", "VARCHAR(20) DEFAULT 'green'"),
    ("handover_note", "TEXT DEFAULT ''"),
]

REVIEW_RECORD_NEW_COLUMNS = [
    ("summary_meta", "TEXT DEFAULT ''"),
    ("review_digest", "TEXT DEFAULT ''"),
]


def ensure_guide_sign_columns():
    inspector = inspect(engine)
    existing = {col["name"] for col in inspector.get_columns("guide_signs")}
    with engine.begin() as conn:
        for column_name, column_ddl in GUIDE_SIGN_NEW_COLUMNS:
            if column_name not in existing:
                conn.execute(text(
                    f"ALTER TABLE guide_signs ADD COLUMN {column_name} {column_ddl}"
                ))


def ensure_anomaly_columns():
    inspector = inspect(engine)
    if not inspector.has_table("anomalies"):
        return
    existing = {col["name"] for col in inspector.get_columns("anomalies")}
    with engine.begin() as conn:
        for column_name, column_ddl in ANOMALY_NEW_COLUMNS:
            if column_name not in existing:
                conn.execute(text(
                    f"ALTER TABLE anomalies ADD COLUMN {column_name} {column_ddl}"
                ))


def ensure_review_record_columns():
    inspector = inspect(engine)
    if not inspector.has_table("review_records"):
        return
    existing = {col["name"] for col in inspector.get_columns("review_records")}
    with engine.begin() as conn:
        for column_name, column_ddl in REVIEW_RECORD_NEW_COLUMNS:
            if column_name not in existing:
                conn.execute(text(
                    f"ALTER TABLE review_records ADD COLUMN {column_name} {column_ddl}"
                ))


ensure_guide_sign_columns()
ensure_anomaly_columns()
ensure_review_record_columns()

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
