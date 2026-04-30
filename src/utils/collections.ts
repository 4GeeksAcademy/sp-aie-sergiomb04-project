import type { Carrier, Product, ProductCategory, WarehouseLocation } from "../types/models.js";

export function filterProductsByWarehouse(
  products: Product[],
  warehouse: WarehouseLocation
): Product[] {
  return products.filter((product) => product.warehouse === warehouse);
}

export function filterProductsByCategory(
  products: Product[],
  category: ProductCategory
): Product[] {
  return products.filter((product) => product.category === category);
}

export function filterLowStockProducts(products: Product[]): Product[] {
  return products.filter((product) => product.stockQuantity <= product.minStockThreshold);
}

export function sortProductsByStock(products: Product[], order: "asc" | "desc"): Product[] {
  // Multiplicador evita duplicar lógica para asc/desc.
  const multiplier = order === "asc" ? 1 : -1;

  // Copia defensiva para no mutar el array original.
  return [...products].sort(
    (left, right) => (left.stockQuantity - right.stockQuantity) * multiplier
  );
}

export function sortCarriersByReliability(
  carriers: Carrier[],
  order: "asc" | "desc"
): Carrier[] {
  const multiplier = order === "asc" ? 1 : -1;

  // Mismo patrón que productos: orden estable sobre copia.
  return [...carriers].sort((left, right) => (left.onTimeRate - right.onTimeRate) * multiplier);
}
