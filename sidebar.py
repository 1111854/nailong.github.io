# sidebar.py - 稳定版（无自动刷新）
import streamlit as st
import os
import shutil
from datetime import datetime
from config import API_URL, DEEPSEEK_URL, BASE_DIR
from utils import AVAILABLE_MODELS, DEFAULT_MODEL, THINKING_MODELS, SEARCH_ENABLED_MODELS
from conversation import list_conversations, load_conversation, delete_conversation

def render_sidebar():
    with st.sidebar:
        st.markdown(f"### 👤 用户：{st.session_state.username}")
        
        with st.expander("🎨 修改头像", expanded=False):
            # 用户头像
            st.markdown("**👤 用户头像**")
            user_choice = st.selectbox("", ["默认", "上传图片"], key="user_choice", label_visibility="collapsed")
            if user_choice == "上传图片":
                img = st.file_uploader("", type=['png', 'jpg'], key="user_img", label_visibility="collapsed")
                if img:
                    with open(os.path.join(BASE_DIR, "User_avatar.png"), "wb") as f:
                        f.write(img.getbuffer())
                    st.success("✅ 已更新，下次发送消息时生效")
            
            st.markdown("---")
            
            # AI头像
            st.markdown("**🤖 AI头像**")
            ai_choice = st.selectbox("", ["默认", "上传图片"], key="ai_choice", label_visibility="collapsed")
            if ai_choice == "上传图片":
                img = st.file_uploader("", type=['png', 'jpg'], key="ai_img", label_visibility="collapsed")
                if img:
                    with open(os.path.join(BASE_DIR, "AI_avatar.png"), "wb") as f:
                        f.write(img.getbuffer())
                    st.success("✅ 已更新，下次发送消息时生效")
        
        if st.button("🚪 退出登录"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        
        gif_path = os.path.join(BASE_DIR, "banner.gif")
        if os.path.exists(gif_path):
            st.image(gif_path)

        api_key_env = os.environ.get('CAPI')
        if api_key_env:
            st.session_state.api_key = api_key_env
        elif not st.session_state.api_key:
            key = st.text_input("API密钥", type="password")
            if key:
                st.session_state.api_key = key
                st.rerun()

        st.markdown("---")
        
        st.subheader("🤖 模型选择")
        selected_model = st.selectbox("", AVAILABLE_MODELS, index=AVAILABLE_MODELS.index(st.session_state.selected_model) if st.session_state.selected_model in AVAILABLE_MODELS else 0)
        if selected_model != st.session_state.selected_model:
            st.session_state.selected_model = selected_model
            st.rerun()
        
        if selected_model == "deepseek-v4-pro":
            st.session_state.api_url = DEEPSEEK_URL
        else:
            st.session_state.api_url = API_URL

        st.markdown("---")
        
        st.subheader("🎭 AI角色设定")
        new_prompt = st.text_area("", value=st.session_state.system_prompt, height=120)
        if st.button("💾 保存"):
            st.session_state.system_prompt = new_prompt
            st.success("已保存")

        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✨ 新建", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        with col2:
            if st.button("🗑️ 删除当前", use_container_width=True):
                if st.session_state.messages:
                    st.session_state.messages = []
                    st.rerun()

        st.markdown("---")
        st.caption(f"消息数: {len(st.session_state.messages)}")
