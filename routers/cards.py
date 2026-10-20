from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
import base64

from core.config import BASE_URL
from core.db import get_connection
from core.templates import templates
from services.cards import card_path, fetch_card_record, make_qr_png, panel_fields
from services.records import CELL_TYPES, detect_record_type

router = APIRouter()


@router.get("/qr/{record_id}.png")
def qr_code(record_id: str):
    """QR code image for a record, used by the graph panel, the cards and for labels."""
    record_type = detect_record_type(record_id)
    if not record_type:
        return Response(status_code=404)
    return Response(content=make_qr_png(BASE_URL + card_path(record_id, record_type)), media_type="image/png")


@router.get("/card/{record_id}", response_class=HTMLResponse)
def view_card(request: Request, record_id: str):
    record_type = detect_record_type(record_id)
    if not record_type:
        return HTMLResponse("Unrecognised ID format.", status_code=404)

    # QR code: cells open their lineage & passport page, other records this card
    qr_base64 = base64.b64encode(make_qr_png(BASE_URL + card_path(record_id, record_type))).decode()

    conn = get_connection()
    cur = conn.cursor()
    record, chain = fetch_card_record(cur, record_type, record_id)
    cur.close()
    conn.close()

    if not record:
        return HTMLResponse("Record not found.", status_code=404)

    return templates.TemplateResponse(
        "card.html",
        {"request": request, "record_id": record_id, "record_type": record_type,
         "record": record, "chain": chain, "qr_base64": qr_base64}
    )


@router.get("/api/card/{record_id}")
def card_data(record_id: str):
    record_type = detect_record_type(record_id)
    if not record_type:
        return JSONResponse({"error": "Unrecognised ID format"}, status_code=404)

    conn = get_connection()
    cur = conn.cursor()
    record, chain = fetch_card_record(cur, record_type, record_id)
    panel = None
    if record and record_type in CELL_TYPES:
        panel = {
            "fields": panel_fields(cur, record_type, record),
            "qr_url": f"/qr/{record_id}.png",
            "card_url": f"/card/{record_id}",
            "lineage_url": f"/card/{record_id}/lineage",
        }
    cur.close()
    conn.close()

    if not record:
        return JSONResponse({"error": "Record not found"}, status_code=404)

    record = {k: (str(v) if v is not None else "N/A") for k, v in record.items()}
    return JSONResponse({"record_id": record_id, "record_type": record_type,
                         "record": record, "chain": chain, "panel": panel})
