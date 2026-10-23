"""Global pytest configuration and sys.path setup."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES_API = ROOT / "services" / "api"
API_VENV_SITE_WIN = SERVICES_API / ".venv" / "Lib" / "site-packages"

if API_VENV_SITE_WIN.exists() and str(API_VENV_SITE_WIN) not in sys.path:
    sys.path.insert(0, str(API_VENV_SITE_WIN))
if str(SERVICES_API) not in sys.path:
    sys.path.insert(0, str(SERVICES_API))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
