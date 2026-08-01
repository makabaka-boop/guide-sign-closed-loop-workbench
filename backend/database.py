from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./guide_sign.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_columns():
    """为已存在的旧表补齐新增列，保证旧数据兼容（新列默认空）。"""
    new_columns = {
        "guide_signs": [
            ("trace_code", "VARCHAR(50) DEFAULT ''"),
            ("scene_scope", "VARCHAR(20) DEFAULT ''"),
            ("risk_level", "VARCHAR(20) DEFAULT ''"),
            ("handover_note", "TEXT DEFAULT ''"),
            ("consistency_state", "VARCHAR(20) DEFAULT ''"),
            ("summary_meta", "TEXT DEFAULT ''"),
            ("flow_digest", "VARCHAR(200) DEFAULT ''"),
        ],
        "anomalies": [
            ("trace_code", "VARCHAR(50) DEFAULT ''"),
            ("scene_scope", "VARCHAR(20) DEFAULT ''"),
            ("risk_level", "VARCHAR(20) DEFAULT ''"),
            ("handover_note", "TEXT DEFAULT ''"),
        ],
        "review_records": [
            ("summary_meta", "TEXT DEFAULT ''"),
            ("review_digest", "TEXT DEFAULT ''"),
        ]
    }
    with engine.connect() as conn:
        for table, columns in new_columns.items():
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            for name, ddl in columns:
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        conn.commit()
