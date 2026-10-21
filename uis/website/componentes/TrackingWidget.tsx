"use client";

import { useState } from "react";

type TrackingStage = {
  title: string;
  location: string;
  date: string;
  completed: boolean;
  current?: boolean;
};

type TrackingData = {
  trackingId: string;
  orderNumber: string;
  clientBrand: string;
  status: "En reparto" | "Entregado" | "En tránsito internacional" | "En preparación";
  carrier: string;
  origin: string;
  destination: string;
  estimatedDelivery: string;
  stages: TrackingStage[];
};

const SAMPLE_SHIPMENTS: Record<string, TrackingData> = {
  "TRF-US-8941": {
    trackingId: "TRF-US-8941",
    orderNumber: "ORD-99214",
    clientBrand: "Aura Apparel",
    status: "En reparto",
    carrier: "FedEx Express (Smart Dispatch)",
    origin: "Hub Los Ángeles (Whse LA-01)",
    destination: "San Francisco, CA 94105",
    estimatedDelivery: "Hoy antes de las 18:00 (SLA Express)",
    stages: [
      {
        title: "Orden recibida e inventario confirmado",
        location: "Hub Los Ángeles",
        date: "20 Oct, 08:30",
        completed: true,
      },
      {
        title: "Picking, packing y pesaje completado",
        location: "Hub Los Ángeles",
        date: "20 Oct, 11:15",
        completed: true,
      },
      {
        title: "Asignado a FedEx Express por Smart Dispatcher",
        location: "Centro de Clasificación LA",
        date: "20 Oct, 14:00",
        completed: true,
      },
      {
        title: "En vehículo de entrega (Última milla)",
        location: "San Francisco Bay Depot",
        date: "21 Oct, 07:45",
        completed: true,
        current: true,
      },
      {
        title: "Entrega completada",
        location: "Destinatario",
        date: "Pendiente",
        completed: false,
      },
    ],
  },
  "TRF-ES-3312": {
    trackingId: "TRF-ES-3312",
    orderNumber: "ORD-48102",
    clientBrand: "ModaViva Studio",
    status: "Entregado",
    carrier: "SEUR Prioritario",
    origin: "Hub Zaragoza (Plaza Logística)",
    destination: "Madrid, 28001 (España)",
    estimatedDelivery: "Entregado a tiempo (SLA 99.2%)",
    stages: [
      {
        title: "Orden recibida en sistema WMS",
        location: "Hub Zaragoza",
        date: "19 Oct, 09:00",
        completed: true,
      },
      {
        title: "Empaquetado y etiqueta multicarrier generada",
        location: "Hub Zaragoza",
        date: "19 Oct, 12:40",
        completed: true,
      },
      {
        title: "Recogido por SEUR en almacén",
        location: "Zaragoza Plataforma",
        date: "19 Oct, 17:20",
        completed: true,
      },
      {
        title: "En ruta de entrega en Madrid Centro",
        location: "Delegación SEUR Coslada",
        date: "20 Oct, 08:30",
        completed: true,
      },
      {
        title: "Entregado y firmado en destino",
        location: "Dirección del cliente",
        date: "20 Oct, 11:15",
        completed: true,
        current: true,
      },
    ],
  },
  "TRF-INT-502": {
    trackingId: "TRF-INT-502",
    orderNumber: "ORD-71932",
    clientBrand: "Nova Botanics",
    status: "En tránsito internacional",
    carrier: "DHL Express Cross-Border",
    origin: "Hub Los Ángeles (Whse LA-01)",
    destination: "Zaragoza / Barcelona (UE)",
    estimatedDelivery: "24 Octubre (En despacho aduanero)",
    stages: [
      {
        title: "Inventario transfronterizo consolidado",
        location: "Hub Los Ángeles",
        date: "18 Oct, 16:00",
        completed: true,
      },
      {
        title: "Documentación comercial y packing exportación",
        location: "Hub Los Ángeles",
        date: "19 Oct, 10:00",
        completed: true,
      },
      {
        title: "Vuelo de carga internacional en tránsito",
        location: "LAX -> MAD Barajas",
        date: "20 Oct, 22:30",
        completed: true,
        current: true,
      },
      {
        title: "Despacho de aduanas e inspección",
        location: "Aduana Aeropuerto Adolfo Suárez",
        date: "Pendiente",
        completed: false,
      },
      {
        title: "Recepción en Hub Zaragoza y entrega local",
        location: "Hub Zaragoza",
        date: "Pendiente",
        completed: false,
      },
    ],
  },
};

