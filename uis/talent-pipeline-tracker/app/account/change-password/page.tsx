import Link from "next/link";

import { ChangePasswordForm } from "@/app/features/auth/components/ChangePasswordForm";

export default function AccountChangePasswordPage() {
  return (
    <main className="min-h-screen bg-slate-100 py-10 px-4">
      <section className="mx-auto w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <header className="mb-6 space-y-2">
          <Link href="/account/profile" className="text-sm text-blue-700 hover:underline">
            ← Volver al perfil
          </Link>
          <h1 className="text-2xl font-bold text-slate-900">Cambiar contraseña</h1>
          <p className="text-sm text-slate-600">
            Actualiza tu contraseña para mantener segura tu cuenta.
          </p>
        </header>

        <ChangePasswordForm />
      </section>
    </main>
  );
}
