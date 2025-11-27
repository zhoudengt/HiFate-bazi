-- ========================================
-- 面相分析V2 数据库表结构
-- ========================================

-- 1. 面相规则表
CREATE TABLE IF NOT EXISTS face_rules_v2 (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '规则ID',
    rule_type VARCHAR(50) NOT NULL COMMENT '规则类型：gongwei/liuqin/shishen/dizhi/feature',
    position VARCHAR(100) NOT NULL COMMENT '具体位置（如"印堂"、"天中"）',
    position_code VARCHAR(50) COMMENT '位置编码',
    conditions JSON NOT NULL COMMENT '特征条件（JSON格式）',
    interpretation TEXT NOT NULL COMMENT '断语',
    category VARCHAR(50) COMMENT '分类：事业/财运/婚姻/健康/性格等',
    tags JSON COMMENT '标签（JSON数组）',
    priority INT DEFAULT 50 COMMENT '优先级（越大越优先）',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    confidence FLOAT DEFAULT 0.8 COMMENT '置信度阈值',
    metadata JSON COMMENT '附加元数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rule_type (rule_type),
    INDEX idx_position (position),
    INDEX idx_category (category),
    INDEX idx_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面相规则表V2';

-- 2. 特征点映射表
CREATE TABLE IF NOT EXISTS landmark_mapping (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '映射ID',
    mediapipe_index INT NOT NULL COMMENT 'MediaPipe点序号（0-467）',
    feature_id INT NOT NULL COMMENT '面相特征点ID（1-99）',
    feature_name VARCHAR(100) NOT NULL COMMENT '面相特征名称',
    gongwei VARCHAR(50) COMMENT '所属宫位',
    position_type VARCHAR(50) COMMENT '位置类型：shisan_gongwei/liuqin/shishen/dizhi',
    region VARCHAR(50) COMMENT '面部区域：forehead/eyebrow/eye/nose/mouth/cheek/chin',
    description TEXT COMMENT '特征描述',
    calculation_method VARCHAR(50) COMMENT '计算方法：direct/average/interpolate',
    calculation_params JSON COMMENT '计算参数（如果是average/interpolate）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_feature_id (feature_id),
    INDEX idx_mediapipe_index (mediapipe_index),
    INDEX idx_gongwei (gongwei),
    INDEX idx_position_type (position_type),
    INDEX idx_region (region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='特征点映射表';

-- 3. 宫位定义表
CREATE TABLE IF NOT EXISTS gongwei_definition (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '宫位ID',
    gongwei_type VARCHAR(50) NOT NULL COMMENT '宫位类型：shisan/liuqin/shishen/dizhi/liunian',
    name VARCHAR(100) NOT NULL COMMENT '宫位名称',
    position_code VARCHAR(50) COMMENT '位置编码',
    region_type VARCHAR(50) COMMENT '区域类型：point/polygon',
    region_data JSON NOT NULL COMMENT '区域数据（坐标或多边形）',
    age_range VARCHAR(50) COMMENT '对应年龄段（仅流年）',
    description TEXT COMMENT '描述',
    related_features JSON COMMENT '相关特征点ID列表',
    metadata JSON COMMENT '附加元数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_type_name (gongwei_type, name),
    INDEX idx_gongwei_type (gongwei_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='宫位定义表';

-- 4. 面相分析记录表
CREATE TABLE IF NOT EXISTS face_analysis_records (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    user_id INT COMMENT '用户ID',
    session_id VARCHAR(100) COMMENT '会话ID',
    image_path VARCHAR(255) COMMENT '图片路径',
    image_hash VARCHAR(64) COMMENT '图片哈希（避免重复分析）',
    landmarks_data JSON COMMENT '检测到的关键点数据',
    analysis_result JSON COMMENT '分析结果（完整JSON）',
    analysis_types VARCHAR(255) COMMENT '分析类型列表',
    birth_info JSON COMMENT '生辰信息（如有）',
    processing_time_ms INT COMMENT '处理时间（毫秒）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_image_hash (image_hash),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面相分析记录表';

-- 5. 规则版本管理表
CREATE TABLE IF NOT EXISTS face_rule_versions (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '版本ID',
    version_number VARCHAR(50) NOT NULL COMMENT '版本号',
    description TEXT COMMENT '版本描述',
    rule_count INT DEFAULT 0 COMMENT '规则数量',
    published TINYINT(1) DEFAULT 0 COMMENT '是否发布',
    published_at TIMESTAMP NULL COMMENT '发布时间',
    created_by VARCHAR(100) COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_version_number (version_number),
    INDEX idx_published (published)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='规则版本管理表';

-- ========================================
-- 初始化数据
-- ========================================

-- 插入十三宫位定义
INSERT INTO gongwei_definition (gongwei_type, name, position_code, region_type, region_data, description) VALUES
('shisan', '天中', 'tianchong', 'point', '{"y_ratio": 0.05}', '发际线中央，主15-16岁运势'),
('shisan', '天庭', 'tinting', 'point', '{"y_ratio": 0.10}', '额头中上部，主17-18岁运势'),
('shisan', '司空', 'sikong', 'point', '{"y_ratio": 0.15}', '额头中部，主19-20岁运势'),
('shisan', '中正', 'zhongzheng', 'point', '{"y_ratio": 0.20}', '额头下部，主21-22岁运势'),
('shisan', '印堂', 'yintang', 'point', '{"y_ratio": 0.25}', '两眉之间，主28岁运势，命宫'),
('shisan', '山根', 'shangen', 'point', '{"y_ratio": 0.35}', '鼻梁起点，主41岁运势'),
('shisan', '年上', 'nianshang', 'point', '{"y_ratio": 0.40}', '鼻梁中部，主44岁运势'),
('shisan', '寿上', 'shoushang', 'point', '{"y_ratio": 0.42}', '鼻梁中部略下，主45岁运势'),
('shisan', '准头', 'zhuntou', 'point', '{"y_ratio": 0.48}', '鼻头，主48-50岁运势，财帛宫'),
('shisan', '人中', 'renzhong', 'point', '{"y_ratio": 0.58}', '鼻下唇上，主51岁运势'),
('shisan', '水星', 'shuixing', 'point', '{"y_ratio": 0.65}', '嘴唇，主60岁运势'),
('shisan', '承浆', 'chengjiang', 'point', '{"y_ratio": 0.75}', '下唇下方，主61岁运势'),
('shisan', '地阁', 'dige', 'point', '{"y_ratio': 0.90}', '下巴，主晚年运势');

-- 插入六亲宫位定义
INSERT INTO gongwei_definition (gongwei_type, name, position_code, region_type, region_data, description) VALUES
('liuqin', '父亲宫', 'father', 'point', '{"position": "left_forehead_upper"}', '左额上部，看父亲运势'),
('liuqin', '母亲宫', 'mother', 'point', '{"position": "right_forehead_upper"}', '右额上部，看母亲运势'),
('liuqin', '兄弟宫', 'brother', 'region', '{"position": "eyebrows"}', '眉毛区域，看兄弟姐妹'),
('liuqin', '夫妻宫', 'spouse', 'region', '{"position": "eye_tail"}', '眼尾鱼尾纹区域，看婚姻'),
('liuqin', '子女宫', 'children', 'region', '{"position": "under_eyes"}', '眼下卧蚕区域，看子女'),
('liuqin', '奴仆宫', 'servant', 'region', '{"position": "lower_cheeks"}', '下腮区域，看下属朋友');

-- 插入十神宫位定义（与八字结合）
INSERT INTO gongwei_definition (gongwei_type, name, position_code, region_type, region_data, description) VALUES
('shishen', '正官', 'zhengguan', 'point', '{"position": "yintang"}', '印堂，正官位'),
('shishen', '偏官', 'pianguan', 'point', '{"position": "sikong"}', '司空，偏官（七杀）位'),
('shishen', '正财', 'zhengcai', 'point', '{"position": "zhuntou"}', '准头（鼻头），正财位'),
('shishen', '偏财', 'piancai', 'region', '{"position": "nose_wings"}', '鼻翼，偏财位'),
('shishen', '食神', 'shishen', 'region', '{"position": "upper_lip"}', '上唇，食神位'),
('shishen', '伤官', 'shangguan', 'region', '{"position": "lower_lip"}', '下唇，伤官位'),
('shishen', '正印', 'zhengyin', 'point', '{"position': 'tinting"}', '天庭，正印位'),
('shishen', '偏印', 'pianyin', 'region', '{"position": "temples"}', '额角，偏印位'),
('shishen', '比肩', 'bijian', 'region', '{"position": "cheekbones"}', '颧骨，比肩位'),
('shishen', '劫财', 'jiecai', 'region', '{"position": "jaw"}', '下颌，劫财位');

-- 插入十二地支宫位定义
INSERT INTO gongwei_definition (gongwei_type, name, position_code, region_type, region_data, description) VALUES
('dizhi', '子', 'zi', 'point', '{"y_ratio": 0.88}', '地阁下部，子位（水）'),
('dizhi', '丑', 'chou', 'point', '{"position": "left_jaw"}', '左下颌，丑位（土）'),
('dizhi', '寅', 'yin', 'point', '{"position": "left_cheek_lower"}', '左颊下部，寅位（木）'),
('dizhi', '卯', 'mao', 'point', '{"position": "left_cheek_upper"}', '左颊上部，卯位（木）'),
('dizhi', '辰', 'chen', 'point', '{"position": "left_temple"}', '左太阳穴，辰位（土）'),
('dizhi', '巳', 'si', 'point', '{"y_ratio": 0.10, "x_offset": -0.15}', '左额上部，巳位（火）'),
('dizhi', '午', 'wu', 'point', '{"y_ratio": 0.05}', '额顶中央，午位（火）'),
('dizhi', '未', 'wei', 'point', '{"y_ratio": 0.10, "x_offset": 0.15}', '右额上部，未位（土）'),
('dizhi', '申', 'shen', 'point', '{"position": "right_temple"}', '右太阳穴，申位（金）'),
('dizhi', '酉', 'you', 'point', '{"position": "right_cheek_upper"}', '右颊上部，酉位（金）'),
('dizhi', '戌', 'xu', 'point', '{"position": "right_cheek_lower"}', '右颊下部，戌位（土）'),
('dizhi', '亥', 'hai', 'point', '{"position": "right_jaw"}', '右下颌，亥位（水）');

-- ========================================
-- 创建视图（方便查询）
-- ========================================

-- 启用的规则视图
CREATE OR REPLACE VIEW v_active_face_rules AS
SELECT 
    id, rule_type, position, position_code, conditions, 
    interpretation, category, priority, confidence
FROM face_rules_v2
WHERE enabled = 1
ORDER BY priority DESC, id;

-- 宫位完整信息视图
CREATE OR REPLACE VIEW v_gongwei_full AS
SELECT 
    gd.id, gd.gongwei_type, gd.name, gd.position_code,
    gd.region_type, gd.region_data, gd.age_range, gd.description,
    COUNT(fr.id) as rule_count
FROM gongwei_definition gd
LEFT JOIN face_rules_v2 fr ON gd.name = fr.position AND fr.enabled = 1
GROUP BY gd.id, gd.gongwei_type, gd.name, gd.position_code,
         gd.region_type, gd.region_data, gd.age_range, gd.description;

-- ========================================
-- 权限设置（根据实际情况调整）
-- ========================================

-- GRANT SELECT, INSERT, UPDATE ON face_rules_v2 TO 'bazi_app'@'%';
-- GRANT SELECT ON landmark_mapping TO 'bazi_app'@'%';
-- GRANT SELECT ON gongwei_definition TO 'bazi_app'@'%';
-- GRANT INSERT ON face_analysis_records TO 'bazi_app'@'%';

