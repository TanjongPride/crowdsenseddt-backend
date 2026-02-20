import uuid
import enum
from sqlalchemy import Column, DateTime, Boolean, Integer, ForeignKey, Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from app.db.base import Base


class MobilityType(str, enum.Enum):
    walking = "walking"
    driving = "driving"
    static  = "static"


class MeasurementSession(Base):
    __tablename__ = "measurement_sessions"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_id     = Column(PG_UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    start_time    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_time      = Column(DateTime(timezone=True), nullable=True)
    mobility_type = Column(PgEnum(MobilityType), nullable=True)
    total_samples = Column(Integer, default=0)
    uploaded      = Column(Boolean, default=False)
