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


def migrate_guide_sign_columns():
    """为已存在的 guide_signs 表补齐批次追踪字段，旧数据默认值保持兼容。"""
    new_columns = {
        "trace_code": "VARCHAR(50) DEFAULT ''",
        "scene_scope": "VARCHAR(20) DEFAULT 'exclusive'",
        "risk_level": "VARCHAR(20) DEFAULT 'none'",
        "handover_note": "TEXT DEFAULT ''",
        "consistency_state": "VARCHAR(20) DEFAULT 'normal'",
        "summary_meta": "TEXT DEFAULT ''",
        "flow_digest": "TEXT DEFAULT ''",
    }
    inspector = inspect(engine)
    if "guide_signs" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("guide_signs")}
    with engine.begin() as conn:
        for name, ddl in new_columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE guide_signs ADD COLUMN {name} {ddl}"))


def migrate_anomaly_columns():
    """为已存在的 anomalies 表补齐批次追踪快照字段，旧数据默认值保持兼容。"""
    new_columns = {
        "trace_code": "VARCHAR(50) DEFAULT ''",
        "scene_scope": "VARCHAR(20) DEFAULT 'exclusive'",
        "risk_level": "VARCHAR(20) DEFAULT 'none'",
        "handover_note": "TEXT DEFAULT ''",
    }
    inspector = inspect(engine)
    if "anomalies" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("anomalies")}
    with engine.begin() as conn:
        for name, ddl in new_columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE anomalies ADD COLUMN {name} {ddl}"))


def migrate_review_record_columns():
    """为已存在的 review_records 表补齐链路摘要字段，旧数据默认值保持兼容。"""
    new_columns = {
        "summary_meta": "TEXT DEFAULT ''",
        "review_digest": "TEXT DEFAULT ''",
    }
    inspector = inspect(engine)
    if "review_records" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("review_records")}
    with engine.begin() as conn:
        for name, ddl in new_columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE review_records ADD COLUMN {name} {ddl}"))


migrate_guide_sign_columns()
migrate_anomaly_columns()
migrate_review_record_columns()

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
