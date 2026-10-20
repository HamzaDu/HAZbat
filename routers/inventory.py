from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
import io

import pandas as pd

from core.auth import get_allowed_projects, require_login
from core.db import get_connection
from core.templates import templates
from services.records import detect_record_type

router = APIRouter()


@router.get("/directory", response_class=HTMLResponse)
def directory(request: Request, record_id: str = None):
    record = None
    record_type = None
    searched = record_id is not None
 
    if record_id:
        record_type = detect_record_type(record_id)
        conn = get_connection()
        cur = conn.cursor()
        allowed = get_allowed_projects(request)  # None = admin, sees everything
 
        if record_type == "material":
            cur.execute(
                "SELECT chemistry, supplier, date_received, quantity_kg, location, availability, notes "
                "FROM tbl_materials WHERE material_id = %s",
                (record_id,)
            )
            columns = ["chemistry", "supplier", "date_received", "quantity_kg", "location", "availability", "notes"]
            row = cur.fetchone()
            if row:
                record = dict(zip(columns, row))
                cur.execute("SELECT coating_id FROM tbl_coating WHERE material_id = %s", (record_id,))
                downstream = [f"Coating: {r[0]}" for r in cur.fetchall()]
                record["_chain"] = downstream if downstream else ["No downstream records yet"]
 
        elif record_type == "coating":
            cur.execute(
                "SELECT material_id, project, coating_date, made_by, coat_weight_gsm, porosity, notes "
                "FROM tbl_coating WHERE coating_id = %s",
                (record_id,)
            )
            columns = ["material_id", "project", "coating_date", "made_by", "coat_weight_gsm", "porosity", "notes"]
            row = cur.fetchone()
            if row and allowed is not None and row[1] not in allowed:
                row = None  # record belongs to a project this user can't see
            if row:
                record = dict(zip(columns, row))
 
                cur.execute("SELECT chemistry FROM tbl_materials WHERE material_id = %s", (record["material_id"],))
                mat = cur.fetchone()
                upstream = [f"Material: {record['material_id']} ({mat[0] if mat else '?'})"]
 
                downstream = []
                cur.execute("SELECT slp_id FROM tbl_slp WHERE coating_id = %s", (record_id,))
                downstream += [f"SLP: {r[0]}" for r in cur.fetchall()]
                cur.execute("SELECT coincell_id FROM tbl_coincell WHERE coating_id = %s", (record_id,))
                downstream += [f"CoinCell: {r[0]}" for r in cur.fetchall()]
                cur.execute("SELECT mlp_id FROM tbl_mlp WHERE cat_coating_id = %s OR an_coating_id = %s", (record_id, record_id))
                downstream += [f"MLP: {r[0]}" for r in cur.fetchall()]
 
                record["_chain"] = upstream + (downstream if downstream else ["No downstream records yet"])
 
        elif record_type == "slp":
            cur.execute(
                "SELECT coating_id, project, date_made, made_by, electrolyte, formation_capacity, np_ratio, notes "
                "FROM tbl_slp WHERE slp_id = %s",
                (record_id,)
            )
            columns = ["coating_id", "project", "date_made", "made_by", "electrolyte", "formation_capacity", "np_ratio", "notes"]
            row = cur.fetchone()
            if row and allowed is not None and row[1] not in allowed:
                row = None  # record belongs to a project this user can't see
            if row:
                record = dict(zip(columns, row))
                cur.execute("SELECT material_id FROM tbl_coating WHERE coating_id = %s", (record["coating_id"],))
                mat = cur.fetchone()
                record["_chain"] = [f"Coating: {record['coating_id']}", f"Material: {mat[0] if mat else '?'}"]
 
        elif record_type == "coincell":
            cur.execute(
                "SELECT coating_id, project, date_made, made_by, electrolyte, formation_capacity, cell_type, gsm, notes "
                "FROM tbl_coincell WHERE coincell_id = %s",
                (record_id,)
            )
            columns = ["coating_id", "project", "date_made", "made_by", "electrolyte", "formation_capacity", "cell_type", "gsm", "notes"]
            row = cur.fetchone()
            if row and allowed is not None and row[1] not in allowed:
                row = None  # record belongs to a project this user can't see
            if row:
                record = dict(zip(columns, row))
                cur.execute("SELECT material_id FROM tbl_coating WHERE coating_id = %s", (record["coating_id"],))
                mat = cur.fetchone()
                record["_chain"] = [f"Coating: {record['coating_id']}", f"Material: {mat[0] if mat else '?'}"]
 
        elif record_type == "mlp":
            cur.execute(
                "SELECT cat_coating_id, an_coating_id, project, date_made, cell_capacity, electrolyte, ac_area_ratio "
                "FROM tbl_mlp WHERE mlp_id = %s",
                (record_id,)
            )
            columns = ["cat_coating_id", "an_coating_id", "project", "date_made", "cell_capacity", "electrolyte", "ac_area_ratio"]
            row = cur.fetchone()
            if row and allowed is not None and row[2] not in allowed:
                row = None  # record belongs to a project this user can't see
            if row:
                record = dict(zip(columns, row))
                chain = []
                for label, cid in (("Cathode coating", record["cat_coating_id"]), ("Anode coating", record["an_coating_id"])):
                    cur.execute("SELECT material_id FROM tbl_coating WHERE coating_id = %s", (cid,))
                    mat = cur.fetchone()
                    chain.append(f"{label}: {cid} (material: {mat[0] if mat else '?'})")
                record["_chain"] = chain
 
        else:
            columns = []
 
        if record_type and record_type not in ("coating", "material", "slp", "coincell", "mlp"):
            row = cur.fetchone()
            if row:
                record = dict(zip(columns, row))
 
        cur.close()
        conn.close()
 
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "record": record, "record_id": record_id, "record_type": record_type, "searched": searched}
    )


