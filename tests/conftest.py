"""Global pytest configuration and sys.path setup."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES_API = ROOT / "services" / "api"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVICES_API) not in sys.path:
    sys.path.insert(0, str(SERVICES_API))
