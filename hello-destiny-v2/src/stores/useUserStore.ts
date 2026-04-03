import { create } from 'zustand';
import { profileApi } from '../api/profile';
import { useGameStore } from './useGameStore';
import { UI_COPY } from '../utils/uiCopy';

interface UserState {
  userId: string | null;
  nickname: string;
  avatarUrl: string | null;
  isLoggedIn: boolean;
  profileLoading: boolean;
  profileError: string | null;
  setUser: (u: { userId: string; nickname: string; avatarUrl?: string }) => void;
  logout: () => void;
  fetchProfile: () => Promise<void>;
  updateNickname: (nickname: string) => Promise<boolean>;
  uploadAvatar: (file: File) => Promise<boolean>;
}

export const useUserStore = create<UserState>((set) => ({
  userId: null,
  nickname: UI_COPY.profile.defaultNickname,
  avatarUrl: null,
  isLoggedIn: false,
  profileLoading: false,
  profileError: null,

  setUser: (u) =>
    set({
      userId: u.userId,
      nickname: u.nickname,
      avatarUrl: u.avatarUrl ?? null,
      isLoggedIn: true,
    }),

  logout: () => {
    localStorage.removeItem('v2_token');
    set({
      userId: null,
      nickname: UI_COPY.profile.defaultNickname,
      avatarUrl: null,
      isLoggedIn: false,
    });
  },

  fetchProfile: async () => {
    set({ profileLoading: true, profileError: null });
    try {
      const res = await profileApi.me();
      const body = res.data;
      if (body.code !== 0 || !body.data) {
        set({ profileError: body.message || 'profile_load_failed', profileLoading: false });
        return;
      }
      const d = body.data;
      set({
        userId: d.id,
        nickname: d.nickname?.trim() || UI_COPY.profile.defaultNickname,
        avatarUrl: d.avatar_url,
        isLoggedIn: true,
        profileLoading: false,
      });
      useGameStore.getState().applyGameState(d.game ?? undefined);
    } catch {
      set({ profileError: 'network_error', profileLoading: false });
    }
  },

  updateNickname: async (nickname: string) => {
    const n = nickname.trim();
    if (!n) return false;
    try {
      const res = await profileApi.updateMe(n);
      if (res.data.code !== 0 || !res.data.data) return false;
      set({ nickname: res.data.data.nickname || n });
      return true;
    } catch {
      return false;
    }
  },

  uploadAvatar: async (file: File) => {
    try {
      const res = await profileApi.uploadAvatar(file);
      if (res.data.code !== 0 || !res.data.data?.avatar_url) return false;
      set({ avatarUrl: res.data.data.avatar_url });
      return true;
    } catch {
      return false;
    }
  },
}));
