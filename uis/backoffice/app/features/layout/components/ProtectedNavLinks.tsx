import Link from "next/link";

type ProtectedNavLinksProps = {
  mobile?: boolean;
};

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/incidents", label: "Incidencias" },
  { href: "/suppliers", label: "Suppliers" },
  { href: "/backoffice/inventory/products", label: "Inventory" },
  { href: "/telemetry", label: "Telemetría" },
  { href: "/reporting", label: "Reportes" },
];

export function ProtectedNavLinks({ mobile = false }: ProtectedNavLinksProps) {
  return (
    <nav
      className={[
        "items-center gap-3 text-sm font-medium text-slate-600",
        mobile ? "mt-4 flex gap-2 md:hidden" : "hidden md:flex",
      ].join(" ")}
      aria-label={mobile ? "Navegacion principal movil" : "Navegacion principal"}
    >
      {navItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          prefetch={false}
          className="rounded-lg px-3 py-2 hover:bg-slate-100"
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
