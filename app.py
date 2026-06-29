"""
app.py
------
Streamlit chat interface for the TVM Solver.
Reads the Anthropic API key from st.secrets (set this in Streamlit Cloud).
"""

import streamlit as st
from agent import run_agent

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TVM Solver",
    page_icon="📐",
    layout="centered",
)

st.title("📐 TVM Solver")
st.caption("Time Value of Money calculator powered by Claude — covers PV, FV, i, n, rate conversions, force of interest, and equation of value.")

# ── API key ───────────────────────────────────────────────────────────────────

try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    api_key = None

if not api_key:
    st.error("⚠️ API key not found. Add ANTHROPIC_API_KEY to your Streamlit secrets.")
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Render conversation history ───────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Example questions sidebar ─────────────────────────────────────────────────

with st.sidebar:
    st.header("💡 Try these")
    examples = [
        "What is the PV of $10,000 received in 5 years at 8% annual?",
        "Find the FV of $2,000 invested today for 10 years at 6%.",
        "What annual rate turns $1,000 into $1,500 in 4 years?",
        "How many years to double money at 7% annual interest?",
        "Convert 9% compounded monthly to an effective annual rate.",
        "What is the force of interest if i = 5%?",
        "Find the PV of cashflows: +$500 at t=1, +$500 at t=2, -$800 at t=0, at 6%.",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.pending_input = ex

# ── Chat input ────────────────────────────────────────────────────────────────

# Handle sidebar button clicks
default_input = st.session_state.pop("pending_input", "")
user_input = st.chat_input("Ask a TVM question...") or default_input

if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Run agent
    with st.chat_message("assistant"):
        with st.spinner("Calculating..."):
            response = run_agent(user_input, api_key)

        if not response["success"]:
            reply = f"❌ **Error:** {response['error']}"
            st.markdown(reply)
        else:
            r = response["result"]
            fn = response["function_called"]
            explanation = response["explanation"]

            # Build formatted answer
            lines = []
            lines.append(f"**{explanation}**")
            lines.append("")
            lines.append(f"**Answer:** `{r['label']} = {r['result']}`")
            lines.append("")
            lines.append(f"**Formula used:** `{r['formula']}`")

            # Show inputs used
            if r.get("inputs"):
                lines.append("")
                lines.append("**Inputs:**")
                for k, v in r["inputs"].items():
                    lines.append(f"- {k} = {v}")

            # Extra info for rate conversion
            if fn == "convert_rate" and "ear" in r:
                lines.append("")
                lines.append(f"**Effective Annual Rate (EAR):** `{r['ear']}`")

            # Equation of value detail
            if fn == "equation_of_value":
                lines.append("")
                if r.get("balanced"):
                    lines.append("✅ **The equation of value balances (net ≈ 0).**")
                else:
                    lines.append(f"ℹ️ Net value at t={r['inputs']['valuation_time']}: `{r['result']}`")
                lines.append("")
                lines.append("**Cashflow breakdown:**")
                for cf in r.get("detail", []):
                    lines.append(
                        f"- CF of {cf['amount']} at t={cf['time']} "
                        f"→ factor {cf['factor']} "
                        f"→ value {cf['value_at_valuation']}"
                    )

            reply = "\n".join(lines)
            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.caption("Sign convention: inflows = positive, outflows = negative. Rates are periodic unless stated otherwise.")
