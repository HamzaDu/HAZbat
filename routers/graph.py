from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from core.db import get_connection
from core.templates import templates
from services.records import detect_record_type

router = APIRouter()


@router.get("/api/graph")
def traceability_graph():
    conn = get_connection()
    cur = conn.cursor()

    nodes = []
    edges = []
    seen_projects = set()

    def add_project_node(project_name):
        if project_name and project_name not in seen_projects:
            nodes.append({"id": f"PROJECT-{project_name}", "label": project_name, "group": "project"})
            seen_projects.add(project_name)

    cur.execute("SELECT material_id, chemistry FROM tbl_materials")
    for mat_id, chem in cur.fetchall():
        nodes.append({"id": mat_id, "label": mat_id, "group": "material", "title": chem or ""})

    cur.execute("SELECT coating_id, material_id, project FROM tbl_coating")
    for coat_id, mat_id, project in cur.fetchall():
        nodes.append({"id": coat_id, "label": coat_id, "group": "coating"})
        edges.append({"from": mat_id, "to": coat_id})
        add_project_node(project)
        if project:
            edges.append({"from": coat_id, "to": f"PROJECT-{project}", "dashes": True})

    cur.execute("SELECT slp_id, coating_id, project FROM tbl_slp")
    for slp_id, coat_id, project in cur.fetchall():
        nodes.append({"id": slp_id, "label": slp_id, "group": "slp"})
        edges.append({"from": coat_id, "to": slp_id})
        add_project_node(project)
        if project:
            edges.append({"from": slp_id, "to": f"PROJECT-{project}", "dashes": True})

    cur.execute("SELECT coincell_id, coating_id, project FROM tbl_coincell")
    for cc_id, coat_id, project in cur.fetchall():
        nodes.append({"id": cc_id, "label": cc_id, "group": "coincell"})
        edges.append({"from": coat_id, "to": cc_id})
        add_project_node(project)
        if project:
            edges.append({"from": cc_id, "to": f"PROJECT-{project}", "dashes": True})

    cur.execute("SELECT mlp_id, cat_coating_id, an_coating_id, project FROM tbl_mlp")
    for mlp_id, cat_id, an_id, project in cur.fetchall():
        nodes.append({"id": mlp_id, "label": mlp_id, "group": "mlp"})
        edges.append({"from": cat_id, "to": mlp_id})
        edges.append({"from": an_id, "to": mlp_id})
        add_project_node(project)
        if project:
            edges.append({"from": mlp_id, "to": f"PROJECT-{project}", "dashes": True})

    cur.close()
    conn.close()
    return JSONResponse({"nodes": nodes, "edges": edges})

@router.get("/graph", response_class=HTMLResponse)
def graph_page(request: Request):
    return templates.TemplateResponse("graph.html", {"request": request})


