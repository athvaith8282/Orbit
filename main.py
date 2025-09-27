from dotenv import load_dotenv
from rich.panel import Panel
from rich.console import Console
import streamlit as st

from planner import PlannerAgent
import config as cfg

st.title("🚀Orbit - Research Agent")

st.set_page_config(page_title="🚀Orbit")

console = Console()

load_dotenv()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "ai",
            "content": "Hello !! How can I help You Today!!"
        }
    ]

if "to_do" not in st.session_state:
    st.session_state.to_do_list = []


if "planner" not in st.session_state:
    st.session_state.planner = PlannerAgent(
        model="gemini-2.5-flash",
        system_prompt=cfg.PLANNER_AGENT_PROMPT
    )

if "files" not in st.session_state:
    st.session_state.files = {}


for msg in st.session_state.messages:

    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "ai":
        st.chat_message("assistant").write(msg["content"])

if prompt := st.chat_input():
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt
    })
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        
        response = st.session_state.planner.invoke(
            prompt, st.container()
        )
        st.write(response.strip())
        st.session_state.messages.append({
            "role": "ai",
            "content": response 
        })