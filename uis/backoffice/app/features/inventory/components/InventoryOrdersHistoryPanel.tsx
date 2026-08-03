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
    <section className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-950">Historial de StockEntry y StockExit</h1>
          <p className="mt-2 text-sm text-slate-600">Vista de solo lectura de movimientos por SKU.</p>
        </div>

        <button
          type="button"
          onClick={() => void loadOrders()}
          className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Refrescar
        </button>
      </header>

      {error && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
      )}

      {isLoading ? (
        <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
          Cargando órdenes...
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-slate-700">
              <tr>
                <th className="px-4 py-3 font-semibold">Tipo</th>
                <th className="px-4 py-3 font-semibold">Nombre del producto</th>
                <th className="px-4 py-3 font-semibold">Cantidad</th>
                <th className="px-4 py-3 font-semibold">Fecha de creación</th>
                <th className="px-4 py-3 font-semibold">user_uuid</th>
                <th className="px-4 py-3 font-semibold">warehouse</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {orders.map((order) => {
                const isInbound = order.order_type === "inbound";
                return (
                  <tr key={`${order.order_type}-${order.id}-${order.created_at}`}>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full border px-2 py-1 text-xs font-semibold ${
                          isInbound
                            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                            : "border-rose-200 bg-rose-50 text-rose-700"
                        }`}
                      >
                        {isInbound ? "StockEntry" : "StockExit"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-900">{order.product_name}</td>
                    <td className="px-4 py-3 text-slate-700">{order.quantity}</td>
                    <td className="px-4 py-3 text-slate-700">{formatDate(order.created_at)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-700">{order.user_uuid}</td>
                    <td className="px-4 py-3 text-slate-700">{order.warehouse}</td>
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
