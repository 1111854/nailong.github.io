# conversation.py
import streamlit as st
from datetime import datetime
from auth import save_user_conversation, load_user_conversations, delete_user_conversation

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
