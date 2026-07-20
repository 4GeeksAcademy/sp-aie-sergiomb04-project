import { redirect } from "next/navigation";

import { LoginForm } from "@/app/features/auth/components/LoginForm";
import { getCurrentUserFromSession } from "@/app/features/auth/server/current-user";

export default async function LoginPage() {
  const currentUser = await getCurrentUserFromSession();

  if (currentUser) {
    redirect("/");
  }

  return (
    <main className="mx-auto flex min-h-full w-full max-w-7xl flex-1 items-center px-6 py-10 lg:px-10">
      <section className="grid w-full gap-10 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[2rem] bg-slate-950 p-8 text-white shadow-xl lg:p-10">
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-emerald-300">
            TrackFlow backoffice
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight">
            Acceso seguro para operaciones internas
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-slate-300 lg:text-base">
            Inicia sesión para gestionar incidencias, consultar proveedores y operar sobre
            endpoints protegidos con JWT en la API de TrackFlow.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <article className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-sm font-medium text-white">Suppliers</p>
              <p className="mt-2 text-sm text-slate-300">
                Altas, estados y tarifas protegidas por autenticación.
              </p>
            </article>
            <article className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-sm font-medium text-white">Incidencias</p>
              <p className="mt-2 text-sm text-slate-300">
                Análisis CSV y exportación solo para usuarios autorizados.
              </p>
            </article>
          </div>
        </div>

        <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm lg:p-10">
          <div className="mb-8">
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">
              Iniciar sesión
            </p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">
              Accede al panel interno
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Usa tu email y contraseña registrados en la API de TrackFlow.
            </p>
          </div>

          <LoginForm />
        </div>
      </section>
    </main>
  );
}