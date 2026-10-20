from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from core.config import SESSION_SECRET
from routers import (auth, bulk_upload, cards, charts, cycling, graph, hazbot, home, inventory, lineage,
                     records, records_edit)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.mount("/static", StaticFiles(directory="static"), name="static")

for module in (home, auth, records, records_edit, bulk_upload, inventory, charts, cycling, cards, lineage, graph, hazbot):
    app.include_router(module.router)
