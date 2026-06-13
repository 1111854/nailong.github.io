# latex_utils.py
import streamlit as st
import re

def is_broken_format(text):
    if not isinstance(text, str):
        return False
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) > 3:
        single_char_count = sum(1 for line in lines[:15] if len(line) == 1)
        if single_char_count > len(lines[:15]) * 0.6:
            return True
    return False

def convert_latex_format(text):
    """将 \[ \] 和 \( \) 格式的 LaTeX 转换为 $$ 和 $ 格式"""
    if not isinstance(text, str):
        return text
    # 修复正则：\[ ... \] -> $$ ... $$
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    # 修复正则：\( ... \) -> $ ... $
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    # 修复微分符号间距
    text = re.sub(r',(dx|dy|dz|dr|dt|d\\theta)', r',\1', text)
    return text

def render_with_latex(content):
    if content:
        try:
            converted = convert_latex_format(content)
            st.markdown(converted)
        except Exception:
            st.text(content)
