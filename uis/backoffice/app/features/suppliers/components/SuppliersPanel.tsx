"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createSupplier,
  deleteSupplier,
  fetchSuppliers,
  updateSupplierRate,
  updateSupplierStatus,
} from "@/app/features/suppliers/services/api";
import {
  Supplier,
  SupplierCategory,
  SupplierCountry,
  SupplierCreateInput,
  SupplierStatus,
  VALID_CATEGORIES,
} from "@/app/features/suppliers/types/suppliers";

type SupplierFormState = {
  name: string;
  country: SupplierCountry;
  categories: SupplierCategory[];
  rate_per_shipment: string;
  currency: "USD" | "EUR";
  status: SupplierStatus;
  service_zone: string;
  contact_email: string;
  notes: string;
};

const CATEGORY_LABELS: Record<SupplierCategory, string> = {
  carrier_last_mile: "Carrier última milla",
  carrier_international: "Carrier internacional",
  warehouse_supplies: "Suministros almacén",
  packaging_materials: "Material de embalaje",
  reverse_logistics: "Logística inversa",
  fleet_maintenance: "Mantenimiento flota",
  it_and_wms_software: "Software IT/WMS",
  cleaning_and_facilities: "Limpieza e instalaciones",
};

const STATUS_LABELS: Record<SupplierStatus, string> = {
  active: "Activo",
  suspended: "Suspendido",
};

const COUNTRY_OPTIONS: SupplierCountry[] = ["USA", "Spain"];

const INITIAL_FORM: SupplierFormState = {
  name: "",
  country: "USA",
  categories: ["carrier_last_mile"],
  rate_per_shipment: "",
  currency: "USD",
  status: "active",
  service_zone: "",
  contact_email: "",
  notes: "",
};

function getCurrencyByCountry(country: SupplierCountry): "USD" | "EUR" {
  return country === "USA" ? "USD" : "EUR";
}

function formatApiDate(isoDate: string): string {
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(isoDate));
}

