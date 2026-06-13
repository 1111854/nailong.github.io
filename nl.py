import streamlit as st
import os
import json
import re
import time
import base64
import httpx
from openai import OpenAI
from datetime import datetime
import PyPDF2
import docx
from tavily import TavilyClient
from utils import AVAILABLE_MODELS, DEFAULT_MODEL
from auth import register_user, login_user, save_user_conversation, load_user_conversations, delete_user_conversation

# 自行维护的工具模块，如果你还没有这些文件，可以注释掉相关代码
# 这里假设你已经有了可用模型列表和默认模型
AVAILABLE_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "deepseek-v4-pro",
    # 请根据你的 api 中转站实际模型修改
]
DEFAULT_MODEL = "gpt-4o-mini"

# ========== 页面配置 ==========
st.set_page_config(page_title="牢大GPT", page_icon="🤖", layout="wide")

# ========== 配置 ==========
API_URL = "https://mynewapi.n1neman.fun/v1"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

for dir_path in [HISTORY_DIR, UPLOAD_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# ========== 简单的用户认证（示例） ==========
# 如果你没有 auth 模块，可以用下面简单的替代
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

# ========== 登录/注册界面 ==========
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

# 如果没登录，显示登录注册页面
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
                    user_conversations = load_user_conversations(username)
                    st.session_state.user_conversations = user_conversations
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

# ========== 头像函数 ==========
def get_avatar(role):
    if role == "user":
        avatar_path = os.path.join(BASE_DIR, "User_avatar.png")
    else:
        avatar_path = os.path.join(BASE_DIR, "AI_avatar.png")
    if os.path.exists(avatar_path):
        return avatar_path
    return "🐉" if role == "user" else "🤖"

# ========== 文件处理函数 ==========
def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

def extract_text_from_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text[:3000]
    except Exception:
        return "无法读取PDF内容"

def extract_text_from_docx(file):
    try:
        doc = docx.Document(file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text[:3000]
    except Exception:
        return "无法读取Word文档内容"

def extract_text_from_txt(file):
    try:
        return file.read().decode('utf-8')[:3000]
    except Exception:
        return file.read().decode('gbk')[:3000]

# ========== LaTeX 渲染函数 ==========
def is_broken_format(text):
    if not isinstance(text, str):
        return False
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) > 3:
        single_char_count = sum(1 for line in lines[:15] if len(line) == 1)
        if single_char_count > len(lines[:15]) * 0.6:
            return True
    return False

def convert_latex_format(text):
    if not isinstance(text, str):
        return text
    text = re.sub(r'$$(.?)$$', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'$(.?)$', r'$\1$', text, flags=re.DOTALL)
    text = re.sub(r',(dx|dy|dz|dr|dt|d\theta)', r',\1', text)
    return text

def render_with_latex(content):
    if content:
        try:
            converted = convert_latex_format(content)
            st.markdown(converted)
        except Exception:
            st.text(content)

# ========== 联网搜索函数（使用环境变量） ==========
def search_web(query, max_results=3):
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return []
    try:
        client = TavilyClient(api_key=tavily_key)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True
        )
        results = []
        if response.get('answer'):
            results.append({'title': '📌 AI 总结', 'snippet': response['answer']})
        for item in response.get('results', [])[:max_results]:
            results.append({
                'title': item.get('title', '无标题'),
                'snippet': item.get('content', '无内容')[:300]
            })
        return results
    except Exception as e:
        st.toast(f"搜索失败: {str(e)[:50]}", icon="⚠️")
        return []

# ========== 消息操作函数 ==========
def copy_to_clipboard(text):
    st.toast("📋 请手动选中文本后按 Ctrl+C 复制", icon="📋")
    return True

def regenerate_last_response():
    if len(st.session_state.messages) >= 2:
        st.session_state.messages.pop()
        st.session_state.need_regenerate = True
        return True
    return False

def delete_message_at_index(index):
    if 0 <= index < len(st.session_state.messages):
        st.session_state.messages = st.session_state.messages[:index]
        save_conversation()
        return True
    return False

# ========== 保存和加载函数（用户专属） ==========
def save_conversation():
    if not st.session_state.messages:
        return
    session_id = st.session_state.current_session_id
    conversation_data = {
        "id": session_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": st.session_state.messages,
        "system_prompt": st.session_state.system_prompt
    }
    save_user_conversation(st.session_state.username, session_id, conversation_data)

def load_conversation(session_id):
    user_conversations = load_user_conversations(st.session_state.username)
    if session_id in user_conversations:
        data = user_conversations[session_id]
        st.session_state.messages = data["messages"]
        st.session_state.current_session_id = session_id
        if "system_prompt" in data:
            st.session_state.system_prompt = data["system_prompt"]
        return True
    return False

def delete_conversation(session_id):
    return delete_user_conversation(st.session_state.username, session_id)

def list_conversations():
    user_conversations = load_user_conversations(st.session_state.username)
    conversations = []
    for session_id, data in user_conversations.items():
        conversations.append({
            "id": session_id,
            "created_at": data["created_at"],
            "message_count": len(data["messages"])
        })
    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    return conversations

