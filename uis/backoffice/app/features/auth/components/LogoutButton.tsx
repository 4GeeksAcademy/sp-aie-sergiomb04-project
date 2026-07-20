"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

export function LogoutButton() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const handleLogout = async () => {
    setError(null);

    try {
      await fetch("/api/auth/logout", {
        method: "POST",
      });

      startTransition(() => {
        router.push("/login");
        router.refresh();
      });
    } catch {
      setError("No se pudo cerrar la sesión");
    }
  };

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        type="button"
        onClick={handleLogout}
        disabled={isPending}
        className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Saliendo..." : "Cerrar sesión"}
      </button>

      {error && <p className="text-xs text-rose-600">{error}</p>}
    </div>
  );
}