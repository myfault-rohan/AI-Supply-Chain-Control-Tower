import streamlit as st
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from alerts.ai_supply_chain_advisor import ask_supply_chain_question
from dashboard.i18n import t

st.title(f"{t('ask_ai')} 🤖")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = [{"role": "assistant", "content": "Hello! I'm your AI Supply Chain Analyst. How can I help you today?"}]

for msg in st.session_state["chat_history"]:
    st.chat_message(msg["role"]).write(msg["content"])

def submit_question(q):
    st.session_state["chat_history"].append({"role": "user", "content": q})
    with st.spinner("AI is analyzing the supply chain data..."):
        ans = ask_supply_chain_question(q)
    st.session_state["chat_history"].append({"role": "assistant", "content": ans})
    st.rerun()

st.markdown("### Suggested Questions")
c1, c2, c3 = st.columns(3)
if c1.button("Which products are at critical stockout risk?"):
    submit_question("Which products are at critical stockout risk?")
if c2.button("Which suppliers are underperforming?"):
    submit_question("Which suppliers are underperforming?")
if c3.button("What is the total financial risk exposure?"):
    submit_question("What is the total financial risk exposure?")

user_q = st.chat_input("Ask a supply chain question...")
if user_q:
    submit_question(user_q)
