#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蓝新金流（NewebPay）支付客户端封装
支持蓝新金流MPG支付功能
使用AES-256-CBC加密和SHA256签名
"""

import os
import logging
import hashlib
import urllib.parse
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    import binascii
    CRYPTO_AVAILABLE = True
except ImportError:
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import padding
        CRYPTO_AVAILABLE = True
        CRYPTO_LIB = "cryptography"
    except ImportError:
        CRYPTO_AVAILABLE = False
        CRYPTO_LIB = None
        logging.warning("pycryptodome 或 cryptography 库未安装，请运行: pip install pycryptodome 或 pip install cryptography")

# 导入支付配置加载器
try:
    from services.payment_service.payment_config_loader import get_payment_config, get_payment_environment
except ImportError:
    # 降级到环境变量
    def get_payment_config(provider: str, config_key: str, environment: str = 'production', default: Optional[str] = None) -> Optional[str]:
        return os.getenv(f"{provider.upper()}_{config_key.upper()}", default)
    def get_payment_environment(default: str = 'production') -> str:
        return os.getenv("PAYMENT_ENVIRONMENT", default)

logger = logging.getLogger(__name__)


class NewebPayClient:
    """蓝新金流支付客户端"""
    
    def __init__(self, environment: Optional[str] = None):
        """
        初始化蓝新金流客户端
        
        Args:
            environment: 环境（production/test），如果为None则自动查找is_active=1的记录
        """
        # 从数据库读取配置，自动查找is_active=1的记录
        # 如果指定了environment，则优先匹配该环境且is_active=1的记录
        self.merchant_id = get_payment_config('newebpay', 'merchant_id', environment) or os.getenv("NEWEBPAY_MERCHANT_ID")
        self.hash_key = get_payment_config('newebpay', 'hash_key', environment) or os.getenv("NEWEBPAY_HASH_KEY")
        self.hash_iv = get_payment_config('newebpay', 'hash_iv', environment) or os.getenv("NEWEBPAY_HASH_IV")
        mode_from_db = get_payment_config('newebpay', 'mode', environment)
        self.mode = mode_from_db or os.getenv("NEWEBPAY_MODE", "test")  # test or production
        
        # 设置API基础URL
        if self.mode == "production":
            production_url = get_payment_config('newebpay', 'production_url', environment)
            self.gateway_url = production_url or os.getenv(
                "NEWEBPAY_PRODUCTION_URL",
                "https://ccore.newebpay.com"
            )
        else:
            test_url = get_payment_config('newebpay', 'test_url', environment)
            self.gateway_url = test_url or os.getenv(
                "NEWEBPAY_TEST_URL",
                "https://ccore.newebpay.com"  # 测试环境通常使用相同URL，但需要测试商户号
            )
        
        if not self.merchant_id:
            logger.warning("蓝新金流商户ID未配置（数据库或环境变量）")
        
        if not CRYPTO_AVAILABLE:
            logger.error("加密库未安装，无法使用蓝新金流功能")
    
    @property
    def is_enabled(self) -> bool:
        """检查蓝新金流客户端是否已启用"""
        return bool(self.merchant_id and self.hash_key and self.hash_iv and CRYPTO_AVAILABLE)
    
    def _encrypt_trade_info(self, data_string: str) -> str:
        """
        AES-256-CBC 加密 TradeInfo
        
        Args:
            data_string: 待加密的参数字符串
        
        Returns:
            加密后的十六进制字符串（大写）
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("加密库未安装")
        
        try:
            # 确保 key 和 IV 长度正确（AES-256需要32字节，AES-128需要16字节）
            # 蓝新金流通常使用 AES-256，但 key 和 IV 都是32字节
            key = self.hash_key.encode('utf-8')
            iv = self.hash_iv.encode('utf-8')
            
            # 如果 key/IV 长度不足，进行填充
            if len(key) < 32:
                key = key.ljust(32, b'\0')
            elif len(key) > 32:
                key = key[:32]
            
            if len(iv) < 16:
                iv = iv.ljust(16, b'\0')
            elif len(iv) > 16:
                iv = iv[:16]
            
            # 使用 pycryptodome
            if CRYPTO_LIB != "cryptography":
                cipher = AES.new(key, AES.MODE_CBC, iv)
                padded_data = pad(data_string.encode('utf-8'), AES.block_size)
                encrypted = cipher.encrypt(padded_data)
                return binascii.hexlify(encrypted).decode('utf-8').upper()
            else:
                # 使用 cryptography
                backend = default_backend()
                cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
                encryptor = cipher.encryptor()
                padder = padding.PKCS7(128).padder()
                padded_data = padder.update(data_string.encode('utf-8')) + padder.finalize()
                encrypted = encryptor.update(padded_data) + encryptor.finalize()
                return binascii.hexlify(encrypted).decode('utf-8').upper()
        
        except Exception as e:
            logger.error(f"加密TradeInfo失败: {e}")
            raise
    
    def _create_trade_sha(self, encrypted_info: str) -> str:
        """
        生成 SHA256 签名（TradeSha）
        
        Args:
            encrypted_info: 加密后的TradeInfo
        
        Returns:
            SHA256签名字符串（大写）
        """
        sha_string = f"HashKey={self.hash_key}&{encrypted_info}&HashIV={self.hash_iv}"
        return hashlib.sha256(sha_string.encode('utf-8')).hexdigest().upper()
    
    def _decrypt_trade_info(self, encrypted_info: str) -> Dict[str, Any]:
        """
        解密 TradeInfo（用于回调验证）
        
        Args:
            encrypted_info: 加密的TradeInfo
        
        Returns:
            解密后的参数字典
        """
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("加密库未安装")
        
        try:
            key = self.hash_key.encode('utf-8')
            iv = self.hash_iv.encode('utf-8')
            
            # 确保长度正确
            if len(key) < 32:
                key = key.ljust(32, b'\0')
            elif len(key) > 32:
                key = key[:32]
            
            if len(iv) < 16:
                iv = iv.ljust(16, b'\0')
            elif len(iv) > 16:
                iv = iv[:16]
            
            encrypted_bytes = binascii.unhexlify(encrypted_info)
            
            # 使用 pycryptodome
            if CRYPTO_LIB != "cryptography":
                cipher = AES.new(key, AES.MODE_CBC, iv)
                decrypted = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
            else:
                # 使用 cryptography
                backend = default_backend()
                cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
                decryptor = cipher.decryptor()
                unpadder = padding.PKCS7(128).unpadder()
                decrypted = unpadder.update(decryptor.update(encrypted_bytes) + decryptor.finalize()) + unpadder.finalize()
            
            # 解析查询字符串
            data_string = decrypted.decode('utf-8')
            params = urllib.parse.parse_qs(data_string)
            
            # 将列表值转换为单个值
            result = {}
            for key, value in params.items():
                result[key] = value[0] if isinstance(value, list) and len(value) > 0 else value
            
            return result
        
        except Exception as e:
            logger.error(f"解密TradeInfo失败: {e}")
            raise
    
    def create_payment(
        self,
        amount: str,
        product_name: str,
        order_id: Optional[str] = None,
        return_url: Optional[str] = None,
        notify_url: Optional[str] = None,
        client_back_url: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建蓝新金流支付订单
        
        Args:
            amount: 金额（字符串，如"100"）
            product_name: 商品名称
            order_id: 商户订单号（可选，如不提供则自动生成）
            return_url: 支付完成后跳转URL
            notify_url: 异步通知URL
            client_back_url: 客户返回URL
            email: 付款人邮箱
        
        Returns:
            包含payment_url和form_data的字典
        """
        if not self.is_enabled:
            return {
                "success": False,
                "error": "蓝新金流客户端未初始化"
            }
        
        try:
            # 生成订单号
            if not order_id:
                import time
                order_id = f"ORDER_{int(time.time() * 1000)}"
            
            # 设置默认URL
            # 从数据库读取URL，如果数据库中没有则降级到环境变量
            frontend_base = get_payment_config('shared', 'frontend_base_url') or os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")
            api_base = get_payment_config('shared', 'api_base_url') or os.getenv("API_BASE_URL", "http://localhost:8001")
            
            if not return_url:
                return_url = f"{frontend_base}/frontend/payment-success.html?provider=newebpay"
            
            if not notify_url:
                notify_url = f"{api_base}/api/v1/payment/webhook/newebpay"
            
            if not client_back_url:
                client_back_url = f"{frontend_base}/frontend/payment-cancel.html?provider=newebpay"
            
            # 构建订单参数
            trade_params = {
                "MerchantID": self.merchant_id,
                "RespondType": "JSON",
                "TimeStamp": str(int(datetime.now().timestamp())),
                "Version": "2.0",
                "MerchantOrderNo": order_id,
                "Amt": str(int(float(amount))),  # 金额必须是整数
                "ItemDesc": product_name,
                "ReturnURL": return_url,
                "NotifyURL": notify_url,
                "ClientBackURL": client_back_url
            }
            
            # 添加邮箱（如果提供）
            if email:
                trade_params["Email"] = email
            
            # 将参数转换为查询字符串
            trade_info_string = urllib.parse.urlencode(trade_params)
            
            # 加密TradeInfo
            encrypted_trade_info = self._encrypt_trade_info(trade_info_string)
            
            # 生成TradeSha
            trade_sha = self._create_trade_sha(encrypted_trade_info)
            
            # 构建表单数据
            form_data = {
                "MerchantID": self.merchant_id,
                "TradeInfo": encrypted_trade_info,
                "TradeSha": trade_sha,
                "Version": "2.0"
            }
            
            return {
                "success": True,
                "order_id": order_id,
                "payment_url": f"{self.gateway_url}/MPG/mpg_gateway",
                "form_data": form_data,
                "status": "created",
                "message": "蓝新金流订单创建成功"
            }
        
        except Exception as e:
            logger.error(f"创建蓝新金流订单失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_payment(self, order_id: str) -> Dict[str, Any]:
        """
        查询支付状态（通过API查询）
        
        注意：蓝新金流主要通过回调通知来确认支付状态
        此方法用于主动查询，但可能不是所有商户都支持
        
        Args:
            order_id: 商户订单号
        
        Returns:
            支付状态信息
        """
        if not self.is_enabled:
            return {
                "success": False,
                "error": "蓝新金流客户端未初始化"
            }
        
        # 蓝新金流的查询接口需要特殊实现
        # 这里返回一个提示，建议使用回调通知
        logger.warning("蓝新金流建议使用回调通知来确认支付状态")
        return {
            "success": False,
            "error": "请使用回调通知来确认支付状态，或联系蓝新金流技术支持获取查询API"
        }
    
    def verify_notify(self, trade_info: str, trade_sha: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        验证回调通知签名并解密数据
        
        Args:
            trade_info: 加密的TradeInfo
            trade_sha: 签名
        
        Returns:
            (签名是否有效, 解密后的数据)
        """
        if not self.is_enabled:
            return False, None
        
        try:
            # 验证签名
            calculated_sha = self._create_trade_sha(trade_info)
            if calculated_sha != trade_sha:
                logger.warning("蓝新金流签名验证失败")
                return False, None
            
            # 解密数据
            decrypted_data = self._decrypt_trade_info(trade_info)
            
            return True, decrypted_data
        
        except Exception as e:
            logger.error(f"验证蓝新金流回调失败: {e}")
            return False, None
    
    def refund(
        self,
        order_id: str,
        amount: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        退款
        
        注意：蓝新金流的退款需要通过后台操作或调用特定API
        这里提供基本结构，具体实现需要根据蓝新金流的退款API文档
        
        Args:
            order_id: 商户订单号
            amount: 退款金额（可选，不提供则全额退款）
        
        Returns:
            退款结果
        """
        if not self.is_enabled:
            return {
                "success": False,
                "error": "蓝新金流客户端未初始化"
            }
        
        # 蓝新金流的退款需要特殊实现
        # 这里返回一个提示
        logger.warning("蓝新金流退款功能需要根据具体API文档实现")
        return {
            "success": False,
            "error": "退款功能需要联系蓝新金流技术支持获取退款API文档"
        }
