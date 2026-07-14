"""
app.py
------
Streamlit chat interface for the TVM Solver.
Runs fully offline — no API key required.
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
st.caption(
    "Time Value of Money calculator — covers PV, FV, i, n, "
    "rate conversions, force of interest, and equation of value."
)

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Render conversation history ───────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Sidebar examples ──────────────────────────────────────────────────────────

with st.sidebar:
    st.header("💡 Try these")
    examples = [
        "What is the PV of $10,000 in 5 years at 8%?",
        "What is the FV of $2,000 invested today for 10 years at 6%?",
        "What annual rate turns $1,000 into $1,500 in 4 years?",
        "How many years to grow $1,000 to $2,000 at 7%?",
        "Convert 12% compounded monthly to an effective annual rate.",
        "What is the force of interest if i = 5%?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.pending_input = ex

# ── Chat input ────────────────────────────────────────────────────────────────

default_input = st.session_state.pop("pending_input", "")
user_input = st.chat_input("Ask a TVM question...") or default_input

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Calculating..."):
            response = run_agent(user_input)

        if not response["success"]:
            reply = f"❌ **Error:** {response['error']}"
            st.markdown(reply)
        else:
            r = response["result"]
            fn = response["function_called"]
            explanation = response["explanation"]

            lines = []
            lines.append(f"**{explanation}**")
            lines.append("")
            lines.append(f"### ✅ {r['label']} = `{r['result']}`")
            lines.append("")
            lines.append(f"**Formula:** `{r['formula']}`")

            if r.get("inputs"):
                lines.append("")
                lines.append("**Inputs used:**")
                for k, v in r["inputs"].items():
                    lines.append(f"- {k} = {v}")

            if fn == "convert_rate" and "ear" in r:
                lines.append("")
                lines.append(f"**Effective Annual Rate (EAR):** `{round(r['ear']*100, 4)}%`")

            if fn == "equation_of_value":
                lines.append("")
                if r.get("balanced"):
                    lines.append("✅ **The equation of value balances.**")
                for cf in r.get("detail", []):
                    lines.append(
                        f"- CF {cf['amount']} at t={cf['time']} "
                        f"→ factor {cf['factor']} "
                        f"→ value at valuation date: {cf['value_at_valuation']}"
                    )

            reply = "\n".join(lines)
            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.caption("Sign convention: inflows = positive, outflows = negative. Rates are periodic unless stated otherwise.")
