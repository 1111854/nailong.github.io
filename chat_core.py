import time
import re
import httpx
from openai import OpenAI
import streamlit as st
from config import API_URL
from latex_utils import convert_latex_format

def search_web(query, max_results=3):
    from tavily import TavilyClient
    tavily_key = "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"
    try:
        client = TavilyClient(api_key=tavily_key)
        response = client.search(query=query, search_depth="basic", max_results=max_results, include_answer=True)
        results = []
        if response.get('answer'):
            results.append({'title': '📌 AI 总结', 'snippet': response['answer']})
        for item in response.get('results', [])[:max_results]:
            results.append({'title': item.get('title', '无标题'), 'snippet': item.get('content', '无内容')[:300]})
        return results
    except:
        return []

def send_message(messages, model, api_key, system_prompt):
    http_client = httpx.Client(timeout=120, follow_redirects=True)
    client = OpenAI(api_key=api_key, base_url=API_URL, http_client=http_client)
    api_messages = [{"role": "system", "content": system_prompt}] + messages
    response = client.chat.completions.create(model=model, messages=api_messages)
    return response.choices[0].message.content or ""

def stream_response(full_reply, message_placeholder):
    displayed = ""
    for char in full_reply:
        displayed += char
        message_placeholder.markdown(convert_latex_format(displayed) + '<span class="typing-cursor"></span>', unsafe_allow_html=True)
        time.sleep(0.008)
    message_placeholder.markdown(convert_latex_format(full_reply))