import type { Metadata } from "next";

import { ServiceApplicationForm } from "../../componentes/ServiceApplicationForm";

export const metadata: Metadata = {
  title: "Solicitud de servicio",
  description:
    "Cuentanos sobre tu operacion y te ayudaremos a optimizar tu logistica.",
};

export default function ApplicationPage() {
  return (
    <main
      id="main-content"
      role="main"
      aria-labelledby="form-title"
      className="px-6 py-16"
    >
      <div className="mx-auto max-w-3xl rounded-xl bg-white p-8 shadow-md dark:border dark:border-slate-800 dark:bg-slate-900">
        <h1 id="form-title" className="mb-2 text-center text-3xl font-bold text-gray-900 dark:text-white">
          Solicitud de servicio
        </h1>
        <p id="form-description" className="mb-3 text-center text-gray-600 dark:text-slate-300">
          Cuentanos sobre tu operacion y te ayudaremos a optimizar tu logistica.
        </p>
        <p id="required-note" className="mb-8 text-center text-sm text-gray-600 dark:text-slate-400">
          Los campos marcados con * son obligatorios.
        </p>

        <ServiceApplicationForm />
      </div>
    </main>
  );
}
