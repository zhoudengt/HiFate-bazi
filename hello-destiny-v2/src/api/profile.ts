import { api } from './client';
import type { GameState } from './game';

export interface ProfileMeData {
  id: string;
  nickname: string | null;
  avatar_url: string | null;
  game: GameState | null;
}

export interface ProfileMeResponse {
  code: number;
  message: string;
  data: ProfileMeData;
}

export const profileApi = {
  me: () => api.get<ProfileMeResponse>('/profile/me'),
  updateMe: (nickname: string) => api.put<ProfileMeResponse>('/profile/me', { nickname }),
  uploadAvatar: (file: File) => {
    const fd = new FormData();
    fd.append('file', file, file.name || 'avatar.jpg');
    return api.post<{ code: number; message: string; data: { avatar_url: string } }>(
      '/profile/avatar',
      fd,
    );
  },
};
