"use client";

import { useCallback, useEffect, useState } from "react";

import { listInventoryOrders } from "@/app/lib/inventory";
import type { InventoryOrderHistoryItem } from "@/app/features/inventory/types/inventory";

function formatDate(isoDate: string): string {
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(isoDate));
}

export function InventoryOrdersHistoryPanel() {
  const [orders, setOrders] = useState<InventoryOrderHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOrders = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await listInventoryOrders();
      setOrders(response.orders);
    } catch (unknownError) {
      setError(unknownError instanceof Error ? unknownError.message : "No se pudo cargar el historial.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadOrders();
  }, [loadOrders]);

  return (
    <section className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-950 dark:text-white">Historial de StockEntry y StockExit</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Vista de solo lectura de movimientos por SKU.</p>
        </div>

        <button
          type="button"
          onClick={() => void loadOrders()}
          className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Refrescar
        </button>
      </header>

      {error && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300">{error}</p>
      )}

      {isLoading ? (
        <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-400">
          Cargando órdenes...
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-800">
            <thead className="bg-slate-50 text-left text-slate-700 dark:bg-slate-800/80 dark:text-slate-300">
              <tr>
                <th className="px-4 py-3 font-semibold">Tipo</th>
                <th className="px-4 py-3 font-semibold">Nombre del producto</th>
                <th className="px-4 py-3 font-semibold">Cantidad</th>
                <th className="px-4 py-3 font-semibold">Fecha de creación</th>
                <th className="px-4 py-3 font-semibold">user_uuid</th>
                <th className="px-4 py-3 font-semibold">warehouse</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white dark:divide-slate-800 dark:bg-slate-900">
              {orders.map((order) => {
                const isInbound = order.order_type === "inbound";
                return (
                  <tr key={`${order.order_type}-${order.id}-${order.created_at}`}>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full border px-2 py-1 text-xs font-semibold ${
                          isInbound
                            ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-300"
                            : "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300"
                        }`}
                      >
                        {isInbound ? "StockEntry" : "StockExit"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-900 dark:text-slate-100">{order.product_name}</td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{order.quantity}</td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{formatDate(order.created_at)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-300">{order.user_uuid}</td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{order.warehouse}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
