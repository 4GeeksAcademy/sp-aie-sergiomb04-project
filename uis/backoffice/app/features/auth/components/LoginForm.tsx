"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { AuthUser, LoginPayload } from "@/app/features/auth/types/auth";

type LoginError = {
  detail?: string;
  error?: string;
};

const INITIAL_FORM: LoginPayload = {
  email: "",
  password: "",
};

export function LoginForm() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [form, setForm] = useState<LoginPayload>(INITIAL_FORM);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as LoginError | null;
        setError(payload?.detail ?? payload?.error ?? "No se pudo iniciar sesion");
        return;
      }

      await response.json().catch(() => null as AuthUser | null);

      startTransition(() => {
        router.push("/");
        router.refresh();
      });
    } catch {
      setError("No se pudo conectar con el servicio de autenticacion");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-2">
        <label htmlFor="email" className="text-sm font-medium text-slate-700">
          Email
        </label>
        <input
          id="email"
          type="email"
          value={form.email}
          onChange={(event) => setForm((prevState) => ({ ...prevState, email: event.target.value }))}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
          placeholder="operator@trackflow.com"
          autoComplete="email"
          required
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="password" className="text-sm font-medium text-slate-700">
          Contraseña
        </label>
        <input
          id="password"
          type="password"
          value={form.password}
          onChange={(event) =>
            setForm((prevState) => ({ ...prevState, password: event.target.value }))
          }
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
          placeholder="Introduce tu contraseña"
          autoComplete="current-password"
          required
        />
      </div>

      {error && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={isPending}
        className="w-full rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Accediendo..." : "Iniciar sesión"}
      </button>
    </form>
  );
}