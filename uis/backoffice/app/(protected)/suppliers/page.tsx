import dynamic from "next/dynamic";

const SuppliersPanel = dynamic(
  () => import("@/app/features/suppliers/components/SuppliersPanel").then((mod) => mod.SuppliersPanel),
  {
    loading: () => (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-500">Cargando módulo de proveedores...</p>
      </section>
    ),
  }
);

export default function SuppliersPage() {
  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      <SuppliersPanel />
    </main>
  );
}