import Link from "next/link";

import { LogoutButton } from "@/app/features/auth/components/LogoutButton";
import { requireAuthenticatedUser } from "@/app/features/auth/server/current-user";

export default async function ProtectedLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const currentUser = await requireAuthenticatedUser();

  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-slate-200 bg-white/95 px-6 py-4 backdrop-blur lg:px-10">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center justify-between gap-6">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">
                TrackFlow
              </p>
              <p className="text-lg font-semibold text-slate-950">Backoffice</p>
            </div>

            <nav className="hidden items-center gap-3 text-sm font-medium text-slate-600 md:flex">
              <Link href="/" className="rounded-lg px-3 py-2 hover:bg-slate-100">
                Dashboard
              </Link>
              <Link href="/incidents" className="rounded-lg px-3 py-2 hover:bg-slate-100">
                Incidencias
              </Link>
              <Link href="/suppliers" className="rounded-lg px-3 py-2 hover:bg-slate-100">
                Suppliers
              </Link>
            </nav>
          </div>

          <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-slate-900">{currentUser.profile.name || currentUser.email}</p>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                {currentUser.role}
              </p>
            </div>
            <LogoutButton />
          </div>
        </div>

        <nav className="mt-4 flex items-center gap-2 text-sm font-medium text-slate-600 md:hidden">
          <Link href="/" className="rounded-lg px-3 py-2 hover:bg-slate-100">
            Dashboard
          </Link>
          <Link href="/incidents" className="rounded-lg px-3 py-2 hover:bg-slate-100">
            Incidencias
          </Link>
          <Link href="/suppliers" className="rounded-lg px-3 py-2 hover:bg-slate-100">
            Suppliers
          </Link>
        </nav>
      </header>

      <div className="mx-auto flex w-full max-w-7xl flex-1">{children}</div>
    </div>
  );
}