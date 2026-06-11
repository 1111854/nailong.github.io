import re
import streamlit as st

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
    if not isinstance(text, str):
        return text
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    text = re.sub(r',(dx|dy|dz|dr|dt|d\\theta)', r'\,\1', text)
    return text

def render_with_latex(content):
    if content:
        try:
            st.markdown(convert_latex_format(content))
        except Exception:
            st.text(content)