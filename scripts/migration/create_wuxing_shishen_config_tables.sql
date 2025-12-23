-- 创建五行属性配置表
CREATE TABLE IF NOT EXISTS `wuxing_attributes` (
    `id` INT PRIMARY KEY,
    `name` VARCHAR(10) NOT NULL UNIQUE COMMENT '五行属性名称',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='五行属性配置表';

-- 插入五行属性数据
INSERT INTO `wuxing_attributes` (`id`, `name`) VALUES
(1, '木'),
(2, '火'),
(3, '土'),
(4, '金'),
(5, '水')
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

-- 创建十神命格配置表
CREATE TABLE IF NOT EXISTS `shishen_patterns` (
    `id` INT PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE COMMENT '十神命格名称',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='十神命格配置表';

-- 插入十神命格数据
INSERT INTO `shishen_patterns` (`id`, `name`) VALUES
(2001, '正官格'),
(2002, '七杀格'),
(2003, '正印格'),
(2004, '偏印格'),
(2005, '正财格'),
(2006, '偏财格'),
(2007, '食神格'),
(2008, '伤官格'),
(2009, '天元暗禄格'),
(2010, '财官双美格'),
(2011, '子午双包格'),
(2012, '稼穑格'),
(2013, '曲直格'),
(2014, '炎上格'),
(2015, '从财格'),
(2016, '从杀格'),
(2017, '金神格'),
(2018, '魁罡格'),
(2019, '六王趋艮格'),
(2020, '六甲趋乾格'),
(2021, '日贵格'),
(2022, '印绶格'),
(2023, '食神制杀格'),
(2024, '伤官生财格'),
(2025, '财官印全格'),
(2026, '金神带刃格'),
(2027, '官星带合格'),
(2028, '壬骑龙背格'),
(2029, '化气格'),
(2030, '六阴朝阳格'),
(2031, '子遥巳格'),
(2032, '丑遥巳格'),
(2033, '井栏叉格'),
(2034, '冲合禄马格'),
(2035, '飞天禄马格'),
(2036, '金神遇火格'),
(2037, '金神带甲格'),
(2038, '凤凰池格'),
(2039, '天医格'),
(2040, '龙德格'),
(2041, '天乙贵人格'),
(2042, '福星贵人格'),
(2043, '文昌格'),
(2044, '驿马格'),
(2045, '三奇格'),
(2046, '三奇格'),
(2047, '拱禄格'),
(2048, '双飞蝴蝶格'),
(2049, '五星聚合格'),
(2050, '专旺格'),
(2051, '从强格'),
(2052, '从弱格'),
(2053, '金神七杀格'),
(2054, '金神印绶格'),
(2055, '金神财星格'),
(2056, '金神伤官格'),
(2057, '金神比肩格'),
(2058, '金神劫财格'),
(2059, '金神食神格')
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

