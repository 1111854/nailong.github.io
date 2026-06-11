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

# ========== 页面配置 ==========
st.set_page_config(page_title="奶龙ChatGPT", page_icon="🤖", layout="wide")

# ========== 配置 ==========
API_URL = "https://mynewapi.n1neman.fun/v1"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

for dir_path in [HISTORY_DIR, UPLOAD_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# ========== Session State初始化 ==========
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'api_key' not in st.session_state:
    st.session_state.api_key = os.environ.get('CAPI')
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'show_uploader' not in st.session_state:
    st.session_state.show_uploader = False
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
if 'system_prompt' not in st.session_state:
    st.session_state.system_prompt = "你是一个友好的AI助手，名叫奶龙。"
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = DEFAULT_MODEL
if 'web_search' not in st.session_state:
    st.session_state.web_search = False

# ========== 辅助函数 ==========
def get_avatar(role):
    return "🐉" if role == "user" else "🤖"

def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

def extract_text_from_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text[:3000]
    except:
        return "无法读取PDF内容"

def extract_text_from_docx(file):
    try:
        doc = docx.Document(file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text[:3000]
    except:
        return "无法读取Word文档内容"

def extract_text_from_txt(file):
    try:
        return file.read().decode('utf-8')[:3000]
    except:
        return file.read().decode('gbk')[:3000]

def convert_latex_format(text):
    if not isinstance(text, str):
        return text
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    return text

def search_web(query, max_results=3):
    tavily_key = "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"
    try:
        client = TavilyClient(api_key=tavily_key)
        response = client.search(query=query, search_depth="basic", max_results=max_results, include_answer=True)
        results = []
        if response.get('answer'):
            results.append({'title': '📌 AI 总结', 'snippet': response['answer']})
        for item in response.get('results', [])[:max_results]:
            results.append({'title': item.get('title', '无标题'), 'snippet': item.get('content', '无内容')[:300]})
        return results
    except:
        return []

def save_conversation():
    if not st.session_state.messages:
        return
    filename = os.path.join(HISTORY_DIR, f"chat_{st.session_state.current_session_id}.json")
    data = {
        "id": st.session_state.current_session_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": st.session_state.messages,
        "system_prompt": st.session_state.system_prompt
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_conversation(session_id):
    filename = os.path.join(HISTORY_DIR, f"chat_{session_id}.json")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def delete_conversation(session_id):
    filename = os.path.join(HISTORY_DIR, f"chat_{session_id}.json")
    try:
        os.remove(filename)
        return True
    except:
        return False

def list_conversations():
    conversations = []
    if os.path.exists(HISTORY_DIR):
        for file in os.listdir(HISTORY_DIR):
            if file.startswith("chat_") and file.endswith(".json"):
                try:
                    with open(os.path.join(HISTORY_DIR, file), "r") as f:
                        data = json.load(f)
                        conversations.append({
                            "id": data["id"],
                            "created_at": data["created_at"],
                            "message_count": len(data["messages"])
                        })
                except:
                    pass
    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    return conversations

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

# ========== 侧边栏 ==========
with st.sidebar:
    st.markdown("### 🐉 奶龙ChatGPT")
    
    gif_path = os.path.join(BASE_DIR, "banner.gif")
    if os.path.exists(gif_path):
        st.image(gif_path)
    
    if not st.session_state.api_key:
        api_input = st.text_input("输入API密钥", type="password")
        if api_input:
            st.session_state.api_key = api_input
            st.rerun()
    else:
        st.success("✅ API密钥已设置")
    
    st.markdown("---")
    
    # 模型选择
    idx = AVAILABLE_MODELS.index(st.session_state.selected_model) if st.session_state.selected_model in AVAILABLE_MODELS else 0
    selected = st.selectbox("选择AI模型", AVAILABLE_MODELS, index=idx)
    if selected != st.session_state.selected_model:
        st.session_state.selected_model = selected
        st.rerun()
    
    st.markdown("---")
    
    # 联网搜索
    st.session_state.web_search = st.toggle("🌐 联网搜索", st.session_state.web_search)
    
    st.markdown("---")
    
    # 系统提示词
    new_prompt = st.text_area("系统提示词", st.session_state.system_prompt, height=100)
    if st.button("保存提示词"):
        st.session_state.system_prompt = new_prompt
        st.rerun()
    
    st.markdown("---")
    
    # 对话管理
    col1, col2 = st.columns(2)
    with col1:
        if st.button("新建对话", use_container_width=True):
            st.session_state.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.messages = []
            st.session_state.uploaded_files = []
            st.rerun()
    with col2:
        if st.button("删除当前", use_container_width=True):
            delete_conversation(st.session_state.current_session_id)
            st.session_state.messages = []
            st.rerun()
    
    st.markdown("---")
    
    # 历史记录
    conversations = list_conversations()
    if conversations:
        st.subheader("历史记录")
        for conv in conversations[:10]:
            prefix = "🟢 " if conv["id"] == st.session_state.current_session_id else "📋 "
            if st.button(f"{prefix}{conv['created_at']} ({conv['message_count']}条)", key=conv['id'], use_container_width=True):
                data = load_conversation(conv['id'])
                if data:
                    st.session_state.messages = data["messages"]
                    st.session_state.current_session_id = conv['id']
                    st.session_state.system_prompt = data.get("system_prompt", st.session_state.system_prompt)
                    st.rerun()
    
    st.markdown("---")
    st.caption(f"消息数: {len(st.session_state.messages)}")

# ========== 主界面 ==========
# 显示已上传文件
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
    with st.chat_message(message["role"], avatar=get_avatar(message["role"])):
        st.markdown(convert_latex_format(message["content"]))
        
        # 操作按钮
        if message["role"] == "assistant":
            col1, col2, col3 = st.columns([1, 1, 10])
            with col1:
                if st.button("📋", key=f"copy_{idx}"):
                    st.toast("请手动选中文本后 Ctrl+C 复制", icon="📋")
            with col2:
                if idx == len(st.session_state.messages) - 1:
                    if st.button("🔄", key=f"regenerate_{idx}"):
                        regenerate_last_response()
                        st.rerun()
            with col3:
                if st.button("🗑️", key=f"delete_{idx}"):
                    delete_message_at_index(idx)
                    st.rerun()
        else:
            col1, col2 = st.columns([1, 11])
            with col1:
                if st.button("📋", key=f"copy_user_{idx}"):
                    st.toast("请手动选中文本后 Ctrl+C 复制", icon="📋")
            with col2:
                if st.button("🗑️", key=f"delete_user_{idx}"):
                    delete_message_at_index(idx)
                    st.rerun()

# CSS样式
st.markdown("""
<style>
    .stButton button { background: transparent; border: none; padding: 0 5px; font-size: 16px; opacity: 0.6; }
    .stButton button:hover { opacity: 1; background: transparent; }
    .typing-cursor { animation: blink 1s infinite; display: inline-block; width: 2px; height: 1.2em; background-color: #00adb5; vertical-align: middle; }
    @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
</style>
""", unsafe_allow_html=True)

# ========== 输入区域 ==========
col1, col2, col3 = st.columns([15, 1, 1])
with col1:
    prompt = st.chat_input("输入消息...")
with col2:
    if st.button("📎", key="toggle_uploader", use_container_width=True):
        st.session_state.show_uploader = not st.session_state.show_uploader
        st.rerun()
with col3:
    if st.button("🗑️", key="clear_files", use_container_width=True):
        st.session_state.uploaded_files = []
        st.rerun()

# ========== 文件上传区域 ==========
if st.session_state.show_uploader:
    with st.container():
        st.markdown("### 📎 上传文件")
        
        if 'uploaded_keys' not in st.session_state:
            st.session_state.uploaded_keys = []
        
        uploaded_files = st.file_uploader(
            "点击或拖拽文件",
            type=['png', 'jpg', 'jpeg', 'pdf', 'docx', 'txt'],
            accept_multiple_files=True,
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
                st.rerun()
        
        if st.button("关闭", use_container_width=True):
            st.session_state.show_uploader = False
            st.rerun()

# ========== 处理消息 ==========
# 重新生成逻辑
if hasattr(st.session_state, 'need_regenerate') and st.session_state.need_regenerate:
    st.session_state.need_regenerate = False
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "user":
            prompt = msg["content"]
            files_to_attach = msg.get("files", [])
            break
    else:
        prompt = None

# 正常发送消息
if prompt and st.session_state.api_key:
    files_to_attach = st.session_state.uploaded_files.copy()
    
    # 显示用户消息
    with st.chat_message("user", avatar=get_avatar("user")):
        if files_to_attach:
            st.caption("📎 附件:")
            for file in files_to_attach:
                st.write(f"- {file['name']}")
        st.markdown(prompt)
    
    # 保存用户消息
    user_msg = {"role": "user", "content": prompt}
    if files_to_attach:
        user_msg["files"] = files_to_attach
    st.session_state.messages.append(user_msg)
    save_conversation()
    
    try:
        # 联网搜索
        search_context = ""
        if st.session_state.web_search:
            with st.spinner("搜索中..."):
                results = search_web(prompt)
                if results:
                    search_context = "\n\n【搜索结果】\n" + "\n".join([f"\n{i}. {r['title']}\n   {r['snippet']}" for i, r in enumerate(results, 1)])
                    st.toast(f"找到 {len(results)} 条结果", icon="🌐")
        
        system_content = st.session_state.system_prompt + search_context
        
        # 调用API
        with st.chat_message("assistant", avatar=get_avatar("assistant")):
            msg_placeholder = st.empty()
            with st.spinner("思考中..."):
                http_client = httpx.Client(timeout=120)
                client = OpenAI(api_key=st.session_state.api_key, base_url=API_URL, http_client=http_client)
                
                api_messages = [{"role": "system", "content": system_content}]
                for m in st.session_state.messages[:-1]:
                    api_messages.append({"role": m["role"], "content": m["content"]})
                
                response = client.chat.completions.create(
                    model=st.session_state.selected_model,
                    messages=api_messages
                )
                reply = response.choices[0].message.content or ""
                
                # 打字机效果
                displayed = ""
                for char in reply:
                    displayed += char
                    msg_placeholder.markdown(convert_latex_format(displayed) + '<span class="typing-cursor"></span>', unsafe_allow_html=True)
                    time.sleep(0.005)
                msg_placeholder.markdown(convert_latex_format(reply))
        
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.session_state.uploaded_files = []
        save_conversation()
        st.rerun()
    
    except Exception as e:
        st.error(f"错误: {e}")
        with st.expander("详情"):
            import traceback
            st.code(traceback.format_exc())
