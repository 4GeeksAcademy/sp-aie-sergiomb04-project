"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { createStockExit, listInventoryProducts } from "@/app/lib/inventory";
import type { InventoryProduct, StockExitType } from "@/app/features/inventory/types/inventory";
import { normalizeWarehouse, track } from "@/app/services/telemetry";

const INITIAL_FORM = {
  sku_id: "",
  quantity: "",
  exit_type: "dispatch" as StockExitType,
  tracking_number: "",
};

export function StockExitFormPanel() {
  const searchParams = useSearchParams();
  const defaultSkuId = searchParams.get("sku_id") ?? "";

  const [products, setProducts] = useState<InventoryProduct[]>([]);
  const [form, setForm] = useState({ ...INITIAL_FORM, sku_id: defaultSkuId });
  const [isLoadingProducts, setIsLoadingProducts] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const mountTimeRef = useRef<number | null>(null);
  const hadValidationErrorRef = useRef<boolean>(false);
  const submittedSuccessfullyRef = useRef<boolean>(false);
  const formRef = useRef(form);
  const productsRef = useRef(products);

  useEffect(() => {
    formRef.current = form;
  }, [form]);

  useEffect(() => {
    productsRef.current = products;
  }, [products]);

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
    mountTimeRef.current = Date.now();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadProducts();
  }, [loadProducts]);

  // Track form abandonment on unmount
  useEffect(() => {
    return () => {
      if (!submittedSuccessfullyRef.current) {
        const currentForm = formRef.current;
        const hasInput = Boolean(currentForm.sku_id || currentForm.quantity || currentForm.tracking_number);
        if (hasInput && mountTimeRef.current) {
          const selected = productsRef.current.find((item) => String(item.id) === currentForm.sku_id);
          const dwellSeconds = Math.round((Date.now() - mountTimeRef.current) / 1000);
          track("inventory_form_abandoned", {
            form_name: "stock_exit",
            step: "form_input",
            dwell_time_seconds: dwellSeconds,
            had_validation_error: hadValidationErrorRef.current,
            warehouse: normalizeWarehouse(selected?.warehouse),
            client_id: selected?.client_name || "unknown",
            product_id: selected?.sku || "unknown",
          });
        }
      }
    };
  }, []);

  const selectedProduct = useMemo(
    () => products.find((item) => String(item.id) === form.sku_id),
    [form.sku_id, products]
  );

  const quantityNumber = Number(form.quantity || 0);
  const exceedsStock = Boolean(
    selectedProduct && Number.isFinite(quantityNumber) && quantityNumber > selectedProduct.current_stock
  );

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      if (!form.sku_id || !selectedProduct) {
        hadValidationErrorRef.current = true;
        track("inventory_form_validation_failed", {
          form_name: "stock_exit",
          error_code: "missing_sku",
          field_name: "sku_id",
          warehouse: normalizeWarehouse(selectedProduct?.warehouse),
          client_id: selectedProduct?.client_name || "unknown",
          product_id: selectedProduct?.sku || "unknown",
          product_category: selectedProduct?.category || "fashion",
          quantity: Number(form.quantity || 0),
        });
        throw new Error("Debes seleccionar un SKU por nombre.");
      }

      if (!form.quantity || Number(form.quantity) <= 0) {
        hadValidationErrorRef.current = true;
        track("inventory_form_validation_failed", {
          form_name: "stock_exit",
          error_code: "invalid_quantity",
          field_name: "quantity",
          warehouse: normalizeWarehouse(selectedProduct.warehouse),
          client_id: selectedProduct.client_name,
          product_id: selectedProduct.sku,
          product_category: selectedProduct.category,
          quantity: Number(form.quantity || 0),
        });
        throw new Error("La cantidad debe ser mayor a 0.");
      }

      if (exceedsStock) {
        hadValidationErrorRef.current = true;
        track("outbound_order_rejected_insufficient_stock", {
          warehouse: normalizeWarehouse(selectedProduct.warehouse),
          client_id: selectedProduct.client_name,
          product_id: selectedProduct.sku,
          product_category: selectedProduct.category,
          quantity: Number(form.quantity),
          available_stock: selectedProduct.current_stock,
          requested_quantity: Number(form.quantity),
          user_uuid: "current_user",
          rejection_reason: "insufficient_stock",
        });
        throw new Error(
          `La cantidad supera el current_stock disponible (${selectedProduct.current_stock}) para este SKU.`
        );
      }

      const response = await createStockExit({
        sku_id: Number(form.sku_id),
        quantity: Number(form.quantity),
        exit_type: form.exit_type,
        tracking_number: form.exit_type === "dispatch" ? form.tracking_number.trim() : null,
        warehouse: selectedProduct.warehouse,
      });

      submittedSuccessfullyRef.current = true;

      // Track outbound_order_created event
      track("outbound_order_created", {
        warehouse: normalizeWarehouse(response.warehouse),
        client_id: selectedProduct.client_name,
        product_id: selectedProduct.sku,
        product_category: selectedProduct.category,
        quantity: response.quantity,
        order_id: String(response.id),
        exit_type: response.exit_type,
        tracking_number_present: Boolean(response.tracking_number && response.tracking_number.trim().length > 0),
        user_uuid: response.user_uuid,
      });

      setForm(INITIAL_FORM);
      setSuccess("StockExit registrada correctamente.");
      await loadProducts();
    } catch (unknownError) {
      setError(unknownError instanceof Error ? unknownError.message : "No se pudo registrar la salida.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <header>
        <h1 className="text-2xl font-semibold text-slate-950">Registrar StockExit</h1>
        <p className="mt-2 text-sm text-slate-600">
          Registra despacho (dispatch) o baja por pérdida (loss) usando current_stock reactivo.
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

        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          current_stock disponible: <span className="font-semibold">{selectedProduct?.current_stock ?? "-"}</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          warehouse asignado automáticamente según SKU: {selectedProduct?.warehouse ?? "-"}
        </div>

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
          <span className="font-medium text-slate-700">exit_type</span>
          <select
            value={form.exit_type}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                exit_type: event.target.value as StockExitType,
                tracking_number: event.target.value === "loss" ? "" : prev.tracking_number,
              }))
            }
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
            required
          >
            <option value="dispatch">dispatch</option>
            <option value="loss">loss</option>
          </select>
        </label>

        <label className="space-y-2 text-sm md:col-span-2">
          <span className="font-medium text-slate-700">tracking_number</span>
          <input
            type="text"
            value={form.tracking_number}
            onChange={(event) => setForm((prev) => ({ ...prev, tracking_number: event.target.value }))}
            className="w-full rounded-xl border border-slate-300 px-3 py-2 text-slate-700"
            placeholder="1Z999AA10123456784"
            required={form.exit_type === "dispatch"}
            disabled={form.exit_type === "loss"}
          />
        </label>

        {exceedsStock && (
          <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700 md:col-span-2">
            Advertencia: la cantidad solicitada supera el current_stock disponible.
          </p>
        )}

        <div className="md:col-span-2">
          <button
            type="submit"
            disabled={isSubmitting || isLoadingProducts || exceedsStock}
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Guardando..." : "Registrar StockExit"}
          </button>
        </div>
      </form>
    </section>
  );
}
