"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import React, { useMemo, useState } from "react";

import { resetPassword } from "@/app/features/auth/services/auth-api";

export function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const token = useMemo(() => searchParams.get("token") ?? "", [searchParams]);

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!token) {
      setError("El enlace no es válido. Solicita uno nuevo.");
      return;
    }

    if (newPassword.trim().length < 8) {
      setError("La nueva contraseña debe tener al menos 8 caracteres");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }

    setIsSubmitting(true);
    try {
      await resetPassword({ token, new_password: newPassword });
      setSuccess("Contraseña actualizada. Redirigiendo al login...");
      setTimeout(() => {
        router.push("/login");
      }, 1200);
    } catch (unknownError: unknown) {
      setError(
        unknownError instanceof Error
          ? unknownError.message
          : "No se pudo restablecer la contraseña"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-2">
        <label htmlFor="new-password" className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Nueva contraseña
        </label>
        <input
          id="new-password"
          type="password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:placeholder:text-slate-500 dark:focus:border-slate-400"
          placeholder="Mínimo 8 caracteres"
          autoComplete="new-password"
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="confirm-password" className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Confirmar contraseña
        </label>
        <input
          id="confirm-password"
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:placeholder:text-slate-500 dark:focus:border-slate-400"
          placeholder="Repite la contraseña"
          autoComplete="new-password"
          required
          disabled={isSubmitting}
        />
      </div>

      {error && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300">
          {error}
        </p>
      )}

      {success && (
        <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-300">
          {success}
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-100"
      >
        {isSubmitting ? "Actualizando..." : "Restablecer contraseña"}
      </button>

      <p className="text-sm text-slate-600 dark:text-slate-400">
        ¿No tienes un enlace válido?{" "}
        <Link href="/forgot-password" className="font-medium text-slate-900 underline dark:text-slate-200">
          Solicitar nuevo enlace
        </Link>
      </p>
    </form>
  );
}
