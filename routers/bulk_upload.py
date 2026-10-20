from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse

from core.auth import require_login
from core.templates import templates
from services.bulk import (check_cell_row, check_coating_row, check_material_row, check_mlp_row,
                           process_bulk_upload, read_upload)

router = APIRouter()


@router.get("/materials/bulk-upload", response_class=HTMLResponse)
def bulk_upload_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("bulk_upload.html", {"request": request})
 
 
@router.post("/materials/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_materials(request: Request, file: UploadFile = File(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        rows = read_upload(await file.read(), file.filename)
    except Exception as e:
        return templates.TemplateResponse("bulk_upload.html", {"request": request, "upload_error": f"Couldn't read that file: {e}"})
    results = process_bulk_upload(rows, "tbl_materials", check=check_material_row)
    return templates.TemplateResponse("bulk_upload.html", {"request": request, "results": results})
 
@router.get("/coatings/bulk-upload", response_class=HTMLResponse)
def bulk_upload_coating_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("bulk_upload_coating.html", {"request": request})
 
 
@router.post("/coatings/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_coatings(request: Request, file: UploadFile = File(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        rows = read_upload(await file.read(), file.filename)
    except Exception as e:
        return templates.TemplateResponse("bulk_upload_coating.html", {"request": request, "upload_error": f"Couldn't read that file: {e}"})
    results = process_bulk_upload(rows, "tbl_coating", check=check_coating_row)
    return templates.TemplateResponse("bulk_upload_coating.html", {"request": request, "results": results})
 
@router.get("/slp/bulk-upload", response_class=HTMLResponse)
def bulk_upload_slp_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("bulk_upload_slp.html", {"request": request})
 
 
@router.post("/slp/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_slp(request: Request, file: UploadFile = File(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        rows = read_upload(await file.read(), file.filename)
    except Exception as e:
        return templates.TemplateResponse("bulk_upload_slp.html", {"request": request, "upload_error": f"Couldn't read that file: {e}"})
    results = process_bulk_upload(rows, "tbl_slp", check=check_cell_row)
    return templates.TemplateResponse("bulk_upload_slp.html", {"request": request, "results": results})
 
@router.get("/coincell/bulk-upload", response_class=HTMLResponse)
def bulk_upload_coincell_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("bulk_upload_coincell.html", {"request": request})
 
@router.post("/coincell/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_coincell(request: Request, file: UploadFile = File(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        rows = read_upload(await file.read(), file.filename)
    except Exception as e:
        return templates.TemplateResponse("bulk_upload_coincell.html", {"request": request, "upload_error": f"Couldn't read that file: {e}"})
    results = process_bulk_upload(rows, "tbl_coincell", check=check_cell_row)
    return templates.TemplateResponse("bulk_upload_coincell.html", {"request": request, "results": results})
 
@router.get("/mlp/bulk-upload", response_class=HTMLResponse)
def bulk_upload_mlp_form(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse("bulk_upload_mlp.html", {"request": request})
 
 
@router.post("/mlp/bulk-upload", response_class=HTMLResponse)
async def bulk_upload_mlp(request: Request, file: UploadFile = File(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        rows = read_upload(await file.read(), file.filename)
    except Exception as e:
        return templates.TemplateResponse("bulk_upload_mlp.html", {"request": request, "upload_error": f"Couldn't read that file: {e}"})
    results = process_bulk_upload(rows, "tbl_mlp", check=check_mlp_row)
    return templates.TemplateResponse("bulk_upload_mlp.html", {"request": request, "results": results})
