# message_display.py - 无 PIL 版本
import streamlit as st
import os
import base64
from config import BASE_DIR

def get_avatar(role):
    """获取头像（支持自定义设置）"""
    
    if role == "user":
        avatar_type = st.session_state.get('user_avatar_type', 'emoji')
        
        if avatar_type == 'emoji':
            return st.session_state.get('user_avatar', '👤')
        elif avatar_type == 'image' and st.session_state.get('user_avatar_image'):
            # 直接返回图片的 base64（不调整大小）
            img_file = st.session_state.user_avatar_image
            img_file.seek(0)
            img_str = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{img_str}"
        elif avatar_type == 'url' and st.session_state.get('user_avatar_url'):
            return st.session_state.user_avatar_url
        else:
            avatar_path = os.path.join(BASE_DIR, "User_avatar.png")
            if os.path.exists(avatar_path):
                return avatar_path
            return "👤"
    
    else:  # assistant
        avatar_type = st.session_state.get('ai_avatar_type', 'emoji')
        
        if avatar_type == 'emoji':
            return st.session_state.get('ai_avatar', '🤖')
        elif avatar_type == 'image' and st.session_state.get('ai_avatar_image'):
            img_file = st.session_state.ai_avatar_image
            img_file.seek(0)
            img_str = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{img_str}"
        elif avatar_type == 'url' and st.session_state.get('ai_avatar_url'):
            return st.session_state.ai_avatar_url
        else:
            avatar_path = os.path.join(BASE_DIR, "AI_avatar.png")
            if os.path.exists(avatar_path):
                return avatar_path
            return "🤖"

def copy_to_clipboard(text):
    st.toast("📋 请手动选中文本后按 Ctrl+C 复制", icon="📋")
    return True
