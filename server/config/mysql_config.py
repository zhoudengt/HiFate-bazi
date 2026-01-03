#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 配置模块 - 支持连接池
"""

import pymysql
from pymysql.cursors import DictCursor
from typing import Optional, Dict, Any
import os
import queue
import threading
import time

# MySQL 连接配置（从环境变量读取）
# ⚠️ 重要：所有环境统一连接生产Node1 Docker MySQL，确保数据一致性
# 生产Node1 Docker MySQL: 8.210.52.217:3306 (公网) / 172.18.121.222:3306 (内网)
# 用户名: root, 密码: Yuanqizhan@163, 数据库: hifate_bazi
mysql_config = {
    'host': os.getenv('MYSQL_HOST', '8.210.52.217'),  # 默认连接生产Node1公网IP
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', os.getenv('MYSQL_ROOT_PASSWORD', 'Yuanqizhan@163')),  # 默认使用生产密码
    'database': os.getenv('MYSQL_DATABASE', 'hifate_bazi'),
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
    'autocommit': False,
    'use_unicode': True,
    'init_command': "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
}

# MySQL 连接池配置
# 优化说明：
# - mincached=2：减少服务启动时连接数（11服务×2=22 < 40，避免超过max_user_connections）
# - maxcached=20：减少最大缓存连接数，节省资源
# - maxconnections=30：每个服务最多30个连接（根据15个用户需求调整）
# - recycle_time=300：连接回收时间5分钟，确保空闲连接及时回收
MYSQL_POOL_CONFIG = {
    'mincached': 2,         # 最小连接数（从5减少到2，减少启动时连接数）
    'maxcached': 20,        # 最大缓存连接数（从30减少到20）
    'maxconnections': 30,   # 最大连接数（从50减少到30，每个服务最多30个连接）
    'connection_timeout': 30,  # 获取连接的超时时间（秒）
    'recycle_time': 300,     # 连接回收时间（秒），超过此时间未使用的连接将被关闭（5分钟）
}

# 全局连接池实例
_mysql_pool: Optional['MySQLConnectionPool'] = None
_pool_lock = threading.Lock()


class MySQLConnectionPool:
    """MySQL连接池管理器"""
    
    def __init__(self, mincached=10, maxcached=50, maxconnections=100, 
                 connection_timeout=30, recycle_time=3600):
        """
        初始化连接池
        
        Args:
            mincached: 最小连接数
            maxcached: 最大缓存连接数
            maxconnections: 最大连接数
            connection_timeout: 获取连接的超时时间（秒）
            recycle_time: 连接回收时间（秒）
        """
        self.mincached = mincached
        self.maxcached = maxcached
        self.maxconnections = maxconnections
        self.connection_timeout = connection_timeout
        self.recycle_time = recycle_time
        
        # 连接队列：存储可用的连接
        self._pool: queue.Queue = queue.Queue(maxsize=maxcached)
        
        # 当前连接数（包括在池中的和在使用的）
        self._current_connections = 0
        self._lock = threading.Lock()
        
        # 连接创建时间记录（用于连接回收）
        self._connection_times: Dict[int, float] = {}
        
        # 预创建最小连接数
        self._init_pool()
    
    def _init_pool(self):
        """初始化连接池，创建最小连接数"""
        for _ in range(self.mincached):
            try:
                conn = self._create_connection()
                if conn:
                    self._pool.put(conn)
            except Exception as e:
                print(f"⚠️  初始化连接池时创建连接失败: {e}")
                break
        print(f"✓ MySQL连接池初始化成功 (min={self.mincached}, max={self.maxconnections})")
    
    def _create_connection(self) -> Optional[pymysql.Connection]:
        """创建新连接"""
        try:
            with self._lock:
                if self._current_connections >= self.maxconnections:
                    return None
                self._current_connections += 1
            
            conn = pymysql.connect(**mysql_config)
            conn_id = id(conn)
            self._connection_times[conn_id] = time.time()
            return conn
        except Exception as e:
            print(f"✗ 创建MySQL连接失败: {e}")
            with self._lock:
                self._current_connections -= 1
            return None
    
    def _is_connection_valid(self, conn: pymysql.Connection) -> bool:
        """检查连接是否有效（优化：连接断开时立即返回False）"""
        try:
            # 先检查连接是否已关闭
            if not conn.open:
                return False
            
            # ping检查连接是否可用
            conn.ping(reconnect=False)
            
            # 检查连接是否过期（超过回收时间）
            conn_id = id(conn)
            if conn_id in self._connection_times:
                age = time.time() - self._connection_times[conn_id]
                if age > self.recycle_time:
                    return False
            return True
        except Exception:
            # 连接断开或异常，立即返回False，触发连接回收
            return False
    
    def connection(self, timeout: Optional[float] = None) -> pymysql.Connection:
        """
        从连接池获取连接
        
        Args:
            timeout: 超时时间（秒），None表示使用默认值
            
        Returns:
            pymysql.Connection: 数据库连接对象
        """
        timeout = timeout or self.connection_timeout
        
        # 尝试从池中获取连接
        try:
            conn = self._pool.get(timeout=timeout)
            
            # 检查连接是否有效
            if self._is_connection_valid(conn):
                return conn
            else:
                # 连接无效，关闭并创建新连接
                try:
                    conn.close()
                except Exception:
                    pass
                with self._lock:
                    self._current_connections -= 1
                    conn_id = id(conn)
                    if conn_id in self._connection_times:
                        del self._connection_times[conn_id]
                
                # 创建新连接
                new_conn = self._create_connection()
                if new_conn:
                    return new_conn
        except queue.Empty:
            # 池中没有可用连接，尝试创建新连接
            pass
        
        # 创建新连接
        new_conn = self._create_connection()
        if new_conn:
            return new_conn
        
        # 如果无法创建新连接，抛出异常
        raise Exception(f"无法获取MySQL连接：已达到最大连接数 {self.maxconnections}")
    
    def return_connection(self, conn: pymysql.Connection):
        """将连接返回到连接池"""
        try:
            # 检查连接是否有效
            if not self._is_connection_valid(conn):
                # 连接无效，关闭连接
                conn.close()
                with self._lock:
                    self._current_connections -= 1
                    conn_id = id(conn)
                    if conn_id in self._connection_times:
                        del self._connection_times[conn_id]
                return
            
            # 将连接返回到池中（如果池未满）
            try:
                self._pool.put_nowait(conn)
            except queue.Full:
                # 池已满，关闭连接
                conn.close()
                with self._lock:
                    self._current_connections -= 1
                    conn_id = id(conn)
                    if conn_id in self._connection_times:
                        del self._connection_times[conn_id]
        except Exception as e:
            # 发生异常，关闭连接
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._current_connections -= 1
                conn_id = id(conn)
                if conn_id in self._connection_times:
                    del self._connection_times[conn_id]
    
    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                pass
        
        with self._lock:
            self._current_connections = 0
            self._connection_times.clear()
    
    def cleanup_idle_connections(self, max_idle_time: int = 300):
        """
        清理长时间未使用的连接
        
        Args:
            max_idle_time: 最大空闲时间（秒），默认300秒（5分钟）
        
        Returns:
            int: 清理的连接数
        """
        cleaned = 0
        current_time = time.time()
        valid_conns = []
        
        # 清理池中的连接
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn_id = id(conn)
                
                # 检查连接是否过期
                if conn_id in self._connection_times:
                    age = current_time - self._connection_times[conn_id]
                    if age > max_idle_time:
                        # 连接过期，关闭
                        try:
                            conn.close()
                        except Exception:
                            pass
                        with self._lock:
                            self._current_connections -= 1
                            del self._connection_times[conn_id]
                        cleaned += 1
                        continue
                
                # 检查连接是否有效
                if self._is_connection_valid(conn):
                    valid_conns.append(conn)
                else:
                    # 连接无效，关闭
                    try:
                        conn.close()
                    except Exception:
                        pass
                    with self._lock:
                        self._current_connections -= 1
                        if conn_id in self._connection_times:
                            del self._connection_times[conn_id]
                    cleaned += 1
            except Exception:
                pass
        
        # 将有效连接放回池中
        for conn in valid_conns:
            try:
                self._pool.put_nowait(conn)
            except queue.Full:
                # 池已满，关闭连接
                try:
                    conn.close()
                except Exception:
                    pass
                with self._lock:
                    self._current_connections -= 1
                    conn_id = id(conn)
                    if conn_id in self._connection_times:
                        del self._connection_times[conn_id]
                cleaned += 1
        
        return cleaned


def _init_mysql_pool():
    """初始化MySQL连接池"""
    global _mysql_pool
    
    if _mysql_pool is not None:
        return _mysql_pool
    
    try:
        _mysql_pool = MySQLConnectionPool(
            mincached=MYSQL_POOL_CONFIG['mincached'],
            maxcached=MYSQL_POOL_CONFIG['maxcached'],
            maxconnections=MYSQL_POOL_CONFIG['maxconnections'],
            connection_timeout=MYSQL_POOL_CONFIG['connection_timeout'],
            recycle_time=MYSQL_POOL_CONFIG['recycle_time']
        )
        return _mysql_pool
    except Exception as e:
        print(f"✗ MySQL连接池初始化失败: {e}")
        return None


def get_mysql_connection():
    """
    获取 MySQL 数据库连接（支持连接池）
    
    优先使用连接池，如果连接池不可用则回退到单连接模式
    
    Returns:
        pymysql.Connection: 数据库连接对象
    """
    global _mysql_pool
    
    with _pool_lock:
        # 初始化连接池（如果还未初始化）
        if _mysql_pool is None:
            _mysql_pool = _init_mysql_pool()
    
    # 如果连接池可用，从连接池获取连接
    if _mysql_pool is not None:
        try:
            return _mysql_pool.connection()
        except Exception as e:
            print(f"⚠️  从连接池获取连接失败，回退到单连接模式: {e}")
            # 连接池失败时回退到单连接模式
    
    # 回退到单连接模式
    try:
        connection = pymysql.connect(**mysql_config)
        return connection
    except Exception as e:
        print(f"MySQL 连接失败: {e}")
        raise


def return_mysql_connection(conn: pymysql.Connection):
    """
    将MySQL连接返回到连接池（如果使用连接池）
    
    Args:
        conn: 数据库连接对象
    """
    global _mysql_pool
    
    if _mysql_pool is not None:
        _mysql_pool.return_connection(conn)
    else:
        # 不使用连接池时，直接关闭连接
        try:
            conn.close()
        except Exception:
            pass


def cleanup_idle_mysql_connections(max_idle_time: int = 300):
    """
    清理长时间未使用的MySQL连接
    
    Args:
        max_idle_time: 最大空闲时间（秒），默认300秒（5分钟）
    
    Returns:
        int: 清理的连接数
    """
    global _mysql_pool
    
    if _mysql_pool is None:
        return 0
    
    try:
        cleaned = _mysql_pool.cleanup_idle_connections(max_idle_time)
        if cleaned > 0:
            print(f"✓ 清理了 {cleaned} 个长时间未使用的MySQL连接")
        return cleaned
    except Exception as e:
        print(f"⚠️  清理MySQL连接失败: {e}")
        return 0


def get_connection_pool_stats() -> Dict[str, Any]:
    """
    获取连接池统计信息
    
    Returns:
        dict: 连接池统计信息，包括当前连接数、池大小等
    """
    global _mysql_pool
    
    if _mysql_pool is None:
        return {"status": "not_initialized"}
    
    try:
        with _mysql_pool._lock:
            return {
                "status": "active",
                "current_connections": _mysql_pool._current_connections,
                "pool_size": _mysql_pool._pool.qsize(),
                "max_connections": _mysql_pool.maxconnections,
                "min_cached": _mysql_pool.mincached,
                "max_cached": _mysql_pool.maxcached,
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def test_mysql_connection() -> bool:
    """测试 MySQL 连接（使用连接池）"""
    try:
        conn = get_mysql_connection()
        return_mysql_connection(conn)
        print(f"✓ MySQL 连接成功（使用连接池）: {mysql_config['host']}:{mysql_config['port']}")
        return True
    except Exception as e:
        print(f"✗ MySQL 连接失败: {e}")
        return False


def execute_query(sql: str, params: tuple = None) -> list:
    """
    执行查询语句（使用连接池）
    
    Args:
        sql: SQL 语句
        params: 参数元组
        
    Returns:
        list: 查询结果
    """
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        return_mysql_connection(conn)


def execute_update(sql: str, params: tuple = None) -> int:
    """
    执行更新语句（使用连接池）
    
    Args:
        sql: SQL 语句
        params: 参数元组
        
    Returns:
        int: 影响的行数
    """
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            affected = cursor.execute(sql, params)
            conn.commit()
            return affected
    except Exception as e:
        conn.rollback()
        raise
    finally:
        return_mysql_connection(conn)








































