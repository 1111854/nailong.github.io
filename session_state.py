import streamlit as st
from datetime import datetime
from config import API_URL
from utils import DEFAULT_MODEL

def init_session_state():
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
        st.session_state.system_prompt = "你是科比·布莱恩特。公式必须用$$写在一行，如$$\\int_a^b fdx$$"
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = DEFAULT_MODEL
    if 'web_search' not in st.session_state:
        st.session_state.web_search = False
    if 'api_url' not in st.session_state:
        st.session_state.api_url = API_URL
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
