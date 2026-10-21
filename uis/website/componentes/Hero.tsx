import Link from "next/link";

export type HeroStat = {
  value: string;
  label: string;
  sublabel?: string;
};

type HeroProps = {
  stats: HeroStat[];
};

export function Hero({ stats }: HeroProps) {
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden bg-gradient-to-b from-blue-50/60 via-white to-gray-50 px-6 py-20 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <div className="mx-auto max-w-6xl text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50/80 px-4 py-1.5 text-xs font-semibold text-blue-700 dark:border-blue-900/50 dark:bg-blue-950/60 dark:text-blue-300">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-600 dark:bg-blue-400"></span>
          </span>
          Logística Inteligente de Última Milla & Almacenes Transfronterizos
        </div>

        <h1
          id="hero-title"
          className="mt-6 text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl md:text-6xl dark:text-white"
        >
          Operaciones de e-commerce <br />
          <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent dark:from-blue-400 dark:to-indigo-300">
            automatizadas con Inteligencia Artificial
          </span>
        </h1>

        <p className="mx-auto mt-6 max-w-3xl text-lg text-gray-600 sm:text-xl dark:text-slate-300">
          Conectamos tus almacenes en <strong>Los Ángeles</strong> y <strong>Zaragoza</strong> con las principales redes de transporte multicarrier. Gestión de inventario en tiempo real, selección algorítmica de carrier y logística inversa sin fricción.
        </p>

        <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
          <Link
            href="/dashboard"
            className="rounded-lg bg-blue-600 px-6 py-3 font-medium !text-white transition hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
          >
            Solicitar Propuesta
            <svg className="ml-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </Link>

          <a
            href="#rastreo"
            className="inline-flex items-center justify-center rounded-xl border border-gray-300 bg-white px-7 py-3.5 text-base font-semibold text-gray-800 shadow-sm transition hover:bg-gray-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            <svg className="mr-2 h-5 w-5 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            Probar Demo de Rastreo
          </a>
        </div>

        <div className="mt-16 grid grid-cols-2 gap-6 rounded-2xl border border-gray-200/80 bg-white/70 p-6 shadow-sm backdrop-blur-sm sm:grid-cols-4 dark:border-slate-800 dark:bg-slate-900/60">
          {stats.map((stat) => (
            <div key={stat.label}>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
              <p className="text-gray-500 dark:text-slate-400">{stat.label}</p>
            <div key={stat.label} className="p-2">
              <p className="text-3xl font-extrabold text-blue-600 dark:text-blue-400">{stat.value}</p>
              <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-white">{stat.label}</p>
              {stat.sublabel && (
                <p className="text-xs text-gray-500 dark:text-slate-400">{stat.sublabel}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
