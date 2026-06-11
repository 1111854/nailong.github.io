import streamlit as st
import os
import re
from datetime import datetime
from utils import AVAILABLE_MODELS, DEFAULT_MODEL
from config import BASE_DIR
from file_handlers import encode_image, extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt
from latex_utils import is_broken_format
from conversation import save_conversation
from chat_core import search_web, send_message, stream_response
from sidebar import render_sidebar
from message_display import render_messages

st.set_page_config(page_title="奶龙ChatGPT", page_icon="🤖", layout="wide")

# 初始化session_state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'api_key' not in st.session_state:
    st.session_state.api_key = None
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'show_uploader' not in st.session_state:
    st.session_state.show_uploader = False
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
if 'system_prompt' not in st.session_state:
    st.session_state.system_prompt = "你是一个友好的AI助手，名叫奶龙。你会用生动、有趣的方式回答问题，公式必须用$$写在一行，如$$\\int_a^b fdx$$"
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = DEFAULT_MODEL
if 'web_search' not in st.session_state:
    st.session_state.web_search = False

# 侧边栏
render_sidebar()

# 主界面 - 已上传文件
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

# 显示消息历史
def on_regenerate():
    if len(st.session_state.messages) >= 2:
        st.session_state.messages.pop()
        st.session_state.need_regenerate = True
        st.rerun()

def on_delete(idx):
    st.session_state.messages = st.session_state.messages[:idx]
    save_conversation(st.session_state.messages, st.session_state.current_session_id, st.session_state.system_prompt)
    st.rerun()

render_messages(st.session_state.messages, BASE_DIR, on_regenerate, on_delete)

# CSS样式
st.markdown("""
<style>
    .stButton button { background: transparent; border: none; padding: 0 5px; font-size: 16px; opacity: 0.6; }
    .stButton button:hover { opacity: 1; background: transparent; }
    @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
    .typing-cursor { animation: blink 1s infinite; display: inline-block; width: 2px; height: 1.2em; background-color: #00adb5; vertical-align: middle; }
</style>
""", unsafe_allow_html=True)

# 输入区域
col1, col2, col3 = st.columns([15, 1, 1])
with col1:
    prompt = st.chat_input("输入消息... (点击右侧按钮上传文件)")
with col2:
    if st.button("📎", key="toggle_uploader", use_container_width=True):
        st.session_state.show_uploader = not st.session_state.show_uploader
        st.rerun()
with col3:
    if st.button("🗑️", key="clear_files_btn", use_container_width=True):
        st.session_state.uploaded_files = []
        st.rerun()

# 文件上传区域
if st.session_state.show_uploader:
    with st.container():
        st.markdown("### 📎 上传文件")
        if 'uploaded_keys' not in st.session_state:
            st.session_state.uploaded_keys = []
        uploaded_files = st.file_uploader("点击或拖拽文件到这里", type=['png','jpg','jpeg','pdf','docx','txt'], accept_multiple_files=True, key="multi_file_uploader", label_visibility="collapsed")
        if uploaded_files:
            new_files = []
            for uploaded_file in uploaded_files:
                file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                if file_key not in st.session_state.uploaded_keys:
                    st.session_state.uploaded_keys.append(file_key)
                    file_info = {"name": uploaded_file.name, "type": uploaded_file.type, "size": uploaded_file.size, "content": None, "is_image": False}
                    with st.spinner(f"正在处理 {uploaded_file.name}..."):
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
                st.rerun()
        if st.button("❌ 关闭上传面板", use_container_width=True):
            st.session_state.show_uploader = False
            st.rerun()

# 处理消息
if hasattr(st.session_state, 'need_regenerate') and st.session_state.need_regenerate:
    st.session_state.need_regenerate = False
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "user":
            prompt = msg["content"]
            files_to_attach = msg.get("files", [])
            break
    else:
        prompt = None

if prompt and st.session_state.api_key:
    files_to_attach = st.session_state.uploaded_files.copy()
    
    with st.chat_message("user", avatar="🐉"):
        if files_to_attach:
            st.caption("📎 附件:")
            for file in files_to_attach:
                st.write(f"- {file['name']}")
        st.markdown(prompt)
    
    st.session_state.messages.append({"role": "user", "content": prompt, "files": files_to_attach} if files_to_attach else {"role": "user", "content": prompt})
    
    try:
        save_conversation(st.session_state.messages, st.session_state.current_session_id, st.session_state.system_prompt)
        
        search_context = ""
        if st.session_state.web_search:
            with st.spinner("🌐 正在搜索网络..."):
                results = search_web(prompt)
                if results:
                    search_context = "\n\n【联网搜索结果】\n" + "\n".join([f"\n{i}. {r['title']}\n   {r['snippet']}" for i, r in enumerate(results, 1)])
                    st.toast(f"✅ 找到 {len(results)} 条搜索结果", icon="🌐")
        
        system_content = st.session_state.system_prompt + search_context
        
        with st.chat_message("assistant", avatar="🤖"):
            msg_placeholder = st.empty()
            with st.spinner("🐉 奶龙正在思考..."):
                history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
                full_reply = send_message(history, st.session_state.selected_model, st.session_state.api_key, system_content)
                if is_broken_format(full_reply):
                    full_reply = f'$$\n{re.sub(r"\s+", "", full_reply)}\n$$'
                stream_response(full_reply, msg_placeholder)
        
        st.session_state.messages.append({"role": "assistant", "content": full_reply})
        st.session_state.uploaded_files = []
        save_conversation(st.session_state.messages, st.session_state.current_session_id, st.session_state.system_prompt)
        st.rerun()
    
    except Exception as e:
        st.error(f"错误: {str(e)}")
        with st.expander("查看详细错误"):
            import traceback
            st.code(traceback.format_exc())
