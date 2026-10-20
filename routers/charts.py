"""Charts page and the small JSON endpoints that feed it (templates/chart.html)."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from core.auth import get_allowed_projects
from core.db import get_connection
from core.templates import templates

router = APIRouter()


@router.get("/api/chart/formation-capacity")
def chart_formation_capacity():
    """Formation capacity of each SLP cell (bar chart data)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT slp_id, formation_capacity FROM tbl_slp WHERE formation_capacity IS NOT NULL ORDER BY slp_id")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    labels = [r[0] for r in rows]
    values = [float(r[1]) for r in rows]
    return JSONResponse({"labels": labels, "values": values})

@router.get("/chart", response_class=HTMLResponse)
def chart_page(request: Request):
    """Charts page."""
    return templates.TemplateResponse("chart.html", {"request": request})


@router.get("/api/chart/my-projects")
def chart_my_projects(request: Request):
    """Number of coatings and cells in each project the user can see."""
    allowed = get_allowed_projects(request)
    conn = get_connection()
    cur = conn.cursor()

    if allowed is None:
        cur.execute("SELECT project_name FROM tbl_projects WHERE active = true")
        allowed = [row[0] for row in cur.fetchall()]

    results = []
    for project in allowed:
        cur.execute("SELECT COUNT(*) FROM tbl_coating WHERE project = %s", (project,))
        coatings = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tbl_slp WHERE project = %s", (project,))
        slp = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tbl_coincell WHERE project = %s", (project,))
        coincell = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tbl_mlp WHERE project = %s", (project,))
        mlp = cur.fetchone()[0]
        results.append({
            "project": project,
            "coatings": coatings,
            "slp": slp,
            "coincell": coincell,
            "mlp": mlp,
            "total": coatings + slp + coincell + mlp
        })

    cur.close()
    conn.close()
    return JSONResponse({"projects": results})


@router.get("/api/chart/gsm-by-coating")
def chart_gsm():
    """Coat weight (g/m²) of each coating."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT coating_id, coat_weight_gsm FROM tbl_coating WHERE coat_weight_gsm IS NOT NULL ORDER BY coating_id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return JSONResponse({"labels": [r[0] for r in rows], "values": [float(r[1]) for r in rows]})


@router.get("/api/chart/records-per-table")
def chart_records_per_table():
    """How many records each table holds."""
    conn = get_connection()
    cur = conn.cursor()
    counts = {}
    for label, table in [("Materials", "tbl_materials"), ("Coatings", "tbl_coating"),
                          ("SLP", "tbl_slp"), ("Coin Cells", "tbl_coincell"), ("MLP", "tbl_mlp")]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        counts[label] = cur.fetchone()[0]
    cur.close()
    conn.close()
    return JSONResponse({"labels": list(counts.keys()), "values": list(counts.values())})


@router.get("/api/chart/coatings-over-time")
def chart_coatings_over_time():
    """Number of coatings made on each date."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT coating_date, COUNT(*) 
        FROM tbl_coating 
        WHERE coating_date IS NOT NULL 
        GROUP BY coating_date 
        ORDER BY coating_date
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return JSONResponse({"labels": [str(r[0]) for r in rows], "values": [r[1] for r in rows]})
