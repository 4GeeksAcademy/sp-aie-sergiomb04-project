export const VALID_CATEGORIES = [
  "carrier_last_mile",
  "carrier_international",
  "warehouse_supplies",
  "packaging_materials",
  "reverse_logistics",
  "fleet_maintenance",
  "it_and_wms_software",
  "cleaning_and_facilities",
] as const;

export const VALID_STATUSES = ["active", "suspended"] as const;

export type SupplierCategory = (typeof VALID_CATEGORIES)[number];
export type SupplierStatus = (typeof VALID_STATUSES)[number];
export type SupplierCountry = "USA" | "Spain";
export type SupplierCurrency = "USD" | "EUR";

export type Supplier = {
  id: string;
  name: string;
  country: SupplierCountry;
  categories: SupplierCategory[];
  rate_per_shipment: number;
  currency: SupplierCurrency;
  updated_at: string;
  status: SupplierStatus;
  service_zone?: string | null;
  contact_email?: string | null;
  notes?: string | null;
};

export type SupplierCreateInput = {
  name: string;
  country: SupplierCountry;
  categories: SupplierCategory[];
  rate_per_shipment: number;
  currency: SupplierCurrency;
  status: SupplierStatus;
  service_zone?: string;
  contact_email?: string;
  notes?: string;
};

export type SupplierRateUpdateInput = {
  rate_per_shipment: number;
};

export type SupplierStatusUpdateInput = {
  status: SupplierStatus;
};
