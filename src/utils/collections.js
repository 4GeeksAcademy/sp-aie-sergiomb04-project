export function filterProductsByWarehouse(products, warehouse) {
    return products.filter((product) => product.warehouse === warehouse);
}
export function filterProductsByCategory(products, category) {
    return products.filter((product) => product.category === category);
}
export function filterLowStockProducts(products) {
    return products.filter((product) => product.stockQuantity <= product.minStockThreshold);
}
export function sortProductsByStock(products, order) {
    // Multiplicador evita duplicar lógica para asc/desc.
    const multiplier = order === "asc" ? 1 : -1;
    // Copia defensiva para no mutar el array original.
    return [...products].sort((left, right) => (left.stockQuantity - right.stockQuantity) * multiplier);
}
export function sortCarriersByReliability(carriers, order) {
    const multiplier = order === "asc" ? 1 : -1;
    // Mismo patrón que productos: orden estable sobre copia.
    return [...carriers].sort((left, right) => (left.onTimeRate - right.onTimeRate) * multiplier);
}
