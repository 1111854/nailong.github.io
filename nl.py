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

# ========== 页面配置 ==========
st.set_page_config(
    page_title="奶龙ChatGPT",
    page_icon="🤖",
    layout="wide"
)

# ========== 配置 ==========
API_URL = "https://mynewapi.n1neman.fun/v1"
MODEL = "gpt-5.5"

# 目录设置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")

# 确保目录存在
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

# ========== 头像函数 ==========
def get_avatar(role):
    return "🐉" if role == "user" else "🤖"

# ========== 文件处理函数 ==========
def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

def extract_text_from_pdf(file):
    try:
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text[:3000]
    except:
        return "无法读取PDF内容"

def extract_text_from_docx(file):
    try:
        import docx
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

# ========== LaTeX渲染 ==========
def convert_latex_format(text):
    if not isinstance(text, str):
        return text
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    return text

# ========== Session State ==========
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'api_key' not in st.session_state:
    st.session_state.api_key = None
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'show_uploader' not in st.session_state:
    st.session_state.show_uploader = False

# ========== 保存和加载函数（简化版）==========
def save_conversation():
    """保存当前对话"""
    if not st.session_state.messages:
        st.warning("没有可保存的对话")
        return None
    
    # 用时间戳作为文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(HISTORY_DIR, f"chat_{timestamp}.json")
    
    data = {
        "id": timestamp,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": st.session_state.messages
    }
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        st.success(f"✅ 对话已保存！")
        return timestamp
    except Exception as e:
        st.error(f"保存失败: {e}")
        return None

def load_conversation(session_id):
    """加载对话"""
    filename = os.path.join(HISTORY_DIR, f"chat_{session_id}.json")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            st.session_state.messages = data["messages"]
            return True
    except Exception as e:
        st.error(f"加载失败: {e}")
        return False

def delete_conversation(session_id):
    """删除对话"""
    filename = os.path.join(HISTORY_DIR, f"chat_{session_id}.json")
    try:
        os.remove(filename)
        return True
    except:
        return False

def list_conversations():
    """列出所有保存的对话"""
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
    
    # API密钥（从Secrets读取）
    api_key = os.environ.get('CAPI')
    if api_key:
        st.session_state.api_key = api_key
        st.success("✅ API密钥已设置")
    elif not st.session_state.api_key:
        api_key_input = st.text_input("输入API密钥", type="password")
        if api_key_input:
            st.session_state.api_key = api_key_input
            st.rerun()
    
    st.markdown("---")
    
    # 对话管理
    st.subheader("💬 对话管理")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 保存", use_container_width=True):
            save_conversation()
            time.sleep(0.5)
            st.rerun()
    
    with col2:
        if st.button("✨ 新建", use_container_width=True):
            st.session_state.messages = []
            st.session_state.uploaded_files = []
            st.rerun()
    
    st.markdown("---")
    
    # 历史记录列表
    conversations = list_conversations()
    if conversations:
        st.subheader("📜 历史记录")
        for conv in conversations[:10]:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(f"📋 {conv['created_at']} ({conv['message_count']}条)", key=f"load_{conv['id']}", use_container_width=True):
                    if load_conversation(conv['id']):
                        st.success("加载成功")
                        st.rerun()
            with col2:
                if st.button("❌", key=f"del_{conv['id']}"):
                    if delete_conversation(conv['id']):
                        st.success("已删除")
                        if len(st.session_state.messages) > 0:
                            st.session_state.messages = []
                        st.rerun()
    else:
        st.info("暂无保存的对话")
    
    st.markdown("---")
    st.caption(f"模型: {MODEL}")
    st.caption(f"当前消息数: {len(st.session_state.messages)}")

# ========== 主界面显示消息 ==========
for message in st.session_state.messages:
    avatar = get_avatar(message["role"])
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(convert_latex_format(message["content"]))

# ========== 输入区域 ==========
prompt = st.chat_input("输入消息...")

if prompt:
    if not st.session_state.api_key:
        st.error("请先在侧边栏设置API密钥")
        st.stop()
    
    # 显示用户消息
    with st.chat_message("user", avatar=get_avatar("user")):
        st.markdown(prompt)
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    try:
        # 创建API客户端
        http_client = httpx.Client(timeout=120, follow_redirects=True)
        client = OpenAI(
            api_key=st.session_state.api_key,
            base_url=API_URL,
            http_client=http_client
        )
        
        # 构建消息（只保留最近10轮，避免太长）
        api_messages = [{"role": "system", "content": "你是一个友好的AI助手，名叫奶龙。"}]
        for msg in st.session_state.messages[-20:]:  # 只保留最近20条消息
            api_messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 获取回复
        with st.chat_message("assistant", avatar=get_avatar("assistant")):
            message_placeholder = st.empty()
            response = client.chat.completions.create(
                model=MODEL,
                messages=api_messages,
                max_tokens=2048
            )
            full_reply = response.choices[0].message.content
            message_placeholder.markdown(convert_latex_format(full_reply))
        
        st.session_state.messages.append({"role": "assistant", "content": full_reply})
        st.rerun()
        
    except Exception as e:
        st.error(f"错误: {str(e)}")
