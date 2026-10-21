export function OperationalWorkflow() {
  const steps = [
    {
      step: "01",
      title: "Inbound & Almacenamiento Unificado",
      description:
        "Recepción de mercancía en nuestros hubs estratégicos de Los Ángeles y Zaragoza. Registro por SKU en tiempo real con 30 días de gracia y tarificación transparente por metro cúbico.",
      badges: ["Almacén LA & Zaragoza", "WMS en Tiempo Real", "30 días gracia"],
      icon: (
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.75}
          d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
        />
      ),
    },
    {
      step: "02",
      title: "Ingesta y Picking Optimizado",
      description:
        "Tus pedidos se sincronizan automáticamente desde tus canales e-commerce. Nuestro sistema calcula la ruta de picking óptima dentro del almacén para minimizar errores y acelerar el empaquetado.",
      badges: ["Integración Shopify/Woo", "Control de Stock", "SLA <4h despacho"],
      icon: (
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.75}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
        />
      ),
    },
    {
      step: "03",
      title: "Smart Carrier Dispatcher",
      description:
        "Un algoritmo predictivo asigna el transportista óptimo para cada envío evaluando destino, dimensiones, urgencia y coste (UPS, FedEx, DHL en EE. UU.; SEUR, MRW en España) sin intervención manual.",
      badges: ["Multicarrier Automático", "Mejor Tarifa/Tiempo", "Etiquetas automáticas"],
      icon: (
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.75}
          d="M13 10V3L4 14h7v7l9-11h-7z"
        />
      ),
    },
    {
      step: "04",
      title: "Logística Inversa & Devoluciones con IA",
      description:
        "Reglas automatizadas de aprobación en menos de 48h. El sistema analiza fotografías del producto devuelto mediante visión computacional para clasificarlo al instante en reventa, reacondicionamiento o reciclaje.",
      badges: ["Aprobación <48h", "Inspección Visual IA", "Portal de Devoluciones"],
      icon: (
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.75}
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
        />
      ),
    },
  ];

  return (
    <section id="operacion" aria-labelledby="workflow-title" className="scroll-mt-16 bg-white py-20 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center">
          <span className="inline-block rounded-full bg-blue-100 px-3.5 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/80 dark:text-blue-300">
            Arquitectura de Operación Logística
          </span>
          <h2 id="workflow-title" className="mt-3 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl dark:text-white">
            Flujo Operativo de Extremo a Extremo
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-gray-600 dark:text-slate-300">
            Diseñado para que tu marca escale su catálogo y volumen de envíos sin necesidad de contratar más personal para tareas operativas repetitivas.
          </p>
        </div>

        <div className="mt-16 grid gap-8 md:grid-cols-2 lg:grid-cols-4">
          {steps.map((item) => (
            <div
              key={item.step}
              className="group relative flex flex-col justify-between rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-blue-500/50 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-blue-500/50"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-2xl font-black text-blue-600/40 dark:text-blue-400/40">
                    {item.step}
                  </span>
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition group-hover:bg-blue-600 group-hover:text-white dark:bg-blue-950/60 dark:text-blue-400 dark:group-hover:bg-blue-500 dark:group-hover:text-white">
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      {item.icon}
                    </svg>
                  </div>
                </div>

                <h3 className="mt-5 text-lg font-bold text-gray-900 dark:text-white">
                  {item.title}
                </h3>
                <p className="mt-2.5 text-sm leading-relaxed text-gray-600 dark:text-slate-300">
                  {item.description}
                </p>
              </div>

              <div className="mt-6 flex flex-wrap gap-1.5 pt-4 border-t border-gray-100 dark:border-slate-800">
                {item.badges.map((badge) => (
                  <span
                    key={badge}
                    className="inline-block rounded-md bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-600 dark:bg-slate-800 dark:text-slate-300"
                  >
                    {badge}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
