# -*- coding: utf-8 -*-
"""
模型微调服务配置
"""
import os

# 服务配置
SERVICE_HOST = os.getenv("MODEL_TUNING_SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("MODEL_TUNING_SERVICE_PORT", "9011"))

# 模型配置
BASE_MODEL_NAME = os.getenv("BASE_MODEL_NAME", "hfl/chinese-roberta-wwm-ext")
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "./models_cache")
TUNED_MODEL_DIR = os.getenv("TUNED_MODEL_DIR", "./tuned_models")

# 训练配置
BATCH_SIZE = int(os.getenv("TRAINING_BATCH_SIZE", "16"))
LEARNING_RATE = float(os.getenv("TRAINING_LEARNING_RATE", "2e-5"))
EPOCHS = int(os.getenv("TRAINING_EPOCHS", "3"))
MIN_QUESTIONS_FOR_TRAINING = int(os.getenv("MIN_QUESTIONS_FOR_TRAINING", "100"))

# 规则扩展配置
AUTO_EXTRACT_KEYWORDS = os.getenv("AUTO_EXTRACT_KEYWORDS", "true").lower() == "true"
MIN_KEYWORD_FREQUENCY = int(os.getenv("MIN_KEYWORD_FREQUENCY", "3"))
MIN_KEYWORD_CONFIDENCE = float(os.getenv("MIN_KEYWORD_CONFIDENCE", "0.8"))

