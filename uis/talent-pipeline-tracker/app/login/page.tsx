import { LoginForm } from "@/app/features/auth/components/LoginForm";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-slate-100 py-10 px-4">
      <section className="mx-auto w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <header className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            TrackFlow Talent
          </p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">Inicia sesión</h1>
          <p className="mt-2 text-sm text-slate-600">
            Accede al panel interno de gestión de candidaturas.
          </p>
        </header>

        <LoginForm />
      </section>
    </main>
  );
}
