# styles.py
import streamlit as st

def apply_custom_styles():
    """应用自定义 CSS 样式"""
    st.markdown("""
<style>
@media (max-width: 768px) {
    .stButton button { font-size: 14px; padding: 5px 10px; }
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}
.typing-cursor {
    animation: blink 1s infinite;
    display: inline-block;
    width: 2px;
    height: 1.2em;
    background-color: #00adb5;
    margin-left: 2px;
    vertical-align: middle;
}
.stButton button {
    background: transparent;
    border: none;
    padding: 0 5px;
    font-size: 16px;
    opacity: 0.6;
    transition: opacity 0.3s;
}
.stButton button:hover {
    opacity: 1;
    background: transparent;
}
</style>
""", unsafe_allow_html=True)
