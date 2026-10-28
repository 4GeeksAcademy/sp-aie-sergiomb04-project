import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";

type NavigationItem = {
  label: string;
  href: string;
};

const navigationItems: NavigationItem[] = [
  { label: "Servicios", href: "/#servicios" },
  { label: "Rastreo", href: "/#rastreo" },
  { label: "Operaciones", href: "/#operacion" },
  { label: "Preguntas Frecuentes", href: "/#faq" },
];

const backofficeUrl =
  process.env.NEXT_PUBLIC_BACKOFFICE_URL ||
  process.env.NEXT_PUBLIC_TRACKFLOW_BACKOFFICE_URL ||
  "http://localhost:3001";

export function Navbar() {
  return (
    <header
      role="banner"
      className="sticky top-0 z-50 border-b border-gray-200 bg-white/95 backdrop-blur-md px-6 py-3.5 shadow-sm transition-colors text-blue-600 dark:border-slate-800 dark:bg-slate-900/90"
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-2xl font-bold tracking-tight text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-md"
        >
          <span>Track</span>
          <span className="text-gray-900 dark:text-white">Flow</span>
          <span className="ml-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700 dark:bg-blue-950 dark:text-blue-300">
            Tech
          </span>
        </Link>

        <div className="flex items-center gap-6">
          <nav role="navigation" aria-label="Navegación principal" className="hidden md:block">
            <ul className="flex items-center gap-6 text-sm font-medium text-gray-700 dark:text-slate-200">
              {navigationItems.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="transition hover:text-blue-600 dark:hover:text-blue-400"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <div className="flex items-center gap-3">
            <a
              href={backofficeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:inline-flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50 hover:text-blue-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 dark:hover:text-white"
              title="Acceder al panel de administración y telemetría"
            >
              <span>Backoffice</span>
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>

            <Link
              href="/application"
              className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow transition hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
            >
              Solicitar Propuesta
            </Link>

            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>
  );
}
