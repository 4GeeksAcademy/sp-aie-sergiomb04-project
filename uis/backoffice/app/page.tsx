import { businessLogicSnapshot } from "../../../src/demo";

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

export default function Home() {
  const categoryEntries = Object.entries(businessLogicSnapshot.categoryCounts);
  const shipmentStatusEntries = Object.entries(businessLogicSnapshot.shipmentsByStatus);

  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-3">
          <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-600">
            Backoffice
          </span>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
            Dashboard operativo
          </h1>
          <p className="max-w-2xl text-slate-600">
            Espacio inicial para modulos internos, indicadores y herramientas de gestion.
          </p>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Mejor transportista</h2>
          <p className="mt-3 text-2xl font-semibold text-slate-950">
            {businessLogicSnapshot.bestCarrier?.carrier.name ?? "Sin resultado"}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Score: {businessLogicSnapshot.bestCarrier?.score ?? "N/D"}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Valor inventario</h2>
          <p className="mt-3 text-2xl font-semibold text-slate-950">
            {formatCurrency(businessLogicSnapshot.inventoryValue)}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Productos con stock bajo: {businessLogicSnapshot.lowStockProducts.length}
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Distancia promedio</h2>
          <p className="mt-3 text-2xl font-semibold text-slate-950">
            {formatDistance(businessLogicSnapshot.averageShipmentDistance)} km
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Top carriers analizados: {businessLogicSnapshot.topCarriers.length}
          </p>
        </article>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Resumen de Hito 2</h2>
              <p className="mt-1 text-sm text-slate-500">
                Datos importados directamente desde [src/demo.ts].
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-4">
              <h3 className="font-medium text-slate-900">Conteo por categoria</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-600">
                {categoryEntries.map(([category, count]) => (
                  <li key={category} className="flex items-center justify-between">
                    <span>{category}</span>
                    <span className="font-medium text-slate-900">{count}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-xl bg-slate-50 p-4">
              <h3 className="font-medium text-slate-900">Envios por estado</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-600">
                {shipmentStatusEntries.map(([status, shipments]) => (
                  <li key={status} className="flex items-center justify-between">
                    <span>{status}</span>
                    <span className="font-medium text-slate-900">{shipments.length}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Validaciones</h2>
          <div className="mt-4 space-y-3 text-sm text-slate-600">
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="font-medium text-slate-900">Producto</p>
              <p className="mt-1 break-words">{getValidationStatus(businessLogicSnapshot.productValidation)}</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="font-medium text-slate-900">Envio</p>
              <p className="mt-1 break-words">{getValidationStatus(businessLogicSnapshot.shipmentValidation)}</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="font-medium text-slate-900">Carrier</p>
              <p className="mt-1 break-words">{getValidationStatus(businessLogicSnapshot.carrierValidation)}</p>
            </div>
          </div>
        </article>
      </section>
    </main>
  );
}

const getValidationStatus = (element: any) => {
  if (element.valid) {
    return "Valido";
  } else {
    return `Invalido: ${element.errors.join(", ")}`;
  }
}