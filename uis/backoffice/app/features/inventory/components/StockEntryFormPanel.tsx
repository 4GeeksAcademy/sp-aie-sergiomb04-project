"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { createStockEntry, listInventoryProducts } from "@/app/lib/inventory";
import type { InventoryProduct } from "@/app/features/inventory/types/inventory";

const INITIAL_FORM = {
  sku_id: "",
  quantity: "",
  reference: "",
};

export function StockEntryFormPanel() {
  const searchParams = useSearchParams();
  const defaultSkuId = searchParams.get("sku_id") ?? "";

  const [products, setProducts] = useState<InventoryProduct[]>([]);
  const [form, setForm] = useState({ ...INITIAL_FORM, sku_id: defaultSkuId });
  const [isLoadingProducts, setIsLoadingProducts] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadProducts = useCallback(async () => {
    setIsLoadingProducts(true);
    setError(null);

    try {
      const data = await listInventoryProducts();
      setProducts(data);
    } catch (unknownError) {
      setError(unknownError instanceof Error ? unknownError.message : "No se pudieron cargar los SKU.");
    } finally {
      setIsLoadingProducts(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadProducts();
  }, [loadProducts]);

  const selectedProduct = useMemo(
    () => products.find((item) => String(item.id) === form.sku_id),
    [form.sku_id, products]
  );

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      if (!form.sku_id || !selectedProduct) {
        throw new Error("Debes seleccionar un SKU por nombre.");
      }

      await createStockEntry({
        sku_id: Number(form.sku_id),
        quantity: Number(form.quantity),
        reference: form.reference.trim(),
        warehouse: selectedProduct.warehouse,
      });

      setForm(INITIAL_FORM);
      setSuccess("StockEntry registrada correctamente.");
      await loadProducts();
    } catch (unknownError) {
      setError(unknownError instanceof Error ? unknownError.message : "No se pudo registrar la entrada.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <header>
        <h1 className="text-2xl font-semibold text-slate-950">Registrar StockEntry</h1>
        <p className="mt-2 text-sm text-slate-600">
          Registra una recepción de mercancía para un SKU existente en LA o ZGZ.
        </p>
      </header>

      {error && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
      )}

      {success && (
        <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          {success}
        </p>
      )}

      <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2 text-sm md:col-span-2">
          <span className="font-medium text-slate-700">SKU (selección por nombre)</span>
          <select
            value={form.sku_id}
            onChange={(event) => setForm((prev) => ({ ...prev, sku_id: event.target.value }))}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
            disabled={isLoadingProducts || isSubmitting}
            required
          >
            <option value="">Selecciona un SKU...</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {product.name} · {product.sku} · {product.warehouse}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-700">quantity</span>
          <input
            type="number"
            min={1}
            value={form.quantity}
            onChange={(event) => setForm((prev) => ({ ...prev, quantity: event.target.value }))}
            className="w-full rounded-xl border border-slate-300 px-3 py-2 text-slate-700"
            required
          />
        </label>

        <label className="space-y-2 text-sm">
          <span className="font-medium text-slate-700">reference</span>
          <input
            type="text"
            value={form.reference}
            onChange={(event) => setForm((prev) => ({ ...prev, reference: event.target.value }))}
            className="w-full rounded-xl border border-slate-300 px-3 py-2 text-slate-700"
            placeholder="PO-2024-0098"
            required
          />
        </label>

        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 md:col-span-2">
          warehouse asignado automáticamente según SKU: {selectedProduct?.warehouse ?? "-"}
        </div>

        <div className="md:col-span-2">
          <button
            type="submit"
            disabled={isSubmitting || isLoadingProducts}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Guardando..." : "Registrar StockEntry"}
          </button>
        </div>
      </form>
    </section>
  );
}
