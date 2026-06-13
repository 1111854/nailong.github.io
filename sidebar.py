# sidebar.py
import streamlit as st
import os
from datetime import datetime
from config import API_URL, DEEPSEEK_URL, BASE_DIR
from utils import AVAILABLE_MODELS, DEFAULT_MODEL, THINKING_MODELS, SEARCH_ENABLED_MODELS
from conversation import list_conversations, load_conversation, delete_conversation

def render_sidebar():
    with st.sidebar:
        st.markdown(f"### 👤 用户：{st.session_state.username}")
        
        # ===== 添加头像设置区域 =====
        with st.expander("🎨 个性化设置（修改头像）", expanded=False):
            st.markdown("### 头像设置")
            
            # 用户头像设置
            st.markdown("**👤 用户头像**")
            user_avatar_choice = st.selectbox(
                "选择用户头像",
                ["默认图片", "上传图片"],
                key="user_avatar_choice",
                label_visibility="collapsed"
            )
            
            if user_avatar_choice == "默认图片":
                # 恢复默认头像
                default_path = os.path.join(BASE_DIR, "User_avatar_default.png")
                if os.path.exists(default_path):
                    import shutil
                    shutil.copy(default_path, os.path.join(BASE_DIR, "User_avatar.png"))
                    st.success("已恢复默认头像")
                    st.rerun()
                else:
                    st.info("默认头像文件不存在")
            
            elif user_avatar_choice == "上传图片":
                uploaded_user_img = st.file_uploader(
                    "上传头像图片", 
                    type=['png', 'jpg', 'jpeg'],
                    key="user_avatar_upload",
                    label_visibility="collapsed"
                )
                if uploaded_user_img:
                    save_path = os.path.join(BASE_DIR, "User_avatar.png")
                    with open(save_path, "wb") as f:
                        f.write(uploaded_user_img.getbuffer())
                    st.image(uploaded_user_img, width=80, caption="预览")
                    st.success("头像已更新！")
                    st.rerun()
            
            st.markdown("---")
            
            # AI头像设置
            st.markdown("**🤖 AI头像**")
            ai_avatar_choice = st.selectbox(
                "选择AI头像",
                ["默认图片", "上传图片"],
                key="ai_avatar_choice",
                label_visibility="collapsed"
            )
            
            if ai_avatar_choice == "默认图片":
                default_path = os.path.join(BASE_DIR, "AI_avatar_default.png")
                if os.path.exists(default_path):
                    import shutil
                    shutil.copy(default_path, os.path.join(BASE_DIR, "AI_avatar.png"))
                    st.success("已恢复默认头像")
                    st.rerun()
                else:
                    st.info("默认头像文件不存在")
            
            elif ai_avatar_choice == "上传图片":
                uploaded_ai_img = st.file_uploader(
                    "上传头像图片", 
                    type=['png', 'jpg', 'jpeg'],
                    key="ai_avatar_upload",
                    label_visibility="collapsed"
                )
                if uploaded_ai_img:
                    save_path = os.path.join(BASE_DIR, "AI_avatar.png")
                    with open(save_path, "wb") as f:
                        f.write(uploaded_ai_img.getbuffer())
                    st.image(uploaded_ai_img, width=80, caption="预览")
                    st.success("头像已更新！")
                    st.rerun()
            
            st.markdown("---")
            st.caption("💡 提示：修改后刷新页面或发送新消息即可看到新头像")
        
        # ===== 原有的退出登录按钮 =====
        if st.button("🚪 退出登录"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        st.markdown("### 🏀 牢大GPT")
        
        gif_path = os.path.join(BASE_DIR, "banner.gif")
        if os.path.exists(gif_path):
            st.image(gif_path)

        # API 密钥设置
        api_key_env = os.environ.get('CAPI')
        if api_key_env:
            st.session_state.api_key = api_key_env
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
        )
        if selected_model != st.session_state.selected_model:
            st.session_state.selected_model = selected_model
            st.rerun()
        st.caption(f"当前模型: `{st.session_state.selected_model}`")

        # 根据模型设定 API 地址和密钥
        if selected_model == "deepseek-v4-pro":
            st.session_state.api_url = DEEPSEEK_URL
            if os.environ.get('DAPI'):
                st.session_state.api_key = os.environ.get('DAPI')
            st.info("💎 使用 DeepSeek 官方 API（稳定但收费）")
        else:
            st.session_state.api_url = API_URL
            if os.environ.get('CAPI'):
                st.session_state.api_key = os.environ.get('CAPI')
            st.info("🎲 使用中转站 API（免费但可能坠机）")

        # 显示模型特性
        if selected_model in THINKING_MODELS:
            st.caption("🧠 支持深度思考")
        if selected_model in SEARCH_ENABLED_MODELS:
            st.caption("🌐 支持联网搜索")

        st.markdown("---")

        # 联网搜索开关
        search_supported = selected_model in SEARCH_ENABLED_MODELS
        if search_supported:
            st.session_state.web_search = st.toggle("🌐 开启联网搜索", value=st.session_state.web_search)
        else:
            st.session_state.web_search = False
            st.caption("⚠️ 当前模型不支持联网搜索")
        st.markdown("---")

        # 自定义提示词
        st.subheader("🎭 AI角色设定")
        new_prompt = st.text_area("自定义系统提示词", value=st.session_state.system_prompt, height=120)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 保存提示词", use_container_width=True):
                st.session_state.system_prompt = new_prompt
                st.success("已保存！")
                st.rerun()
        with col2:
            if st.button("🔄 重置", use_container_width=True):
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
                if 'need_regenerate' in st.session_state:
                    del st.session_state.need_regenerate
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

        # 历史记录
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
