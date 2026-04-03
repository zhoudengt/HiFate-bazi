import { api } from './client';

export const socialApi = {
  generateInvite: () => api.post('/social/invite/generate'),
  inviteStats: () => api.get('/social/invite/stats'),
  claimInvite: (invite_code: string) =>
    api.post('/social/invite/claim', { invite_code }),
};
