# message_display.py
import streamlit as st
import os
from config import BASE_DIR

def get_avatar(role):
    if role == "user":
        avatar_path = os.path.join(BASE_DIR, "User_avatar.png")
    else:
        avatar_path = os.path.join(BASE_DIR, "AI_avatar.png")
    
    if os.path.exists(avatar_path):
        return avatar_path
    return "🐉" if role == "user" else "🤖"

def copy_to_clipboard(text):
    st.toast("📋 请手动选中文本后按 Ctrl+C 复制", icon="📋")
    return True
