import axios, { type InternalAxiosRequestConfig } from 'axios';
import { API_BASE } from '../utils/constants';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((cfg: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('v2_token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  const guest = localStorage.getItem('v2_guest_token');
  if (guest) cfg.headers['X-V2-Guest-Token'] = guest;

  // FormData 必须去掉默认的 application/json，否则无 boundary，后端无法解析 file（422）
  if (typeof FormData !== 'undefined' && cfg.data instanceof FormData) {
    cfg.headers.delete('Content-Type');
  }

  return cfg;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('v2_token');
    }
    return Promise.reject(err);
  },
);
