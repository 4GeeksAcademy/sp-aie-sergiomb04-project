from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, Optional


@dataclass
class StoredAnalysis:
    generated_at: str
    source_file: str
    export_file_name: str
    export_csv: str
    result: Dict[str, Any]


_latest_analysis: Optional[StoredAnalysis] = None
_store_lock = Lock()


def set_latest_analysis(analysis: StoredAnalysis) -> None:
    global _latest_analysis
    with _store_lock:
        _latest_analysis = analysis


def get_latest_analysis() -> Optional[StoredAnalysis]:
    with _store_lock:
        return _latest_analysis