# ========== 缓存 OpenAI 客户端 ==========
@st.cache_resource
def get_openai_client(api_key, api_url):
    http_client = httpx.Client(
        timeout=httpx.Timeout(60.0, connect=10.0),
        follow_redirects=True
    )
    return OpenAI(
        api_key=api_key,
        base_url=api_url,
        http_client=http_client
    )

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
with st.sidebar:
    st.markdown(f"### 👤 用户：{st.session_state.username}")
    if st.button("🚪 退出登录"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 🏀 牢大GPT")
    # 如果有 banner.gif 就显示
    gif_path = os.path.join(BASE_DIR, "banner.gif")
    if os.path.exists(gif_path):
        st.image(gif_path)

    # API 密钥设置
    api_key_env = os.environ.get('CAPI')
    if api_key_env:
        st.session_state.api_key = api_key_env
        st.success("✅ API密钥已设置")
    elif not st.session_state.api_key:
        api_key_input = st.text_input("输入API密钥", type="password", key="api_input")
        if api_key_input:
            st.session_state.api_key = api_key_input
            st.rerun()

    st.markdown("---")

    # 模型选择
    st.subheader("🤖 模型选择")
    selected_model = st.selectbox(
        "选择AI模型",
        options=AVAILABLE_MODELS,
        index=AVAILABLE_MODELS.index(st.session_state.selected_model) if st.session_state.selected_model in AVAILABLE_MODELS else 0,
    )
    if selected_model != st.session_state.selected_model:
        st.session_state.selected_model = selected_model
        st.rerun()
    st.caption(f"当前模型: `{st.session_state.selected_model}`")

    # 根据模型设定 API 地址和密钥
    if selected_model == "deepseek-v4-pro":
        st.session_state.api_url = "https://api.deepseek.com"
        if os.environ.get('DAPI'):
            st.session_state.api_key = os.environ.get('DAPI')
    else:
        st.session_state.api_url = API_URL
        if os.environ.get('CAPI'):
            st.session_state.api_key = os.environ.get('CAPI')

    st.markdown("---")

    # 联网搜索开关
    st.session_state.web_search = st.toggle("🌐 开启联网搜索", value=st.session_state.web_search)
    st.markdown("---")

    # 自定义提示词
    st.subheader("🎭 AI角色设定")
    new_prompt = st.text_area("自定义系统提示词", value=st.session_state.system_prompt, height=120)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存提示词", use_container_width=True):
            st.session_state.system_prompt = new_prompt
            st.success("已保存！")
            st.rerun()
    with col2:
        if st.button("🔄 重置", use_container_width=True):
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
            if 'need_regenerate' in st.session_state:
                del st.session_state.need_regenerate
            st.rerun()
    with col2:
        if st.button("🗑️ 删除当前", use_container_width=True):
            if st.session_state.messages:
                delete_conversation(st.session_state.current_session_id)
                st.session_state.messages = []
                st.session_state.uploaded_files = []
                st.success("已删除当前对话")
                st.rerun()
            else:
                st.warning("没有可删除的对话")
    st.markdown("---")

    # 历史记录
    conversations = list_conversations()
    if conversations:
        st.subheader("📜 历史记录")
        for conv in conversations[:10]:
            is_current = (conv["id"] == st.session_state.current_session_id)
            prefix = "🟢 " if is_current else "📋 "
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(f"{prefix}{conv['created_at']} ({conv['message_count']}条)", key=f"load_{conv['id']}", use_container_width=True):
                    if load_conversation(conv['id']):
                        st.success("加载成功")
                        st.rerun()
            with col2:
                if st.button("❌", key=f"del_{conv['id']}"):
                    if delete_conversation(conv['id']):
                        st.success("已删除")
                        if conv["id"] == st.session_state.current_session_id:
                            st.session_state.messages = []
                        st.rerun()
    else:
        st.info("暂无保存的对话")

    st.markdown("---")
    st.caption(f"消息数: {len(st.session_state.messages)}")

# ========== 主界面 ==========
# 显示已上传的文件
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
                        if regenerate_last_response():
                            st.rerun()
                else:
                    st.write("")
            with col3:
                if st.button("🗑️", key=f"delete_msg_{idx}", help="删除从此处开始的对话"):
                    if delete_message_at_index(idx):
                        st.rerun()
        else:
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button("📋", key=f"copy_user_{idx}", help="复制消息"):
                    copy_to_clipboard(message["content"])
            with col2:
                if st.button("🗑️", key=f"delete_user_msg_{idx}", help="删除从此处开始的对话"):
                    if delete_message_at_index(idx):
                        st.rerun()

# CSS 样式
st.markdown("""
<style>
@media (max-width: 768px) {
    .stButton button {
        font-size: 14px;
        padding: 5px 10px;
    }
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

# ========== 处理消息 ==========
# 重新生成逻辑
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

        # 限制历史消息条数，加快响应
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
            full_reply = ""

            try:
                # 流式输出，显示“牢大肘击中...”
                with st.spinner("牢大肘击中..."):
                    stream_response = client.chat.completions.create(
                        model=st.session_state.selected_model,
                        messages=api_messages,
                        stream=True,
                        timeout=30  # 设置较短的超时，让 spinner 尽快启动
                    )

                last_update_time = time.time()
                update_interval = 0.04  # 最多每秒更新 25 次，减少 UI 压力

                for chunk in stream_response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        full_reply += delta.content

                        now = time.time()
                        if now - last_update_time >= update_interval:
                            converted = convert_latex_format(full_reply)
                            message_placeholder.markdown(
                                converted + '<span class="typing-cursor"></span>',
                                unsafe_allow_html=True
                            )
                            last_update_time = now

                # 最终显示，无光标
                final_converted = convert_latex_format(full_reply)
                message_placeholder.markdown(final_converted)

            except Exception as stream_error:
                st.warning(f"流式输出失败，切换到普通模式: {str(stream_error)[:100]}")

                with st.spinner("牢大普通肘击中..."):
                    response = client.chat.completions.create(
                        model=st.session_state.selected_model,
                        messages=api_messages,
                        stream=False
                    )

                full_reply = response.choices[0].message.content or ""
                converted = convert_latex_format(full_reply)
                message_placeholder.markdown(converted)

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_reply
        })

        st.session_state.uploaded_files = []
        save_conversation()
        # 不再强制 rerun，让 Streamlit 自然刷新
        # st.rerun()

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
