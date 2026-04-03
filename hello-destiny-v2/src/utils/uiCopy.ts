/**
 * 界面文案集中配置（元辰宫 V2），避免散落在组件中硬编码。
 * 后续可替换为接口/CMS 下发。
 */

export const UI_COPY = {
  topBar: {
    destinyPointsLabel: '命运点数',
    levelLabel: '等级',
    /** 参考稿 B：Lv: 14 */
    levelMarkTemplate: (level: number) => `Lv: ${level}`,
    xpShortLabel: '经验',
    xpProgressTemplate: (current: number, need: number) =>
      need > 0 ? `${current} / ${need}` : `${current} · 已满级`,
    nicknameLoading: '载入中…',
    idShortLabel: 'ID',
    openProfileAria: '个人中心：上传头像与编辑资料',
    /** 非 Tab 页顶栏返回上一页 */
    backAria: '返回上一页',
    profileLoadErrorHint: '档案未同步',
  },
  home: {
    title: '元辰宫',
    welcomeTemplate: (nickname: string) => `${nickname}，你好`,
    /** 首页 HUD 下问候行：默认昵称「元辰旅人」显示为「元辰，你好」与需求稿一致 */
    welcomeDisplayTemplate: (nickname: string) => {
      const s = nickname.replace(/旅人\s*$/, '').trim() || nickname.trim() || '元辰';
      return `${s}，你好`;
    },
    welcomeLoading: '正在载入档案…',
    subtitle: '择殿而入，问卜前程',
    /** 主场景入口：名称与路由、建筑 code 可配置（与 homeSceneLayout 热区顺序一一对应） */
    entries: [
      { name: '兑换殿', path: '/exchange', buildingCode: 'exchange' as const },
      { name: '事业殿', path: '/palace/shiye', buildingCode: 'shiye' as const },
      { name: '学堂', path: '/academy', buildingCode: 'academy' as const },
      { name: '任务', path: '/quest' },
      { name: '生命之树', path: '/tree' },
      { name: '感情殿', path: '/palace/ganqing', buildingCode: 'ganqing' as const },
      { name: '财神殿', path: '/palace/caishen', buildingCode: 'caishen' as const },
    ],
    materialTierUnknown: (level: number) => `灵阶 ${level}`,
  },
  nav: {
    mainNavAria: '主导航',
    tabs: [
      { label: '元辰宫', path: '/' as const },
      { label: '任务', path: '/quest' as const },
      { label: '学堂', path: '/academy' as const },
      { label: '命理', path: '/liuyao/question' as const },
      { label: '我的', path: '/profile' as const },
    ],
  },
  profile: {
    defaultNickname: '元辰旅人',
    levelBadgeTemplate: (level: number) => `等级 ${level}`,
    idLabel: '元辰宫 ID',
    destinyPointsStat: '命运点数',
    xpStat: '当前经验',
    xpToNextStat: '距升级',
    castCountStat: '起卦次数',
    studyDaysStat: '学习天数',
    progressTitle: '元辰宫行程',
    /** 说明性文案，与数值系统解耦，便于运营调整 */
    progressHints: [
      '完成学堂学习与测验可获得经验值。',
      '命运点数将随任务、祈福等玩法逐步开放。',
      '等级提升后可解锁更多殿宇玩法与外观阶段。',
    ],
    changeAvatarHint: '点击更换头像',
    nicknamePlaceholder: '编辑元辰宫昵称',
    saveNickname: '保存昵称',
    uploadAvatar: '上传头像',
    menuBadge: '勋章图鉴',
    menuLiuyaoHistory: '历史卦象',
    menuSettings: '设置',
    menuAbout: '关于',
    statPlaceholder: '—',
  },
  academy: {
    lessonCompleteButton: '完成学习',
    lessonCompleteXpNote: '已获得修学经验',
    quizXpNote: '已获得测验经验',
    quizBackButton: '返回学堂',
  },
  exchange: {
    title: '兑换殿',
    balanceLabel: '当前命运点数',
    pointsUnit: '点',
    redeemButton: '兑换',
    redeemDisabled: '点数不足',
    loading: '加载商品…',
    loadError: '商品加载失败',
    purchaseSuccess: '兑换成功',
    purchaseFail: '兑换失败',
    viewBackpack: '查看背包',
    grantNoteTemplate: (n: number) => `获得 ×${n}`,
    costTemplate: (cost: number) => `${cost} 命运点数`,
  },
  inventory: {
    title: '背包',
    empty: '暂无道具，去兑换殿看看吧',
    backToShop: '返回兑换殿',
    quantityLabel: (q: number) => `数量 ${q}`,
    menuLabel: '我的背包',
  },
} as const;
