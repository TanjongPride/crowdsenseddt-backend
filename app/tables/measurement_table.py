from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from app.db.base import Base


class NetworkMeasurement(Base):
    __tablename__ = "network_measurements"

    id                = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id        = Column(PG_UUID(as_uuid=True), ForeignKey("measurement_sessions.id"), nullable=False)
    device_id         = Column(PG_UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    user_id           = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    timestamp         = Column(DateTime, nullable=False)

    network_type      = Column(String(20))
    operator_name     = Column(String(50))
    mcc               = Column(Integer)
    mnc               = Column(Integer)
    cell_id           = Column(BigInteger)
    pci               = Column(Integer)
    earfcn            = Column(Integer)
    bandwidth_mhz     = Column(Integer)

    rsrp              = Column(Float)
    rsrq              = Column(Float)
    sinr              = Column(Float)
    rssi              = Column(Float)
    rscp              = Column(Float)
    ecno              = Column(Float)
    cqi               = Column(Integer)
    ta                = Column(Integer)

    latitude          = Column(Float)
    longitude         = Column(Float)
    altitude          = Column(Float)
    speed             = Column(Float)
    heading           = Column(Float)
    location_accuracy = Column(Float)

    is_roaming        = Column(Boolean)
    is_data_active    = Column(Boolean)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
