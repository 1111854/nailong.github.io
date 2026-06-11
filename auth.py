import os
import json
from datetime import datetime

AUTH_FILE = "users.json"

def load_users():
    """加载用户数据"""
    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    """保存用户数据"""
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def register_user(username):
    """注册新用户"""
    if not username or not username.strip():
        return False, "用户名不能为空"
    
    users = load_users()
    if username in users:
        return False, "用户名已存在"
    
    users[username] = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "conversations": {}
    }
    save_users(users)
    return True, "注册成功"

def login_user(username):
    """登录用户"""
    if not username or not username.strip():
        return False, "用户名不能为空"
    
    users = load_users()
    if username not in users:
        return False, "用户名不存在，请先注册"
    return True, "登录成功"

def save_user_conversation(username, session_id, conversation_data):
    """保存用户的对话"""
    users = load_users()
    if username in users:
        if "conversations" not in users[username]:
            users[username]["conversations"] = {}
        users[username]["conversations"][session_id] = conversation_data
        save_users(users)
        return True
    return False

def load_user_conversations(username):
    """加载用户的所有对话"""
    users = load_users()
    if username in users:
        return users[username].get("conversations", {})
    return {}

def delete_user_conversation(username, session_id):
    """删除用户的对话"""
    users = load_users()
    if username in users and "conversations" in users[username]:
        if session_id in users[username]["conversations"]:
            del users[username]["conversations"][session_id]
            save_users(users)
            return True
    return False