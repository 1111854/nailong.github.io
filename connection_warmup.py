# connection_warmup.py - 新建文件

import streamlit as st
import time
import threading
from datetime import datetime
import requests

class ConnectionWarmup:
    """连接预热管理器"""
    
    def __init__(self):
        self.last_warmup = None
        self.is_warming = False
        
    def warmup_if_needed(self, api_key, api_url):
        """如果需要则预热连接"""
        now = time.time()
        
        # 每30秒预热一次
        if self.last_warmup and (now - self.last_warmup) < 30:
            return
        
        # 避免重复预热
        if self.is_warming:
            return
        
        # 启动后台预热
        def warmup():
            self.is_warming = True
            try:
                # 创建连接
                session = requests.Session()
                session.headers.update({
                    'Authorization': f'Bearer {api_key}',
                    'Connection': 'keep-alive'
                })
                
                # 建立TCP连接（不发送实际请求）
                session.get(api_url, timeout=2)
                
                # 保持会话
                st.session_state._warm_session = session
                self.last_warmup = time.time()
                
            except Exception as e:
                # 预热失败不影响主流程
                pass
            finally:
                self.is_warming = False
        
        thread = threading.Thread(target=warmup, daemon=True)
        thread.start()
    
    def get_warm_session(self):
        """获取预热的会话"""
        return st.session_state.get('_warm_session')

# 创建全局实例
warmup_manager = ConnectionWarmup()

# 在nl.py中使用
from connection_warmup import warmup_manager

# 在用户登录后
if st.session_state.logged_in:
    warmup_manager.warmup_if_needed(
        st.session_state.api_key,
        st.session_state.api_url
    )

# 在发送消息时使用预热会话
if prompt and st.session_state.api_key:
    # 使用预热过的会话
    warm_session = warmup_manager.get_warm_session()
    if warm_session:
        # 复用连接
        client = get_openai_client_with_session(warm_session)
    else:
        client = get_openai_client(...)
