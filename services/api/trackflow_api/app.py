from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from .store import StoredAnalysis, get_latest_analysis, set_latest_analysis

BASE_DIR = Path(__file__).resolve().parents[3]
ANALYZER_DIR = BASE_DIR / "scripts" / "incidents-analysis"

if str(ANALYZER_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYZER_DIR))

from domain.analyzer import analyze_csv  # type: ignore  # noqa: E402
from domain.exporter import write_export_csv  # type: ignore  # noqa: E402

app = FastAPI(
    title="TrackFlow API",
    version="1.0.0",
    description="Backend Python unificado para incidencias y suppliers de TrackFlow.",
)


def _cleanup_file(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


@app.post("/api/incidents/analyze")
async def analyze_incidents(file: UploadFile = File(...)) -> JSONResponse:
    filename = file.filename or "incidents.csv"

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=415,
            detail="Formato incorrecto: el archivo debe tener extension .csv",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="El fichero esta vacio")

    text_preview = content[:2048].decode("utf-8", errors="ignore")
    if "," not in text_preview:
        raise HTTPException(
            status_code=415,
            detail="Formato incorrecto: no parece un CSV delimitado por comas",
        )

    input_tmp = NamedTemporaryFile(mode="wb", suffix=".csv", delete=False)
    export_tmp = NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")

    try:
        input_tmp.write(content)
        input_tmp.flush()
        export_tmp.flush()

        result = analyze_csv(Path(input_tmp.name))
        write_export_csv(result, Path(export_tmp.name))

        export_csv = Path(export_tmp.name).read_text(encoding="utf-8")
        generated_at = datetime.now(timezone.utc).isoformat()

        payload = result.to_dict()
        set_latest_analysis(
            StoredAnalysis(
                generated_at=generated_at,
                source_file=filename,
                export_file_name=f"incidents-results-{uuid4().hex[:8]}.csv",
                export_csv=export_csv,
                result=payload,
            )
        )

        return JSONResponse(
            {
                "data": payload,
                "meta": {
                    "source_file": filename,
                    "generated_at": generated_at,
                },
            },
            status_code=200,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except HTTPException:
        raise
    except Exception as error:  # pragma: no cover
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo analizar el archivo CSV: {error}",
        ) from error
    finally:
        input_tmp.close()
        export_tmp.close()
        _cleanup_file(input_tmp.name)
        _cleanup_file(export_tmp.name)


@app.get("/api/incidents/results/export")
def export_latest_analysis() -> Response:
    latest = get_latest_analysis()
    if latest is None:
        raise HTTPException(
            status_code=404,
            detail="No hay resultados para exportar. Ejecuta primero POST /api/incidents/analyze",
        )

    headers = {
        "Content-Disposition": f'attachment; filename="{latest.export_file_name}"',
        "Cache-Control": "no-store",
    }
    return Response(content=latest.export_csv, media_type="text/csv; charset=utf-8", headers=headers)
