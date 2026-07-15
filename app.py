"""
app.py
------
Streamlit chat interface for the TVM Solver.
Runs fully offline — no API key required.
"""

import streamlit as st
from agent import run_agent

st.set_page_config(page_title="TVM Solver", page_icon="📐", layout="centered")
st.title("📐 TVM Solver")
st.caption("Covers PV, FV, rate, n, rate conversions, force of interest, bond pricing, loan repayments, and yield of return.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

with st.sidebar:
    st.header("💡 Try these")
    examples = [
        "What is the PV of $10,000 in 5 years at 8%?",
        "What is the FV of $2,000 invested today for 10 years at 6%?",
        "What annual rate turns $1,000 into $1,500 in 4 years?",
        "How many years to grow $1,000 to $2,000 at 7%?",
        "Convert 12% compounded monthly to an effective annual rate.",
        "What is the force of interest if i = 5%?",
        "Price a 15-year bond, face 100000, coupon 9% semi-annual, yield 10% semi-annual.",
        "Monthly repayment on a loan of 80000 at 12% monthly over 5 years.",
        "Outstanding balance after the 24th payment on a loan of 80000 at 12% monthly over 5 years.",
        "Total interest paid during first 24 payments on loan of 80000 at 12% monthly over 5 years.",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.pending_input = ex

default_input = st.session_state.pop("pending_input", "")
user_input = st.chat_input("Ask a TVM, bond, or loan question...") or default_input

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

            # Financial interpretation
            if r.get("interpretation"):
                lines.append("")
                lines.append(f"**📊 Interpretation:** {r['interpretation']}")

            # Inputs
            if r.get("inputs"):
                lines.append("")
                lines.append("**Inputs & Intermediate Values:**")
                for k, v in r["inputs"].items():
                    lines.append(f"- {k} = {v}")

            # EAR for rate conversions
            if fn == "convert_rate" and "ear" in r:
                lines.append("")
                lines.append(f"**Effective Annual Rate (EAR):** `{round(r['ear']*100, 4)}%`")

            # Equation of value detail
            if fn == "equation_of_value":
                lines.append("")
                if r.get("balanced"):
                    lines.append("✅ **The equation of value balances.**")
                for cf in r.get("detail", []):
                    lines.append(f"- CF {cf['amount']} at t={cf['time']} → factor {cf['factor']} → value {cf['value_at_valuation']}")

            reply = "\n".join(lines)
            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

st.divider()
st.caption("Sign convention: inflows = positive, outflows = negative. Rates are periodic unless stated otherwise.")
