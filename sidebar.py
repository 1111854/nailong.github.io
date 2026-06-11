import streamlit as st
import os
from datetime import datetime
from utils import AVAILABLE_MODELS, DEFAULT_MODEL
from conversation import delete_conversation, list_conversations, load_conversation

def render_sidebar():
    with st.sidebar:
        st.markdown("### 🐉 奶龙ChatGPT")
        
        gif_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banner.gif")
        if os.path.exists(gif_path):
            st.image(gif_path)
        
        # API密钥
        api_key = os.environ.get('CAPI')
        if api_key:
            st.session_state.api_key = api_key
            st.success("✅ API密钥已设置")
        elif not st.session_state.get('api_key'):
            api_key_input = st.text_input("输入API密钥", type="password", key="api_input")
            if api_key_input:
                st.session_state.api_key = api_key_input
                st.rerun()
        
        st.markdown("---")
        
        # 模型选择
        st.subheader("🤖 模型选择")
        idx = AVAILABLE_MODELS.index(st.session_state.selected_model) if st.session_state.selected_model in AVAILABLE_MODELS else 0
        selected = st.selectbox("选择AI模型", options=AVAILABLE_MODELS, index=idx)
        if selected != st.session_state.selected_model:
            st.session_state.selected_model = selected
            st.rerun()
        st.caption(f"当前模型: `{st.session_state.selected_model}`")
        st.markdown("---")
        
        # 联网搜索
        st.session_state.web_search = st.toggle("🌐 开启联网搜索", value=st.session_state.get('web_search', False))
        st.markdown("---")
        
        # 角色设定
        st.subheader("🎭 AI角色设定")
        new_prompt = st.text_area("自定义系统提示词", value=st.session_state.system_prompt, height=120)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 保存提示词", use_container_width=True):
                st.session_state.system_prompt = new_prompt
                st.rerun()
        with col2:
            if st.button("🔄 重置", use_container_width=True):
                st.session_state.system_prompt = "你是一个友好的AI助手，名叫奶龙。你会用生动、有趣的方式回答问题，公式必须用$$写在一行，如$$\\int_a^b fdx$$"
                st.rerun()
        st.markdown("---")
        
        # 对话管理
        st.subheader("💬 对话管理")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✨ 新建", use_container_width=True):
                st.session_state.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.session_state.messages = []
                st.session_state.uploaded_files = []
                st.rerun()
        with col2:
            if st.button("🗑️ 删除当前", use_container_width=True):
                if st.session_state.messages:
                    delete_conversation(st.session_state.current_session_id)
                    st.session_state.messages = []
                    st.session_state.uploaded_files = []
                    st.rerun()
        st.markdown("---")
        
        # 历史记录
        conversations = list_conversations()
        if conversations:
            st.subheader("📜 历史记录")
            for conv in conversations[:10]:
                is_current = conv["id"] == st.session_state.current_session_id
                prefix = "🟢 " if is_current else "📋 "
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(f"{prefix}{conv['created_at']} ({conv['message_count']}条)", key=f"load_{conv['id']}", use_container_width=True):
                        data = load_conversation(conv['id'])
                        if data:
                            st.session_state.messages = data["messages"]
                            st.session_state.current_session_id = conv['id']
                            st.session_state.system_prompt = data.get("system_prompt", st.session_state.system_prompt)
                            st.rerun()
                with col2:
                    if st.button("❌", key=f"del_{conv['id']}"):
                        delete_conversation(conv['id'])
                        if conv["id"] == st.session_state.current_session_id:
                            st.session_state.messages = []
                        st.rerun()
        else:
            st.info("暂无保存的对话")
        
        st.markdown("---")
        st.caption(f"消息数: {len(st.session_state.messages)}")