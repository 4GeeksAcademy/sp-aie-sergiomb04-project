import { RegisterForm } from "@/app/features/auth/components/RegisterForm";

export default function RegisterPage() {
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">
      <section className="mx-auto w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <header className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            TrackFlow backoffice
          </p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">Crear cuenta</h1>
          <p className="mt-2 text-sm text-slate-600">
            Registra un usuario para acceder al panel interno.
          </p>
        </header>

        <RegisterForm />
      </section>
    </main>
  );
}
