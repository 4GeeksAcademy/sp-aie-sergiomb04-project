from __future__ import annotations

from incidents_api.app import app
from incidents_api.routes.suppliers import router as suppliers_router

app.include_router(suppliers_router)
