-- V2 经济：物品目录、商店上架、多货币钱包、背包
-- 执行示例: mysql -u root -p YOUR_DATABASE < server/db/migrations/v2_003_economy.sql
-- 依赖: v2_yonghu_profiles, v2_youxi_states

CREATE TABLE IF NOT EXISTS v2_jingji_items (
  id INT NOT NULL PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  item_type INT NOT NULL DEFAULT 1 COMMENT '1=道具 6=货币',
  category INT NOT NULL DEFAULT 0,
  icon_id INT NOT NULL DEFAULT 0,
  rarity INT NOT NULL DEFAULT 1,
  use_condition INT NOT NULL DEFAULT 0,
  description VARCHAR(200) DEFAULT '',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO v2_jingji_items (id, name, item_type, category, icon_id, rarity, use_condition, description) VALUES
(1001, '命运点数', 6, 0, 1001, 6, 0, '可用于兑换道具'),
(10001, '龟甲', 1, 0, 10001, 5, 0, '我是一把桃木剑'),
(10002, '桃木剑', 1, 0, 10002, 5, 0, '我是一把桃木剑'),
(10003, '符箓', 1, 0, 10003, 5, 0, '我是一把桃木剑'),
(10004, '铜铃', 1, 0, 10004, 5, 0, '我是一把桃木剑'),
(10005, '水晶', 1, 0, 10005, 5, 0, '我是一把桃木剑'),
(10006, '香火', 1, 0, 10006, 5, 0, '我是一把桃木剑'),
(10007, '铜币', 1, 0, 10007, 5, 0, '我是一把桃木剑')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  item_type = VALUES(item_type),
  category = VALUES(category),
  icon_id = VALUES(icon_id),
  rarity = VALUES(rarity),
  use_condition = VALUES(use_condition),
  description = VALUES(description);

CREATE TABLE IF NOT EXISTS v2_jingji_shop_listings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  shop_id INT NOT NULL DEFAULT 1,
  item_id INT NOT NULL,
  quantity INT NOT NULL DEFAULT 1,
  currency_item_id INT NOT NULL,
  cost INT NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  enabled TINYINT NOT NULL DEFAULT 1,
  CONSTRAINT fk_shop_item FOREIGN KEY (item_id) REFERENCES v2_jingji_items(id),
  CONSTRAINT fk_shop_currency FOREIGN KEY (currency_item_id) REFERENCES v2_jingji_items(id),
  KEY idx_shop (shop_id, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 可重复执行：先清空默认商店再写入上架数据
DELETE FROM v2_jingji_shop_listings WHERE shop_id = 1;
INSERT INTO v2_jingji_shop_listings (shop_id, item_id, quantity, currency_item_id, cost, sort_order, enabled) VALUES
(1, 10001, 1, 1001, 100, 1, 1),
(1, 10002, 2, 1001, 200, 2, 1),
(1, 10003, 3, 1001, 300, 3, 1),
(1, 10004, 4, 1001, 150, 4, 1),
(1, 10005, 5, 1001, 250, 5, 1),
(1, 10006, 6, 1001, 350, 6, 1),
(1, 10007, 7, 1001, 500, 7, 1);

CREATE TABLE IF NOT EXISTS v2_jingji_user_currencies (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  currency_item_id INT NOT NULL,
  balance BIGINT NOT NULL DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_currency (user_id, currency_item_id),
  CONSTRAINT fk_uc_user FOREIGN KEY (user_id) REFERENCES v2_yonghu_profiles(id) ON DELETE CASCADE,
  CONSTRAINT fk_uc_item FOREIGN KEY (currency_item_id) REFERENCES v2_jingji_items(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS v2_jingji_user_inventory (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  item_id INT NOT NULL,
  quantity INT NOT NULL DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_item (user_id, item_id),
  CONSTRAINT fk_inv_user FOREIGN KEY (user_id) REFERENCES v2_yonghu_profiles(id) ON DELETE CASCADE,
  CONSTRAINT fk_inv_item FOREIGN KEY (item_id) REFERENCES v2_jingji_items(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 从 v2_youxi_states 同步命运点数到钱包（1001）；已有行则取较大值避免回退？取 game_states 为准覆盖
INSERT INTO v2_jingji_user_currencies (user_id, currency_item_id, balance)
SELECT user_id, 1001, destiny_points
FROM v2_youxi_states
ON DUPLICATE KEY UPDATE balance = VALUES(balance);
