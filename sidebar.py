# 用户头像 - 上传图片
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
        st.success("✅ 头像已更新！刷新页面或发送新消息即可看到")

# AI头像 - 上传图片
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
        st.success("✅ 头像已更新！刷新页面或发送新消息即可看到")