export function TrackingWidget() {
  const [query, setQuery] = useState("TRF-US-8941");
  const [activeTracking, setActiveTracking] = useState<TrackingData | null>(
    SAMPLE_SHIPMENTS["TRF-US-8941"]
  );
  const [hasSearched, setHasSearched] = useState(true);

  function handleSearch(searchCode: string) {
    const code = searchCode.trim().toUpperCase();
    setQuery(code);
    setHasSearched(true);
    if (SAMPLE_SHIPMENTS[code]) {
      setActiveTracking(SAMPLE_SHIPMENTS[code]);
    } else {
      setActiveTracking(null);
    }
  }

  return (
    <section id="rastreo" aria-labelledby="tracking-title" className="scroll-mt-16 bg-gray-50 py-20 dark:bg-slate-900/50">
      <div className="mx-auto max-w-5xl px-6">
        <div className="text-center">
          <span className="inline-block rounded-full bg-blue-100 px-3.5 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/80 dark:text-blue-300">
            Demostración en vivo · Portal Unificado
          </span>
          <h2 id="tracking-title" className="mt-3 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl dark:text-white">
            Seguimiento de Envíos Multicarrier
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-gray-600 dark:text-slate-300">
            Consulta el estado de cualquier paquete en tiempo real sin importar si se procesa en Los Ángeles con UPS/FedEx o en Zaragoza con SEUR/MRW.
          </p>
        </div>

        {/* Search bar & quick chips */}
        <div className="mt-10 mx-auto max-w-2xl">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSearch(query);
            }}
            className="flex flex-col gap-2 sm:flex-row"
          >
            <div className="relative flex-1">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5">
                <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ej: TRF-US-8941 o TRF-ES-3312"
                className="w-full rounded-xl border border-gray-300 bg-white py-3.5 pl-10 pr-4 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>
            <button
              type="submit"
              className="rounded-xl bg-blue-600 px-6 py-3.5 text-sm font-semibold text-white shadow transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-blue-500 dark:hover:bg-blue-600"
            >
              Rastrear Envío
            </button>
          </form>

          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-600 dark:text-slate-400">
            <span>Envíos de prueba:</span>
            {Object.keys(SAMPLE_SHIPMENTS).map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => handleSearch(code)}
                className={`rounded-md px-2.5 py-1 font-mono font-medium transition ${
                  query === code
                    ? "bg-blue-600 text-white dark:bg-blue-500"
                    : "bg-gray-200 hover:bg-gray-300 text-gray-800 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300"
                }`}
              >
                {code}
              </button>
            ))}
          </div>
        </div>

        {/* Tracking Details Card */}
        <div className="mt-8 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8 dark:border-slate-800 dark:bg-slate-900">
          {activeTracking ? (
            <div>
              <div className="flex flex-col gap-4 border-b border-gray-100 pb-6 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-mono text-xl font-bold text-gray-900 dark:text-white">
                      {activeTracking.trackingId}
                    </h3>
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        activeTracking.status === "Entregado"
                          ? "bg-green-100 text-green-800 dark:bg-green-950/80 dark:text-green-300"
                          : "bg-blue-100 text-blue-800 dark:bg-blue-950/80 dark:text-blue-300"
                      }`}
                    >
                      {activeTracking.status}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-500 dark:text-slate-400">
                    Marca: <span className="font-medium text-gray-700 dark:text-slate-300">{activeTracking.clientBrand}</span> · Pedido: {activeTracking.orderNumber}
                  </p>
                </div>

                <div className="text-left sm:text-right">
                  <p className="text-xs text-gray-500 dark:text-slate-400">Estimación de entrega</p>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">
                    {activeTracking.estimatedDelivery}
                  </p>
                </div>
              </div>

              {/* Quick details grid */}
              <div className="grid grid-cols-1 gap-4 py-6 sm:grid-cols-3 text-sm border-b border-gray-100 dark:border-slate-800">
                <div>
                  <p className="text-xs text-gray-500 dark:text-slate-400">Origen & Almacén</p>
                  <p className="mt-0.5 font-medium text-gray-900 dark:text-white">{activeTracking.origin}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-slate-400">Destino</p>
                  <p className="mt-0.5 font-medium text-gray-900 dark:text-white">{activeTracking.destination}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-slate-400">Transportista asignado</p>
                  <p className="mt-0.5 font-medium text-blue-600 dark:text-blue-400">{activeTracking.carrier}</p>
                </div>
              </div>

              {/* Timeline */}
              <div className="pt-6">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-6">
                  Cronología de eventos operativos
                </h4>
                <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-200 dark:before:bg-slate-800">
                  {activeTracking.stages.map((stage, idx) => (
                    <div key={idx} className="relative flex items-start justify-between gap-4">
                      <div
                        className={`absolute -left-6 top-1 h-5 w-5 rounded-full border-2 flex items-center justify-center transition ${
                          stage.current
                            ? "border-blue-600 bg-blue-600 ring-4 ring-blue-100 dark:ring-blue-950"
                            : stage.completed
                            ? "border-blue-600 bg-blue-600 dark:border-blue-500 dark:bg-blue-500"
                            : "border-gray-300 bg-white dark:border-slate-700 dark:bg-slate-900"
                        }`}
                      >
                        {stage.completed && (
                          <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                      <div>
                        <p className={`text-sm font-semibold ${stage.completed ? "text-gray-900 dark:text-white" : "text-gray-400 dark:text-slate-500"}`}>
                          {stage.title}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-slate-400">{stage.location}</p>
                      </div>
                      <span className="text-xs font-mono text-gray-400 dark:text-slate-500 whitespace-nowrap">
                        {stage.date}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : hasSearched ? (
            <div className="py-12 text-center">
              <svg className="mx-auto h-12 w-12 text-gray-400 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3 className="mt-3 text-base font-semibold text-gray-900 dark:text-white">
                No se encontró el envío con código &quot;{query}&quot;
              </h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-slate-400">
                Prueba con los códigos de muestra: <strong className="font-mono">TRF-US-8941</strong>, <strong className="font-mono">TRF-ES-3312</strong> o <strong className="font-mono">TRF-INT-502</strong>.
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
