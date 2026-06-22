export function findProductBySKU(products, sku) {
    // Normalizamos para permitir búsqueda case-insensitive. (Que siempre sea strings en minuscula para que busque bien)
    const normalizedTarget = sku.trim().toLowerCase();
    for (const product of products) {
        if (product.sku.toLowerCase() === normalizedTarget) {
            return product;
        }
    }
    return null;
}
export function findShipmentById(shipments, id) {
    for (const shipment of shipments) {
        if (shipment.id === id) {
            return shipment;
        }
    }
    return null;
}
export function binarySearchProductByWeight(sortedProducts, targetWeight) {
    // Requiere entrada preordenada por weightKg ascendente.
    let left = 0;
    let right = sortedProducts.length - 1;
    while (left <= right) {
        // División entera para mantener índices válidos.
        const middle = Math.floor((left + right) / 2);
        const currentWeight = sortedProducts[middle].weightKg;
        if (currentWeight === targetWeight) {
            return middle;
        }
        if (currentWeight < targetWeight) {
            left = middle + 1;
        }
        else {
            right = middle - 1;
        }
    }
    return -1;
}
