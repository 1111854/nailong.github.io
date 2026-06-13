# config.py
import os

# API 配置
API_URL = "https://mynewapi.n1neman.fun/v1"
DEEPSEEK_URL = "https://api.deepseek.com"

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# 聊天配置
MAX_HISTORY = 12
UPDATE_INTERVAL = 0.03

# 模型配置（从 utils 导入，这里先留空）
# AVAILABLE_MODELS 和 DEFAULT_MODEL 在 utils.py 中定义
