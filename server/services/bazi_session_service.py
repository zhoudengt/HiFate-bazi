# -*- coding: utf-8 -*-
"""
八字会话管理服务
负责保存和获取用户的完整八字数据（包括：八字、五行、十神、大运流年、数据库规则等）
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 尝试导入Redis
try:
    from server.config.redis_config import get_redis_client
    REDIS_AVAILABLE = True
except Exception as e:
    REDIS_AVAILABLE = False
    logger.warning(f"Redis不可用: {e}")


class BaziSessionService:
    """八字会话管理服务"""
    
    # Redis key前缀
    SESSION_KEY_PREFIX = "bazi_session:"
    # 默认TTL：24小时
    DEFAULT_TTL = 86400
    
    @staticmethod
    def _get_session_key(user_id: str) -> str:
        """生成会话key"""
        return f"{BaziSessionService.SESSION_KEY_PREFIX}{user_id}"
    
    @staticmethod
    def save_bazi_session(user_id: str, bazi_data: Dict[str, Any], ttl: int = None) -> bool:
        """
        保存完整八字数据到会话缓存
        
        Args:
            user_id: 用户ID
            bazi_data: 完整八字数据（包括：八字、五行、十神、大运流年、数据库规则等）
            ttl: 过期时间（秒），默认24小时
            
        Returns:
            bool: 是否保存成功
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis不可用，无法保存会话数据")
            return False
        
        if not user_id:
            logger.warning("user_id为空，无法保存会话数据")
            return False
        
        try:
            redis_client = get_redis_client()
            if not redis_client:
                logger.warning("Redis客户端不可用")
                return False
            
            session_key = BaziSessionService._get_session_key(user_id)
            ttl = ttl or BaziSessionService.DEFAULT_TTL
            
            # 序列化数据
            session_data = {
                "bazi_data": bazi_data,
                "created_at": datetime.now().isoformat(),
                "ttl": ttl
            }
            
            # 保存到Redis（使用JSON序列化）
            redis_client.setex(
                session_key,
                ttl,
                json.dumps(session_data, ensure_ascii=False)
            )
            
            logger.info(f"✅ 保存八字会话数据成功: user_id={user_id}, ttl={ttl}秒")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存八字会话数据失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_bazi_session(user_id: str) -> Optional[Dict[str, Any]]:
        """
        从会话缓存获取完整八字数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 完整八字数据，如果不存在则返回None
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis不可用，无法获取会话数据")
            return None
        
        if not user_id:
            logger.warning("user_id为空，无法获取会话数据")
            return None
        
        try:
            redis_client = get_redis_client()
            if not redis_client:
                logger.warning("Redis客户端不可用")
                return None
            
            session_key = BaziSessionService._get_session_key(user_id)
            
            # 从Redis获取数据
            session_data_str = redis_client.get(session_key)
            if not session_data_str:
                logger.info(f"⚠️ 会话数据不存在: user_id={user_id}")
                return None
            
            # 反序列化数据
            if isinstance(session_data_str, bytes):
                session_data_str = session_data_str.decode('utf-8')
            
            session_data = json.loads(session_data_str)
            bazi_data = session_data.get("bazi_data")
            
            logger.info(f"✅ 获取八字会话数据成功: user_id={user_id}")
            return bazi_data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ 解析会话数据失败: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"❌ 获取八字会话数据失败: {e}", exc_info=True)
            return None
    
    @staticmethod
    def clear_bazi_session(user_id: str) -> bool:
        """
        清除会话数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否清除成功
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis不可用，无法清除会话数据")
            return False
        
        if not user_id:
            logger.warning("user_id为空，无法清除会话数据")
            return False
        
        try:
            redis_client = get_redis_client()
            if not redis_client:
                logger.warning("Redis客户端不可用")
                return False
            
            session_key = BaziSessionService._get_session_key(user_id)
            deleted = redis_client.delete(session_key)
            
            if deleted:
                logger.info(f"✅ 清除八字会话数据成功: user_id={user_id}")
            else:
                logger.info(f"⚠️ 会话数据不存在，无需清除: user_id={user_id}")
            
            return bool(deleted)
            
        except Exception as e:
            logger.error(f"❌ 清除八字会话数据失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    def check_session_exists(user_id: str) -> bool:
        """
        检查会话是否存在
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 会话是否存在
        """
        if not REDIS_AVAILABLE:
            return False
        
        if not user_id:
            return False
        
        try:
            redis_client = get_redis_client()
            if not redis_client:
                return False
            
            session_key = BaziSessionService._get_session_key(user_id)
            exists = redis_client.exists(session_key)
            
            return bool(exists)
            
        except Exception as e:
            logger.error(f"❌ 检查会话存在性失败: {e}", exc_info=True)
            return False

