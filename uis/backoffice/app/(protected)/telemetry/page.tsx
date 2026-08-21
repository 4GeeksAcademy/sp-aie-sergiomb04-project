"use client";

import { useEffect, useState, useTransition } from "react";

type EventsPerDayItem = {
  date: string;
  count: number;
};

type ErrorRateItem = {
  event_type: string;
  count: number;
  total_events: number;
  error_rate: number;
};

type AuthFailureRateItem = {
  date: string;
  failed: number;
  succeeded: number;
  total_attempts: number;
  failure_rate: number;
};

type LatencyByRouteItem = {
  api_route: string;
  method: string;
  sample_count: number;
  avg_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  p95_latency_ms: number;
};

type TelemetryReportData = {
  period: {
    from: string;
    to: string;
  };
  metrics: {
    events_per_day: EventsPerDayItem[];
    error_rate_by_type: ErrorRateItem[];
    auth_failure_rate: AuthFailureRateItem[];
    latency_by_route?: LatencyByRouteItem[];
  };
};

export default function TelemetryDashboardPage() {
  const [data, setData] = useState<TelemetryReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRange, setSelectedRange] = useState<"7d" | "24h" | "30d" | "custom">("7d");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [isPending, startTransition] = useTransition();

  const fetchReport = async (start?: string, end?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (start) params.set("start_date", start);
      if (end) params.set("end_date", end);

      const query = params.toString() ? `?${params.toString()}` : "";
      const res = await fetch(`/api/telemetry/report${query}`, {
        cache: "no-store",
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Error HTTP ${res.status}`);
      }

      const json = (await res.json()) as TelemetryReportData;
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar reporte de telemetria");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    async function loadInitial() {
      try {
        const res = await fetch("/api/telemetry/report", { cache: "no-store" });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Error HTTP ${res.status}`);
        }
        const json = (await res.json()) as TelemetryReportData;
        if (!ignore) {
          setData(json);
          setLoading(false);
        }
      } catch (err) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Error al cargar reporte de telemetria");
          setLoading(false);
        }
      }
    }
    loadInitial();
    return () => {
      ignore = true;
    };
  }, []);

  const handleRangeChange = (range: "7d" | "24h" | "30d") => {
    setSelectedRange(range);
    const now = new Date();
    let startDate: Date;

    if (range === "24h") {
      startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    } else if (range === "30d") {
      startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    } else {
      // 7 days default
      startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    }

    startTransition(() => {
      fetchReport(startDate.toISOString(), now.toISOString());
    });
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customStart || !customEnd) return;
    setSelectedRange("custom");
    startTransition(() => {
      fetchReport(new Date(customStart).toISOString(), new Date(customEnd).toISOString());
    });
  };

  // Calculations for KPI summaries
  const totalEventsInPeriod =
    data?.metrics.events_per_day.reduce((acc, curr) => acc + curr.count, 0) ?? 0;

  const totalAuthAttempts =
    data?.metrics.auth_failure_rate.reduce((acc, curr) => acc + curr.total_attempts, 0) ?? 0;

  const totalAuthFailures =
    data?.metrics.auth_failure_rate.reduce((acc, curr) => acc + curr.failed, 0) ?? 0;

  const globalAuthFailureRate =
    totalAuthAttempts > 0 ? ((totalAuthFailures / totalAuthAttempts) * 100).toFixed(1) : "0.0";

  const totalErrors =
    data?.metrics.error_rate_by_type.reduce((acc, curr) => acc + curr.count, 0) ?? 0;

  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      {/* Header section */}
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <span className="w-fit rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700">
                Observabilidad & Telemetría
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                Caché TTL: 60s
              </span>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
              Dashboard Técnico de Telemetría
            </h1>
            <p className="max-w-2xl text-slate-600">
              Análisis técnico y operacional de eventos persistidos en TrackFlow. Monitoreo de
              volumen, fallos de autenticación, errores de API y rendimiento.
            </p>
          </div>

          {/* Range selection buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => handleRangeChange("24h")}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                selectedRange === "24h"
                  ? "bg-slate-900 text-white"
                  : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Últimas 24h
            </button>
            <button
              onClick={() => handleRangeChange("7d")}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                selectedRange === "7d"
                  ? "bg-slate-900 text-white"
                  : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Últimos 7 días
            </button>
            <button
              onClick={() => handleRangeChange("30d")}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                selectedRange === "30d"
                  ? "bg-slate-900 text-white"
                  : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              Últimos 30 días
            </button>
            <button
              onClick={() => fetchReport(data?.period.from, data?.period.to)}
              disabled={loading || isPending}
              className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
              title="Refrescar reporte"
            >
              {loading || isPending ? "Cargando..." : "↻ Refrescar"}
            </button>
          </div>
        </div>

        {/* Period info banner */}
        {data && (
          <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-4 text-xs text-slate-500">
            <div>
              <span className="font-semibold text-slate-700">Período analizado (UTC):</span>{" "}
              <span className="font-mono text-slate-900">{data.period.from}</span>{" "}
              <span className="text-slate-400">→</span>{" "}
              <span className="font-mono text-slate-900">{data.period.to}</span>
            </div>
            <div className="text-slate-500">
              Datos generados mediante pipeline técnico Pandas / FastAPI
            </div>
          </div>
        )}
      </section>

      {/* Error state */}
      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold">Error al cargar telemetría</p>
              <p className="mt-1 text-sm">{error}</p>
            </div>
            <button
              onClick={() => fetchReport()}
              className="rounded-lg bg-red-700 px-4 py-2 text-sm font-medium text-white hover:bg-red-800"
            >
              Reintentar
            </button>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !data && (
        <div className="grid gap-6 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-36 animate-pulse rounded-2xl border border-slate-200 bg-slate-100 p-6"
            />
          ))}
        </div>
      )}

      {/* Main KPI Summary Cards */}
      {data && (
        <section className="grid gap-6 md:grid-cols-3">
          <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-sm font-medium text-slate-500">Volumen Total de Eventos</h2>
            <p className="mt-3 text-3xl font-bold text-slate-950">{totalEventsInPeriod}</p>
            <p className="mt-2 text-xs text-slate-500">
              Registrados en la ventana temporal seleccionada
            </p>
          </article>

          <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-sm font-medium text-slate-500">Tasa de Fallo en Autenticación</h2>
            <div className="mt-3 flex items-baseline gap-2">
              <p className="text-3xl font-bold text-slate-950">{globalAuthFailureRate}%</p>
              <span className="text-xs text-slate-500">
                ({totalAuthFailures} de {totalAuthAttempts} intentos)
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Métrica agregada de intentos fallidos vs exitosos
            </p>
          </article>

          <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-sm font-medium text-slate-500">Total Errores y Rechazos</h2>
            <p className="mt-3 text-3xl font-bold text-slate-950">{totalErrors}</p>
            <p className="mt-2 text-xs text-slate-500">
              Eventos de fallo técnico o rechazo de validación operativa
            </p>
          </article>
        </section>
      )}

      {/* Metric 1 & Metric 2 Tables */}
      {data && (
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Events per day */}
          <section className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-950">Volumen Diario de Eventos</h3>
                <p className="text-xs text-slate-500">Métrica: events_per_day</p>
              </div>
              <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                {data.metrics.events_per_day.length} días con actividad
              </span>
            </div>

            <div className="mt-4 flex-1 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-500">
                    <th className="pb-3 font-semibold">Fecha</th>
                    <th className="pb-3 text-right font-semibold">Volumen</th>
                    <th className="pb-3 text-right font-semibold">Proporción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.metrics.events_per_day.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="py-6 text-center text-sm text-slate-500">
                        No hay eventos en el período seleccionado
                      </td>
                    </tr>
                  ) : (
                    data.metrics.events_per_day.map((item) => {
                      const pct =
                        totalEventsInPeriod > 0
                          ? ((item.count / totalEventsInPeriod) * 100).toFixed(1)
                          : "0";
                      return (
                        <tr key={item.date} className="hover:bg-slate-50/50">
                          <td className="py-3 font-mono text-xs font-medium text-slate-900">
                            {item.date}
                          </td>
                          <td className="py-3 text-right font-semibold text-slate-950">
                            {item.count}
                          </td>
                          <td className="py-3 text-right text-xs text-slate-500">{pct}%</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* Auth Failure Rate */}
          <section className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-950">
                  Tasa de Fallos de Autenticación
                </h3>
                <p className="text-xs text-slate-500">Métrica: auth_failure_rate</p>
              </div>
              <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">
                Logins
              </span>
            </div>

            <div className="mt-4 flex-1 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-500">
                    <th className="pb-3 font-semibold">Fecha</th>
                    <th className="pb-3 text-center font-semibold">Intentos</th>
                    <th className="pb-3 text-center font-semibold">Éxitos</th>
                    <th className="pb-3 text-center font-semibold">Fallos</th>
                    <th className="pb-3 text-right font-semibold">Tasa Fallo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.metrics.auth_failure_rate.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-sm text-slate-500">
                        No hay eventos de autenticación en este rango
                      </td>
                    </tr>
                  ) : (
                    data.metrics.auth_failure_rate.map((item) => {
                      const ratePct = (item.failure_rate * 100).toFixed(1);
                      const isHighFailure = item.failure_rate > 0.3;
                      return (
                        <tr key={item.date} className="hover:bg-slate-50/50">
                          <td className="py-3 font-mono text-xs font-medium text-slate-900">
                            {item.date}
                          </td>
                          <td className="py-3 text-center text-slate-700">
                            {item.total_attempts}
                          </td>
                          <td className="py-3 text-center text-emerald-600 font-medium">
                            {item.succeeded}
                          </td>
                          <td className="py-3 text-center text-red-600 font-medium">
                            {item.failed}
                          </td>
                          <td className="py-3 text-right">
                            <span
                              className={`rounded-md px-2 py-0.5 text-xs font-semibold ${
                                isHighFailure
                                  ? "bg-red-50 text-red-700"
                                  : item.failed > 0
                                  ? "bg-amber-50 text-amber-700"
                                  : "bg-emerald-50 text-emerald-700"
                              }`}
                            >
                              {ratePct}%
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* Metric 3 & Metric 4 Tables */}
      {data && (
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Error Rate by Type */}
          <section className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-950">
                  Tasa de Errores y Rechazos por Tipo
                </h3>
                <p className="text-xs text-slate-500">Métrica: error_rate_by_type</p>
              </div>
              <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700">
                Incidencias Técnicas
              </span>
            </div>

            <div className="mt-4 flex-1 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-500">
                    <th className="pb-3 font-semibold">Tipo de Evento</th>
                    <th className="pb-3 text-center font-semibold">Conteo</th>
                    <th className="pb-3 text-right font-semibold">Tasa s/ Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.metrics.error_rate_by_type.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="py-6 text-center text-sm text-slate-500">
                        No se registraron errores o rechazos en el período
                      </td>
                    </tr>
                  ) : (
                    data.metrics.error_rate_by_type.map((item) => {
                      const ratePct = (item.error_rate * 100).toFixed(2);
                      return (
                        <tr key={item.event_type} className="hover:bg-slate-50/50">
                          <td className="py-3 font-mono text-xs font-medium text-slate-900">
                            {item.event_type}
                          </td>
                          <td className="py-3 text-center font-semibold text-rose-600">
                            {item.count}
                          </td>
                          <td className="py-3 text-right font-mono text-xs text-slate-600">
                            {ratePct}%
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* Latency by Route */}
          <section className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-950">
                  Latencia y Rendimiento API
                </h3>
                <p className="text-xs text-slate-500">Métrica: latency_by_route</p>
              </div>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                Muestreo API
              </span>
            </div>

            <div className="mt-4 flex-1 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-500">
                    <th className="pb-3 font-semibold">Ruta / Método</th>
                    <th className="pb-3 text-center font-semibold">Muestras</th>
                    <th className="pb-3 text-right font-semibold">Media (ms)</th>
                    <th className="pb-3 text-right font-semibold">P95 (ms)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {!data.metrics.latency_by_route || data.metrics.latency_by_route.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-6 text-center text-sm text-slate-500">
                        No hay muestras de latencia en el período
                      </td>
                    </tr>
                  ) : (
                    data.metrics.latency_by_route.map((item) => (
                      <tr
                        key={`${item.api_route}-${item.method}`}
                        className="hover:bg-slate-50/50"
                      >
                        <td className="py-3">
                          <span className="mr-2 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] font-bold text-slate-700">
                            {item.method}
                          </span>
                          <span className="font-mono text-xs text-slate-900">
                            {item.api_route}
                          </span>
                        </td>
                        <td className="py-3 text-center text-xs text-slate-600">
                          {item.sample_count}
                        </td>
                        <td className="py-3 text-right font-semibold text-slate-900">
                          {item.avg_latency_ms} ms
                        </td>
                        <td className="py-3 text-right font-semibold text-indigo-600">
                          {item.p95_latency_ms} ms
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* Custom Date Filter Section */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Filtrar por Rango Personalizado</h3>
        <form onSubmit={handleCustomSubmit} className="mt-4 flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600">Fecha / Hora Inicio (Local)</label>
            <input
              type="datetime-local"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600">Fecha / Hora Fin (Local)</label>
            <input
              type="datetime-local"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading || isPending}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            Aplicar Filtro
          </button>
        </form>
      </section>
    </main>
  );
}
