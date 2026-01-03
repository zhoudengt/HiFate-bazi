#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户交互数据访问层 - MongoDB
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, OperationFailure
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("pymongo not available, MongoDB features disabled")

from server.config.database_config import MONGO_CONFIG

logger = logging.getLogger(__name__)


class MongoInteractionDAO:
    """用户交互数据访问对象（MongoDB）"""
    
    def __init__(self):
        """初始化MongoDB连接"""
        if not MONGO_AVAILABLE:
            self.client = None
            self.db = None
            logger.warning("[MongoInteractionDAO] pymongo不可用，MongoDB功能已禁用")
            return
        
        try:
            self.client = MongoClient(
                MONGO_CONFIG['connection_string'],
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            # 测试连接
            self.client.admin.command('ping')
            self.db = self.client[MONGO_CONFIG['database']]
            self.collection = self.db['function_usage_details']
            logger.info(f"[MongoInteractionDAO] MongoDB连接成功: {MONGO_CONFIG['host']}:{MONGO_CONFIG['port']}")
        except Exception as e:
            logger.error(f"[MongoInteractionDAO] MongoDB连接失败: {e}", exc_info=True)
            self.client = None
            self.db = None
    
    def save_details(
        self,
        record_id: str,
        session_id: Optional[str],
        user_id: str,
        function_type: str,
        function_name: str,
        frontend_input: Dict[str, Any],
        input_data: Dict[str, Any],
        llm_output: str,
        performance: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        保存详细数据到MongoDB
        
        Returns:
            str: MongoDB文档ID，失败返回None
        """
        if not self.collection:
            logger.warning("[MongoInteractionDAO] MongoDB不可用，跳过保存")
            return None
        
        try:
            # 格式化input_data为字符串（用于查看）
            input_data_formatted = json.dumps(input_data, ensure_ascii=False, indent=2)
            input_data_size = len(json.dumps(input_data, ensure_ascii=False).encode('utf-8'))
            
            # 计算输出大小
            llm_output_size = len(llm_output.encode('utf-8')) if llm_output else 0
            
            document = {
                'record_id': record_id,
                'session_id': session_id,
                'user_id': user_id,
                'function_type': function_type,
                'function_name': function_name,
                
                # 前端输入（完整）
                'frontend_input': frontend_input,
                
                # 给大模型的input_data（完整，必须记录）
                'input_data': {
                    'full_content': input_data,
                    'formatted_string': input_data_formatted,
                    'size_bytes': input_data_size
                },
                
                # 大模型输出（完整）
                'llm_output': {
                    'full_content': llm_output,
                    'streaming': metadata.get('streaming', False),
                    'size_bytes': llm_output_size
                },
                
                # 性能指标（详细）
                'performance': performance,
                
                # 元数据
                'metadata': metadata,
                
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            result = self.collection.insert_one(document)
            doc_id = str(result.inserted_id)
            logger.debug(f"[MongoInteractionDAO] 详细数据保存成功: record_id={record_id}, doc_id={doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"[MongoInteractionDAO] 保存详细数据失败: {e}", exc_info=True)
            return None
    
    def get_details_by_record_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """根据记录ID获取详细数据"""
        if not self.collection:
            return None
        
        try:
            document = self.collection.find_one({'record_id': record_id})
            if document:
                # 转换ObjectId为字符串
                document['_id'] = str(document['_id'])
            return document
        except Exception as e:
            logger.error(f"[MongoInteractionDAO] 获取详细数据失败: {e}", exc_info=True)
            return None
    
    def close(self):
        """关闭MongoDB连接"""
        if self.client:
            self.client.close()
            logger.info("[MongoInteractionDAO] MongoDB连接已关闭")


# 全局实例
_mongo_dao_instance: Optional[MongoInteractionDAO] = None


def get_mongo_dao() -> MongoInteractionDAO:
    """获取MongoDB DAO实例（单例）"""
    global _mongo_dao_instance
    if _mongo_dao_instance is None:
        _mongo_dao_instance = MongoInteractionDAO()
    return _mongo_dao_instance

