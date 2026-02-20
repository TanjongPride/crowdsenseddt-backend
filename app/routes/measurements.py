from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from app.db.session import get_db
from app.tables.measurement_table import NetworkMeasurement
from app.tables.session_table import MeasurementSession, MobilityType
from app.tables.upload_log_table import UploadLog, UploadLogStatus
from app.schemas import NetworkMeasurementSchema

router = APIRouter(tags=["measurements"])


@router.post("/upload")
def upload_measurements(
    measurements: List[NetworkMeasurementSchema],
    db: Session = Depends(get_db)
):
    if not measurements:
        raise HTTPException(status_code=400, detail="Empty payload")

    session_id = measurements[0].session_id
    user_id    = measurements[0].user_id
    device_id  = measurements[0].device_id

    session = db.query(MeasurementSession).filter(
        MeasurementSession.id == session_id
    ).first()

    if not session:
        session = MeasurementSession(
            id            = session_id,
            user_id       = user_id,
            device_id     = device_id,
            mobility_type = MobilityType.static,
        )
        db.add(session)
        db.commit()

    inserted = []
    try:
        for m in measurements:
            row = NetworkMeasurement(
                session_id        = m.session_id,
                device_id         = m.device_id,
                user_id           = m.user_id,
                timestamp         = m.timestamp,
                network_type      = m.network_type,
                operator_name     = m.operator_name,
                mcc               = m.mcc,
                mnc               = m.mnc,
                cell_id           = m.cell_id,
                pci               = m.pci,
                earfcn            = m.earfcn,
                bandwidth_mhz     = m.bandwidth_mhz,
                rsrp              = m.rsrp,
                rsrq              = m.rsrq,
                sinr              = m.sinr,
                rssi              = m.rssi,
                rscp              = m.rscp,
                ecno              = m.ecno,
                cqi               = m.cqi,
                ta                = m.ta,
                latitude          = m.latitude,
                longitude         = m.longitude,
                altitude          = m.altitude,
                speed             = m.speed,
                heading           = m.heading,
                location_accuracy = m.location_accuracy,
                is_roaming        = m.is_roaming,
                is_data_active    = m.is_data_active,
            )
            db.add(row)
            inserted.append(row)

        db.commit()

        log = UploadLog(
            session_id = session_id,
            status     = UploadLogStatus.success,
            rows_sent  = len(inserted)
        )
        db.add(log)
        db.commit()

        return {"status": "ok", "count": len(inserted)}

    except Exception as e:
        db.rollback()
        log = UploadLog(
            session_id    = session_id,
            status        = UploadLogStatus.fail,
            rows_sent     = 0,
            error_message = str(e)
        )
        db.add(log)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


class MeasurementResponse(BaseModel):
    id:            int
    session_id:    UUID
    timestamp:     datetime
    network_type:  Optional[str]
    operator_name: Optional[str]
    rsrp:          Optional[float]
    rsrq:          Optional[float]
    sinr:          Optional[float]
    rssi:          Optional[float]
    latitude:      Optional[float]
    longitude:     Optional[float]

    class Config:
        from_attributes = True


@router.get("/measurements", response_model=List[MeasurementResponse])
def get_measurements(
    limit:        int           = 100,
    network_type: Optional[str] = None,
    min_rsrp:     Optional[float] = None,
    db:           Session       = Depends(get_db)
):
    query = db.query(NetworkMeasurement)

    if network_type:
        query = query.filter(NetworkMeasurement.network_type == network_type)
    if min_rsrp is not None:
        query = query.filter(NetworkMeasurement.rsrp >= min_rsrp)

    return (
        query
        .order_by(NetworkMeasurement.id.desc())
        .limit(min(limit, 500))  # max 500 per page
        .all()
    )
