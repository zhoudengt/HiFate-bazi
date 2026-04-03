-- V2 剧情配置表（模块 juqing），Excel 导入后可热更新缓存
CREATE TABLE IF NOT EXISTS v2_juqing_config (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  dialogue_id INT NOT NULL COMMENT '对话组ID, e.g. 101',
  seq         INT NOT NULL COMMENT '顺序',
  speaker     VARCHAR(50) NOT NULL COMMENT '说话人名称',
  avatar_id   INT NOT NULL COMMENT '头像图片ID, 对应 /assets/story/{id}.png',
  content     TEXT NOT NULL COMMENT '对话内容',
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_dialogue_seq (dialogue_id, seq),
  KEY idx_dialogue_id (dialogue_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO v2_juqing_config (dialogue_id, seq, speaker, avatar_id, content) VALUES
  (101, 1, '卦师', 101, '小友，你有啥想问的吗？'),
  (101, 2, '玩家自己', 102, '我想咨询下'),
  (101, 3, '卦师', 101, '小友，你有啥想问的吗？1'),
  (101, 4, '玩家自己', 102, '我想咨询下1'),
  (101, 5, '卦师', 101, '小友，你有啥想问的吗？2'),
  (101, 6, '玩家自己', 102, '我想咨询下2'),
  (101, 7, '卦师', 101, '小友，你有啥想问的吗？3'),
  (101, 8, '玩家自己', 102, '我想咨询下3'),
  (101, 9, '卦师', 101, '小友，你有啥想问的吗？4'),
  (101, 10, '玩家自己', 102, '我想咨询下4'),
  (102, 1, '卦师', 101, '小友，你有啥想问的吗？'),
  (102, 2, '玩家自己', 103, '我想咨询下'),
  (102, 3, '卦师', 101, '小友，你有啥想问的吗？1'),
  (102, 4, '玩家自己', 103, '我想咨询下1'),
  (102, 5, '卦师', 101, '小友，你有啥想问的吗？2'),
  (102, 6, '玩家自己', 103, '我想咨询下2'),
  (102, 7, '卦师', 101, '小友，你有啥想问的吗？3'),
  (102, 8, '玩家自己', 103, '我想咨询下3'),
  (102, 9, '卦师', 101, '小友，你有啥想问的吗？4'),
  (102, 10, '玩家自己', 103, '我想咨询下4');
