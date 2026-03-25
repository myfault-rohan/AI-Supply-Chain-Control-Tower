import streamlit as st

TRANSLATIONS = {
    "en": {
        "title": "AI Supply Chain Control Tower",
        "overview": "Commander Overview",
        "critical_products": "Critical Products",
        "warnings": "Warnings",
        "health_score": "Health Score",
        "reorder_now": "Reorder Now",
        "supplier_performance": "Supplier Performance",
        "run_simulation": "Run Crisis Simulation",
        "ask_ai": "Ask AI Advisor",
        "upload_data": "Upload Data",
        "run_analysis": "Run Analysis",
        "no_data": "No Data",
        "nav_operations": "Operations",
        "nav_overview": "Overview",
        "nav_analytics": "Analytics",
        "nav_risk_map": "Risk Map",
        "nav_data_lab": "Data Lab",
        "nav_data_mgmt": "Data Management",
        "nav_sim_lab": "Simulation Lab",
        "nav_ai": "AI Advisor",
        "nav_system": "System",
        "nav_admin": "Admin",
        "log_in": "Log In",
        "username": "Username",
        "password": "Password",
        "lang_toggle": "🇯🇵 日本語 / 🇬🇧 English",
        "logout": "Log Out"
    },
    "ja": {
        "title": "AIサプライチェーン コントロールタワー",
        "overview": "司令官概要",
        "critical_products": "重要製品",
        "warnings": "警告",
        "health_score": "ヘルススコア",
        "reorder_now": "今すぐ再注文",
        "supplier_performance": "サプライヤーパフォーマンス",
        "run_simulation": "危機シミュレーション実行",
        "ask_ai": "AIアドバイザーに質問",
        "upload_data": "データアップロード",
        "run_analysis": "分析実行",
        "no_data": "データなし",
        "nav_operations": "運用",
        "nav_overview": "概要",
        "nav_analytics": "分析",
        "nav_risk_map": "リスクマップ",
        "nav_data_lab": "データラボ",
        "nav_data_mgmt": "データ管理",
        "nav_sim_lab": "シミュレーションラボ",
        "nav_ai": "AIアドバイザー",
        "nav_system": "システム",
        "nav_admin": "管理者",
        "log_in": "ログイン",
        "username": "ユーザー名",
        "password": "パスワード",
        "lang_toggle": "🇬🇧 English / 🇯🇵 日本語",
        "logout": "ログアウト"
    }
}

def t(key):
    lang = st.session_state.get("lang", "en")
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

def toggle_language():
    current = st.session_state.get("lang", "en")
    st.session_state["lang"] = "ja" if current == "en" else "en"
