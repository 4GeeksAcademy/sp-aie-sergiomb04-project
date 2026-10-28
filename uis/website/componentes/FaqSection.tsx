export function FaqSection() {
  const faqs = [
    {
      question: "¿Cuáles son los compromisos de entrega (SLAs) de TrackFlow?",
      answer:
        "Para envíos nacionales estándar dentro de EE. UU. o España el plazo habitual es de 3 a 5 días hábiles. En zonas metropolitanas (Los Ángeles y corredor Zaragoza-Madrid) ofrecemos servicio express de 24 a 48 horas. Para envíos transfronterizos entre ambos países el tiempo estimado es de 7 a 12 días hábiles sujeto a aduanas. Nuestro compromiso contractual estándar es mantener un SLA de entregas a tiempo superior al 90%.",
      category: "SLA & Entrega",
    },
    {
      question: "¿Con qué transportistas trabaja TrackFlow en cada país?",
      answer:
        "En Estados Unidos (Hub Los Ángeles) operamos con UPS (nacional y paquetes pesados >5kg), FedEx (express) y DHL (internacional). En España (Hub Zaragoza) trabajamos con SEUR, MRW, DHL y transportistas especializados de última milla. El algoritmo Smart Dispatcher selecciona automáticamente el mejor transportista por coste, urgencia y destino.",
      category: "Transportistas",
    },
    {
      question: "¿Cómo funciona el proceso de devoluciones y logística inversa?",
      answer:
        "Disponemos de una ventana estándar de 30 días. Si la solicitud del comprador cumple las reglas de la marca, se emite una etiqueta prepagada al instante. Al llegar al almacén, el producto se inspecciona y se clasifica con asistencia de IA en menos de 48-72 horas (apto para reventa, reacondicionamiento o baja). Las devoluciones internacionales cuentan con seguimiento asistido.",
      category: "Logística Inversa",
    },
    {
      question: "¿Cómo se calculan las tarifas de almacenamiento en los almacenes?",
      answer:
        "Cobramos estrictamente por volumen ocupado real en metros cúbicos ($18 USD/m³ al mes en Los Ángeles y 16 EUR/m³ al mes en Zaragoza), no por unidad de producto. Además, los primeros 30 días de cualquier producto nuevo disfrutan de periodo de gracia sin coste de almacenamiento.",
      category: "Tarifas & Hubs",
    },
    {
      question: "¿Cómo se integra TrackFlow con mi plataforma e-commerce?",
      answer:
        "Contamos con integraciones nativas para Shopify, WooCommerce, Amazon Marketplace y Magento, además de una API REST moderna y webhooks para ERPs y sistemas a medida. La sincronización de catálogo, pedidos y stock se realiza en tiempo real.",
      category: "Tecnología",
    },
  ];

  return (
    <section id="faq" aria-labelledby="faq-title" className="scroll-mt-16 bg-gray-50 py-20 dark:bg-slate-900/40">
      <div className="mx-auto max-w-4xl px-6">
        <div className="text-center">
          <span className="inline-block rounded-full bg-blue-100 px-3.5 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/80 dark:text-blue-300">
            Base de Conocimiento · Respuestas Rápidas
          </span>
          <h2 id="faq-title" className="mt-3 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl dark:text-white">
            Preguntas Frecuentes de Operación
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-gray-600 dark:text-slate-300">
            Políticas claras, compromisos contractuales y criterios de servicio de nuestra red logística en EE. UU. y España.
          </p>
        </div>

        <div className="mt-12 space-y-4">
          {faqs.map((faq, index) => (
            <details
              key={index}
              className="group rounded-2xl border border-gray-200 bg-white p-5 transition shadow-sm open:shadow-md dark:border-slate-800 dark:bg-slate-900"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-gray-900 dark:text-white">
                <span className="flex items-center gap-3">
                  <span className="rounded-md bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-700 dark:bg-blue-950/70 dark:text-blue-300">
                    {faq.category}
                  </span>
                  <span>{faq.question}</span>
                </span>
                <span className="ml-2 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-600 transition group-open:rotate-180 dark:bg-slate-800 dark:text-slate-300">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </span>
              </summary>
              <p className="mt-4 text-sm leading-relaxed text-gray-600 border-t border-gray-100 pt-4 dark:border-slate-800 dark:text-slate-300">
                {faq.answer}
              </p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
