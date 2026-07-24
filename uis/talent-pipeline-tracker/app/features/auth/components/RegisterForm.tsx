"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useMemo, useState, useTransition } from "react";

import { useAuthSession } from "@/app/features/auth/components/AuthSessionProvider";
import { setSessionToken } from "@/app/features/auth/lib/session";
import { fetchMe, login, register } from "@/app/features/auth/services/auth-api";
import { RegisterPayload, RegisterRequestPayload } from "@/app/features/auth/types/auth";

type RegisterErrors = Partial<Record<keyof RegisterPayload, string>>;

const INITIAL_FORM: RegisterPayload = {
  email: "",
  password: "",
  name: "",
  phone: "",
  address: "",
};

function validateForm(form: RegisterPayload): RegisterErrors {
  const errors: RegisterErrors = {};

  if (!form.email?.trim()) {
    errors.email = "El email es obligatorio";
  }

  if (!form.password?.trim()) {
    errors.password = "La contraseña es obligatoria";
  } else if (form.password.trim().length < 8) {
    errors.password = "La contraseña debe tener al menos 8 caracteres";
  }

  if (form.name?.trim() && form.name.trim().length < 2) {
    errors.name = "El nombre debe tener al menos 2 caracteres";
  }

  return errors;
}

function toRegisterRequestPayload(form: RegisterPayload): RegisterRequestPayload {
  return {
    email: form.email.trim(),
    password: form.password,
    name: form.name?.trim() || "Usuario TrackFlow",
    phone: form.phone?.trim() || "No informado",
    address: form.address?.trim() || "No informada",
  };
}

export function RegisterForm() {
  const router = useRouter();
  const { setUser } = useAuthSession();
  const [isPending, startTransition] = useTransition();
  const [form, setForm] = useState<RegisterPayload>(INITIAL_FORM);
  const [errors, setErrors] = useState<RegisterErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  const hasErrors = useMemo(() => Object.keys(errors).length > 0, [errors]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    const validationErrors = validateForm(form);
    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    const registerPayload = toRegisterRequestPayload(form);

    try {
      await register(registerPayload);

      const loginResponse = await login({
        email: registerPayload.email,
        password: registerPayload.password,
      });

      setSessionToken(loginResponse.access_token);
      const currentUser = await fetchMe();
      setUser(currentUser);

      startTransition(() => {
        router.push("/");
        router.refresh();
      });
    } catch (unknownError: unknown) {
      setSubmitError(
        unknownError instanceof Error ? unknownError.message : "No se pudo completar el registro"
      );
    }
  };

  const handleChange = (field: keyof RegisterPayload, value: string) => {
    setForm((prevState) => ({ ...prevState, [field]: value }));
    setErrors((prevErrors) => {
      if (!prevErrors[field]) {
        return prevErrors;
      }

      const nextErrors = { ...prevErrors };
      delete nextErrors[field];
      return nextErrors;
    });
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
          onChange={(event) => handleChange("email", event.target.value)}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
          placeholder="operator@trackflow.com"
          autoComplete="email"
          required
        />
        {errors.email && <p className="text-xs text-rose-700">{errors.email}</p>}
      </div>

      <div className="space-y-2">
        <label htmlFor="password" className="text-sm font-medium text-slate-700">
          Contraseña
        </label>
        <input
          id="password"
          type="password"
          value={form.password}
          onChange={(event) => handleChange("password", event.target.value)}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
          placeholder="Mínimo 8 caracteres"
          autoComplete="new-password"
          required
        />
        {errors.password && <p className="text-xs text-rose-700">{errors.password}</p>}
      </div>

      <div className="space-y-2">
        <label htmlFor="name" className="text-sm font-medium text-slate-700">
          Nombre (opcional)
        </label>
        <input
          id="name"
          type="text"
          value={form.name}
          onChange={(event) => handleChange("name", event.target.value)}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
          placeholder="Nombre completo"
        />
        {errors.name && <p className="text-xs text-rose-700">{errors.name}</p>}
      </div>

      <div className="space-y-2">
        <label htmlFor="phone" className="text-sm font-medium text-slate-700">
          Teléfono (opcional)
        </label>
        <input
          id="phone"
          type="text"
          value={form.phone}
          onChange={(event) => handleChange("phone", event.target.value)}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
          placeholder="+34 600 000 000"
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="address" className="text-sm font-medium text-slate-700">
          Dirección (opcional)
        </label>
        <input
          id="address"
          type="text"
          value={form.address}
          onChange={(event) => handleChange("address", event.target.value)}
          className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
          placeholder="Calle, ciudad, país"
        />
      </div>

      {submitError && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {submitError}
        </p>
      )}

      <button
        type="submit"
        disabled={isPending || hasErrors}
        className="w-full rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Creando cuenta..." : "Crear cuenta"}
      </button>

      <p className="text-sm text-slate-600">
        ¿Ya tienes cuenta?{" "}
        <Link href="/login" className="font-medium text-slate-900 underline">
          Inicia sesión
        </Link>
      </p>
    </form>
  );
}
