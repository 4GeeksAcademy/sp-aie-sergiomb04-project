import Link from "next/link";

import { ProfileForm } from "@/app/features/auth/components/ProfileForm";

export default function AccountProfilePage() {
  return (
    <main className="min-h-screen bg-slate-100 py-10 px-4">
      <section className="mx-auto w-full max-w-2xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <header className="mb-6">
          <Link href="/" className="text-sm text-blue-700 hover:underline">
            ← Volver al dashboard
          </Link>
          <h1 className="mt-3 text-2xl font-bold text-slate-900">Perfil de usuario</h1>
          <p className="mt-2 text-sm text-slate-600">
            Gestiona tus datos de cuenta en TrackFlow Talent.
          </p>
          <p className="mt-2 text-sm">
            <Link href="/account/change-password" className="text-blue-700 hover:underline">
              Cambiar contraseña
            </Link>
          </p>
        </header>

        <ProfileForm />
      </section>
    </main>
  );
}
