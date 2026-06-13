# session_state.py
import streamlit as st
from datetime import datetime
from config import API_URL
from utils import DEFAULT_MODEL

def init_session_state():
    """初始化所有 session state 变量"""
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
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_avatar' not in st.session_state:
        st.session_state.user_avatar = "👤"
    if 'user_avatar_type' not in st.session_state:
        st.session_state.user_avatar_type = "emoji"
    if 'user_avatar_image' not in st.session_state:
        st.session_state.user_avatar_image = None
    if 'user_avatar_url' not in st.session_state:
        st.session_state.user_avatar_url = ""
    if 'ai_avatar' not in st.session_state:
        st.session_state.ai_avatar = "🤖"
    if 'ai_avatar_type' not in st.session_state:
        st.session_state.ai_avatar_type = "emoji"
    if 'ai_avatar_image' not in st.session_state:
        st.session_state.ai_avatar_image = None
    if 'ai_avatar_url' not in st.session_state:
        st.session_state.ai_avatar_url = ""
    if 'username' not in st.session_state:
        st.session_state.username = None
