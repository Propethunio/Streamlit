NEON_CSS = """
<style>
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.loader {
    border: 3px solid rgba(0, 212, 255, 0.1); border-top: 3px solid #00d4ff;
    border-radius: 50%; width: 24px; height: 24px; animation: spin 1s linear infinite;
    display: inline-block; margin-right: 10px; vertical-align: middle;
}
.thinking-box {
    background: rgba(0, 212, 255, 0.05); border: 1px solid rgba(0, 212, 255, 0.2);
    padding: 15px; border-radius: 10px; color: #00d4ff;
    font-family: 'Courier New', monospace; margin-bottom: 20px;
}
.stApp { background: radial-gradient(circle at top right, #0f0c29, #0b0d17, #000000); color: #e6edf3; }
.stChatMessage {
    background: rgba(255, 255, 255, 0.03) !important; backdrop-filter: blur(15px);
    border: 1px solid rgba(0, 212, 255, 0.15) !important; border-radius: 15px !important;
}
.big-title {
    font-size: 50px !important; font-weight: 900 !important;
    background: linear-gradient(90deg, #00d4ff, #8a2be2, #ff00c8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-align: center; margin-top: -20px; margin-bottom: 20px;
}
.rpg-card {
    background: rgba(138, 43, 226, 0.06); border: 1px solid rgba(138, 43, 226, 0.3);
    padding: 14px; border-radius: 10px; margin-bottom: 12px; font-size: 14px; line-height: 1.5;
}
[data-testid="stSidebar"] {
    background-color: #080911 !important;
    border-right: 1px solid rgba(0, 212, 255, 0.1) !important;
}
[data-testid="stSidebar"] .stExpander {
    background: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(0, 212, 255, 0.1) !important;
    border-radius: 10px !important; margin-bottom: 12px !important;
}
[data-testid="stSidebar"] p { color: #b4c6ef !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(0, 212, 255, 0.1) !important;
    padding: 10px 15px !important; border-radius: 8px !important;
    margin-bottom: 8px !important; transition: all 0.3s ease;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
    border-color: #00d4ff !important; background: rgba(0, 212, 255, 0.05) !important;
}
/* Przyciski globalne (akcje resetowania itp.) */
button[kind="primary"], button[data-testid="baseButton-primary"] {
    background-color: #ff2a5f !important; border: 1px solid #ff003c !important;
    box-shadow: 0 0 10px rgba(255, 42, 95, 0.2) !important;
}
button[kind="primary"] p, button[data-testid="baseButton-primary"] p {
    color: #ffffff !important; font-weight: 700 !important;
}
/* Przyciski secondary w głównej treści (opcje RPG i inne) — jednolity styl fioletowy */
[data-testid="stMainBlockContainer"] button[kind="secondary"],
[data-testid="stMainBlockContainer"] button[data-testid="baseButton-secondary"] {
    background: rgba(138, 43, 226, 0.08) !important;
    border: 1px solid rgba(138, 43, 226, 0.4) !important;
    color: #e6edf3 !important;
    border-radius: 10px !important; transition: all 0.25s ease !important;
}
[data-testid="stMainBlockContainer"] button[kind="secondary"]:hover,
[data-testid="stMainBlockContainer"] button[data-testid="baseButton-secondary"]:hover {
    background: rgba(138, 43, 226, 0.2) !important;
    border-color: #8a2be2 !important;
    box-shadow: 0 0 12px rgba(138, 43, 226, 0.25) !important;
}
/* Redukowanie efektu przyciemnienia podczas rerunu Streamlita */
[data-testid="stAppViewContainer"] { transition: opacity 0.05s !important; }
.custom-hr { margin-top: 15px !important; margin-bottom: 15px !important; border: 0; border-top: 1px solid rgba(0, 212, 255, 0.15); }
.token-counter {
    padding: 12px; border-radius: 10px; background: rgba(0, 212, 255, 0.04);
    border: 1px solid rgba(0, 212, 255, 0.2); font-family: monospace; font-size: 12px; color: #00d4ff;
}
</style>
"""

THINKING_BOX_HTML = '<div class="thinking-box"><div class="loader"></div><span>{message}</span></div>'

# JS scrollujący do dołu strony — działa przez iframe komponentu Streamlit
SCROLL_TO_BOTTOM_JS = """
<script>
(function() {
    function scrollToBottom() {
        var doc = window.parent.document;
        var scrolled = false;
        var selectors = [
            '[data-testid="stMainBlockContainer"]',
            '[data-testid="stAppViewBlockContainer"]',
            '[data-testid="stAppViewContainer"]',
            'section.main',
            '.main'
        ];
        for (var i = 0; i < selectors.length; i++) {
            var el = doc.querySelector(selectors[i]);
            if (el && el.scrollHeight > el.clientHeight) {
                el.scrollTop = el.scrollHeight;
                scrolled = true;
            }
        }
        if (!scrolled) {
            doc.documentElement.scrollTop = doc.documentElement.scrollHeight;
        }
    }
    scrollToBottom();
    setTimeout(scrollToBottom, 150);
    setTimeout(scrollToBottom, 500);
})();
</script>
"""
