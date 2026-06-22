import { pathToFileURL } from "node:url";

import type { Carrier, Product, Shipment } from "./types/models.js";
import {
  filterLowStockProducts,
  filterProductsByCategory,
  filterProductsByWarehouse,
  sortCarriersByReliability,
  sortProductsByStock
} from "./utils/collections.js";
import {
  binarySearchProductByWeight,
  findProductBySKU,
  findShipmentById
} from "./utils/search.js";
import {
  calculateAverageShipmentDistance,
  calculateShippingCost,
  calculateTotalInventoryValue,
  countProductsByCategory,
  findTopCarriers,
  groupShipmentsByStatus,
  scoreCarrierForShipment,
  selectBestCarrier
} from "./utils/transformations.js";
import { validateCarrier, validateProduct, validateShipment } from "./utils/validations.js";

const sampleProducts: Product[] = [
  {
    sku: "SHOE-BLK-42",
    name: "Zapatillas Negras Running - Talla 42",
    category: "Fashion",
    weightKg: 0.8,
    dimensions: { lengthCm: 35, widthCm: 22, heightCm: 12 },
    warehouse: "Los Angeles",
    stockQuantity: 45,
    minStockThreshold: 20,
    unitCostUSD: 35,
    isFragile: false,
    status: "Active"
  },
  {
    sku: "LAPTOP-DELL-15",
    name: "Laptop Dell 15 pulgadas",
    category: "Electronics",
    weightKg: 2.3,
    dimensions: { lengthCm: 40, widthCm: 28, heightCm: 3 },
    warehouse: "Zaragoza",
    stockQuantity: 8,
    minStockThreshold: 10,
    unitCostUSD: 650,
    isFragile: true,
    status: "Low stock"
  },
  {
    sku: "PERFUME-COCO-50",
    name: "Perfume Coco 50ml",
    category: "Cosmetics",
    weightKg: 0.3,
    dimensions: { lengthCm: 12, widthCm: 8, heightCm: 15 },
    warehouse: "Los Angeles",
    stockQuantity: 120,
    minStockThreshold: 30,
    unitCostUSD: 85,
    isFragile: true,
    status: "Active"
  }
];

const sampleCarriers: Carrier[] = [
  {
    id: "CAR-UPS",
    name: "UPS",
    operatesIn: ["United States"],
    baseRateUSD: 5,
    ratePerKgUSD: 1.2,
    ratePerKmUSD: 0.05,
    avgDeliveryDays: 3,
    onTimeRate: 88,
    maxWeightKg: 30,
    handlesFragile: true,
    acceptsPriority: ["Standard", "Express"]
  },
  {
    id: "CAR-SEUR",
    name: "SEUR",
    operatesIn: ["Spain"],
    baseRateUSD: 6.5,
    ratePerKgUSD: 1.5,
    ratePerKmUSD: 0.08,
    avgDeliveryDays: 2,
    onTimeRate: 92,
    maxWeightKg: 25,
    handlesFragile: true,
    acceptsPriority: ["Standard", "Express", "Same-day"]
  },
  {
    id: "CAR-DHL",
    name: "DHL Express",
    operatesIn: ["United States", "Spain"],
    baseRateUSD: 12,
    ratePerKgUSD: 2,
    ratePerKmUSD: 0.1,
    avgDeliveryDays: 1,
    onTimeRate: 95,
    maxWeightKg: 50,
    handlesFragile: true,
    acceptsPriority: ["Express", "Same-day"]
  }
];

const sampleShipment: Shipment = {
  id: "SH-2024-8821",
  sku: "LAPTOP-DELL-15",
  quantity: 1,
  origin: "Zaragoza",
  destination: {
    city: "Madrid",
    country: "Spain",
    postalCode: "28001",
    distanceKm: 320
  },
  priority: "Express",
  declaredValueUSD: 650,
  carrier: null,
  status: "Pending",
  createdAt: new Date("2024-03-15")
};

const extraShipments: Shipment[] = [
  sampleShipment,
  {
    id: "SH-2024-8822",
    sku: "SHOE-BLK-42",
    quantity: 2,
    origin: "Los Angeles",
    destination: {
      city: "San Diego",
      country: "United States",
      postalCode: "92101",
      distanceKm: 195
    },
    priority: "Standard",
    declaredValueUSD: 70,
    carrier: "UPS",
    status: "Assigned",
    createdAt: new Date("2024-03-16")
  },
  {
    id: "SH-2024-8823",
    sku: "PERFUME-COCO-50",
    quantity: 1,
    origin: "Los Angeles",
    destination: {
      city: "Valencia",
      country: "Spain",
      postalCode: "46001",
      distanceKm: 900
    },
    priority: "Same-day",
    declaredValueUSD: 85,
    carrier: "DHL Express",
    status: "In transit",
    createdAt: new Date("2024-03-17")
  }
];

