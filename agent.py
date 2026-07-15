"""
agent.py
--------
Orchestrator: parses the user's natural-language question using
keyword matching and extracts TVM variables — no API needed.
Calls the matching deterministic function from tvm_tools.py.
"""

import re
from tvm_tools import (
    solve_pv, solve_fv, solve_rate, solve_n,
    convert_rate, force_of_interest, rate_from_force, equation_of_value,
)


def extract_numbers(text: str) -> list:
    """Pull all plain numbers out of a string, safely."""
    results = []
    for x in re.findall(r"\b[\d,]+\.?\d*\b", text):
        try:
            results.append(float(x.replace(",", "")))
        except ValueError:
            continue
    return results


def extract_rate(text: str) -> float | None:
    """Find a percentage in text and return as decimal."""
    match = re.search(r"([\d.]+)\s*%", text)
    if match:
        try:
            return float(match.group(1)) / 100
        except ValueError:
            return None
    return None


def run_agent(user_question: str, api_key: str = "") -> dict:
    """
    Parse the question, pick the right tool, run the math, return result.
    api_key is accepted for compatibility but not used.
    """
    try:
        q = user_question.lower()
        nums = extract_numbers(q)
        rate = extract_rate(user_question)

        # ── Force of interest ────────────────────────────────────────────────
        if "force of interest" in q and "from" not in q and "convert" not in q:
            if rate:
                result = force_of_interest(rate)
                return {"success": True, "explanation": f"Computing force of interest for i = {rate}", "function_called": "force_of_interest", "result": result}
            if nums:
                i = nums[0] if nums[0] < 1 else nums[0] / 100
                result = force_of_interest(i)
                return {"success": True, "explanation": f"Computing force of interest for i = {i}", "function_called": "force_of_interest", "result": result}

        # ── Rate conversion ──────────────────────────────────────────────────
        if any(w in q for w in ["convert", "equivalent", "compounded", "nominal", "effective annual"]):
            if rate is None and nums:
                rate = nums[0] if nums[0] < 1 else nums[0] / 100

            from_comp = 1
            to_comp = 1

            if "monthly" in q and ("to" in q or "annual" in q or "effective" in q):
                from_comp = 12
                to_comp = 1
            elif "quarterly" in q and ("to" in q or "annual" in q):
                from_comp = 4
                to_comp = 1
            elif "semi" in q and ("to" in q or "annual" in q):
                from_comp = 2
                to_comp = 1
            elif "annual" in q and "monthly" in q:
                from_comp = 1
                to_comp = 12
            elif "continuous" in q:
                from_comp = 0
                to_comp = 1

            if rate:
                result = convert_rate(rate, from_comp, to_comp)
                return {"success": True, "explanation": f"Converting {rate*100:.4f}% from compounding {from_comp} to {to_comp}", "function_called": "convert_rate", "result": result}

        # ── Solve for n ──────────────────────────────────────────────────────
        if any(w in q for w in ["how many years", "how long", "number of years", "number of periods", "solve for n"]):
            if rate and len(nums) >= 2:
                pv = nums[0]   # keep positive — solve_n uses ratio fv/pv
                fv = nums[1]
                result = solve_n(pv, fv, rate)
                return {"success": True, "explanation": f"Solving for n: PV={pv}, FV={fv}, i={rate}", "function_called": "solve_n", "result": result}

        # ── Solve for rate ───────────────────────────────────────────────────
        if any(w in q for w in ["what rate", "what interest", "solve for i", "find the rate", "annual rate"]):
            if len(nums) >= 3:
                pv = nums[0]   # keep positive — solve_rate uses ratio fv/pv
                fv = nums[1]
                n = nums[2]
                result = solve_rate(pv, fv, n)
                return {"success": True, "explanation": f"Solving for i: PV={pv}, FV={fv}, n={n}", "function_called": "solve_rate", "result": result}
            elif len(nums) >= 2:
                n_match = re.search(r"(\d+)\s*(years?|periods?)", q)
                if n_match:
                    n = float(n_match.group(1))
                    pv = nums[0]
                    fv = nums[1]
                    result = solve_rate(pv, fv, n)
                    return {"success": True, "explanation": f"Solving for i: PV={pv}, FV={fv}, n={n}", "function_called": "solve_rate", "result": result}

        # ── Future Value ─────────────────────────────────────────────────────
        if any(w in q for w in ["future value", "fv", "accumulated", "grow", "worth in"]):
            n_match = re.search(r"(\d+)\s*(years?|periods?)", q)
            n = float(n_match.group(1)) if n_match else (nums[-1] if nums else 0)
            if rate and nums:
                pv = nums[0]
                result = solve_fv(pv=pv, pmt=0, i=rate, n=n)
                return {"success": True, "explanation": f"Computing FV: PV={pv}, i={rate}, n={n}", "function_called": "solve_fv", "result": result}

        # ── Present Value (default) ──────────────────────────────────────────
        n_match = re.search(r"(\d+)\s*(years?|periods?)", q)
        n = float(n_match.group(1)) if n_match else None

        if rate and nums and n:
            fv = nums[0]
            result = solve_pv(fv=fv, pmt=0, i=rate, n=n)
            return {
                "success": True,
                "explanation": f"Discounting ${fv:,.2f} back {n} years at {rate*100}%",
                "function_called": "solve_pv",
                "result": result,
            }

        # ── Fallback ─────────────────────────────────────────────────────────
        return {
            "success": False,
            "error": (
                "I couldn't extract enough information from your question. "
                "Please include the known values clearly — for example: "
                "'What is the PV of $10,000 in 5 years at 8%?'"
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": (
                f"Something went wrong parsing your question: {str(e)}. "
                "Try rephrasing — e.g. 'What is the PV of $10,000 in 5 years at 8%?'"
            ),
        }
