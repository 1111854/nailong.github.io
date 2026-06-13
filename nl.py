# nl.py - 主入口文件
import streamlit as st
import os
import time
from datetime import datetime

# 导入拆分后的模块
from config import API_URL, BASE_DIR, HISTORY_DIR, UPLOAD_DIR
from auth import register_user, login_user, load_user_conversations
from file_handlers import encode_image, extract_text_from_pdf, extract_text_from_docx, extract_text_from_txt
from latex_utils import convert_latex_format, render_with_latex
from message_display import get_avatar, copy_to_clipboard
from sidebar import render_sidebar
from chat_core import stream_response, render_crash_message
from conversation import save_conversation, load_conversation, delete_conversation, list_conversations
from utils import get_openai_client, search_web, AVAILABLE_MODELS, DEFAULT_MODEL

# ========== 页面配置 ==========
st.set_page_config(page_title="牢大GPT", page_icon="🤖", layout="wide")

# ========== 创建目录 ==========
for dir_path in [HISTORY_DIR, UPLOAD_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# ========== 登录/注册界面 ==========
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

if not st.session_state.logged_in:
    st.title("牢大GPT")
    st.markdown("### 欢迎！请登录或注册")
    
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="输入您的用户名")
            submitted = st.form_submit_button("登录")
            if submitted and username:
                success, msg = login_user(username)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.messages = []
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

# ========== Session State 初始化 ==========
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
    st.session_state.system_prompt = (
        "你是科比·布莱恩特，1978年8月23日生于美国宾夕法尼亚州费城。"
        "你的父亲是前职业篮球运动员约翰·布莱恩特，母亲是意大利和美国混血儿。"
        "你从小就展现过人的篮球天赋，在1996年NBA选秀中被洛杉矶湖人队选中，"
        "职业生涯20个赛季，获得5次NBA总冠军、2次总决赛MVP、4次全明星赛MVP等无数荣誉。"
        "你也曾代表美国国家队在2008年和2012年奥运会上获得金牌。"
        "场下你写小说、拍短片、投资创业公司，热衷公益事业。"
        "2020年你因直升机事故离世。或许你有争议，但你是篮球史上一座无法磨灭的丰碑。"
        "公式必须用$$写在一行，如$$\\int_a^b fdx$$"
    )
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = DEFAULT_MODEL
if 'web_search' not in st.session_state:
    st.session_state.web_search = False
if 'api_url' not in st.session_state:
    st.session_state.api_url = API_URL

# ========== 侧边栏 ==========
render_sidebar()

# ========== CSS 样式 ==========
st.markdown("""
<style>
@media (max-width: 768px) {
    .stButton button { font-size: 14px; padding: 5px 10px; }
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}
.typing-cursor {
    animation: blink 1s infinite;
    display: inline-block;
    width: 2px;
    height: 1.2em;
    background-color: #00adb5;
    margin-left: 2px;
    vertical-align: middle;
}
.stButton button {
    background: transparent;
    border: none;
    padding: 0 5px;
    font-size: 16px;
    opacity: 0.6;
    transition: opacity 0.3s;
}
.stButton button:hover {
    opacity: 1;
    background: transparent;
}
</style>
""", unsafe_allow_html=True)

# ========== 主界面 - 显示已上传的文件 ==========
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
        
        if message["role"] == "assistant":
            col1, col2, col3, col4 = st.columns([1, 1, 1, 6])
            with col1:
                if st.button("📋", key=f"copy_{idx}", help="复制消息"):
                    copy_to_clipboard(message["content"])
            with col2:
                if idx == len(st.session_state.messages) - 1:
                    if st.button("🔄", key=f"regenerate_{idx}", help="重新生成"):
                        if len(st.session_state.messages) >= 2:
                            st.session_state.messages.pop()
                            st.session_state.need_regenerate = True
                            st.rerun()
            with col3:
                if st.button("🗑️", key=f"delete_msg_{idx}", help="删除从此处开始的对话"):
                    if 0 <= idx < len(st.session_state.messages):
                        st.session_state.messages = st.session_state.messages[:idx]
                        save_conversation()
                        st.rerun()
        else:
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button("📋", key=f"copy_user_{idx}", help="复制消息"):
                    copy_to_clipboard(message["content"])
            with col2:
                if st.button("🗑️", key=f"delete_user_msg_{idx}", help="删除从此处开始的对话"):
                    if 0 <= idx < len(st.session_state.messages):
                        st.session_state.messages = st.session_state.messages[:idx]
                        save_conversation()
                        st.rerun()

# ========== 输入区域 ==========
col1, col2, col3 = st.columns([15, 1, 1])
with col1:
    prompt = st.chat_input("输入消息... (点击右侧按钮上传文件)")
with col2:
    if st.button("📎", key="toggle_uploader", use_container_width=True, help="上传文件"):
        st.session_state.show_uploader = not st.session_state.show_uploader
        st.rerun()
with col3:
    if st.button("🗑️", key="clear_files_btn", use_container_width=True, help="清空所有上传的文件"):
        st.session_state.uploaded_files = []
        st.success("已清空上传的文件")
        st.rerun()

