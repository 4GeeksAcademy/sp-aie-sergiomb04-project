import Link from "next/link";

export function CtaBanner() {
  return (
    <section aria-labelledby="cta-title" className="bg-white py-16 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl px-6">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-blue-600 to-indigo-700 px-8 py-14 text-center text-white shadow-xl sm:px-16 dark:from-blue-700 dark:to-indigo-900">
          <div className="relative z-10 mx-auto max-w-3xl">
            <h2 id="cta-title" className="text-3xl font-extrabold tracking-tight sm:text-4xl text-white">
              ¿Listo para optimizar tu logística en EE. UU. y España?
            </h2>
            <p className="mt-4 text-base sm:text-lg text-blue-100">
              Automatiza la preparación de pedidos, reduce un 30% los costes de envío multicarrier y ofrece a tus clientes una experiencia de entrega y devoluciones impecable.
            </p>

            <div className="mt-8 flex flex-col justify-center gap-4 sm:flex-row">
              <Link
                href="/application"
                className="inline-flex items-center justify-center rounded-xl bg-white px-7 py-3.5 text-sm font-bold text-blue-700 shadow-md transition hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-white"
              >
                Solicitar Propuesta Personalizada
              </Link>
              <a
                href="mailto:info@trackflow.com"
                className="inline-flex items-center justify-center rounded-xl border border-white/40 bg-white/10 px-7 py-3.5 text-sm font-semibold text-white backdrop-blur-sm transition hover:bg-white/20"
              >
                Hablar con un Especialista
              </a>
            </div>

            <p className="mt-6 text-xs text-blue-200">
              Onboarding en menos de 10 días hábiles · SLA contractual garantizado &gt;90%
            </p>
          </div>

          {/* Decorative background circles */}
          <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-white/10 blur-2xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-blue-500/20 blur-2xl pointer-events-none" />
        </div>
      </div>
    </section>
  );
}
