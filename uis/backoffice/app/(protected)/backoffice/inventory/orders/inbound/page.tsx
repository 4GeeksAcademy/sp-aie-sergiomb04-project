import { StockEntryFormPanel } from "@/app/features/inventory/components/StockEntryFormPanel";

export default function InventoryInboundOrderPage() {
  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      <StockEntryFormPanel />
    </main>
  );
}