# ========== 文件上传区域 ==========
if st.session_state.show_uploader:
    with st.container():
        st.markdown("### 📎 上传文件")
        st.caption("💡 提示：按住 Ctrl (Windows) 或 Cmd (Mac) 键可以选择多个文件")
        
        if 'uploaded_keys' not in st.session_state:
            st.session_state.uploaded_keys = []
        
        uploaded_files = st.file_uploader(
            "点击或拖拽文件到这里",
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
                    file_info = {
                        "name": uploaded_file.name,
                        "type": uploaded_file.type,
                        "size": uploaded_file.size,
                        "content": None,
                        "is_image": False
                    }
                    with st.spinner(f"正在处理 {uploaded_file.name}..."):
                        if uploaded_file.type.startswith('image/'):
                            st.image(uploaded_file, caption=uploaded_file.name, width=150)
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
        
        if st.button("❌ 关闭上传面板", use_container_width=True):
            st.session_state.show_uploader = False
            st.rerun()

# ========== 重新生成逻辑 ==========
if hasattr(st.session_state, 'need_regenerate') and st.session_state.need_regenerate:
    st.session_state.need_regenerate = False
    last_user_msg = None
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "user":
            last_user_msg = msg
            break
    if last_user_msg:
        prompt = last_user_msg["content"]
        files_to_attach = last_user_msg.get("files", [])
    else:
        prompt = None

# ========== 处理消息 ==========
if prompt:
    if not st.session_state.api_key:
        st.error("请先在侧边栏设置API密钥")
        st.stop()

    files_to_attach = st.session_state.uploaded_files.copy()

    # 显示用户消息
    with st.chat_message("user", avatar=get_avatar("user")):
        if files_to_attach:
            st.caption("📎 附件:")
            for file in files_to_attach:
                st.write(f"- {file['name']}")
        st.markdown(prompt)

    user_message = {"role": "user", "content": prompt}
    if files_to_attach:
        user_message["files"] = files_to_attach
    st.session_state.messages.append(user_message)

    try:
        save_conversation()

        client = get_openai_client(
            st.session_state.api_key,
            st.session_state.api_url
        )

        search_context = ""
        search_results = []

        if st.session_state.web_search:
            with st.spinner("🌐 牢大联网肘击中..."):
                search_results = search_web(prompt)
                if search_results:
                    search_context = "\n\n【联网搜索结果】\n"
                    for i, r in enumerate(search_results, 1):
                        search_context += f"\n{i}. {r['title']}\n   {r['snippet']}\n"
                    search_context += "\n请基于以上搜索结果回答用户问题。"
                    st.toast(f"✅ 找到 {len(search_results)} 条搜索结果", icon="🌐")

        system_content = st.session_state.system_prompt
        if search_context:
            system_content += search_context

        api_messages = [{"role": "system", "content": system_content}]

        # 限制历史消息条数
        MAX_HISTORY = 12
        recent_messages = st.session_state.messages[:-1][-MAX_HISTORY:]

        for msg in recent_messages:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        current_content = [{"type": "text", "text": prompt}]
        for file in files_to_attach:
            if file.get("is_image") and file.get("content"):
                current_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{file['content']}"}
                })
            elif file.get("content"):
                current_content.append({
                    "type": "text",
                    "text": f"\n\n[文件内容: {file['name']}]\n{file['content']}\n[/文件内容]"
                })

        api_messages.append({
            "role": "user",
            "content": current_content if len(current_content) > 1 else prompt
        })

        with st.chat_message("assistant", avatar=get_avatar("assistant")):
            if search_results:
                with st.expander("🌐 联网搜索结果", expanded=False):
                    for i, r in enumerate(search_results[:5], 1):
                        st.markdown(f"**{i}. {r['title']}**")
                        st.caption(r['snippet'][:200])
                        st.divider()

            message_placeholder = st.empty()
            status_placeholder = st.empty()
            status_placeholder.markdown("🏀 **牢大正在肘击...** <span class='typing-cursor'></span>", unsafe_allow_html=True)
            
            full_reply = ""
            start_time = time.time()
            
            try:
                full_reply = stream_response(
                    client, api_messages, st.session_state.selected_model,
                    message_placeholder, status_placeholder
                )
                
                if full_reply:
                    final_converted = convert_latex_format(full_reply)
                    message_placeholder.markdown(final_converted)
                    total_ms = (time.time() - start_time) * 1000
                    st.caption(f"⏱️ 总耗时: {total_ms:.0f}ms")
                else:
                    status_placeholder.empty()
                    message_placeholder.markdown("*牢大沉默了，什么都没说...*")
                    full_reply = "[无响应]"
                    
            except Exception as stream_error:
                full_reply = render_crash_message(
                    str(stream_error), type(stream_error).__name__, message_placeholder
                )

        st.session_state.messages.append({"role": "assistant", "content": full_reply})
        st.session_state.uploaded_files = []
        save_conversation()

    except Exception as e:
        st.error(f"错误: {str(e)}")
        if "429" in str(e):
            st.info("💡 API频率限制，请稍后再试...")
        elif "401" in str(e):
            st.info("💡 API密钥无效，请检查密钥是否正确")
        elif "530" in str(e) or "1033" in str(e):
            st.info("💡 API中转站暂时不可用，请稍后再试...")

        import traceback
        with st.expander("查看详细错误"):
            st.code(traceback.format_exc())