export function SuppliersPanel() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [countryFilter, setCountryFilter] = useState<SupplierCountry | "all">("all");
  const [categoryFilter, setCategoryFilter] = useState<SupplierCategory | "all">("all");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [form, setForm] = useState<SupplierFormState>(INITIAL_FORM);
  const [rateEdits, setRateEdits] = useState<Record<string, string>>({});
  const [statusEdits, setStatusEdits] = useState<Record<string, SupplierStatus>>({});

  const activeFilters = useMemo(
    () => ({
      country: countryFilter === "all" ? undefined : countryFilter,
      category: categoryFilter === "all" ? undefined : categoryFilter,
    }),
    [countryFilter, categoryFilter]
  );

  const loadSuppliers = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await fetchSuppliers(activeFilters);
      setSuppliers(data);
      setRateEdits(
        Object.fromEntries(data.map((supplier) => [supplier.id, String(supplier.rate_per_shipment)]))
      );
      setStatusEdits(
        Object.fromEntries(data.map((supplier) => [supplier.id, supplier.status])) as Record<
          string,
          SupplierStatus
        >
      );
    } catch (unknownError: unknown) {
      setError(
        unknownError instanceof Error
          ? unknownError.message
          : "No se pudo cargar el directorio de proveedores"
      );
    } finally {
      setIsLoading(false);
    }
  }, [activeFilters]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadSuppliers();
  }, [loadSuppliers]);

  const handleCategoryToggle = (category: SupplierCategory) => {
    setForm((prevState) => {
      const alreadySelected = prevState.categories.includes(category);
      const nextCategories = alreadySelected
        ? prevState.categories.filter((item) => item !== category)
        : [...prevState.categories, category];

      return {
        ...prevState,
        categories: nextCategories,
      };
    });
  };

  const handleCreateSupplier = async (event: React.FormEvent) => {
    event.preventDefault();

    if (form.categories.length === 0) {
      setError("Debes seleccionar al menos una categoría");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const payload: SupplierCreateInput = {
        name: form.name,
        country: form.country,
        categories: form.categories,
        rate_per_shipment: Number(form.rate_per_shipment),
        currency: form.currency,
        status: form.status,
        service_zone: form.service_zone || undefined,
        contact_email: form.contact_email || undefined,
        notes: form.notes || undefined,
      };

      await createSupplier(payload);
      setForm({ ...INITIAL_FORM, country: form.country, currency: form.currency });
      setSuccess("Proveedor creado correctamente");
      await loadSuppliers();
    } catch (unknownError: unknown) {
      setError(
        unknownError instanceof Error ? unknownError.message : "No se pudo crear el proveedor"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRateUpdate = async (supplierId: string) => {
    setError(null);
    setSuccess(null);

    try {
      await updateSupplierRate(supplierId, {
        rate_per_shipment: Number(rateEdits[supplierId]),
      });
      setSuccess("Tarifa actualizada");
      await loadSuppliers();
    } catch (unknownError: unknown) {
      setError(
        unknownError instanceof Error ? unknownError.message : "No se pudo actualizar la tarifa"
      );
    }
  };

  const handleStatusUpdate = async (supplierId: string) => {
    setError(null);
    setSuccess(null);

    try {
      await updateSupplierStatus(supplierId, {
        status: statusEdits[supplierId],
      });
      setSuccess("Estado actualizado");
      await loadSuppliers();
    } catch (unknownError: unknown) {
      setError(
        unknownError instanceof Error ? unknownError.message : "No se pudo actualizar el estado"
      );
    }
  };

  const handleDeleteSupplier = async (supplierId: string) => {
    setError(null);
    setSuccess(null);

    try {
      await deleteSupplier(supplierId);
      setSuccess("Proveedor eliminado");
      await loadSuppliers();
    } catch (unknownError: unknown) {
      setError(
        unknownError instanceof Error ? unknownError.message : "No se pudo eliminar el proveedor"
      );
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-950">Suppliers</h1>
        <p className="mt-2 max-w-3xl text-slate-600">
          Directorio de proveedores para gestionar tarifas, estados de operación y cobertura en
          USA y Spain.
        </p>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <label className="space-y-2 text-sm">
            <span className="font-medium text-slate-700">Filtrar por país</span>
            <select
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
              value={countryFilter}
              onChange={(event) => setCountryFilter(event.target.value as SupplierCountry | "all")}
            >
              <option value="all">Todos</option>
              {COUNTRY_OPTIONS.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-2 text-sm">
            <span className="font-medium text-slate-700">Filtrar por categoría</span>
            <select
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
              value={categoryFilter}
              onChange={(event) =>
                setCategoryFilter(event.target.value as SupplierCategory | "all")
              }
            >
              <option value="all">Todas</option>
              {VALID_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {CATEGORY_LABELS[category]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Alta de proveedor</h2>

        <form onSubmit={handleCreateSupplier} className="mt-4 grid gap-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm">
              <span className="font-medium text-slate-700">Nombre</span>
              <input
                required
                value={form.name}
                onChange={(event) => setForm((prevState) => ({ ...prevState, name: event.target.value }))}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
              />
            </label>

            <label className="space-y-2 text-sm">
              <span className="font-medium text-slate-700">País</span>
              <select
                value={form.country}
                onChange={(event) => {
                  const country = event.target.value as SupplierCountry;
                  setForm((prevState) => ({
                    ...prevState,
                    country,
                    currency: getCurrencyByCountry(country),
                  }));
                }}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
              >
                {COUNTRY_OPTIONS.map((country) => (
                  <option key={country} value={country}>
                    {country}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2 text-sm">
              <span className="font-medium text-slate-700">Tarifa por envío</span>
              <input
                required
                min="0"
                step="0.01"
                type="number"
                value={form.rate_per_shipment}
                onChange={(event) =>
                  setForm((prevState) => ({ ...prevState, rate_per_shipment: event.target.value }))
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
              />
            </label>

            <label className="space-y-2 text-sm">
              <span className="font-medium text-slate-700">Moneda</span>
              <input
                readOnly
                value={form.currency}
                className="w-full rounded-xl border border-slate-200 bg-slate-100 px-3 py-2 text-slate-600"
              />
            </label>

            <label className="space-y-2 text-sm">
              <span className="font-medium text-slate-700">Estado inicial</span>
              <select
                value={form.status}
                onChange={(event) =>
                  setForm((prevState) => ({
                    ...prevState,
                    status: event.target.value as SupplierStatus,
                  }))
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
              >
                <option value="active">Activo</option>
                <option value="suspended">Suspendido</option>
              </select>
            </label>

            <label className="space-y-2 text-sm">
              <span className="font-medium text-slate-700">Zona de servicio</span>
              <input
                value={form.service_zone}
                onChange={(event) =>
                  setForm((prevState) => ({ ...prevState, service_zone: event.target.value }))
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
              />
            </label>

            <label className="space-y-2 text-sm">
              <span className="font-medium text-slate-700">Email de contacto</span>
              <input
                type="email"
                value={form.contact_email}
                onChange={(event) =>
                  setForm((prevState) => ({ ...prevState, contact_email: event.target.value }))
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
              />
            </label>

            <label className="space-y-2 text-sm md:col-span-2">
              <span className="font-medium text-slate-700">Notas</span>
              <textarea
                rows={3}
                value={form.notes}
                onChange={(event) => setForm((prevState) => ({ ...prevState, notes: event.target.value }))}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
              />
            </label>
          </div>

          <fieldset className="rounded-xl border border-slate-200 p-4">
            <legend className="px-2 text-sm font-medium text-slate-700">Categorías</legend>
            <div className="mt-2 grid gap-3 md:grid-cols-2">
              {VALID_CATEGORIES.map((category) => (
                <label key={category} className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={form.categories.includes(category)}
                    onChange={() => handleCategoryToggle(category)}
                  />
                  <span>{CATEGORY_LABELS[category]}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? "Guardando..." : "Crear proveedor"}
            </button>
          </div>
        </form>

        {error && (
          <p className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </p>
        )}
        {success && (
          <p className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {success}
          </p>
        )}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-slate-900">Directorio de proveedores</h2>
          <span className="text-sm text-slate-500">{suppliers.length} proveedores</span>
        </div>

        {isLoading ? (
          <p className="text-sm text-slate-600">Cargando proveedores...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700">Proveedor</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700">Categorías</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700">Tarifa</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700">Estado</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700">Actualizado</th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-700">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {suppliers.map((supplier) => (
                  <tr key={supplier.id}>
                    <td className="px-3 py-3 align-top">
                      <p className="font-semibold text-slate-900">{supplier.name}</p>
                      <p className="text-xs text-slate-500">
                        {supplier.country} · {supplier.currency}
                      </p>
                    </td>
                    <td className="px-3 py-3 align-top text-slate-700">
                      {supplier.categories.map((category) => CATEGORY_LABELS[category]).join(", ")}
                    </td>
                    <td className="px-3 py-3 align-top text-slate-700">
                      {supplier.rate_per_shipment.toFixed(2)} {supplier.currency}
                    </td>
                    <td className="px-3 py-3 align-top">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                          supplier.status === "active"
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {STATUS_LABELS[supplier.status]}
                      </span>
                    </td>
                    <td className="px-3 py-3 align-top text-slate-600">
                      {formatApiDate(supplier.updated_at)}
                    </td>
                    <td className="px-3 py-3 align-top">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={rateEdits[supplier.id] ?? String(supplier.rate_per_shipment)}
                            onChange={(event) =>
                              setRateEdits((prevState) => ({
                                ...prevState,
                                [supplier.id]: event.target.value,
                              }))
                            }
                            className="w-28 rounded-lg border border-slate-300 px-2 py-1"
                          />
                          <button
                            onClick={() => void handleRateUpdate(supplier.id)}
                            className="rounded-lg border border-slate-300 px-2 py-1 font-medium text-slate-700 hover:bg-slate-100"
                          >
                            Guardar tarifa
                          </button>
                        </div>

                        <div className="flex items-center gap-2">
                          <select
                            value={statusEdits[supplier.id] ?? supplier.status}
                            onChange={(event) =>
                              setStatusEdits((prevState) => ({
                                ...prevState,
                                [supplier.id]: event.target.value as SupplierStatus,
                              }))
                            }
                            className="rounded-lg border border-slate-300 px-2 py-1"
                          >
                            <option value="active">Activo</option>
                            <option value="suspended">Suspendido</option>
                          </select>
                          <button
                            onClick={() => void handleStatusUpdate(supplier.id)}
                            className="rounded-lg border border-slate-300 px-2 py-1 font-medium text-slate-700 hover:bg-slate-100"
                          >
                            Guardar estado
                          </button>
                        </div>

                        <button
                          onClick={() => void handleDeleteSupplier(supplier.id)}
                          className="rounded-lg border border-rose-200 px-2 py-1 text-rose-700 hover:bg-rose-50"
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
