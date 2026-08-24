from __future__ import annotations

from trackflow_api.app import app
from trackflow_api.routes.auth import router as auth_router
from trackflow_api.routes.incidents import router as incidents_router
from trackflow_api.routes.inventory import router as inventory_router
from trackflow_api.routes.profiles import router as profiles_router
from trackflow_api.routes.reporting import router as reporting_router
from trackflow_api.routes.suppliers import router as suppliers_router
from trackflow_api.routes.telemetry import router as telemetry_router
from trackflow_api.routes.users import router as users_router

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(suppliers_router)
app.include_router(incidents_router)
app.include_router(inventory_router)
app.include_router(telemetry_router)
app.include_router(reporting_router)

