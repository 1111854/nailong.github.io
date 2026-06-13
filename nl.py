# nl.py - 主入口文件（精简版）
import streamlit as st
import time
from datetime import datetime
import os
# 导入模块
from config import API_URL, BASE_DIR, HISTORY_DIR, UPLOAD_DIR
from auth import register_user, login_user
from session_state import init_session_state
from styles import apply_custom_styles
from file_handlers import encode_image, extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt
from latex_utils import convert_latex_format, render_with_latex
from message_display import get_avatar, copy_to_clipboard
from sidebar import render_sidebar
from chat_core import stream_response, render_crash_message
from conversation import save_conversation, load_conversation, delete_conversation, list_conversations
from utils import get_openai_client, search_web, AVAILABLE_MODELS, DEFAULT_MODEL
from connection_warmup import warmup_manager
# ========== 页面配置 ==========
st.set_page_config(page_title="牢大GPT", page_icon="🤖", layout="wide")

# ========== 创建目录 ==========
for dir_path in [HISTORY_DIR, UPLOAD_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# ========== 初始化 ==========
init_session_state()
apply_custom_styles()

# ========== 登录/注册界面 ==========
if not st.session_state.logged_in:
    st.title("牢大GPT")
    st.markdown("### 欢迎！请登录或注册")
    
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="输入您的用户名")
            submitted = st.form_submit_button("登录")
           ```python
            if submitted and username:
                success, msg = login_user(username)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.messages = []
                    
                    # ===== 添加预热代码 =====
                    if st.session_state.get('api_key'):
                        warmup_manager.warmup_if_needed(
                            st.session_state.api_key,
                            st.session_state.api_url
                        )
                    # =====================
                    
                    st.rerun()
                else:
                    st.error(msg)
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("用户名", placeholder="输入您想要的用户名")
            submitted = st.form_submit_button("注册")
            if submitted and new_username:
                success, msg = register_user(new_username)
                if success:
                    st.success(msg + "，请登录")
                else:
                    st.error(msg)
    
    st.stop()

# ========== 侧边栏 ==========
render_sidebar()

# ========== 显示已上传的文件 ==========
if st.session_state.uploaded_files:
    with st.expander("📎 已上传的文件", expanded=True):
        for idx, file in enumerate(st.session_state.uploaded_files):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"📄 {file['name']} ({file['size']} bytes)")
            with col2:
                if st.button("❌", key=f"remove_file_{idx}"):
                    st.session_state.uploaded_files.pop(idx)
                    st.rerun()

# ========== 显示消息历史 ==========
for idx, message in enumerate(st.session_state.messages):
    avatar = get_avatar(message["role"])
    with st.chat_message(message["role"], avatar=avatar):
        if "files" in message:
            st.caption("📎 附件:")
            for file in message["files"]:
                st.write(f"- {file['name']}")
        render_with_latex(message["content"])
        
        # 操作按钮（复制、重新生成、删除）
        if message["role"] == "assistant":
            col1, col2, col3, col4 = st.columns([1, 1, 1, 6])
            with col1:
                if st.button("📋", key=f"copy_{idx}"):
                    copy_to_clipboard(message["content"])
            with col2:
                if idx == len(st.session_state.messages) - 1:
                    if st.button("🔄", key=f"regenerate_{idx}"):
                        if len(st.session_state.messages) >= 2:
                            st.session_state.messages.pop()
                            st.session_state.need_regenerate = True
                            st.rerun()
            with col3:
                if st.button("🗑️", key=f"delete_msg_{idx}"):
                    if 0 <= idx < len(st.session_state.messages):
                        st.session_state.messages = st.session_state.messages[:idx]
                        save_conversation()
                        st.rerun()
        else:
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button("📋", key=f"copy_user_{idx}"):
                    copy_to_clipboard(message["content"])
            with col2:
                if st.button("🗑️", key=f"delete_user_msg_{idx}"):
                    if 0 <= idx < len(st.session_state.messages):
                        st.session_state.messages = st.session_state.messages[:idx]
                        save_conversation()
                        st.rerun()

# ========== 输入区域 ==========
col1, col2, col3 = st.columns([15, 1, 1])
with col1:
    prompt = st.chat_input("输入消息... (点击右侧按钮上传文件)")
with col2:
    if st.button("📎", key="toggle_uploader"):
        st.session_state.show_uploader = not st.session_state.show_uploader
        st.rerun()
with col3:
    if st.button("🗑️", key="clear_files_btn"):
        st.session_state.uploaded_files = []
        st.success("已清空上传的文件")
        st.rerun()

# ========== 文件上传区域 ==========
if st.session_state.show_uploader:
    with st.container():
        st.markdown("### 📎 上传文件")
        st.caption("💡 按住 Ctrl/Cmd 可以选择多个文件")
        
        if 'uploaded_keys' not in st.session_state:
            st.session_state.uploaded_keys = []
        
        uploaded_files = st.file_uploader(
            "点击或拖拽文件",
            type=['png', 'jpg', 'jpeg', 'pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            key="multi_file_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_files:
            new_files = []
            for uploaded_file in uploaded_files:
                file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                if file_key not in st.session_state.uploaded_keys:
                    st.session_state.uploaded_keys.append(file_key)
                    file_info = {"name": uploaded_file.name, "type": uploaded_file.type, "size": uploaded_file.size, "content": None, "is_image": False}
                    with st.spinner(f"处理 {uploaded_file.name}..."):
                        if uploaded_file.type.startswith('image/'):
                            st.image(uploaded_file, width=150)
                            uploaded_file.seek(0)
                            file_info["content"] = encode_image(uploaded_file)
                            file_info["is_image"] = True
                        elif uploaded_file.type == 'application/pdf':
                            uploaded_file.seek(0)
                            file_info["content"] = extract_text_from_pdf(uploaded_file)
                        elif uploaded_file.type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                            uploaded_file.seek(0)
                            file_info["content"] = extract_text_from_docx(uploaded_file)
                        elif uploaded_file.type == 'text/plain':
                            uploaded_file.seek(0)
                            file_info["content"] = extract_text_from_txt(uploaded_file)
                    new_files.append(file_info)
            
            if new_files:
                st.session_state.uploaded_files.extend(new_files)
                st.session_state.show_uploader = False
                st.success(f"✅ 已添加 {len(new_files)} 个文件")
                st.rerun()
        
        if st.button("❌ 关闭"):
            st.session_state.show_uploader = False
            st.rerun()

# ========== 重新生成逻辑 ==========
if hasattr(st.session_state, 'need_regenerate') and st.session_state.need_regenerate:
    st.session_state.need_regenerate = False
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "user":
            prompt = msg["content"]
            files_to_attach = msg.get("files", [])
            break
    else:
        prompt = None

# ========== 处理消息 ==========
if prompt and st.session_state.api_key:
    files_to_attach = st.session_state.uploaded_files.copy()

    with st.chat_message("user", avatar=get_avatar("user")):
        if files_to_attach:
            st.caption("📎 附件:")
            for file in files_to_attach:
                st.write(f"- {file['name']}")
        st.markdown(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt, "files": files_to_attach})

    try:
        save_conversation()
        client = get_openai_client(st.session_state.api_key, st.session_state.api_url)

        # 构建 API 消息
        api_messages = [{"role": "system", "content": st.session_state.system_prompt}]
        for msg in st.session_state.messages[:-1][-12:]:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        # 处理文件
        content = [{"type": "text", "text": prompt}]
        for file in files_to_attach:
            if file.get("is_image"):
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{file['content']}"}})
            elif file.get("content"):
                content.append({"type": "text", "text": f"\n\n[文件: {file['name']}]\n{file['content']}\n[/文件]"})
        api_messages.append({"role": "user", "content": content if len(content) > 1 else prompt})

        with st.chat_message("assistant", avatar=get_avatar("assistant")):
            placeholder = st.empty()
            status = st.empty()
            status.markdown("🏀 **牢大正在肘击...**", unsafe_allow_html=True)
            
            try:
                full_reply = stream_response(client, api_messages, st.session_state.selected_model, placeholder, status)
                if full_reply:
                    placeholder.markdown(convert_latex_format(full_reply))
                else:
                    status.empty()
                    placeholder.markdown("*牢大沉默了...*")
                    full_reply = "[无响应]"
            except Exception as e:
                full_reply = render_crash_message(str(e), type(e).__name__, placeholder)

        st.session_state.messages.append({"role": "assistant", "content": full_reply})
        st.session_state.uploaded_files = []
        save_conversation()
        st.rerun()

    except Exception as e:
        st.error(f"错误: {str(e)}")
