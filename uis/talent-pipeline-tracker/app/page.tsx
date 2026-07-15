export default function Home() {
  return (
    <main className="flex min-h-screen flex-1 items-center justify-center bg-zinc-50 px-4">
      <section className="w-full max-w-2xl rounded-2xl border border-zinc-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-zinc-900">Modulo migrado</h1>
        <p className="mt-3 text-zinc-700">
          La logica de candidaturas ya no vive en este frontend.
        </p>
        <p className="mt-2 text-zinc-700">
          El modulo de incidents se gestiona desde la app de backoffice.
        </p>
      </section>
    </main>
  );
}
