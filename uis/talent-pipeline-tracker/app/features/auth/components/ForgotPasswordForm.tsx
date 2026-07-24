"use client";

import Link from "next/link";
import React, { useState } from "react";

import { forgotPassword } from "@/app/features/auth/services/auth-api";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting || submitted) {
      return;
    }

    setIsSubmitting(true);
    setMessage(null);

    try {
      const response = await forgotPassword({ email: email.trim() });
      setSubmitted(true);
      setMessage(response.detail);
    } catch {
      // Mismo mensaje para no revelar si el email existe o no.
      setSubmitted(true);
      setMessage("Si esa direccion esta registrada, recibiras un enlace en breve.");
    } finally {
      setIsSubmitting(false);
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
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
          placeholder="operator@trackflow.com"
          autoComplete="email"
          required
          disabled={submitted || isSubmitting}
        />
      </div>

      {message && (
        <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {message}
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting || submitted}
        className="w-full rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "Enviando..." : "Enviar enlace de recuperación"}
      </button>

      <p className="text-sm text-slate-600">
        <Link href="/login" className="font-medium text-slate-900 underline">
          Volver a iniciar sesión
        </Link>
      </p>
    </form>
  );
}
