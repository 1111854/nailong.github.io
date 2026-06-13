# ========== 模型配置 ==========
# 所有可用模型
AVAILABLE_MODELS = [
    "deepseek-v4-pro",
    "gpt-5.4",
    "gpt-5.4-mini", 
    "gpt-5.5",
    "codex-auto-review",
    "claude-sonnet-4-6-thinking",
    "claude-sonnet-4-6",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-haiku-4-5-20251001",
    "claude-haiku-4-5",
    "gpt-oss-120b-medium",
    "gpt-image-2",
    "gemini-pro-agent",
    "gemini-3.5-flash-low",
    "gemini-3.1-pro-preview",
    "gemini-3.1-pro-low",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-image-preview",
    "gemini-3.1-flash-image",
]
# ========== 深度思考支持的模型 ==========
THINKING_MODELS = [
    "claude-sonnet-4-6-thinking",
    "claude-sonnet-4-6",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.5",
    "gemini-3.1-pro-preview",
    "gemini-3.5-flash-low",
    "gemini-3.1-flash-lite",
    "deepseek-v4-pro"
]

# ========== 联网搜索支持的模型 ==========
SEARCH_ENABLED_MODELS = [
    "gpt-5.4",
    "gpt-5.4-mini", 
    "gpt-5.5",
    "claude-sonnet-4-6",
    "gemini-3.5-flash-low",
    "deepseek-v4-pro"
]

# 默认模型
DEFAULT_MODEL = "gpt-5.5"
# ========== 添加到 utils.py 末尾 ==========
import httpx
from openai import OpenAI
import streamlit as st

@st.cache_resource
def get_openai_client(api_key, api_url):
    """获取 OpenAI 客户端（带缓存）"""
    http_client = httpx.Client(
        timeout=httpx.Timeout(60.0, connect=10.0),
        follow_redirects=True
    )
    return OpenAI(
        api_key=api_key,
        base_url=api_url,
        http_client=http_client
    )

def search_web(query, max_results=3):
    """联网搜索"""
    from tavily import TavilyClient
    import os
    
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return []
    try:
        client = TavilyClient(api_key=tavily_key)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True
        )
        results = []
        if response.get('answer'):
            results.append({'title': '📌 AI 总结', 'snippet': response['answer']})
        for item in response.get('results', [])[:max_results]:
            results.append({
                'title': item.get('title', '无标题'),
                'snippet': item.get('content', '无内容')[:300]
            })
        return results
    except Exception as e:
        st.toast(f"搜索失败: {str(e)[:50]}", icon="⚠️")
        return []
