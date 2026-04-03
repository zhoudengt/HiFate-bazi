import { api } from './client';

/** 与 economyApi.purchase 一致：按商店上架 id 扣命运点数兑换 */
export const paymentApi = {
  createOrder: (listing_id: number, _pay_method?: string) =>
    api.post<{ code: number; message?: string; data: unknown }>('/economy/shop/purchase', { listing_id }),
};
