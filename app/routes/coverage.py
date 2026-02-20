from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from typing import Optional

router = APIRouter(prefix="/coverage", tags=["coverage"])


@router.get("/holes")
def get_coverage_holes(operator: Optional[str] = None, db: Session = Depends(get_db)):
    """Coverage holes — areas with RSRP below -100 dBm."""
    try:
        filters = ["rsrp < -100", "latitude IS NOT NULL"]
        params  = {}
        if operator:
            filters.append("operator_name = :operator")
            params["operator"] = operator

        where = " AND ".join(filters)
        sql   = text(f"""
            SELECT latitude, longitude, rsrp, operator_name, network_type
            FROM network_measurements
            WHERE {where}
            ORDER BY rsrp ASC
            LIMIT 1000
        """)
        rows = db.execute(sql, params).fetchall()
        return [
            {
                "lat":           r.latitude,
                "lon":           r.longitude,
                "avg_rsrp":      round(r.rsrp, 2),
                "operator_name": r.operator_name,
                "network_type":  r.network_type,
                "severity":      _severity(r.rsrp)
            }
            for r in rows
        ]
    except Exception as e:
        return {"error": str(e), "holes": []}


@router.get("/heatmap")
def get_heatmap(
    network_type:  Optional[str] = None,
    operator_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """All geo-referenced measurements for heatmap rendering."""
    try:
        filters = ["latitude IS NOT NULL", "longitude IS NOT NULL"]
        params  = {}

        if network_type:
            filters.append("network_type = :network_type")
            params["network_type"] = network_type
        if operator_name:
            filters.append("operator_name = :operator_name")
            params["operator_name"] = operator_name

        where = " AND ".join(filters)
        sql   = text(f"""
            SELECT latitude, longitude, rsrp, rsrq, sinr, rssi, rscp,
                   network_type, operator_name
            FROM network_measurements
            WHERE {where}
            ORDER BY id DESC
            LIMIT 5000
        """)
        rows = db.execute(sql, params).fetchall()
        return [
            {
                "lat":           r.latitude,
                "lon":           r.longitude,
                "rsrp":          r.rsrp,
                "rsrq":          r.rsrq,
                "sinr":          r.sinr,
                "rssi":          r.rssi,
                "rscp":          r.rscp,
                "network_type":  r.network_type,
                "operator_name": r.operator_name,
            }
            for r in rows
        ]
    except Exception as e:
        return {"error": str(e), "points": []}


def _severity(avg_rsrp: float) -> str:
    if avg_rsrp is None:  return "unknown"
    if avg_rsrp >= -105:  return "mild"
    if avg_rsrp >= -115:  return "moderate"
    return "severe"
