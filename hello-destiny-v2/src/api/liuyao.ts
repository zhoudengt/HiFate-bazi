import { api } from './client';

export interface DivinateRequest {
  question: string;
  method: 'coin' | 'number' | 'time';
  category: string;
  coin_results?: number[];
  number?: number[];
  divination_time?: string;
  persist?: boolean;
}

export const liuyaoApi = {
  divinate: (data: DivinateRequest) =>
    api.post('/liuyao/divinate', data),

  streamUrl: '/api/v2/liuyao/stream',

  getHistory: (page = 1, size = 20, category?: string) =>
    api.get('/liuyao/history', { params: { page, size, category } }),
};
