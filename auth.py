# auth.py
import os
import json
from datetime import datetime
from config import BASE_DIR, HISTORY_DIR

def register_user(username):
    users_file = os.path.join(BASE_DIR, "users.json")
    users = {}
    if os.path.exists(users_file):
        with open(users_file, "r", encoding="utf-8") as f:
            users = json.load(f)
    if username in users:
        return False, "用户名已存在"
    users[username] = {"created_at": datetime.now().isoformat()}
    with open(users_file, "w", encoding="utf-8") as f:
        json.dump(users, f)
    return True, "注册成功"

def login_user(username):
    users_file = os.path.join(BASE_DIR, "users.json")
    if not os.path.exists(users_file):
        return False, "用户不存在"
    with open(users_file, "r", encoding="utf-8") as f:
        users = json.load(f)
    if username in users:
        return True, "登录成功"
    return False, "用户不存在"

def save_user_conversation(username, session_id, data):
    user_dir = os.path.join(HISTORY_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, f"{session_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def load_user_conversations(username):
    user_dir = os.path.join(HISTORY_DIR, username)
    if not os.path.exists(user_dir):
        return {}
    conversations = {}
    for filename in os.listdir(user_dir):
        if filename.endswith(".json"):
            session_id = filename[:-5]
            with open(os.path.join(user_dir, filename), "r", encoding="utf-8") as f:
                conversations[session_id] = json.load(f)
    return conversations

def delete_user_conversation(username, session_id):
    user_dir = os.path.join(HISTORY_DIR, username)
    file_path = os.path.join(user_dir, f"{session_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False
