import streamlit as st
from latex_utils import render_with_latex

def get_avatar(role, base_dir):
    if role == "user":
        avatar_path = os.path.join(base_dir, "User_avatar.png")
    else:
        avatar_path = os.path.join(base_dir, "AI_avatar.png")
    if os.path.exists(avatar_path):
        return avatar_path
    return "🐉" if role == "user" else "🤖"

def render_messages(messages, base_dir, on_regenerate, on_delete):
    for idx, message in enumerate(messages):
        avatar = get_avatar(message["role"], base_dir)
        with st.chat_message(message["role"], avatar=avatar):
            if "files" in message:
                st.caption("📎 附件:")
                for file in message["files"]:
                    st.write(f"- {file['name']}")
            render_with_latex(message["content"])
            
            if message["role"] == "assistant":
                col1, col2, col3, _ = st.columns([1, 1, 1, 6])
                with col1:
                    if st.button("📋", key=f"copy_{idx}", help="复制消息"):
                        st.toast("📋 请手动选中文本后按 Ctrl+C 复制", icon="📋")
                with col2:
                    if idx == len(messages) - 1:
                        if st.button("🔄", key=f"regenerate_{idx}", help="重新生成"):
                            on_regenerate()
                with col3:
                    if st.button("🗑️", key=f"delete_msg_{idx}", help="删除从此处开始的对话"):
                        on_delete(idx)
            else:
                col1, col2, _ = st.columns([1, 1, 8])
                with col1:
                    if st.button("📋", key=f"copy_user_{idx}", help="复制消息"):
                        st.toast("📋 请手动选中文本后按 Ctrl+C 复制", icon="📋")
                with col2:
                    if st.button("🗑️", key=f"delete_user_msg_{idx}", help="删除从此处开始的对话"):
                        on_delete(idx)