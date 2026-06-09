import flet as ft
import os
import json
from datetime import datetime
import base64
import PyPDF2
import docx
import re
import time
import threading
import httpx
from openai import OpenAI
from tavily import TavilyClient

# 导入模型配置
from utils import AVAILABLE_MODELS, DEFAULT_MODEL

# ========== 配置 ==========
API_URL = "https://mynewapi.n1neman.fun/v1"
TAVILY_KEY = "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"

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

for dir_path in [HISTORY_DIR, UPLOAD_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# ========== 联网搜索函数 ==========
def search_web(query, max_results=3):
    try:
        client = TavilyClient(api_key=TAVILY_KEY)
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

# ========== 文件处理函数 ==========
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

def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

# ========== LaTeX渲染函数 ==========
def convert_latex_format(text):
    if not isinstance(text, str):
        return text
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    return text

# ========== 保存对话 ==========
def save_conversation(session_id, messages, system_prompt):
    filename = os.path.join(HISTORY_DIR, f"chat_{session_id}.json")
    data = {
        "id": session_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": messages,
        "system_prompt": system_prompt
    }
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def load_conversation(session_id):
    filename = os.path.join(HISTORY_DIR, f"chat_{session_id}.json")
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

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

# ========== 主应用 ==========
def main(page: ft.Page):
    page.title = "奶龙ChatGPT"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.window_width = 400
    page.window_height = 700
    
    # 状态变量
    messages = []
    api_key = None
    selected_model = DEFAULT_MODEL
    system_prompt = "你是一个友好的AI助手，名叫奶龙。你会用生动、有趣的方式回答问题。"
    web_search_enabled = False
    current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    uploaded_files = []
    
    # 聊天显示容器
    chat_container = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    
    # 输入框
    input_field = ft.TextField(
        hint_text="输入消息...",
        multiline=True,
        min_lines=1,
        max_lines=5,
        expand=True,
        border_radius=20,
        bgcolor=ft.Colors.WHITE,
    )
    
    # ========== 发送消息函数 ==========
    def send_message(e):
        nonlocal api_key, selected_model, system_prompt, web_search_enabled, current_session_id, uploaded_files, messages
        
        prompt = input_field.value
        if not prompt:
            return
        
        input_field.value = ""
        page.update()
        
        # 添加用户消息到界面
        user_bubble = ft.Container(
            content=ft.Text(prompt, size=14),
            padding=10,
            border_radius=ft.border_radius.only(top_left=10, top_right=10, bottom_left=10),
            bgcolor=ft.Colors.BLUE_400,
            alignment=ft.alignment.center_right,
        )
        chat_container.controls.append(ft.Row([user_bubble], alignment=ft.MainAxisAlignment.END))
        page.update()
        
        # 保存用户消息
        messages.append({"role": "user", "content": prompt})
        
        # 显示思考状态
        thinking = ft.Row([ft.ProgressRing(width=20, height=20), ft.Text("🐉 奶龙正在思考...")], alignment=ft.MainAxisAlignment.START)
        chat_container.controls.append(thinking)
        page.update()
        
        # 在新线程中处理API请求
        def process():
            nonlocal messages
            
            try:
                http_client = httpx.Client(timeout=120, follow_redirects=True)
                client = OpenAI(
                    api_key=api_key or os.environ.get('CAPI', ''),
                    base_url=API_URL,
                    http_client=http_client
                )
                
                # 联网搜索
                search_context = ""
                search_results = []
                if web_search_enabled:
                    search_results = search_web(prompt)
                    if search_results:
                        search_context = "\n\n【联网搜索结果】\n"
                        for i, r in enumerate(search_results, 1):
                            search_context += f"\n{i}. {r['title']}\n   {r['snippet']}\n"
                        search_context += "\n请基于以上搜索结果回答用户问题。"
                
                # 构建消息
                system_content = system_prompt
                if search_context:
                    system_content += search_context
                
                api_messages = [{"role": "system", "content": system_content}]
                for msg in messages[:-1]:
                    api_messages.append({"role": msg["role"], "content": msg["content"]})
                api_messages.append({"role": "user", "content": prompt})
                
                # 调用API
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=api_messages
                )
                full_reply = response.choices[0].message.content or ""
                
                # 移除思考状态
                chat_container.controls.remove(thinking)
                
                # 显示搜索结果（如果有）
                if search_results:
                    search_expand = ft.ExpansionTile(
                        title=ft.Text("🌐 联网搜索结果"),
                        controls=[ft.Text(f"{i+1}. {r['title']}\n{r['snippet'][:200]}") for i, r in enumerate(search_results[:3])]
                    )
                    chat_container.controls.append(search_expand)
                
                # 显示AI回答
                reply_bubble = ft.Container(
                    content=ft.Text(full_reply, size=14, selectable=True),
                    padding=10,
                    border_radius=ft.border_radius.only(top_left=10, top_right=10, bottom_right=10),
                    bgcolor=ft.Colors.GREY_200,
                )
                chat_container.controls.append(ft.Row([reply_bubble], alignment=ft.MainAxisAlignment.START))
                
                # 保存消息
                messages.append({"role": "assistant", "content": full_reply})
                save_conversation(current_session_id, messages, system_prompt)
                
                page.update()
                
            except Exception as e:
                chat_container.controls.remove(thinking)
                error_bubble = ft.Container(
                    content=ft.Text(f"错误: {str(e)}", size=14, color=ft.Colors.RED),
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.Colors.RED_50,
                )
                chat_container.controls.append(ft.Row([error_bubble], alignment=ft.MainAxisAlignment.START))
                page.update()
        
        threading.Thread(target=process).start()
    
    # ========== 侧边栏抽屉 ==========
    def close_drawer(e):
        page.close(drawer)
    
    drawer = ft.NavigationDrawer(
        controls=[
            ft.Container(height=20),
            ft.Text("🐉 奶龙ChatGPT", size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("🤖 模型选择", size=16, weight=ft.FontWeight.BOLD),
            ft.Dropdown(
                options=[ft.dropdown.Option(m) for m in AVAILABLE_MODELS],
                value=selected_model,
                on_change=lambda e: setattr(globals(), 'selected_model', e.data)
            ),
            ft.Divider(),
            ft.Row([
                ft.Text("🌐 联网搜索"),
                ft.Switch(value=web_search_enabled, on_change=lambda e: setattr(globals(), 'web_search_enabled', e.data))
            ]),
            ft.Divider(),
            ft.Text("🎭 AI角色设定", size=16, weight=ft.FontWeight.BOLD),
            ft.TextField(
                hint_text="自定义系统提示词",
                value=system_prompt,
                multiline=True,
                min_lines=3,
                max_lines=5,
                on_change=lambda e: setattr(globals(), 'system_prompt', e.data)
            ),
            ft.Divider(),
            ft.Text("💬 对话管理", size=16, weight=ft.FontWeight.BOLD),
            ft.ElevatedButton("✨ 新建对话", on_click=lambda e: clear_conversation()),
            ft.ElevatedButton("🗑️ 删除当前", on_click=lambda e: delete_current()),
        ],
    )
    
    def clear_conversation():
        nonlocal messages, current_session_id
        messages = []
        current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        chat_container.controls.clear()
        page.close(drawer)
        page.update()
    
    def delete_current():
        nonlocal messages
        if messages:
            delete_conversation(current_session_id)
            messages = []
            chat_container.controls.clear()
        page.close(drawer)
        page.update()
    
    # ========== 主界面布局 ==========
    app_bar = ft.AppBar(
        title=ft.Text("奶龙ChatGPT"),
        center_title=True,
        leading=ft.IconButton(ft.icons.MENU, on_click=lambda e: page.open(drawer)),
        bgcolor=ft.Colors.BLUE_400,
    )
    
    # 输入行
    input_row = ft.Row([
        input_field,
        ft.IconButton(ft.icons.SEND, icon_color=ft.Colors.BLUE_400, on_click=send_message),
    ])
    
    page.add(app_bar)
    page.add(ft.Container(content=chat_container, expand=True))
    page.add(ft.Container(content=input_row, padding=10))
    
    # 加载历史对话
    conversations = list_conversations()
    if conversations:
        for conv in conversations[:3]:
            data = load_conversation(conv["id"])
            if data:
                messages = data["messages"]
                current_session_id = conv["id"]
                for msg in messages:
                    if msg["role"] == "user":
                        user_bubble = ft.Container(
                            content=ft.Text(msg["content"], size=14),
                            padding=10,
                            border_radius=ft.border_radius.only(top_left=10, top_right=10, bottom_left=10),
                            bgcolor=ft.Colors.BLUE_400,
                        )
                        chat_container.controls.append(ft.Row([user_bubble], alignment=ft.MainAxisAlignment.END))
                    else:
                        reply_bubble = ft.Container(
                            content=ft.Text(msg["content"], size=14, selectable=True),
                            padding=10,
                            border_radius=ft.border_radius.only(top_left=10, top_right=10, bottom_right=10),
                            bgcolor=ft.Colors.GREY_200,
                        )
                        chat_container.controls.append(ft.Row([reply_bubble], alignment=ft.MainAxisAlignment.START))
                break
        page.update()

ft.app(target=main)