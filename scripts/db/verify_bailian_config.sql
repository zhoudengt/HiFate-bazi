-- ============================================
-- 验证百炼平台配置 - SQL 脚本
-- ============================================
-- 用于检查百炼平台配置是否完整
-- ============================================

-- 1. 检查全局平台配置
SELECT 
    '全局平台配置' as check_type,
    config_key,
    config_value,
    CASE 
        WHEN config_value = 'bailian' THEN '✅ 已配置为百炼'
        WHEN config_value = 'coze' THEN '⚠️ 当前使用 Coze'
        ELSE '❌ 配置值无效'
    END as status
FROM service_configs 
WHERE config_key = 'LLM_PLATFORM';

-- 2. 检查场景级平台配置
SELECT 
    '场景级平台配置' as check_type,
    config_key,
    config_value,
    CASE 
        WHEN config_value = 'bailian' THEN '✅ 使用百炼'
        WHEN config_value = 'coze' THEN '⚠️ 使用 Coze'
        ELSE '❌ 配置值无效'
    END as status
FROM service_configs 
WHERE config_key LIKE '%_LLM_PLATFORM'
ORDER BY config_key;

-- 3. 检查百炼 API Key
SELECT 
    '百炼 API Key' as check_type,
    config_key,
    CASE 
        WHEN config_value IS NULL OR config_value = '' THEN '❌ 未配置'
        WHEN config_value LIKE 'sk-%' THEN CONCAT('✅ 已配置 (', LEFT(config_value, 10), '...)')
        ELSE '⚠️ 格式可能不正确'
    END as status
FROM service_configs 
WHERE config_key = 'BAILIAN_API_KEY';

-- 4. 检查各场景 App ID 配置
SELECT 
    '百炼 App ID 配置' as check_type,
    config_key,
    CASE 
        WHEN config_value IS NULL OR config_value = '' THEN '❌ 未配置'
        WHEN LENGTH(config_value) >= 32 THEN CONCAT('✅ 已配置 (', LEFT(config_value, 8), '...)')
        ELSE '⚠️ 格式可能不正确'
    END as status
FROM service_configs 
WHERE config_key LIKE 'BAILIAN_%_APP_ID'
ORDER BY config_key;

-- 5. 汇总检查结果
SELECT 
    '配置完整性检查' as check_type,
    COUNT(DISTINCT CASE WHEN config_key = 'LLM_PLATFORM' THEN 1 END) as has_global_platform,
    COUNT(DISTINCT CASE WHEN config_key = 'BAILIAN_API_KEY' AND config_value IS NOT NULL AND config_value != '' THEN 1 END) as has_api_key,
    COUNT(DISTINCT CASE WHEN config_key LIKE 'BAILIAN_%_APP_ID' AND config_value IS NOT NULL AND config_value != '' THEN 1 END) as app_id_count,
    CASE 
        WHEN COUNT(DISTINCT CASE WHEN config_key = 'BAILIAN_API_KEY' AND config_value IS NOT NULL AND config_value != '' THEN 1 END) > 0 
         AND COUNT(DISTINCT CASE WHEN config_key = 'LLM_PLATFORM' AND config_value = 'bailian' THEN 1 END) > 0
        THEN '✅ 基本配置完整'
        ELSE '❌ 配置不完整'
    END as overall_status
FROM service_configs
WHERE config_key IN ('LLM_PLATFORM', 'BAILIAN_API_KEY') 
   OR config_key LIKE 'BAILIAN_%_APP_ID';
