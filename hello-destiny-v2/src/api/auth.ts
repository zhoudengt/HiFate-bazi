import { api } from './client';

export const authApi = {
  register: (data: { phone?: string; email?: string; password: string; nickname?: string }) =>
    api.post('/auth/register', data),
  login: (data: { phone?: string; email?: string; password: string }) =>
    api.post('/auth/login', data),
  refresh: (refresh_token: string) =>
    api.post('/auth/refresh', { refresh_token }),
  me: () => api.get('/auth/me'),
};
