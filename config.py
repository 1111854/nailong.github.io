import os

API_URL = "https://mynewapi.n1neman.fun/v1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

for dir_path in [HISTORY_DIR, UPLOAD_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)