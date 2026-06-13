# chat_core.py - 聊天核心逻辑
import streamlit as st
import time
import httpx
from crash_messages import get_random_crash_message, get_random_quote
from latex_utils import convert_latex_format, is_broken_format
from config import UPDATE_INTERVAL

def stream_response(client, api_messages, selected_model, message_placeholder, status_placeholder):
    """流式响应处理"""
    full_reply = ""
    start_time = time.time()
    first_token_received = False
    
    stream_response = client.chat.completions.create(
        model=selected_model,
        messages=api_messages,
        stream=True,
        timeout=httpx.Timeout(60.0, connect=10.0)
    )
    
    last_update_time = time.time()
    buffer = ""
    buffer_size = 0
    
    for chunk in stream_response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            content_chunk = delta.content
            full_reply += content_chunk
            buffer += content_chunk
            buffer_size += len(content_chunk)
            
            if not first_token_received:
                first_token_received = True
                status_placeholder.empty()
            
            now = time.time()
            if buffer_size >= 3 or (now - last_update_time) >= UPDATE_INTERVAL:
                if is_broken_format(full_reply):
                    fixed = re.sub(r'\s+', '', full_reply)
                    full_reply = f'$$\n{fixed}\n$$'
                
                converted = convert_latex_format(full_reply)
                message_placeholder.markdown(
                    converted + '<span class="typing-cursor"></span>',
                    unsafe_allow_html=True
                )
                last_update_time = now
                buffer = ""
                buffer_size = 0
    
    return full_reply

def render_crash_message(error_msg, error_type, message_placeholder):
    """显示坠机消息"""
    death_msg = get_random_crash_message()
    quote = get_random_quote()
    
    st.error(f"💀 **{death_msg}** 💀")
    st.caption(f"🏀 牢大状态: RIP | 错误: {error_type}")
    st.markdown(f"> *{quote}*")
    
    with st.expander("🔧 坠机黑匣子记录 (点击展开)"):
        st.code(f"错误详情: {error_msg[:500]}")
        import traceback
        st.code(traceback.format_exc())
    
    full_reply = f"💀 **{death_msg}**\n\n牢大暂时无法肘击，请稍后再试...\n\n🕯️ RIP 🕯️"
    message_placeholder.markdown(full_reply)
    return full_reply
