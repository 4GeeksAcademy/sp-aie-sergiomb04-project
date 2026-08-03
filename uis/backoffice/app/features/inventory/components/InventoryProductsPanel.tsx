"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { listInventoryProducts } from "@/app/lib/inventory";
import type { InventoryProduct } from "@/app/features/inventory/types/inventory";

function getStockVisualState(stock: number): { label: string; className: string } {
  // Threshold policy: stock <= 10 is considered low stock, stock > 10 is normal stock.
  if (stock <= 10) {
    return {
      label: "Stock bajo",
      className: "border-amber-200 bg-amber-50 text-amber-700",
    };
  }

  return {
    label: "Stock normal",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  };
}

export function InventoryProductsPanel() {
  const [products, setProducts] = useState<InventoryProduct[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProducts = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await listInventoryProducts();
      setProducts(response);
    } catch (unknownError) {
      setError(unknownError instanceof Error ? unknownError.message : "No se pudo cargar la lista de SKU.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadProducts();
  }, [loadProducts]);

  const lowStockCount = useMemo(
    () => products.filter((product) => product.current_stock <= 10).length,
    [products]
  );

  return (
    <section className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-950">SKU Inventory</h1>
          <p className="mt-2 text-sm text-slate-600">
            Vista unificada de SKU por almacén (LA y ZGZ) con current_stock calculado desde StockEntry y StockExit.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            Total SKU: {products.length}
          </span>
          <span className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
            Stock bajo: {lowStockCount}
          </span>
          <button
            type="button"
            onClick={() => void loadProducts()}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Refrescar
          </button>
        </div>
      </header>

      {error && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
      )}

      {isLoading ? (
        <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
          Cargando SKU...
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-slate-700">
              <tr>
                <th className="px-4 py-3 font-semibold">id</th>
                <th className="px-4 py-3 font-semibold">name</th>
                <th className="px-4 py-3 font-semibold">sku</th>
                <th className="px-4 py-3 font-semibold">client_name</th>
                <th className="px-4 py-3 font-semibold">category</th>
                <th className="px-4 py-3 font-semibold">warehouse</th>
                <th className="px-4 py-3 font-semibold">current_stock</th>
                <th className="px-4 py-3 font-semibold">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {products.map((product) => {
                const stockVisual = getStockVisualState(product.current_stock);

                return (
                  <tr key={product.id}>
                    <td className="px-4 py-3 text-slate-700">{product.id}</td>
                    <td className="px-4 py-3 text-slate-900">{product.name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-700">{product.sku}</td>
                    <td className="px-4 py-3 text-slate-700">{product.client_name}</td>
                    <td className="px-4 py-3 text-slate-700">{product.category}</td>
                    <td className="px-4 py-3 text-slate-700">{product.warehouse}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-900">{product.current_stock}</span>
                        <span className={`rounded-full border px-2 py-1 text-xs font-medium ${stockVisual.className}`}>
                          {stockVisual.label}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <Link
                          href={`/backoffice/inventory/orders/inbound?sku_id=${product.id}`}
                          className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
                        >
                          + StockEntry
                        </Link>
                        <Link
                          href={`/backoffice/inventory/orders/outbound?sku_id=${product.id}`}
                          className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100"
                        >
                          - StockExit
                        </Link>
                      </div>
                    </td>
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
