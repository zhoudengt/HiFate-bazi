-- ========================================
-- 首页内容表 - 图片字段迁移（Base64 -> OSS URL）
-- ========================================
-- 创建时间: 2026-01-28
-- 说明: 将图片存储从base64编码改为OSS地址存储，提高存储和传输效率

USE `hifate_bazi`;

-- ========================================
-- 添加新字段 image_url
-- ========================================
ALTER TABLE `homepage_contents` 
ADD COLUMN `image_url` VARCHAR(500) NULL COMMENT '图片OSS地址（如：https://destiny-ducket.oss-cn-hongkong.aliyuncs.com/xxx.jpeg）' 
AFTER `description`;

-- ========================================
-- 数据迁移（可选）
-- ========================================
-- 如果需要将现有的base64数据迁移到OSS，需要先上传到OSS获取URL
-- 这里暂时不处理，保留image_base64字段用于过渡

-- ========================================
-- 后续清理（稳定运行后可执行）
-- ========================================
-- ALTER TABLE `homepage_contents` DROP COLUMN `image_base64`;
