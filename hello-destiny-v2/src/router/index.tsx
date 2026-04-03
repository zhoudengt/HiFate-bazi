import { createBrowserRouter } from 'react-router-dom';
import { lazy } from 'react';
import AppLayout from '../App';

const HomePage = lazy(() => import('../pages/home/HomePage'));
const CaiShenDian = lazy(() => import('../pages/palace/CaiShenDian'));
const GanQingDian = lazy(() => import('../pages/palace/GanQingDian'));
const ShiYeDian = lazy(() => import('../pages/palace/ShiYeDian'));
const QuestionInput = lazy(() => import('../pages/liuyao/QuestionInput'));
const CastingPage = lazy(() => import('../pages/liuyao/CastingPage'));
const HexagramResult = lazy(() => import('../pages/liuyao/HexagramResult'));
const AiAnalysis = lazy(() => import('../pages/liuyao/AiAnalysis'));
const ChapterMap = lazy(() => import('../pages/academy/ChapterMap'));
const StageList = lazy(() => import('../pages/academy/StageList'));
const LessonPage = lazy(() => import('../pages/academy/LessonPage'));
const QuizPage = lazy(() => import('../pages/academy/QuizPage'));
const QuestCenter = lazy(() => import('../pages/quest/QuestCenter'));
const ExchangeShop = lazy(() => import('../pages/exchange/ExchangeShop'));
const InventoryPage = lazy(() => import('../pages/exchange/InventoryPage'));
const PrayerPage = lazy(() => import('../pages/prayer/PrayerPage'));
const LifeTree = lazy(() => import('../pages/tree/LifeTree'));
const ProfilePage = lazy(() => import('../pages/profile/ProfilePage'));
const BadgeGallery = lazy(() => import('../pages/profile/BadgeGallery'));
const BoothPage = lazy(() => import('../pages/social/BoothPage'));
const InvitePage = lazy(() => import('../pages/social/InvitePage'));
const AiConsult = lazy(() => import('../pages/consultation/AiConsult'));
const MasterBooking = lazy(() => import('../pages/consultation/MasterBooking'));
const V1WebView = lazy(() => import('../pages/v1-bridge/V1WebView'));

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'quest', element: <QuestCenter /> },
      { path: 'academy', element: <ChapterMap /> },
      { path: 'profile', element: <ProfilePage /> },
      { path: 'v1', element: <V1WebView /> },

      { path: 'palace/caishen', element: <CaiShenDian /> },
      { path: 'palace/ganqing', element: <GanQingDian /> },
      { path: 'palace/shiye', element: <ShiYeDian /> },

      { path: 'liuyao/question', element: <QuestionInput /> },
      { path: 'liuyao/casting', element: <CastingPage /> },
      { path: 'liuyao/result/:id', element: <HexagramResult /> },
      { path: 'liuyao/ai/:id', element: <AiAnalysis /> },

      { path: 'academy/chapter/:id', element: <StageList /> },
      { path: 'academy/lesson/:id', element: <LessonPage /> },
      { path: 'academy/quiz/:id', element: <QuizPage /> },

      { path: 'exchange', element: <ExchangeShop /> },
      { path: 'inventory', element: <InventoryPage /> },
      { path: 'prayer', element: <PrayerPage /> },
      { path: 'tree', element: <LifeTree /> },
      { path: 'badge', element: <BadgeGallery /> },
      { path: 'booth', element: <BoothPage /> },
      { path: 'invite', element: <InvitePage /> },
      { path: 'consult/ai', element: <AiConsult /> },
      { path: 'consult/master', element: <MasterBooking /> },
    ],
  },
], { basename: '/v2' });
