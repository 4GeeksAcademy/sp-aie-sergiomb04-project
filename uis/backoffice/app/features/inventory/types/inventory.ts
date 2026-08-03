export type InventoryCategory = "fashion" | "electronics" | "cosmetics";
export type InventoryWarehouse = "LA" | "ZGZ";
export type StockExitType = "dispatch" | "loss";

export type InventoryProduct = {
  id: number;
  name: string;
  sku: string;
  client_name: string;
  category: InventoryCategory;
  warehouse: InventoryWarehouse;
  current_stock: number;
};

export type InventoryStockEntryCreateInput = {
  sku_id: number;
  quantity: number;
  reference: string;
  warehouse: InventoryWarehouse;
};

export type InventoryStockEntryResponse = {
  id: number;
  sku_id: number;
  quantity: number;
  reference: string;
  warehouse: InventoryWarehouse;
  created_at: string;
  user_uuid: string;
};

export type InventoryStockExitCreateInput = {
  sku_id: number;
  quantity: number;
  exit_type: StockExitType;
  tracking_number: string | null;
  warehouse: InventoryWarehouse;
};

export type InventoryStockExitResponse = {
  id: number;
  sku_id: number;
  quantity: number;
  exit_type: StockExitType;
  tracking_number: string | null;
  warehouse: InventoryWarehouse;
  created_at: string;
  user_uuid: string;
};

export type InventoryOrderHistoryItem = {
  id: number;
  order_type: "inbound" | "outbound";
  sku_id: number;
  sku: string;
  product_name: string;
  quantity: number;
  warehouse: InventoryWarehouse;
  created_at: string;
  user_uuid: string;
  reference?: string | null;
  exit_type?: StockExitType | null;
  tracking_number?: string | null;
};

export type InventoryOrdersResponse = {
  orders: InventoryOrderHistoryItem[];
};
