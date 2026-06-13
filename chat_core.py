# chat_core.py
import streamlit as st
import time
import re
import httpx
from crash_messages import get_random_crash_message, get_random_quote
from config import UPDATE_INTERVAL
from latex_utils import convert_latex_format, is_broken_format

def stream_response(client, api_messages, selected_model, message_placeholder, status_placeholder):
    """流式响应处理（支持停止生成）"""
    full_reply = ""
    first_token_received = False
    
    # 初始化停止标志
    if 'stop_generation' not in st.session_state:
        st.session_state.stop_generation = False
    st.session_state.stop_generation = False
    
    # 创建停止按钮（在状态栏中）
    with status_placeholder.container():
        col1, col2 = st.columns([3, 1])
        col1.markdown("🏀 **牢大正在肘击...**")
        stop_button = col2.button("⏹️ 停止", key="stop_btn", use_container_width=True)
    
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
        # 检查是否点击了停止按钮
        if stop_button or st.session_state.stop_generation:
            st.session_state.stop_generation = True
            status_placeholder.markdown("⏸️ **生成已停止**")
            full_reply += "\n\n---\n*（用户停止了生成）*"
            break
        
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
                # 清除状态栏内容但保留停止按钮区域
                status_placeholder.empty()
                # 重新显示状态栏（不带停止按钮）
                with status_placeholder.container():
                    col1, col2 = st.columns([3, 1])
                    col1.markdown("🏀 **牢大正在肘击...**")
                    # 更新停止按钮的引用
                    stop_button = col2.button("⏹️ 停止", key="stop_btn_active", use_container_width=True)
            
            now = time.time()
            if buffer_size >= 3 or (now - last_update_time) >= UPDATE_INTERVAL:
                if is_broken_format(full_reply):
                    fixed = re.sub(r'\s+', '', full_reply)
                    full_reply = f'$$\n{fixed}\n$$'
                
                converted = convert_latex_format(full_reply)
                # 如果未停止，显示光标
                if not st.session_state.stop_generation:
                    message_placeholder.markdown(
                        converted + '<span class="typing-cursor"></span>',
                        unsafe_allow_html=True
                    )
                else:
                    message_placeholder.markdown(converted, unsafe_allow_html=True)
                last_update_time = now
                buffer = ""
                buffer_size = 0
    
    # 清理：移除光标并显示最终内容
    if not st.session_state.stop_generation:
        final_converted = convert_latex_format(full_reply)
        message_placeholder.markdown(final_converted, unsafe_allow_html=True)
    
    status_placeholder.empty()
    return full_reply


# 简化版（如果你觉得上面的太复杂，用这个版本）
def stream_response_simple(client, api_messages, selected_model, message_placeholder, status_placeholder):
    """流式响应处理（简化版，仅支持停止）"""
    full_reply = ""
    
    # 重置停止标志
    st.session_state.stop_generation = False
    
    # 显示停止按钮
    status = status_placeholder.markdown("🏀 **牢大正在肘击...**")
    stop_col = status_placeholder.empty()
    if stop_col.button("⏹️ 停止", key="simple_stop"):
        st.session_state.stop_generation = True
    
    try:
        stream_response = client.chat.completions.create(
            model=selected_model,
            messages=api_messages,
            stream=True,
            timeout=httpx.Timeout(60.0, connect=10.0)
        )
        
        for chunk in stream_response:
            if st.session_state.stop_generation:
                status_placeholder.markdown("⏸️ **已停止生成**")
                full_reply += "\n\n[用户停止了生成]"
                break
            
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_reply += content
                
                # 实时显示
                converted = convert_latex_format(full_reply)
                message_placeholder.markdown(
                    converted + (' ▌' if not st.session_state.stop_generation else ''),
                    unsafe_allow_html=True
                )
        
        status_placeholder.empty()
        return full_reply
        
    except Exception as e:
        status_placeholder.empty()
        return render_crash_message(str(e), type(e).__name__, message_placeholder)


def render_crash_message(error_msg, error_type, message_placeholder):
    """显示坠机消息"""
    death_msg = get_random_crash_message()
    quote = get_random_quote()
    
    st.error(f"💀 **{death_msg}** 💀")
    st.caption(f"🏀 牢大状态: RIP | 错误代码: {error_type}")
    st.markdown(f"> *{quote}*")
    
    with st.expander("🔧 坠机黑匣子记录 (点击展开)"):
        st.code(f"错误详情: {error_msg[:500]}")
        import traceback
        st.code(traceback.format_exc())
    
    full_reply = f"💀 **{death_msg}**\n\n牢大暂时无法肘击，请稍后再试...\n\n🕯️ RIP 🕯️"
    message_placeholder.markdown(full_reply)
    return full_reply
