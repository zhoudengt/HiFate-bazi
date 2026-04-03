import { api } from './client';

export type StoryLine = {
  seq: number;
  speaker: string;
  avatar_id: number;
  content: string;
};

export type StoryDialogueResponse = {
  code: number;
  message?: string;
  data?: { lines: StoryLine[] };
};

export const storyApi = {
  async getDialogue(dialogueId: number) {
    // baseURL 已是 /api/v2，勿再加前缀，否则会变成 /api/v2/api/v2/...
    const res = await api.get<StoryDialogueResponse>(`/story/dialogue/${dialogueId}`);
    return res.data;
  },
};
