from __future__ import annotations

from trackflow_api.app import app
from trackflow_api.routes.auth import router as auth_router
from trackflow_api.routes.profiles import router as profiles_router
from trackflow_api.routes.suppliers import router as suppliers_router
from trackflow_api.routes.users import router as users_router

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(suppliers_router)
