function roundTo2(value) {
    // Redondeo centralizado para consistencia en costos y scores.
    return Math.round(value * 100) / 100;
}
function getPriorityMultiplier(priority) {
    // Mapeo explícito de prioridad -> recargo.
    if (priority === "Express") {
        return 1.3;
    }
    if (priority === "Same-day") {
        return 1.6;
    }
    return 1;
}
export function calculateShippingCost(shipment, product, carrier) {
    // Fórmula desglosada por componentes para facilitar auditoría.
    const baseCost = carrier.baseRateUSD;
    const weightCost = product.weightKg * carrier.ratePerKgUSD * shipment.quantity;
    const distanceCost = shipment.destination.distanceKm * carrier.ratePerKmUSD;
    const rawTotal = (baseCost + weightCost + distanceCost) * getPriorityMultiplier(shipment.priority);
    return roundTo2(rawTotal);
}
export function scoreCarrierForShipment(carrier, shipment, product) {
    // Score acumulativo según reglas de negocio (máximo 100).
    let score = 0;
    const totalWeight = product.weightKg * shipment.quantity;
    if (carrier.operatesIn.includes(shipment.destination.country)) {
        score += 20;
    }
    if (totalWeight <= carrier.maxWeightKg) {
        score += 20;
    }
    if (carrier.acceptsPriority.includes(shipment.priority)) {
        score += 15;
    }
    if (!product.isFragile || carrier.handlesFragile) {
        score += 15;
    }
    score += carrier.onTimeRate * 0.3;
    return roundTo2(score);
}
export function selectBestCarrier(carriers, shipment, product) {
    // Selección por costo mínimo entre carriers aceptables (score >= 50).
    let best = null;
    for (const carrier of carriers) {
        const score = scoreCarrierForShipment(carrier, shipment, product);
        if (score < 50) {
            continue;
        }
        const cost = calculateShippingCost(shipment, product, carrier);
        // Desempate: a igual costo, priorizamos mayor score.
        if (!best || cost < best.cost || (cost === best.cost && score > best.score)) {
            best = { carrier, score, cost };
        }
    }
    return best;
}
export function countProductsByCategory(products) {
    const counts = {
        Fashion: 0,
        Electronics: 0,
        Cosmetics: 0,
        Home: 0,
        Other: 0
    };
    for (const product of products) {
        counts[product.category] += 1;
    }
    return counts;
}
export function calculateTotalInventoryValue(products) {
    const total = products.reduce((acc, product) => {
        return acc + product.stockQuantity * product.unitCostUSD;
    }, 0);
    return roundTo2(total);
}
export function calculateAverageShipmentDistance(shipments) {
    if (shipments.length === 0) {
        return 0;
    }
    const totalDistance = shipments.reduce((acc, shipment) => {
        return acc + shipment.destination.distanceKm;
    }, 0);
    return roundTo2(totalDistance / shipments.length);
}
export function groupShipmentsByStatus(shipments) {
    // Inicializamos todas las claves para mantener shape estable en UI/reportes.
    const grouped = {
        Pending: [],
        Assigned: [],
        "In transit": [],
        Delivered: [],
        Failed: []
    };
    for (const shipment of shipments) {
        grouped[shipment.status].push(shipment);
    }
    return grouped;
}
export function findTopCarriers(shipments, topN) {
    if (topN <= 0) {
        return [];
    }
    // Diccionario simple carrier -> cantidad de usos.
    const counter = {};
    for (const shipment of shipments) {
        if (!shipment.carrier) {
            continue;
        }
        counter[shipment.carrier] = (counter[shipment.carrier] ?? 0) + 1;
    }
    return Object.entries(counter)
        .map(([carrier, count]) => ({ carrier, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, topN);
}