const laptop = findProductBySKU(sampleProducts, sampleShipment.sku);

const sortedProductsByStock = sortProductsByStock(sampleProducts, "asc");
const topCarriers = findTopCarriers(extraShipments, 2);
const shipmentsByStatus = groupShipmentsByStatus(extraShipments);
const categoryCounts = countProductsByCategory(sampleProducts);
const inventoryValue = calculateTotalInventoryValue(sampleProducts);
const averageShipmentDistance = calculateAverageShipmentDistance(extraShipments);
const lowStockProducts = filterLowStockProducts(sampleProducts);
const reliableCarriers = sortCarriersByReliability(sampleCarriers, "desc");

export const businessLogicSnapshot = {
  productsInLosAngeles: filterProductsByWarehouse(sampleProducts, "Los Angeles"),
  electronicsProducts: filterProductsByCategory(sampleProducts, "Electronics"),
  lowStockProducts,
  sortedProductsByStock,
  reliableCarriers,
  productSearchResult: findProductBySKU(sampleProducts, "laptop-dell-15"),
  shipmentSearchResult: findShipmentById(extraShipments, "SH-2024-8822"),
  weightSearchResult: binarySearchProductByWeight(
    [...sampleProducts].sort((a, b) => a.weightKg - b.weightKg),
    2.3
  ),
  costWithSeur: laptop
    ? calculateShippingCost(sampleShipment, laptop, sampleCarriers[1])
    : null,
  scoreSeur: laptop
    ? scoreCarrierForShipment(sampleCarriers[1], sampleShipment, laptop)
    : null,
  bestCarrier: laptop
    ? selectBestCarrier(sampleCarriers, sampleShipment, laptop)
    : null,
  categoryCounts,
  inventoryValue,
  averageShipmentDistance,
  shipmentsByStatus,
  topCarriers,
  productValidation: validateProduct(sampleProducts[0]),
  shipmentValidation: validateShipment(sampleShipment),
  carrierValidation: validateCarrier(sampleCarriers[0])
} as const;

export function logBusinessLogicDemo() {
  console.log("Productos en Los Angeles:", filterProductsByWarehouse(sampleProducts, "Los Angeles"));
  console.log("Productos de Electronics:", filterProductsByCategory(sampleProducts, "Electronics"));
  console.log("Productos con stock bajo:", lowStockProducts);
  console.log("Productos por stock asc:", sortedProductsByStock);
  console.log("Transportistas por confiabilidad desc:", reliableCarriers);
  console.log("Buscar producto por SKU:", findProductBySKU(sampleProducts, "laptop-dell-15"));
  console.log("Buscar envío por ID:", findShipmentById(extraShipments, "SH-2024-8822"));
  console.log(
    "Búsqueda binaria por peso:",
    binarySearchProductByWeight([...sampleProducts].sort((a, b) => a.weightKg - b.weightKg), 2.3)
  );

  if (laptop) {
    console.log("Costo con SEUR:", calculateShippingCost(sampleShipment, laptop, sampleCarriers[1]));
    console.log("Score SEUR:", scoreCarrierForShipment(sampleCarriers[1], sampleShipment, laptop));
    console.log("Mejor transportista:", selectBestCarrier(sampleCarriers, sampleShipment, laptop));
  }

  console.log("Conteo por categoría:", categoryCounts);
  console.log("Valor total inventario:", inventoryValue);
  console.log("Distancia promedio de envíos:", averageShipmentDistance);
  console.log("Envíos agrupados por estado:", shipmentsByStatus);
  console.log("Top carriers:", topCarriers);
  console.log("Validación producto:", validateProduct(sampleProducts[0]));
  console.log("Validación envío:", validateShipment(sampleShipment));
  console.log("Validación carrier:", validateCarrier(sampleCarriers[0]));
}

const isDirectExecution =
  typeof process !== "undefined" &&
  Boolean(process.argv[1]) &&
  import.meta.url === pathToFileURL(process.argv[1]).href;

if (isDirectExecution) {
  logBusinessLogicDemo();
}
