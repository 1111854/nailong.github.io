# message_display.py
import streamlit as st
import os
from config import BASE_DIR

def get_avatar(role):
    """获取头像（只使用本地图片文件）"""
    
    if role == "user":
        avatar_path = os.path.join(BASE_DIR, "User_avatar.png")
    else:
        avatar_path = os.path.join(BASE_DIR, "AI_avatar.png")
    
    # 直接返回图片路径，不管文件存不存在
    return avatar_path

def copy_to_clipboard(text):
    st.toast("📋 请手动选中文本后按 Ctrl+C 复制", icon="📋")
    return True
