"use client";

import { useEffect, useState, useTransition } from "react";

type PerformanceEntry = {
  warehouse: string;
  client_id: string;
  inbound_units_count: number;
  outbound_orders_count: number;
  stockout_events_count: number;
  discrepancy_events_count: number;
  discrepancy_rate: number;
};

type PerformanceReportData = {
  week_start: string;
  total_records: number;
  entries: PerformanceEntry[];
};

type PipelineRunStatus = {
  run_id: string;
  pipeline_name: string;
  execution_status: string;
  target_week_start: string;
  records_extracted: number;
  records_loaded: number;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  triggered_by: string;
  error_details: Record<string, unknown> | null;
};

export default function BusinessReportingDashboardPage() {
  const [data, setData] = useState<PerformanceReportData | null>(null);
  const [pipelineRun, setPipelineRun] = useState<PipelineRunStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>("all");
  const [clientSearch, setClientSearch] = useState<string>("");
  const [targetWeek, setTargetWeek] = useState<string>("");
  const [isPending, startTransition] = useTransition();

  const fetchReport = async (week?: string, warehouse?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (week) params.set("week_start", week);
      if (warehouse && warehouse !== "all") params.set("warehouse", warehouse);

      const query = params.toString() ? `?${params.toString()}` : "";
      const res = await fetch(`/api/reporting/weekly-warehouse-client-performance${query}`, {
        cache: "no-store",
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Error HTTP ${res.status}`);
      }

      const json = (await res.json()) as PerformanceReportData;
      setData(json);
      if (json.week_start && !targetWeek) {
        setTargetWeek(json.week_start);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar reporte de desempeño");
    } finally {
      setLoading(false);
    }
  };

  const fetchLatestPipelineRun = async () => {
    try {
      const res = await fetch("/api/reporting/pipeline-runs", { cache: "no-store" });
      if (res.ok) {
        const json = (await res.json()) as PipelineRunStatus;
        setPipelineRun(json);
      }
    } catch {
      // Non-critical, ignore silent fail for status banner
    }
  };

  const handleTriggerPipeline = async () => {
    setPipelineLoading(true);
    try {
      const res = await fetch("/api/reporting/pipeline-runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_week_start: targetWeek || undefined,
          force_recompute: true,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Error al disparar pipeline");
      }

      await fetchLatestPipelineRun();
      await fetchReport(targetWeek, selectedWarehouse);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Error al ejecutar pipeline");
    } finally {
      setPipelineLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    async function loadInitial() {
      try {
        const [reportRes, runRes] = await Promise.all([
          fetch("/api/reporting/weekly-warehouse-client-performance", { cache: "no-store" }),
          fetch("/api/reporting/pipeline-runs", { cache: "no-store" }).catch(() => null),
        ]);

        if (!reportRes.ok) {
          const errData = await reportRes.json().catch(() => ({}));
          throw new Error(errData.detail || `Error HTTP ${reportRes.status}`);
        }

        const reportJson = (await reportRes.json()) as PerformanceReportData;
        if (!ignore) {
          setData(reportJson);
          if (reportJson.week_start) {
            setTargetWeek(reportJson.week_start);
          }
          setLoading(false);
        }

        if (runRes && runRes.ok && !ignore) {
          const runJson = (await runRes.json()) as PipelineRunStatus;
          setPipelineRun(runJson);
        }
      } catch (err) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Error al cargar datos");
          setLoading(false);
        }
      }
    }
    loadInitial();
    return () => {
      ignore = true;
    };
  }, []);

  const handleWarehouseFilterChange = (wh: string) => {
    setSelectedWarehouse(wh);
    startTransition(() => {
      fetchReport(targetWeek, wh);
    });
  };

  const handleWeekSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetWeek) return;
    startTransition(() => {
      fetchReport(targetWeek, selectedWarehouse);
    });
  };

  // Filtered list based on client search
  const filteredEntries =
    data?.entries.filter((item) =>
      clientSearch ? item.client_id.toLowerCase().includes(clientSearch.toLowerCase()) : true
    ) ?? [];

  // Aggregated KPIs
  const totalInboundUnits =
    filteredEntries.reduce((acc, curr) => acc + curr.inbound_units_count, 0);
  const totalOutboundOrders =
    filteredEntries.reduce((acc, curr) => acc + curr.outbound_orders_count, 0);
  const totalStockouts =
    filteredEntries.reduce((acc, curr) => acc + curr.stockout_events_count, 0);
  const totalDiscrepancies =
    filteredEntries.reduce((acc, curr) => acc + curr.discrepancy_events_count, 0);
  const aggregateDiscrepancyRate =
    totalOutboundOrders > 0
      ? ((totalDiscrepancies / totalOutboundOrders) * 100).toFixed(2)
      : "0.00";

  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      {/* Header & Pipeline Control Section */}
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-3">
              <span className="w-fit rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700">
                Operaciones & Negocio
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                Prefect 3 Subflows · Idempotente
              </span>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
              Desempeño Semanal por Almacén y Cliente
            </h1>
            <p className="max-w-2xl text-slate-600">
              Consolidado operacional y ejecutivo para Thomas Harry (CEO) y Ana Whitfield (Head of
              Operations). Métricas de throughput, quiebres de stock y auditoría de inventario.
            </p>
          </div>

          {/* Action Trigger Buttons */}
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => fetchReport(targetWeek, selectedWarehouse)}
              disabled={loading || isPending}
              className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
            >
              {loading || isPending ? "Cargando..." : "↻ Refrescar"}
            </button>
            <button
              onClick={handleTriggerPipeline}
              disabled={pipelineLoading || loading}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
            >
              {pipelineLoading ? "Ejecutando Subflows..." : "▶ Recalcular Pipeline"}
            </button>
          </div>
        </div>

        {/* Pipeline Run Status Banner */}
        {pipelineRun && (
          <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-4 text-xs text-slate-500">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-700">Última ejecución:</span>
              <span
                className={`rounded px-2 py-0.5 font-semibold uppercase ${
                  pipelineRun.execution_status === "COMPLETED"
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-amber-50 text-amber-700"
                }`}
              >
                {pipelineRun.execution_status}
              </span>
              <span>· Semana: <strong className="font-mono text-slate-900">{pipelineRun.target_week_start}</strong></span>
              <span>· Duración: <strong>{pipelineRun.duration_seconds ?? 0}s</strong></span>
              <span>· Extraídos: <strong>{pipelineRun.records_extracted}</strong></span>
              <span>· Cargados: <strong>{pipelineRun.records_loaded}</strong></span>
            </div>
            <div className="text-slate-400">
              Disparador: {pipelineRun.triggered_by} ({new Date(pipelineRun.started_at).toLocaleTimeString()})
            </div>
          </div>
        )}
      </section>

      {/* Error state */}
      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold">Error al cargar reporte de negocio</p>
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

      {/* Filters Bar */}
      <section className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {/* Warehouse Tabs */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 mr-2">
            Sede / Almacén:
          </span>
          <button
            onClick={() => handleWarehouseFilterChange("all")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              selectedWarehouse === "all"
                ? "bg-slate-900 text-white"
                : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            Todos
          </button>
          <button
            onClick={() => handleWarehouseFilterChange("los_angeles")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              selectedWarehouse === "los_angeles"
                ? "bg-slate-900 text-white"
                : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            🇺🇸 Los Ángeles
          </button>
          <button
            onClick={() => handleWarehouseFilterChange("zaragoza")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              selectedWarehouse === "zaragoza"
                ? "bg-slate-900 text-white"
                : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            🇪🇸 Zaragoza
          </button>
        </div>

        {/* Client Search & Week Selection */}
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <input
              type="text"
              placeholder="Buscar marca cliente..."
              value={clientSearch}
              onChange={(e) => setClientSearch(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <form onSubmit={handleWeekSubmit} className="flex items-center gap-2">
            <input
              type="date"
              value={targetWeek}
              onChange={(e) => setTargetWeek(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading || isPending}
              className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-900 disabled:opacity-50"
            >
              Filtrar Semana
            </button>
          </form>
        </div>
      </section>

      {/* Summary KPI Cards */}
      <section className="grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Unidades Entrantes
          </h2>
          <p className="mt-2 text-2xl font-bold text-slate-950">{totalInboundUnits.toLocaleString()}</p>
          <p className="mt-1 text-xs text-slate-500">Métrica: inbound_units_count</p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Órdenes Despachadas
          </h2>
          <p className="mt-2 text-2xl font-bold text-slate-950">{totalOutboundOrders.toLocaleString()}</p>
          <p className="mt-1 text-xs text-slate-500">Métrica: outbound_orders_count</p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Alertas Stock Bajo
          </h2>
          <p className="mt-2 text-2xl font-bold text-amber-600">{totalStockouts}</p>
          <p className="mt-1 text-xs text-slate-500">Métrica: stockout_events_count</p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Discrepancias Físicas
          </h2>
          <p className="mt-2 text-2xl font-bold text-rose-600">{totalDiscrepancies}</p>
          <p className="mt-1 text-xs text-slate-500">Métrica: discrepancy_events_count</p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Tasa Discrepancia
          </h2>
          <div className="mt-2 flex items-baseline gap-2">
            <p className="text-2xl font-bold text-slate-950">{aggregateDiscrepancyRate}%</p>
          </div>
          <p className="mt-1 text-xs text-slate-500">Métrica: discrepancy_rate</p>
        </article>
      </section>

      {/* Detailed KPI Table */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-950">
              Desglose Operacional por Almacén y Cliente
            </h3>
            <p className="text-xs text-slate-500">
              Período: Semana del <strong className="font-mono text-slate-900">{data?.week_start || targetWeek}</strong> (Lunes a Domingo)
            </p>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
            {filteredEntries.length} marcas clientes registradas
          </span>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs uppercase tracking-wider text-slate-500">
                <th className="pb-3 font-semibold">Almacén</th>
                <th className="pb-3 font-semibold">Marca Cliente</th>
                <th className="pb-3 text-right font-semibold">Entradas (Uds)</th>
                <th className="pb-3 text-right font-semibold">Salidas (Órdenes)</th>
                <th className="pb-3 text-center font-semibold">Alertas Stock</th>
                <th className="pb-3 text-center font-semibold">Discrepancias</th>
                <th className="pb-3 text-right font-semibold">Tasa Discrepancia</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredEntries.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-sm text-slate-500">
                    No se encontraron registros para los filtros seleccionados.
                  </td>
                </tr>
              ) : (
                filteredEntries.map((item) => {
                  const ratePct = (item.discrepancy_rate * 100).toFixed(2);
                  const isHighRate = item.discrepancy_rate > 0.05;
                  const warehouseLabel =
                    item.warehouse === "los_angeles" ? "🇺🇸 Los Ángeles" : "🇪🇸 Zaragoza";

                  return (
                    <tr key={`${item.warehouse}-${item.client_id}`} className="hover:bg-slate-50/50">
                      <td className="py-3.5 font-medium text-slate-800">{warehouseLabel}</td>
                      <td className="py-3.5 font-mono text-xs font-semibold text-indigo-700">
                        {item.client_id}
                      </td>
                      <td className="py-3.5 text-right font-medium text-slate-900">
                        {item.inbound_units_count.toLocaleString()}
                      </td>
                      <td className="py-3.5 text-right font-medium text-slate-900">
                        {item.outbound_orders_count.toLocaleString()}
                      </td>
                      <td className="py-3.5 text-center">
                        {item.stockout_events_count > 0 ? (
                          <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700">
                            {item.stockout_events_count}
                          </span>
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>
                      <td className="py-3.5 text-center">
                        {item.discrepancy_events_count > 0 ? (
                          <span className="rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-semibold text-rose-700">
                            {item.discrepancy_events_count}
                          </span>
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>
                      <td className="py-3.5 text-right">
                        <span
                          className={`rounded-md px-2.5 py-1 text-xs font-bold font-mono ${
                            isHighRate
                              ? "bg-red-100 text-red-800"
                              : item.discrepancy_events_count > 0
                              ? "bg-amber-100 text-amber-800"
                              : "bg-emerald-100 text-emerald-800"
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
    </main>
  );
}
