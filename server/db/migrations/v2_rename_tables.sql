-- V2 表统一命名规范：v2_<模块拼音>_<表名>
-- 模块：yonghu(用户) youxi(游戏) jingji(经济) liuyao(六爻) renwu(任务)
-- 执行前请备份！
-- 执行示例: mysql -u root -p YOUR_DATABASE < server/db/migrations/v2_rename_tables.sql

-- 先删除外键约束（RENAME 时外键会自动跟随，但旧约束名保留）
-- 注意：RENAME TABLE 是原子操作，旧表名不可用期间为零。

-- ═══════════════════════════════════════
-- 模块 yonghu（用户）
-- ═══════════════════════════════════════
RENAME TABLE v2_user_profiles TO v2_yonghu_profiles;

-- ═══════════════════════════════════════
-- 模块 youxi（游戏）
-- ═══════════════════════════════════════
RENAME TABLE v2_game_states  TO v2_youxi_states;
RENAME TABLE v2_level_config TO v2_youxi_level_config;
RENAME TABLE v2_xp_logs      TO v2_youxi_xp_logs;
RENAME TABLE v2_points_logs   TO v2_youxi_points_logs;

-- ═══════════════════════════════════════
-- 模块 jingji（经济）
-- ═══════════════════════════════════════
RENAME TABLE v2_items            TO v2_jingji_items;
RENAME TABLE v2_shop_listings    TO v2_jingji_shop_listings;
RENAME TABLE v2_user_currencies  TO v2_jingji_user_currencies;
RENAME TABLE v2_user_inventory   TO v2_jingji_user_inventory;

-- ═══════════════════════════════════════
-- 模块 liuyao（六爻）— 已符合规范，不改
-- v2_liuyao_castings 保持原样
-- ═══════════════════════════════════════
