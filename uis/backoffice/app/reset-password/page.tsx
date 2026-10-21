import { Suspense } from "react";
import { ResetPasswordForm } from "@/app/features/auth/components/ResetPasswordForm";
import { ThemeToggle } from "@/app/features/layout/components/ThemeToggle";

export default function ResetPasswordPage() {
  return (
    <main className="relative min-h-screen bg-slate-100 px-4 py-10 dark:bg-slate-950">
      <div className="absolute top-6 right-6">
        <ThemeToggle />
      </div>
      <section className="mx-auto w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <header className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            TrackFlow backoffice
          </p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">Restablecer contraseña</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Introduce tu nueva contraseña para recuperar el acceso.
          </p>
        </header>

        <Suspense fallback={<div className="py-4 text-center text-sm text-slate-500 dark:text-slate-400">Cargando formulario...</div>}>
          <ResetPasswordForm />
        </Suspense>
      </section>
    </main>
  );
}
