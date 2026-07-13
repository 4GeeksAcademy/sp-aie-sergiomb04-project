"use client";

import Link from "next/link";
import React, { useMemo, useState } from "react";

import {
  analyzeIncidentsFile,
  downloadCsvBlob,
  getLatestExportCsv,
  hasAnalysisResult,
} from "@/app/features/incidents/services/incidents-api";
import { IncidentSummary } from "@/app/features/incidents/components/IncidentSummary";
import { IncidentAnalysisResult } from "@/app/features/incidents/types/incidents";

export function IncidentUploadForm() {
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

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedFile) {
      setError("Selecciona un archivo CSV antes de analizar");
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
      setError(
        unknownError instanceof Error
          ? unknownError.message
          : "No se pudo completar el analisis"
      );
      setResult(null);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleExport = async () => {
    setIsDownloading(true);
    setError(null);
    setSuccess(null);

    try {
      const csvBlob = await getLatestExportCsv();
      downloadCsvBlob(csvBlob, "incidents-analysis-results.csv");
      setSuccess("CSV exportado correctamente");
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
    <div className="mx-auto w-full max-w-5xl space-y-6 py-8">
      <header className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-3xl font-bold text-zinc-900">Incidents Analysis</h1>
          <Link
            href="/"
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-100"
          >
            Volver a candidatos
          </Link>
        </div>
        <p className="text-zinc-600">
          Carga un CSV de incidencias para obtener metricas de calidad, volumen y satisfaccion.
        </p>
      </header>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"
      >
        <label className="block space-y-2">
          <span className="text-sm font-medium text-zinc-700">Archivo CSV</span>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setSelectedFile(file);
            }}
            className="block w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-2 text-sm"
          />
        </label>

        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            disabled={!canAnalyze}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isAnalyzing ? "Analizando..." : "Analizar CSV"}
          </button>

          <button
            type="button"
            onClick={handleExport}
            disabled={!hasAnalysisResult(result) || isDownloading}
            className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-semibold text-zinc-700 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isDownloading ? "Descargando..." : "Descargar resultados CSV"}
          </button>
        </div>

        {error && (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </p>
        )}
        {success && (
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {success}
          </p>
        )}
      </form>

      {result && <IncidentSummary result={result} />}
    </div>
  );
}
