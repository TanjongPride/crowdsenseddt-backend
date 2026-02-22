from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.db.session import get_db

router = APIRouter(prefix="/coverage", tags=["coverage"])


@router.get("/heatmap")
def get_heatmap(
    network_type:  Optional[str] = None,
    operator_name: Optional[str] = None,
    precision:     int           = 4,   # decimal places for grid cell (4 = ~11m cells)
    db:            Session       = Depends(get_db)
):
    """
    Returns aggregated coverage data grouped into geographic grid cells.
    Instead of returning 200,000 raw points, groups them by location and
    returns the average signal quality per cell. This scales to any dataset size.

    precision=3 → ~111m grid cells  (city-wide overview)
    precision=4 → ~11m  grid cells  (street-level detail)  ← default
    precision=5 → ~1m   grid cells  (very dense, only useful zoomed in)
    """
    try:
        filters = ["latitude IS NOT NULL", "longitude IS NOT NULL", "rsrp IS NOT NULL"]
        params  = {"precision": precision}

        if network_type:
            filters.append("network_type = :network_type")
            params["network_type"] = network_type
        if operator_name:
            filters.append("operator_name = :operator_name")
            params["operator_name"] = operator_name

        where = " AND ".join(filters)

        # Group by rounded lat/lon grid cell — aggregate all metrics per cell
        sql = text(f"""
            SELECT
                ROUND(CAST(latitude  AS NUMERIC), :precision) AS lat,
                ROUND(CAST(longitude AS NUMERIC), :precision) AS lon,
                AVG(rsrp)          AS rsrp,
                AVG(rsrq)          AS rsrq,
                AVG(sinr)          AS sinr,
                AVG(rssi)          AS rssi,
                AVG(rscp)          AS rscp,
                COUNT(*)           AS sample_count,
                MAX(network_type)  AS network_type,
                MAX(operator_name) AS operator_name
            FROM network_measurements
            WHERE {where}
            GROUP BY
                ROUND(CAST(latitude  AS NUMERIC), :precision),
                ROUND(CAST(longitude AS NUMERIC), :precision)
            ORDER BY sample_count DESC
            LIMIT 50000
        """)

        rows = db.execute(sql, params).fetchall()

        return [
            {
                "lat":          float(r.lat),
                "lon":          float(r.lon),
                "rsrp":         round(float(r.rsrp), 2) if r.rsrp else None,
                "rsrq":         round(float(r.rsrq), 2) if r.rsrq else None,
                "sinr":         round(float(r.sinr), 2) if r.sinr else None,
                "rssi":         round(float(r.rssi), 2) if r.rssi else None,
                "rscp":         round(float(r.rscp), 2) if r.rscp else None,
                "sample_count": int(r.sample_count),
                "network_type": r.network_type,
                "operator_name":r.operator_name,
            }
            for r in rows
        ]
    except Exception as e:
        return {"error": str(e), "points": []}


@router.get("/heatmap/raw")
def get_heatmap_raw(
    network_type:  Optional[str] = None,
    operator_name: Optional[str] = None,
    limit:         int           = 5000,
    db:            Session       = Depends(get_db)
):
    """
    Returns raw (non-aggregated) measurements. Use for small areas or exports.
    Hard-capped at 10,000 rows to protect the server.
    """
    try:
        filters = ["latitude IS NOT NULL", "longitude IS NOT NULL"]
        params  = {}

        if network_type:
            filters.append("network_type = :network_type")
            params["network_type"] = network_type
        if operator_name:
            filters.append("operator_name = :operator_name")
            params["operator_name"] = operator_name

        params["limit"] = min(limit, 10000)
        where = " AND ".join(filters)

        sql = text(f"""
            SELECT latitude, longitude, rsrp, rsrq, sinr, rssi, rscp,
                   network_type, operator_name
            FROM network_measurements
            WHERE {where}
            ORDER BY id DESC
            LIMIT :limit
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
                "sample_count":  1,
            }
            for r in rows
        ]
    except Exception as e:
        return {"error": str(e), "points": []}


@router.get("/holes")
def get_coverage_holes(
    operator: Optional[str] = None,
    db:       Session       = Depends(get_db)
):
    """Coverage holes — grid cells where average RSRP is below -100 dBm."""
    try:
        filters = ["rsrp IS NOT NULL", "latitude IS NOT NULL"]
        params  = {}
        if operator:
            filters.append("operator_name = :operator")
            params["operator"] = operator

        where = " AND ".join(filters)
        sql = text(f"""
            SELECT
                ROUND(CAST(latitude  AS NUMERIC), 3) AS lat,
                ROUND(CAST(longitude AS NUMERIC), 3) AS lon,
                AVG(rsrp)  AS avg_rsrp,
                COUNT(*)   AS sample_count,
                MAX(operator_name) AS operator_name,
                MAX(network_type)  AS network_type
            FROM network_measurements
            WHERE {where}
            GROUP BY
                ROUND(CAST(latitude  AS NUMERIC), 3),
                ROUND(CAST(longitude AS NUMERIC), 3)
            HAVING AVG(rsrp) < -100
            ORDER BY avg_rsrp ASC
            LIMIT 2000
        """)
        rows = db.execute(sql, params).fetchall()
        return [
            {
                "lat":           float(r.lat),
                "lon":           float(r.lon),
                "avg_rsrp":      round(float(r.avg_rsrp), 2),
                "sample_count":  int(r.sample_count),
                "operator_name": r.operator_name,
                "network_type":  r.network_type,
                "severity":      _severity(r.avg_rsrp)
            }
            for r in rows
        ]
    except Exception as e:
        return {"error": str(e), "holes": []}


@router.get("/summary/grid")
def get_grid_summary(
    precision: int     = 3,
    db:        Session = Depends(get_db)
):
    """
    City-level grid summary — perfect for overview maps.
    precision=3 gives ~111m cells, ideal for seeing city-wide patterns.
    """
    try:
        sql = text("""
            SELECT
                ROUND(CAST(latitude  AS NUMERIC), :precision) AS lat,
                ROUND(CAST(longitude AS NUMERIC), :precision) AS lon,
                AVG(rsrp)   AS avg_rsrp,
                COUNT(*)    AS samples,
                SUM(CASE WHEN rsrp >= -80  THEN 1 ELSE 0 END) AS excellent,
                SUM(CASE WHEN rsrp >= -90  AND rsrp < -80  THEN 1 ELSE 0 END) AS good,
                SUM(CASE WHEN rsrp >= -100 AND rsrp < -90  THEN 1 ELSE 0 END) AS fair,
                SUM(CASE WHEN rsrp < -100  THEN 1 ELSE 0 END) AS poor
            FROM network_measurements
            WHERE latitude IS NOT NULL AND rsrp IS NOT NULL
            GROUP BY
                ROUND(CAST(latitude  AS NUMERIC), :precision),
                ROUND(CAST(longitude AS NUMERIC), :precision)
            ORDER BY samples DESC
            LIMIT 10000
        """)
        rows = db.execute(sql, {"precision": precision}).fetchall()
        return [
            {
                "lat":       float(r.lat),
                "lon":       float(r.lon),
                "avg_rsrp":  round(float(r.avg_rsrp), 2),
                "samples":   int(r.samples),
                "excellent": int(r.excellent),
                "good":      int(r.good),
                "fair":      int(r.fair),
                "poor":      int(r.poor),
            }
            for r in rows
        ]
    except Exception as e:
        return {"error": str(e)}


def _severity(rsrp) -> str:
    if rsrp is None:  return "unknown"
    if rsrp >= -105:  return "mild"
    if rsrp >= -115:  return "moderate"
    return "severe"
