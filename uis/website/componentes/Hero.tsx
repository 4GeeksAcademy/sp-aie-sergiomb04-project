import Link from "next/link";

export type HeroStat = {
  value: string;
  label: string;
};

type HeroProps = {
  stats: HeroStat[];
};

export function Hero({ stats }: HeroProps) {
  return (
    <section aria-labelledby="hero-title" className="bg-gray-100 px-6 py-20">
      <div className="mx-auto max-w-6xl text-center">
        <span className="mb-6 inline-block rounded-full bg-blue-100 px-4 py-1 text-sm font-semibold text-blue-600">
          AI Engineering · Logistica Inteligente
        </span>

        <h1
          id="hero-title"
          className="mb-6 text-4xl leading-tight font-bold text-gray-900 md:text-5xl"
        >
          Bienvenido a <span className="text-blue-600">Track</span>
          <span className="text-gray-800">Flow</span>
        </h1>

        <p className="mx-auto mb-8 max-w-3xl text-lg text-gray-600">
          Impulsamos la logistica de ultima milla para marcas de e-commerce. Desde
          el almacen hasta la puerta del cliente, automatizamos cada paso con
          tecnologia, datos e inteligencia artificial.
        </p>

        <div className="flex flex-col justify-center gap-4 sm:flex-row">
          <Link
            href="/dashboard"
            className="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition hover:bg-blue-700"
          >
            Ir al Dashboard
          </Link>

          <Link
            href="/projects"
            className="rounded-lg border border-gray-300 bg-white px-6 py-3 font-medium transition hover:bg-gray-50"
          >
            Ver Proyectos
          </Link>
        </div>

        <div className="mt-16 grid grid-cols-2 gap-8 text-center md:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label}>
              <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-gray-500">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}