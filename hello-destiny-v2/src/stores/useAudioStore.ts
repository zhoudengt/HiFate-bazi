import { create } from 'zustand';

interface AudioState {
  bgmEnabled: boolean;
  sfxEnabled: boolean;
  bgmVolume: number;
  sfxVolume: number;
  toggleBgm: () => void;
  toggleSfx: () => void;
  setBgmVolume: (v: number) => void;
  setSfxVolume: (v: number) => void;
}

export const useAudioStore = create<AudioState>((set) => ({
  bgmEnabled: true,
  sfxEnabled: true,
  bgmVolume: 0.5,
  sfxVolume: 0.8,

  toggleBgm: () => set((s) => ({ bgmEnabled: !s.bgmEnabled })),
  toggleSfx: () => set((s) => ({ sfxEnabled: !s.sfxEnabled })),
  setBgmVolume: (v) => set({ bgmVolume: v }),
  setSfxVolume: (v) => set({ sfxVolume: v }),
}));
