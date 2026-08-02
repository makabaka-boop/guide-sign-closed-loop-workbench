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


def _migrate_guide_signs():
    inspector = inspect(engine)
    if "guide_signs" not in inspector.get_table_names():
        return
    existing_cols = {c["name"] for c in inspector.get_columns("guide_signs")}
    new_columns = [
        ("trace_code", "VARCHAR(100) DEFAULT ''"),
        ("scene_scope", "VARCHAR(20) DEFAULT 'exclusive'"),
        ("risk_level", "VARCHAR(20) DEFAULT 'normal'"),
        ("handover_note", "TEXT DEFAULT ''"),
        ("consistency_state", "VARCHAR(20) DEFAULT 'ok'"),
        ("summary_meta", "TEXT DEFAULT ''"),
        ("flow_digest", "TEXT DEFAULT ''"),
    ]
    with engine.begin() as conn:
        for col_name, col_def in new_columns:
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE guide_signs ADD COLUMN {col_name} {col_def}"))

    if "anomalies" in inspector.get_table_names():
        anomaly_cols = {c["name"] for c in inspector.get_columns("anomalies")}
        anomaly_new_columns = [
            ("trace_code", "VARCHAR(100) DEFAULT ''"),
            ("scene_scope", "VARCHAR(20) DEFAULT 'exclusive'"),
            ("risk_level", "VARCHAR(20) DEFAULT 'normal'"),
            ("handover_note", "TEXT DEFAULT ''"),
        ]
        with engine.begin() as conn:
            for col_name, col_def in anomaly_new_columns:
                if col_name not in anomaly_cols:
                    conn.execute(text(f"ALTER TABLE anomalies ADD COLUMN {col_name} {col_def}"))

    if "review_records" in inspector.get_table_names():
        review_cols = {c["name"] for c in inspector.get_columns("review_records")}
        review_new_columns = [
            ("summary_meta", "TEXT DEFAULT ''"),
            ("review_digest", "TEXT DEFAULT ''"),
        ]
        with engine.begin() as conn:
            for col_name, col_def in review_new_columns:
                if col_name not in review_cols:
                    conn.execute(text(f"ALTER TABLE review_records ADD COLUMN {col_name} {col_def}"))

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
    _migrate_guide_signs()
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
