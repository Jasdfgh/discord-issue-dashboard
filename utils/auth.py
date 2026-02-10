"""
简单密码认证模块
用于 Streamlit Cloud 公网部署时的访问控制

- Docker 内网部署: REQUIRE_AUTH=false (默认), 不弹密码
- Streamlit Cloud: REQUIRE_AUTH=true, 需要输入共享密码
"""

import os
import hmac
import streamlit as st


def _is_auth_required():
    """Check if authentication is required"""
    # 环境变量控制 (Docker 部署用)
    env_val = os.getenv("REQUIRE_AUTH", "").lower()
    if env_val in ("true", "1", "yes"):
        return True
    if env_val in ("false", "0", "no"):
        return False
    
    # 如果 st.secrets 中有 password 字段，则启用认证
    try:
        if "password" in st.secrets:
            return True
    except Exception:
        pass
    
    return False


def _get_password():
    """Get the configured password from secrets or env"""
    # 优先 st.secrets
    try:
        if "password" in st.secrets:
            return st.secrets["password"]
    except Exception:
        pass
    
    # fallback 到环境变量
    return os.getenv("DASHBOARD_PASSWORD", "")


def check_auth():
    """
    Check authentication. Call at the top of every page.
    
    - If auth is not required, returns immediately (no UI change)
    - If auth is required, shows login form and blocks with st.stop()
    """
    if not _is_auth_required():
        return
    
    # Already verified this session
    if st.session_state.get("authenticated", False):
        return
    
    # Show login form
    _show_login()
    st.stop()


def _show_login():
    """Render the login form"""
    # Note: set_page_config is called by the importing page, not here
    st.markdown("## 🔒 Discord Issue Dashboard")
    st.markdown("Please enter the access password to continue.")
    
    password_input = st.text_input(
        "Password",
        type="password",
        placeholder="Enter password...",
        key="login_password_input",
    )
    
    if st.button("Login", type="primary"):
        expected = _get_password()
        if expected and hmac.compare_digest(password_input, expected):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