@router.get("/inventory/materials", response_class=HTMLResponse)
def inventory_materials(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT material_id, chemistry, supplier, date_received, quantity_kg, location, availability "
        "FROM tbl_materials ORDER BY material_id"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
 
    columns = ["Material ID", "Chemistry", "Supplier", "Date Received", "Quantity (kg)", "Location", "Availability"]
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "title": "Materials", "columns": columns, "rows": rows,
         "new_url": "/materials/new", "bulk_url": "/materials/bulk-upload",
         "edit_url_base": "/materials"}
    )
 
@router.get("/inventory/coatings", response_class=HTMLResponse)
def inventory_coatings(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    allowed = get_allowed_projects(request)  # None = admin, sees everything
    where, params = ("", ()) if allowed is None else (" WHERE project = ANY(%s)", (list(allowed),))
    cur.execute(
        "SELECT coating_id, material_id, project, coating_date, made_by, coat_weight_gsm, porosity "
        "FROM tbl_coating" + where + " ORDER BY coating_id", params
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    columns = ["Coating ID", "Material ID", "Project", "Coating Date", "Made By", "GSM", "Porosity"]
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "title": "Coatings", "columns": columns, "rows": rows,
         "new_url": "/coatings/new", "bulk_url": "/coatings/bulk-upload",
         "edit_url_base": "/coatings"}
    )
 
 
@router.get("/inventory/slp", response_class=HTMLResponse)
def inventory_slp(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    allowed = get_allowed_projects(request)  # None = admin, sees everything
    where, params = ("", ()) if allowed is None else (" WHERE project = ANY(%s)", (list(allowed),))
    cur.execute(
        "SELECT slp_id, coating_id, project, date_made, made_by, electrolyte, formation_capacity "
        "FROM tbl_slp" + where + " ORDER BY slp_id", params
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    columns = ["SLP ID", "Coating ID", "Project", "Date Made", "Made By", "Electrolyte", "Formation Capacity"]
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "title": "SLP Cells", "columns": columns, "rows": rows,
         "new_url": "/slp/new","edit_url_base": "/slp" ,"bulk_url": "/slp/bulk-upload"}
    )
 
