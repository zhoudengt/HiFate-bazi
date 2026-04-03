-- V2 六爻记录（无 JWT 阶段，可选持久化；表不存在时接口仍可用）
CREATE TABLE IF NOT EXISTS v2_liuyao_castings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    question TEXT NOT NULL,
    method VARCHAR(16) NOT NULL,
    category VARCHAR(32) NULL DEFAULT 'general',
    coin_results JSON NULL,
    number_input JSON NULL,
    divination_time VARCHAR(32) NULL,
    result_json JSON NOT NULL,
    ai_reading LONGTEXT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'completed',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_v2_liuyao_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