@router.get("/api/graph/{record_id}")
def record_graph(record_id: str):
    record_type = detect_record_type(record_id)
    if not record_type:
        return JSONResponse({"error": "Unrecognised ID format"}, status_code=404)

    conn = get_connection()
    cur = conn.cursor()
    nodes = []
    edges = []
    seen = set()

    def add_node(node_id, group):
        if node_id not in seen:
            nodes.append({"id": node_id, "label": node_id, "group": group})
            seen.add(node_id)

    add_node(record_id, record_type)

    if record_type == "material":
        cur.execute("SELECT coating_id FROM tbl_coating WHERE material_id = %s", (record_id,))
        for (coating_id,) in cur.fetchall():
            add_node(coating_id, "coating")
            edges.append({"from": record_id, "to": coating_id})

    elif record_type == "coating":
        cur.execute("SELECT material_id FROM tbl_coating WHERE coating_id = %s", (record_id,))
        row = cur.fetchone()
        if row:
            add_node(row[0], "material")
            edges.append({"from": row[0], "to": record_id})

        cur.execute("SELECT slp_id FROM tbl_slp WHERE coating_id = %s", (record_id,))
        for (slp_id,) in cur.fetchall():
            add_node(slp_id, "slp")
            edges.append({"from": record_id, "to": slp_id})

        cur.execute("SELECT coincell_id FROM tbl_coincell WHERE coating_id = %s", (record_id,))
        for (cc_id,) in cur.fetchall():
            add_node(cc_id, "coincell")
            edges.append({"from": record_id, "to": cc_id})

        cur.execute("SELECT mlp_id FROM tbl_mlp WHERE cat_coating_id = %s OR an_coating_id = %s", (record_id, record_id))
        for (mlp_id,) in cur.fetchall():
            add_node(mlp_id, "mlp")
            edges.append({"from": record_id, "to": mlp_id})

    elif record_type in ("slp", "coincell"):
        table = "tbl_slp" if record_type == "slp" else "tbl_coincell"
        id_col = "slp_id" if record_type == "slp" else "coincell_id"
        cur.execute(f"SELECT coating_id FROM {table} WHERE {id_col} = %s", (record_id,))
        row = cur.fetchone()
        if row:
            coating_id = row[0]
            add_node(coating_id, "coating")
            edges.append({"from": coating_id, "to": record_id})

            cur.execute("SELECT material_id FROM tbl_coating WHERE coating_id = %s", (coating_id,))
            mat_row = cur.fetchone()
            if mat_row:
                add_node(mat_row[0], "material")
                edges.append({"from": mat_row[0], "to": coating_id})

    elif record_type == "mlp":
        cur.execute("SELECT cat_coating_id, an_coating_id FROM tbl_mlp WHERE mlp_id = %s", (record_id,))
        row = cur.fetchone()
        if row:
            for coating_id in row:
                add_node(coating_id, "coating")
                edges.append({"from": coating_id, "to": record_id})
                cur.execute("SELECT material_id FROM tbl_coating WHERE coating_id = %s", (coating_id,))
                mat_row = cur.fetchone()
                if mat_row:
                    add_node(mat_row[0], "material")
                    edges.append({"from": mat_row[0], "to": coating_id})

    cur.close()
    conn.close()
    return JSONResponse({"nodes": nodes, "edges": edges})


@router.get("/api/filters")
def graph_filters():
    """
    Filter options for the traceability graph. Shape matches buildFilterUI()
    in templates/graph.html: {material:{...}, coating:{...}, cell:{...}}.
    """
    conn = get_connection()
    cur = conn.cursor()

    def distinct(sql):
        cur.execute(sql)
        return [r[0] for r in cur.fetchall() if r[0] not in (None, "")]

    def value_range(sql):
        cur.execute(sql)
        lo, hi = cur.fetchone()
        if lo is None or hi is None:
            return None
        return {"min": float(lo), "max": float(hi)}

    cells_made_by = distinct("""
        SELECT made_by FROM (
            SELECT made_by FROM tbl_slp
            UNION SELECT made_by FROM tbl_coincell
        ) t ORDER BY 1""")
    cells_electrolyte = distinct("""
        SELECT electrolyte FROM (
            SELECT electrolyte FROM tbl_slp
            UNION SELECT electrolyte FROM tbl_coincell
            UNION SELECT electrolyte FROM tbl_mlp
        ) t ORDER BY 1""")
    cell_capacity = value_range("""
        SELECT MIN(c), MAX(c) FROM (
            SELECT formation_capacity AS c FROM tbl_slp
            UNION ALL SELECT formation_capacity FROM tbl_coincell
            UNION ALL SELECT cell_capacity FROM tbl_mlp
        ) t""")

    result = {
        "material": {
            "chemistry":    distinct("SELECT DISTINCT chemistry FROM tbl_materials ORDER BY 1"),
            "supplier":     distinct("SELECT DISTINCT supplier FROM tbl_materials ORDER BY 1"),
            "location":     distinct("SELECT DISTINCT location FROM tbl_materials ORDER BY 1"),
            "availability": distinct("SELECT DISTINCT availability FROM tbl_materials ORDER BY 1"),
            "quantity_kg":  value_range("SELECT MIN(quantity_kg), MAX(quantity_kg) FROM tbl_materials"),
        },
        "coating": {
            "made_by":         distinct("SELECT DISTINCT made_by FROM tbl_coating ORDER BY 1"),
            "coat_weight_gsm": value_range("SELECT MIN(coat_weight_gsm), MAX(coat_weight_gsm) FROM tbl_coating"),
            "porosity":        value_range("SELECT MIN(porosity), MAX(porosity) FROM tbl_coating"),
        },
        "cell": {
            "made_by":            cells_made_by,
            "electrolyte":        cells_electrolyte,
            "formation_capacity": cell_capacity,
            "np_ratio":           value_range("SELECT MIN(np_ratio), MAX(np_ratio) FROM tbl_slp"),
        },
    }
    cur.close()
    conn.close()
    return result