@router.get("/inventory/coincell", response_class=HTMLResponse)
def inventory_coincell(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    allowed = get_allowed_projects(request)  # None = admin, sees everything
    where, params = ("", ()) if allowed is None else (" WHERE project = ANY(%s)", (list(allowed),))
    cur.execute(
        "SELECT coincell_id, coating_id, project, date_made, made_by, electrolyte, formation_capacity "
        "FROM tbl_coincell" + where + " ORDER BY coincell_id", params
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    columns = ["Coin Cell ID", "Coating ID", "Project", "Date Made", "Made By", "Electrolyte", "Formation Capacity"]
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "title": "Coin Cells", "columns": columns, "rows": rows,
         "new_url": "/coincell/new", "bulk_url": "/coincell/bulk-upload"}
    )
 
 
@router.get("/inventory/mlp", response_class=HTMLResponse)
def inventory_mlp(request: Request):
    conn = get_connection()
    cur = conn.cursor()
    allowed = get_allowed_projects(request)  # None = admin, sees everything
    where, params = ("", ()) if allowed is None else (" WHERE project = ANY(%s)", (list(allowed),))
    cur.execute(
        "SELECT mlp_id, cat_coating_id, an_coating_id, project, date_made, cell_capacity "
        "FROM tbl_mlp" + where + " ORDER BY mlp_id", params
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    columns = ["MLP ID", "Cathode Coating", "Anode Coating", "Project", "Date Made", "Cell Capacity"]
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "title": "MLP Cells", "columns": columns, "rows": rows,
         "new_url": "/mlp/new", "bulk_url": "/mlp/bulk-upload"}
    )
 

# --- Export an inventory table to CSV or Excel --------------------------------
# URL key -> (table, ID column used for sorting, sheet/file name)
EXPORT_TABLES = {
    "materials": ("tbl_materials", "material_id", "Materials"),
    "coatings":  ("tbl_coating", "coating_id", "Coatings"),
    "slp":       ("tbl_slp", "slp_id", "SLP"),
    "coincell":  ("tbl_coincell", "coincell_id", "CoinCells"),
    "mlp":       ("tbl_mlp", "mlp_id", "MLP"),
}
EXPORT_BLANK = "N/A"  # empty cells are written as N/A (bulk upload reads N/A back as "no data")


@router.get("/inventory/{table_key}/export")
def export_inventory(request: Request, table_key: str, format: str = "csv"):
    redirect = require_login(request)
    if redirect:
        return redirect
    if table_key not in EXPORT_TABLES or format not in ("csv", "xlsx"):
        return HTMLResponse("Unknown table or format.", status_code=404)
    table, id_column, name = EXPORT_TABLES[table_key]

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Every column, so the file has all fields and can be re-uploaded through Bulk Upload.
        # Same project filter as the inventory pages (materials have no project column).
        allowed = get_allowed_projects(request)
        if allowed is None or table == "tbl_materials":
            cur.execute(f"SELECT * FROM {table} ORDER BY {id_column}")
        else:
            cur.execute(f"SELECT * FROM {table} WHERE project = ANY(%s) ORDER BY {id_column}", (list(allowed),))
        columns = [d[0] for d in cur.description]
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    df = pd.DataFrame(rows, columns=columns).astype(object)
    df = df.where(df.notna(), EXPORT_BLANK)
    from datetime import date  # local import keeps this change separate from other open PRs
    filename = f"hazbat_{table_key}_{date.today().isoformat()}.{format}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    if format == "csv":
        # utf-8-sig so Excel opens symbols such as ² and µ correctly
        data = df.to_csv(index=False).encode("utf-8-sig")
        return Response(content=data, media_type="text/csv", headers=headers)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=name)
        sheet = writer.sheets[name]
        sheet.freeze_panes = "A2"  # keep the header row visible when scrolling
        for cell in sheet[1]:
            cell.font = cell.font.copy(bold=True)
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                if cell.is_date:
                    cell.number_format = "yyyy-mm-dd"  # show 2026-09-24, not 2026-09-24 00:00:00
        for column_cells in sheet.columns:
            width = max(len(str(c.value)) if c.value is not None else 0 for c in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = min(max(width + 2, 10), 50)
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
