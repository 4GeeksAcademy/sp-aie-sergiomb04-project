"use client";

import React, { useMemo, useState } from "react";

import { IncidentSummary } from "@/app/features/incidents/components/IncidentSummary";
import {
  analyzeIncidentsFile,
  downloadCsvBlob,
  getLatestExportCsv,
  hasAnalysisResult,
} from "@/app/features/incidents/services/api";
import { IncidentAnalysisResult } from "@/app/features/incidents/types/incidents";

export function IncidentUploadPanel() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<IncidentAnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const canAnalyze = useMemo(
    () => selectedFile !== null && !isAnalyzing,
    [selectedFile, isAnalyzing]
  );

  const handleAnalyze = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedFile) {
      setError("Selecciona un CSV para iniciar el analisis");
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await analyzeIncidentsFile(selectedFile);
      setResult(response.data);
      setSuccess("Analisis completado correctamente");
    } catch (unknownError: unknown) {
      setResult(null);
      setError(
        unknownError instanceof Error
          ? unknownError.message
          : "No se pudo analizar el CSV"
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDownload = async () => {
    setIsDownloading(true);
    setError(null);
    setSuccess(null);

    try {
      const blob = await getLatestExportCsv();
      downloadCsvBlob(blob, "incidents-analysis-results.csv");
      setSuccess("CSV descargado correctamente");
    } catch (unknownError: unknown) {
      setError(
        unknownError instanceof Error
          ? unknownError.message
          : "No se pudo descargar el CSV"
      );
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-950">
          Analisis de incidencias
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Carga un fichero CSV para validar calidad de datos y ver metricas de volumen,
          categoria, estado e indice de satisfaccion.
        </p>

        <form onSubmit={handleAnalyze} className="mt-6 space-y-4">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Fichero CSV</span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              className="block w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-700"
            />
          </label>

          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={!canAnalyze}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isAnalyzing ? "Analizando..." : "Analizar CSV"}
            </button>

            <button
              type="button"
              onClick={handleDownload}
              disabled={!hasAnalysisResult(result) || isDownloading}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isDownloading ? "Descargando..." : "Descargar CSV"}
            </button>
          </div>

          {error && (
            <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </p>
          )}
          {success && (
            <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              {success}
            </p>
          )}
        </form>
      </section>

      {result && <IncidentSummary result={result} />}
    </div>
  );
}
