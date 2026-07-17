from __future__ import annotations

from trackflow_api.app import app
from trackflow_api.routes.suppliers import router as suppliers_router

app.include_router(suppliers_router)
