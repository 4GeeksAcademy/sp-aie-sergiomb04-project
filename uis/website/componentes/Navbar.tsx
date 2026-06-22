"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

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
  const pathname = usePathname();

  return (
    <header
      role="banner"
      className="flex flex-col gap-4 bg-white px-6 py-4 shadow-md md:flex-row md:items-center md:justify-between text-blue-600"
    >
      <Link href="/" className="text-2xl font-bold tracking-wide">
        Track<span className="text-gray-800">Flow</span>
      </Link>

      <nav role="navigation" aria-label="Navegacion principal">
        <ul className="flex flex-wrap items-center gap-4 md:gap-6 text-gray-800">
          {navigationItems.map((item) => {
            const isCurrent = pathname === item.href;

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={isCurrent ? "page" : undefined}
                  className={[
                    "transition hover:text-blue-600",
                    isCurrent ? "font-medium text-blue-600" : "text-gray-700",
                  ].join(" ")}
                >
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}