export type WarehouseLocation = "Los Angeles" | "Zaragoza";

export type ProductStatus = "Active" | "Low stock" | "Out of stock" | "Discounted";

export type ProductCategory = "Fashion" | "Electronics" | "Cosmetics" | "Home" | "Other";

export interface Dimensions {
    lengthCm: number,
    widthCm: number,
    heightCm: number;
}

export interface Product {
    // SKU = identificador operativo para inventario y envíos
    sku: string;
    name: string;
    category: ProductCategory;
    weightKg: number;
    dimensions: Dimensions;
    warehouse: WarehouseLocation;
    stockQuantity: number;
    // umbral mínimo de stock (parametro útil para logistica)
    minStockThreshold: number;
    unitCostUSD: number;
    isFragile: boolean,
    status: ProductStatus;
}

export type Country = "United States" | "Spain";

export interface Destination {
    city: string,
    country: Country;
    postalCode: string;
    distanceKm: number;
}

export type ShipmentPriority = "Standard" | "Express" | "Same-day";

export type ShipmentStatus = "Pending" | "Assigned" | "In transit" | "Delivered" | "Failed"

export interface Shipment {
    id: string;
    // SKU relacionado con Product.sku sin duplicar producto (Solo ID del producto)
    sku: string;
    quantity: number;
    origin: WarehouseLocation;
    destination: Destination;
    priority: ShipmentPriority;
    declaredValueUSD: number;
    // Valor = null si no está aún establecido (Relacionado con Carrier.id)
    carrier: string | null;
    status: ShipmentStatus;
    createdAt: Date;
}

export interface Carrier {
    id: string;
    name: string;
    operatesIn: Country[];
    baseRateUSD: number;
    ratePerKgUSD: number;
    ratePerKmUSD: number;
    avgDeliveryDays: number;
    onTimeRate: number;
    maxWeightKg: number;
    // Capacidades declarativas para selección automática de carrier.
    handlesFragile: boolean;
    acceptsPriority: ShipmentPriority[];
}

export type MovementType = "Inbound" | "Outbound" | "Transfer" | "Adjustment";

export interface InventoryMovement {
    id: string;
    sku: string;
    warehouse: WarehouseLocation;
    type: MovementType;
    quantity: number;
    reason: string;
    timestamp: Date;
}

export interface ValidationReport {
  // Estructura estándar de salida para todas las validaciones.
  valid: boolean;
  errors: string[];
}