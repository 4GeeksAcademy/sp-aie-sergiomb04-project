import Link from "next/link";
import { ThemeToggle } from "./ThemeToggle";

type NavigationItem = {
  label: string;
  href: string;
};

const navigationItems: NavigationItem[] = [
  { label: "Inicio", href: "/" },
  { label: "Proyectos", href: "/projects" },
  { label: "Tareas", href: "/tasks" },
  { label: "Reportes", href: "/reports" },
  { label: "Inscribirse", href: "/application" },
];

export function Navbar() {
  return (
    <header
      role="banner"
      className="flex flex-col gap-4 bg-white px-6 py-4 shadow-md md:flex-row md:items-center md:justify-between text-blue-600 dark:bg-slate-900 dark:border-b dark:border-slate-800"
    >
      <Link href="/" className="text-2xl font-bold tracking-wide">
        Track<span className="text-gray-800 dark:text-white">Flow</span>
      </Link>

      <div className="flex items-center justify-between gap-4">
        <nav role="navigation" aria-label="Navegacion principal">
          <ul className="flex flex-wrap items-center gap-4 md:gap-6 text-gray-800 dark:text-slate-200">
            {navigationItems.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  prefetch={false}
                  className="text-gray-700 transition hover:text-blue-600 dark:text-slate-300 dark:hover:text-blue-400"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <ThemeToggle />
      </div>
    </header>
  );
}
