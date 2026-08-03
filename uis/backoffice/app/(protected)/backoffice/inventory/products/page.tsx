import { InventoryProductsPanel } from "@/app/features/inventory/components/InventoryProductsPanel";

export default function InventoryProductsPage() {
  return (
    <main className="flex flex-1 flex-col gap-8 px-6 py-10 lg:px-10">
      <InventoryProductsPanel />
    </main>
  );
}
