import { Suspense } from "react";
import { StockExitFormPanel } from "@/app/features/inventory/components/StockExitFormPanel";

export default function InventoryOutboundOrderPage() {
  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      <Suspense fallback={<div className="py-6 text-center text-sm text-slate-500">Cargando formulario...</div>}>
        <StockExitFormPanel />
      </Suspense>
    </main>
  );
}
