"use client";

import { useEffect, useState } from "react";

import { useAuthSession } from "@/app/features/auth/components/AuthSessionProvider";
import { fetchMe, updateMyProfile } from "@/app/features/auth/services/auth-api";

type ProfileFormState = {
  name: string;
  phone: string;
  address: string;
};

export function ProfileForm() {
  const { user, setUser, logout } = useAuthSession();
  const [form, setForm] = useState<ProfileFormState>({
    name: "",
    phone: "",
    address: "",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const loadProfile = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const me = await fetchMe();
        setUser(me);
        setForm({
          name: me.profile.name,
          phone: me.profile.phone,
          address: me.profile.address,
        });
      } catch (unknownError: unknown) {
        setError(
          unknownError instanceof Error
            ? unknownError.message
            : "No se pudo cargar el perfil"
        );
      } finally {
        setIsLoading(false);
      }
    };

    void loadProfile();
  }, [setUser]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!form.name.trim() || !form.phone.trim() || !form.address.trim()) {
      setError("Nombre, teléfono y dirección son obligatorios");
      return;
    }

    setIsSaving(true);
    try {
      const updatedProfile = await updateMyProfile({
        name: form.name.trim(),
        phone: form.phone.trim(),
        address: form.address.trim(),
      });

      if (user) {
        setUser({ ...user, profile: updatedProfile });
      }

      setForm({
        name: updatedProfile.name,
        phone: updatedProfile.phone,
        address: updatedProfile.address,
      });

      setSuccess("Perfil actualizado correctamente");
    } catch (unknownError: unknown) {
      setError(
        unknownError instanceof Error
          ? unknownError.message
          : "No se pudo actualizar el perfil"
      );
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <p className="text-sm text-slate-600">Cargando perfil...</p>;
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-sm text-slate-600">Email</p>
        <p className="text-base font-semibold text-slate-900">{user?.email ?? "No disponible"}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="name" className="text-sm font-medium text-slate-700">
            Nombre
          </label>
          <input
            id="name"
            type="text"
            value={form.name}
            onChange={(event) => setForm((prevState) => ({ ...prevState, name: event.target.value }))}
            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
            required
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="phone" className="text-sm font-medium text-slate-700">
            Teléfono
          </label>
          <input
            id="phone"
            type="text"
            value={form.phone}
            onChange={(event) => setForm((prevState) => ({ ...prevState, phone: event.target.value }))}
            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
            required
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="address" className="text-sm font-medium text-slate-700">
            Dirección
          </label>
          <input
            id="address"
            type="text"
            value={form.address}
            onChange={(event) => setForm((prevState) => ({ ...prevState, address: event.target.value }))}
            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-slate-500"
            required
          />
        </div>

        {error && (
          <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </p>
        )}

        {success && (
          <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {success}
          </p>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={isSaving}
            className="rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSaving ? "Guardando..." : "Guardar cambios"}
          </button>

          <button
            type="button"
            onClick={logout}
            className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-800"
          >
            Cerrar sesión
          </button>
        </div>
      </form>
    </div>
  );
}
