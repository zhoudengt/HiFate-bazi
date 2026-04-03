import { api } from './client';
import type { GameState } from './game';

export interface LearningChapter {
  id: number;
  code: string;
  name: string;
  description: string;
  cover: string;
  sections_count: number;
  completed_stages: number;
  completed_pct: number;
  unlocked: boolean;
}

export interface LearningStage {
  sn: number;
  code: string;
  chapter_id: number;
  stage_index: number;
  name: string;
  battlefield: number;
  locked: boolean;
  completed: boolean;
  playable: boolean;
  reward_preview: { destiny_points: number; xp: number };
}

export interface StageDetail {
  stage: {
    sn: number;
    chapter_id: number;
    stage_index: number;
    name: string;
    battlefield: number;
    completed: boolean;
  };
  lesson_body: string;
  experience_variant: number;
  experience_variant_label: string;
  start_dialogue: { seq: number; speaker: string; avatar_id: number; content: string }[];
  end_dialogue: { seq: number; speaker: string; avatar_id: number; content: string }[];
}

export interface QuizQuestion {
  id: string;
  text: string;
  options: string[];
  type: string;
}

export interface CompleteResponse {
  ok: boolean;
  already_completed?: boolean;
  score?: number;
  total_questions?: number;
  rewards?: {
    destiny_points: number;
    xp: number;
    drops: { item_id: number; quantity: number }[];
  } | null;
  state?: GameState;
}

export const learningApi = {
  chapters: () =>
    api.get<{ code: number; data: { chapters: LearningChapter[] }; message?: string }>('/learning/chapters'),

  chapterStages: (chapterId: number) =>
    api.get<{
      code: number;
      data: {
        chapter: { id: number; name: string; description: string; cover: string };
        stages: LearningStage[];
      };
      message?: string;
    }>(`/learning/chapters/${chapterId}/stages`),

  stageDetail: (stageSn: number) =>
    api.get<{ code: number; data: StageDetail; message?: string }>(`/learning/stages/${stageSn}/detail`),

  stageQuiz: (stageSn: number) =>
    api.get<{
      code: number;
      data: { quiz_id: number; battlefield?: number; questions: QuizQuestion[] };
      message?: string;
    }>(`/learning/stages/${stageSn}/quiz`),

  completeStage: (stageSn: number, answers: number[]) =>
    api.post<{ code: number; data: CompleteResponse; message?: string }>(`/learning/stages/${stageSn}/complete`, {
      answers,
    }),
};
