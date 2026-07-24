import { ForgotPasswordForm } from "@/app/features/auth/components/ForgotPasswordForm";

export default function ForgotPasswordPage() {
  return (
    <main className="min-h-screen bg-slate-100 py-10 px-4">
      <section className="mx-auto w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <header className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            TrackFlow Talent
          </p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">Recuperar contraseña</h1>
          <p className="mt-2 text-sm text-slate-600">
            Te enviaremos un enlace para restablecer tu acceso.
          </p>
        </header>

        <ForgotPasswordForm />
      </section>
    </main>
  );
}
