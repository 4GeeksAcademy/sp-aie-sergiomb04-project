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
const RATE_AUTOSAVE_DELAY_MS = 1500;

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
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [form, setForm] = useState<SupplierFormState>(INITIAL_FORM);
  const [rateEdits, setRateEdits] = useState<Record<string, string>>({});
  const [pendingRateIds, setPendingRateIds] = useState<Record<string, boolean>>({});
  const [statusEdits, setStatusEdits] = useState<Record<string, SupplierStatus>>({});
  const [savingRateIds, setSavingRateIds] = useState<Record<string, boolean>>({});
  const [savingStatusIds, setSavingStatusIds] = useState<Record<string, boolean>>({});

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
      setPendingRateIds({});
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

  const replaceSupplierInState = useCallback((updatedSupplier: Supplier) => {
    setSuppliers((prevState) =>
      prevState.map((supplier) =>
        supplier.id === updatedSupplier.id ? updatedSupplier : supplier
      )
    );
  }, []);

  const handleRateAutosave = useCallback(
    async (supplierId: string) => {
      const rateValue = rateEdits[supplierId];
      const currentSupplier = suppliers.find((supplier) => supplier.id === supplierId);

      if (!currentSupplier || rateValue === undefined || rateValue.trim() === "") {
        return;
      }

      const parsedRate = Number(rateValue);

      if (
        Number.isNaN(parsedRate) ||
        parsedRate < 0 ||
        !pendingRateIds[supplierId] ||
        parsedRate === currentSupplier.rate_per_shipment
      ) {
        return;
      }

      setSavingRateIds((prevState) => ({ ...prevState, [supplierId]: true }));
      setError(null);
      setSuccess(null);

      try {
        const updatedSupplier = await updateSupplierRate(supplierId, {
          rate_per_shipment: parsedRate,
        });

        replaceSupplierInState(updatedSupplier);
        setRateEdits((prevState) =>
          prevState[supplierId] === rateValue
            ? { ...prevState, [supplierId]: String(updatedSupplier.rate_per_shipment) }
            : prevState
        );
        setStatusEdits((prevState) => ({
          ...prevState,
          [supplierId]: updatedSupplier.status,
        }));
        setSuccess("Tarifa actualizada");
      } catch (unknownError: unknown) {
        setError(
          unknownError instanceof Error ? unknownError.message : "No se pudo actualizar la tarifa"
        );
      } finally {
        setPendingRateIds((prevState) => ({ ...prevState, [supplierId]: false }));
        setSavingRateIds((prevState) => ({ ...prevState, [supplierId]: false }));
      }
    },
    [pendingRateIds, rateEdits, replaceSupplierInState, suppliers]
  );

  useEffect(() => {
    const hasPendingRateChanges = suppliers.some((supplier) => {
      const rateValue = rateEdits[supplier.id];

      if (
        rateValue === undefined ||
        rateValue.trim() === "" ||
        savingRateIds[supplier.id] ||
        !pendingRateIds[supplier.id]
      ) {
        return false;
      }

      const parsedRate = Number(rateValue);
      return !Number.isNaN(parsedRate) && parsedRate >= 0 && parsedRate !== supplier.rate_per_shipment;
    });

    if (!hasPendingRateChanges) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      suppliers.forEach((supplier) => {
        void handleRateAutosave(supplier.id);
      });
    }, RATE_AUTOSAVE_DELAY_MS);

    return () => window.clearTimeout(timeoutId);
  }, [handleRateAutosave, pendingRateIds, rateEdits, savingRateIds, suppliers]);

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
      setForm(INITIAL_FORM);
      setIsCreateModalOpen(false);
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

  const handleStatusUpdate = async (supplierId: string, nextStatus: SupplierStatus) => {
    setSavingStatusIds((prevState) => ({ ...prevState, [supplierId]: true }));
    setError(null);
    setSuccess(null);

    try {
      const updatedSupplier = await updateSupplierStatus(supplierId, {
        status: nextStatus,
      });
      replaceSupplierInState(updatedSupplier);
      setStatusEdits((prevState) => ({
        ...prevState,
        [supplierId]: updatedSupplier.status,
      }));
      setSuccess("Estado actualizado");
    } catch (unknownError: unknown) {
      setStatusEdits((prevState) => {
        const currentSupplier = suppliers.find((supplier) => supplier.id === supplierId);
        if (!currentSupplier) {
          return prevState;
        }

        return {
          ...prevState,
          [supplierId]: currentSupplier.status,
        };
      });
      setError(
        unknownError instanceof Error ? unknownError.message : "No se pudo actualizar el estado"
      );
    } finally {
      setSavingStatusIds((prevState) => ({ ...prevState, [supplierId]: false }));
    }
  };

  const handleDeleteSupplier = async (supplierId: string) => {
    setError(null);
    setSuccess(null);

    try {
      await deleteSupplier(supplierId);
      setSuppliers((prevState) => prevState.filter((supplier) => supplier.id !== supplierId));
      setRateEdits((prevState) => {
        const nextState = { ...prevState };
        delete nextState[supplierId];
        return nextState;
      });
      setPendingRateIds((prevState) => {
        const nextState = { ...prevState };
        delete nextState[supplierId];
        return nextState;
      });
      setStatusEdits((prevState) => {
        const nextState = { ...prevState };
        delete nextState[supplierId];
        return nextState;
      });
      setSuccess("Proveedor eliminado");
    } catch (unknownError: unknown) {
      setError(
        unknownError instanceof Error ? unknownError.message : "No se pudo eliminar el proveedor"
      );
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-950">
              Directorio de proveedores
            </h1>
            <p className="mt-2 max-w-3xl text-slate-600">
              Gestiona tarifas, estados de operación y cobertura de proveedores en USA y Spain.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500">{suppliers.length} proveedores</span>
            <button
              type="button"
              onClick={() => {
                setError(null);
                setSuccess(null);
                setForm(INITIAL_FORM);
                setIsCreateModalOpen(true);
              }}
              className="inline-flex items-center justify-center rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
            >
              + Registrar proveedor
            </button>
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] xl:items-end">
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

          <p className="text-xs text-slate-500 xl:pb-2">
            La tarifa se guarda sola tras {RATE_AUTOSAVE_DELAY_MS / 1000}s sin cambios.
          </p>
        </div>

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

        {isLoading ? (
          <p className="mt-6 text-sm text-slate-600">Cargando proveedores...</p>
        ) : (
          <div className="mt-6 overflow-x-auto">
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
                        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${supplier.status === "active"
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
                      <div className="flex items-center gap-2 flex-nowrap">
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            disabled={savingRateIds[supplier.id]}
                            value={rateEdits[supplier.id] ?? String(supplier.rate_per_shipment)}
                            onChange={(event) => {
                              setRateEdits((prevState) => ({
                                ...prevState,
                                [supplier.id]: event.target.value,
                              }));
                              setPendingRateIds((prevState) => ({
                                ...prevState,
                                [supplier.id]: true,
                              }));
                            }
                            }
                            className="w-28 rounded-lg border border-slate-300 px-2 py-1"
                          />
                        </div>

                        <div className="flex items-center gap-2">
                          <select
                            disabled={savingStatusIds[supplier.id]}
                            value={statusEdits[supplier.id] ?? supplier.status}
                            onChange={(event) => {
                              const nextStatus = event.target.value as SupplierStatus;

                              setStatusEdits((prevState) => ({
                                ...prevState,
                                [supplier.id]: nextStatus,
                              }));
                              void handleStatusUpdate(supplier.id, nextStatus);
                            }}
                            className="rounded-lg border border-slate-300 px-2 py-1"
                          >
                            <option value="active">Activo</option>
                            <option value="suspended">Suspendido</option>
                          </select>
                          {savingStatusIds[supplier.id] && (
                            <span className="text-xs text-slate-500">Actualizando...</span>
                          )}
                        </div>

                        <button
                          type="button"
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

      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="supplier-create-title"
            className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="supplier-create-title" className="text-xl font-semibold text-slate-900">
                  Alta de proveedor
                </h2>
                <p className="mt-2 text-sm text-slate-600">
                  Registra un nuevo partner logístico con su cobertura, tarifa y categorías.
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  setIsCreateModalOpen(false);
                  setError(null);
                }}
                className="rounded-full border border-slate-200 px-3 py-1 text-sm text-slate-600 hover:bg-slate-100"
              >
                Cerrar
              </button>
            </div>

            <form onSubmit={handleCreateSupplier} className="mt-6 grid gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm">
                  <span className="font-medium text-slate-700">Nombre</span>
                  <input
                    required
                    value={form.name}
                    onChange={(event) =>
                      setForm((prevState) => ({ ...prevState, name: event.target.value }))
                    }
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
                      setForm((prevState) => ({
                        ...prevState,
                        rate_per_shipment: event.target.value,
                      }))
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
                      setForm((prevState) => ({
                        ...prevState,
                        contact_email: event.target.value,
                      }))
                    }
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-700"
                  />
                </label>

                <label className="space-y-2 text-sm md:col-span-2">
                  <span className="font-medium text-slate-700">Notas</span>
                  <textarea
                    rows={3}
                    value={form.notes}
                    onChange={(event) =>
                      setForm((prevState) => ({ ...prevState, notes: event.target.value }))
                    }
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

              {error && (
                <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  {error}
                </p>
              )}

              <div className="flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsCreateModalOpen(false);
                    setError(null);
                  }}
                  className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting ? "Guardando..." : "Crear proveedor"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
