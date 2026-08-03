import { InventoryOrdersHistoryPanel } from "@/app/features/inventory/components/InventoryOrdersHistoryPanel";

export default function InventoryOrdersPage() {
  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      <InventoryOrdersHistoryPanel />
    </main>
  );
}
