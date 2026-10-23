import { getSessionToken } from "@/app/features/auth/server/session";
import { RfpDashboardNotifications } from "@/app/features/rfp/components/RfpDashboardNotifications";
import { businessLogicSnapshot } from "../../../../src/demo";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDistance(value: number) {
  return new Intl.NumberFormat("es-ES", {
    maximumFractionDigits: 0,
  }).format(value);
}

type ValidationResult = {
  valid: boolean;
  errors: string[];
};

const getValidationStatus = (element: ValidationResult) => {
  if (element.valid) {
    return "Valido";
  }

  return `Invalido: ${element.errors.join(", ")}`;
};

export default async function Home() {
  let sessionToken: string | null = null;
  try {
    sessionToken = await getSessionToken();
  } catch {
    sessionToken = null;
  }

  const categoryEntries = Object.entries(businessLogicSnapshot.categoryCounts);
  const shipmentStatusEntries = Object.entries(businessLogicSnapshot.shipmentsByStatus);

  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-3">
          <span className="w-fit rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
            Sesión protegida
          </span>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950 dark:text-white">
            Dashboard operativo
          </h1>
          <p className="max-w-2xl text-slate-600 dark:text-slate-400">
            El acceso autenticado habilita la operativa interna de incidencias, proveedores,
            notificaciones comerciales de RFPs en tiempo real (SSE) y seguimiento del estado del
            negocio desde un único panel.
          </p>
        </div>
      </section>

      {/* Real-time SSE RFP Notifications Panel (visually distinguishable from operational metrics) */}
      <RfpDashboardNotifications initialToken={sessionToken} />

      <section className="grid gap-6 md:grid-cols-3">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Mejor transportista</h2>
          <p className="mt-3 text-2xl font-semibold text-slate-950 dark:text-white">
            {businessLogicSnapshot.bestCarrier?.carrier.name ?? "Sin resultado"}
          </p>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Score: {businessLogicSnapshot.bestCarrier?.score ?? "N/D"}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Valor inventario</h2>
          <p className="mt-3 text-2xl font-semibold text-slate-950 dark:text-white">
            {formatCurrency(businessLogicSnapshot.inventoryValue)}
          </p>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Productos con stock bajo: {businessLogicSnapshot.lowStockProducts.length}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Distancia promedio</h2>
          <p className="mt-3 text-2xl font-semibold text-slate-950 dark:text-white">
            {formatDistance(businessLogicSnapshot.averageShipmentDistance)} km
          </p>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Top carriers analizados: {businessLogicSnapshot.topCarriers.length}
          </p>
        </article>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Resumen de Hito 2</h2>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                Datos importados directamente desde [src/demo.ts].
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800/60">
              <h3 className="font-medium text-slate-900 dark:text-slate-100">Conteo por categoria</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                {categoryEntries.map(([category, count]) => (
                  <li key={category} className="flex items-center justify-between">
                    <span>{category}</span>
                    <span className="font-medium text-slate-900 dark:text-slate-100">{count}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800/60">
              <h3 className="font-medium text-slate-900 dark:text-slate-100">Envios por estado</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                {shipmentStatusEntries.map(([status, shipments]) => (
                  <li key={status} className="flex items-center justify-between">
                    <span>{status}</span>
                    <span className="font-medium text-slate-900 dark:text-slate-100">{shipments.length}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Validaciones</h2>
          <div className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
            <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800/60">
              <p className="font-medium text-slate-900 dark:text-slate-100">Producto</p>
              <p className="mt-1 break-words">{getValidationStatus(businessLogicSnapshot.productValidation)}</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800/60">
              <p className="font-medium text-slate-900 dark:text-slate-100">Envio</p>
              <p className="mt-1 break-words">{getValidationStatus(businessLogicSnapshot.shipmentValidation)}</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800/60">
              <p className="font-medium text-slate-900 dark:text-slate-100">Carrier</p>
              <p className="mt-1 break-words">{getValidationStatus(businessLogicSnapshot.carrierValidation)}</p>
            </div>
          </div>
        </article>
      </section>
    </main>
  );
}
