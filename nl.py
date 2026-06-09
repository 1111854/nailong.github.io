import streamlit as st
import os
import json
from openai import OpenAI
from datetime import datetime
import base64
import PyPDF2
import docx
import re
import time
import httpx
import uuid
import google.generativeai as genai
from tavily import TavilyClient

# 导入模型配置
from utils import AVAILABLE_MODELS, DEFAULT_MODEL

# ========== 页面配置 ==========
st.set_page_config(
    page_title="奶龙ChatGPT",
    page_icon="🤖",
    layout="wide"
)

# ========== 配置 ==========
API_URL = "https://mynewapi.n1neman.fun/v1"

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# 确保目录存在
for dir_path in [HISTORY_DIR, UPLOAD_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# ========== 头像函数 ==========
def get_avatar(role):
    if role == "user":
        avatar_path = os.path.join(BASE_DIR, "User_avatar.png")
    else:
        avatar_path = os.path.join(BASE_DIR, "AI_avatar.png")
    if os.path.exists(avatar_path):
        return avatar_path
    return "🐉" if role == "user" else "🤖"

def show_banner_gif():
    gif_path = os.path.join(BASE_DIR, "banner.gif")
    if os.path.exists(gif_path):
        st.image(gif_path)
    else:
        st.caption("🐉 奶龙陪你聊天~")

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

# ========== LaTeX渲染函数 ==========
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
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    text = re.sub(r',(dx|dy|dz|dr|dt|d\\theta)', r'\,\1', text)
    return text

def render_with_latex(content):
    if content:
        try:
            converted = convert_latex_format(content)
            st.markdown(converted)
        except Exception:
            st.text(content)

# ========== 联网搜索函数 ==========
def search_web(query, max_results=3):
    tavily_key = os.environ.get('TAPI', '')
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
        print(f"搜索失败: {e}")
        return []

# ========== Session State初始化 ==========
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

# ========== 保存和加载函数 ==========
def save_conversation():
    if not st.session_state.messages:
        return None
    session_id = st.session_state.current_session_id
    filename = os.path.join(HISTORY_DIR, f"chat_{session_id}.json")
    data = {
        "id": session_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": st.session_state.messages,
        "system_prompt": st.session_state.system_prompt
    }
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存失败: {e}")
        return False

def load_conversation(session_id):
    filename = os.path.join(HISTORY_DIR, f"chat_{session_id}.json")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            st.session_state.messages = data["messages"]
            st.session_state.current_session_id = session_id
            if "system_prompt" in data:
                st.session_state.system_prompt = data["system_prompt"]
            return True
    except Exception as e:
        st.error(f"加载失败: {e}")
        return False

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
                filepath = os.path.join(HISTORY_DIR, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
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

# ========== 侧边栏 ==========
with st.sidebar:
    st.markdown("### 🐉 奶龙ChatGPT")
    show_banner_gif()
    
    api_key = os.environ.get('CAPI')
    if api_key:
        st.session_state.api_key = api_key
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
        help="从列表中选择模型"
    )
    
    if selected_model != st.session_state.selected_model:
        st.session_state.selected_model = selected_model
        st.success(f"已切换到: {selected_model}")
        st.rerun()
    
    st.caption(f"当前模型: `{st.session_state.selected_model}`")
    st.markdown("---")
    
    # 联网搜索开关
    st.session_state.web_search = st.toggle(
        "🌐 开启联网搜索", 
        value=st.session_state.web_search,
        help="开启后，奶龙可以搜索最新信息"
    )
    
    st.markdown("---")
    
    # 自定义提示词
    st.subheader("🎭 AI角色设定")
    new_prompt = st.text_area(
        "自定义系统提示词",
        value=st.session_state.system_prompt,
        height=120
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存提示词", use_container_width=True):
            st.session_state.system_prompt = new_prompt
            st.success("已保存！")
            st.rerun()
    with col2:
        if st.button("🔄 重置", use_container_width=True):
            st.session_state.system_prompt = "你是一个友好的AI助手，名叫奶龙。你会用生动、有趣的方式回答问题，公式必须用$$写在一行，如$$\\int_a^b fdx$$"
            st.success("已重置")
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
                st.success("已删除当前对话")
                st.rerun()
            else:
                st.warning("没有可删除的对话")
    
    st.markdown("---")
    
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

for message in st.session_state.messages:
    avatar = get_avatar(message["role"])
    with st.chat_message(message["role"], avatar=avatar):
        if "files" in message:
            st.caption("📎 附件:")
            for file in message["files"]:
                st.write(f"- {file['name']}")
        render_with_latex(message["content"])

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
if prompt:
    if not st.session_state.api_key:
        st.error("请先在侧边栏设置API密钥")
        st.stop()

    files_to_attach = st.session_state.uploaded_files.copy()

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

        http_client = httpx.Client(timeout=120, follow_redirects=True)
        client = OpenAI(
            api_key=st.session_state.api_key,
            base_url=API_URL,
            http_client=http_client
        )

        # ========== 联网搜索 ==========
        search_context = ""
        search_results = []
        if st.session_state.web_search:
            with st.spinner("🌐 正在搜索网络..."):
                search_results = search_web(prompt)
                if search_results:
                    search_context = "\n\n【联网搜索结果】\n"
                    for i, r in enumerate(search_results, 1):
                        search_context += f"\n{i}. {r['title']}\n   {r['snippet']}\n"
                    search_context += "\n请基于以上搜索结果回答用户问题。"
                    st.toast(f"✅ 找到 {len(search_results)} 条搜索结果", icon="🌐")
        
        # 构建 API 消息（使用原始 system_prompt + 临时搜索上下文）
        system_content = st.session_state.system_prompt
        if search_context:
            system_content += search_context
        
        api_messages = [{"role": "system", "content": system_content}]
        
        for msg in st.session_state.messages[:-1]:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

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
            # 如果有搜索结果，先显示搜索来源
            if search_results:
                with st.expander("🌐 联网搜索结果", expanded=False):
                    for i, r in enumerate(search_results[:5], 1):
                        st.markdown(f"**{i}. {r['title']}**")
                        st.caption(r['snippet'][:200])
                        st.divider()
            
            message_placeholder = st.empty()
            full_reply = ""
            with st.spinner("🐉 奶龙正在思考..."):
                response = client.chat.completions.create(
                    model=st.session_state.selected_model,
                    messages=api_messages
                )
                full_reply = response.choices[0].message.content or ""

                if is_broken_format(full_reply):
                    fixed = re.sub(r'\s+', '', full_reply)
                    full_reply = f'$$\n{fixed}\n$$'

                displayed = ""
                for char in full_reply:
                    displayed += char
                    converted = convert_latex_format(displayed)
                    message_placeholder.markdown(converted + '<span class="typing-cursor"></span>', unsafe_allow_html=True)
                    time.sleep(0.008)

                message_placeholder.markdown(convert_latex_format(full_reply))

        st.session_state.messages.append({"role": "assistant", "content": full_reply})
        st.session_state.uploaded_files = []
        save_conversation()
        st.rerun()

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
