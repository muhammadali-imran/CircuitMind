"""
CircuitMind - Streamlit Web UI
Monolithic Architecture (Direct Python Imports)

Single unified chat interface backed by the LangChain gateway agent,
replacing the old Generate / Explain / Diagnose / Export / Chatbot tabs —
the agent now routes a message to whichever of those actions fits.
"""

import os
import sys
import json
import uuid
import base64
from dotenv import load_dotenv
import streamlit as st

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.executor import conversational_agent
from agent.session_store import get_circuit, clear_session
from export.export_module import export_module

load_dotenv()

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="CircuitMind", layout="wide", page_icon="⚡")

st.title("⚡ CircuitMind")
st.subheader("AI-Powered Electronics Assistant")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hi! Describe a circuit you'd like me to generate, then ask me "
                "to explain, diagnose, or export it — or ask a digital-logic "
                "hint question. 😊"
            ),
        }
    ]

col_chat, col_circuit = st.columns([2, 1])

# ── CHAT COLUMN ──────────────────────────────────────────────────────────────
with col_chat:
    if st.button("🗑️ Reset session"):
        clear_session(st.session_state.session_id)
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = [
            {"role": "assistant", "content": "Session reset. What circuit would you like?"}
        ]
        st.rerun()

    chat_container = st.container(height=500)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    user_input = st.chat_input("Ask CircuitMind...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        try:
            result = conversational_agent.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": st.session_state.session_id}},
            )
            response = result["output"]
        except Exception as e:
            response = f"Sorry, something went wrong: {e}"

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

# ── CURRENT CIRCUIT COLUMN ────────────────────────────────────────────────────
with col_circuit:
    st.markdown("### Current Circuit")
    circuit = get_circuit(st.session_state.session_id)

    if not circuit:
        st.caption("No circuit generated yet this session.")
    else:
        st.markdown(f"**{circuit.get('circuit_name', 'Untitled')}**")

        st.markdown("**Components:**")
        for c in circuit.get("components", []):
            st.markdown(f"- {c}")

        st.markdown("**Connections:**")
        for c in circuit.get("connections", []):
            st.markdown(f"- {c}")

        svg_res = export_module(json.dumps(circuit), export_format="svg")
        if svg_res.get("status") == "success" and "svg_markup" in svg_res:
            b64 = base64.b64encode(svg_res["svg_markup"].encode()).decode()
            st.markdown(
                f'<img src="data:image/svg+xml;base64,{b64}" '
                f'style="max-width:100%;width:100%;background:white;padding:16px;border-radius:8px;">',
                unsafe_allow_html=True,
            )

        with st.expander("Circuit JSON"):
            st.code(json.dumps(circuit, indent=2), language="json")

        fmt = st.radio("Export format", ["spice", "svg", "gate_json"], horizontal=True, key="export_fmt")
        export_res = export_module(json.dumps(circuit), export_format=fmt)

        if export_res.get("status") == "success":
            if fmt == "spice":
                st.download_button(
                    "⬇️ Download SPICE",
                    export_res["spice_netlist"],
                    file_name="circuit.sp",
                    mime="text/plain",
                )
            elif fmt == "svg":
                st.download_button(
                    "⬇️ Download SVG",
                    export_res["svg_markup"],
                    file_name=f"{circuit.get('circuit_name', 'circuit').replace(' ', '_')}.svg",
                    mime="image/svg+xml",
                )
            elif fmt == "gate_json":
                st.download_button(
                    "⬇️ Download Gate JSON",
                    json.dumps(export_res["gate_json"], indent=2),
                    file_name="circuit_gate.json",
                    mime="application/json",
                )
        else:
            st.caption(f"Export unavailable: {export_res.get('message', 'unknown error')}")

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ CircuitMind")
    st.markdown("AI-powered electronics assistant")
    st.caption("Built by Team Delta")

st.caption("CircuitMind")
