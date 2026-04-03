import { api } from './client';

export interface CurrencyBalance {
  currency_item_id: number;
  name: string;
  balance: number;
  icon_url: string;
}

export interface BalanceResponse {
  code: number;
  message?: string;
  data: {
    currencies: CurrencyBalance[];
    destiny_points: number;
  };
}

export interface ShopItem {
  listing_id: number;
  shop_id: number;
  item_id: number;
  name: string;
  description: string;
  quantity: number;
  currency_item_id: number;
  cost: number;
  rarity: number;
  icon_url: string;
}

export interface ShopItemsResponse {
  code: number;
  data: { items: ShopItem[] };
}

export interface InventoryItem {
  item_id: number;
  name: string;
  quantity: number;
  description: string;
  icon_url: string;
  item_type: number;
}

export interface InventoryResponse {
  code: number;
  data: { items: InventoryItem[] };
}

export interface PurchaseResponse {
  code: number;
  message?: string;
  data: {
    ok?: boolean;
    error?: string;
    listing_id?: number;
    item_id?: number;
    quantity_granted?: number;
    new_balance?: number;
  };
}

export interface TransactionRow {
  amount: number;
  type: string;
  source: string;
  description: string;
  created_at: string;
}

export const economyApi = {
  balance: () => api.get<BalanceResponse>('/economy/balance'),
  transactions: (page = 1, size = 20) =>
    api.get<{ code: number; data: { items: TransactionRow[]; total: number } }>('/economy/transactions', {
      params: { page, size },
    }),
  shopItems: () => api.get<ShopItemsResponse>('/economy/shop/items'),
  purchase: (listing_id: number) =>
    api.post<PurchaseResponse>('/economy/shop/purchase', { listing_id }),
  inventory: () => api.get<InventoryResponse>('/economy/inventory'),
};
