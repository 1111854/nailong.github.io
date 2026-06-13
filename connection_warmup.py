# connection_warmup.py - 线程安全版本

import streamlit as st
import time
import threading
import requests
from streamlit.runtime.scriptrunner import add_script_run_ctx

class ConnectionWarmup:
    """连接预热管理器（线程安全版本）"""
    
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
        
        # 启动后台预热（带 Streamlit 上下文）
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
                
                # ✅ 关键：在 Streamlit 上下文中安全访问 session_state
                st.session_state._warm_session = session
                self.last_warmup = time.time()
                
            except Exception as e:
                # 预热失败不影响主流程
                print(f"预热失败: {e}")
            finally:
                self.is_warming = False
        
        # 创建线程
        thread = threading.Thread(target=warmup, daemon=True)
        
        # ✅ 关键：添加 Streamlit 脚本运行上下文
        add_script_run_ctx(thread)
        
        # 启动线程
        thread.start()
    
    def get_warm_session(self):
        """获取预热的会话"""
        return st.session_state.get('_warm_session')

# 创建全局实例
warmup_manager = ConnectionWarmup()
