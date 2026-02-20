from fastapi import FastAPI
from sqlalchemy import text
from app.db.base import Base
from app.db.session import engine
from app.tables import user_table, device_table, session_table, measurement_table, upload_log_table  # noqa
from app.routes import auth, devices, sessions, measurements, stats, coverage

# Create tables (uuid_generate_v4 not needed — UUIDs generated in Python)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CrowdSenseDDT API", version="3.0")

app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(sessions.router)
app.include_router(measurements.router)
app.include_router(stats.router)
app.include_router(coverage.router)

@app.get("/")
def root():
    return {"status": "CrowdSenseDDT API v3 running"}
