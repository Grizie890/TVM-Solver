"""
agent.py
--------
Orchestrator: parses natural-language questions using keyword matching.
No API needed — all math is deterministic Python.
"""

import re
from tvm_tools import (
    solve_pv, solve_fv, solve_rate, solve_n,
    convert_rate, force_of_interest, rate_from_force,
    equation_of_value, bond_price,
    loan_repayment, outstanding_balance, total_interest_paid,
    effective_yield,
)


def extract_numbers(text: str) -> list:
    results = []
    for x in re.findall(r"\b[\d,]+\.?\d*\b", text):
        try:
            results.append(float(x.replace(",", "")))
        except ValueError:
            continue
    return results


def extract_all_rates(text: str) -> list:
    return [float(m) / 100 for m in re.findall(r"([\d.]+)\s*%", text)]


def extract_rate(text: str) -> float | None:
    rates = extract_all_rates(text)
    return rates[0] if rates else None


def run_agent(user_question: str, api_key: str = "") -> dict:
    try:
        q = user_question.lower()
        nums = extract_numbers(q)
        rates = extract_all_rates(user_question)
        rate = rates[0] if rates else None

        # ── Effective annual yield / IRR ──────────────────────────────────────
        if any(w in q for w in ["rate of return", "effective annual yield", "irr", "yield over"]):
            # Hardcoded example: bond sold after 10th coupon, reinvestment at 7%
            # General: needs structured input — guide user
            return {
                "success": False,
                "error": (
                    "Yield / IRR calculation requires structured cashflow input. "
                    "Please provide your cashflows like this:\n\n"
                    "'Calculate yield: initial outflow 92313, "
                    "cashflows [4500,4500,4500,4500,4500,4500,4500,4500,4500,4500,95000], "
                    "times [0.5,1,1.5,2,2.5,3,3.5,4,4.5,5,5]'"
                ),
            }

        # ── IRR structured input ──────────────────────────────────────────────
        if "calculate yield" in q or "irr:" in q:
            outflow_match = re.search(r"outflow\s*([\d,]+\.?\d*)", q)
            cf_match = re.search(r"cashflows?\s*\[([^\]]+)\]", q)
            t_match = re.search(r"times?\s*\[([^\]]+)\]", q)
            if outflow_match and cf_match and t_match:
                outflow = float(outflow_match.group(1).replace(",", ""))
                cfs = [float(x.strip()) for x in cf_match.group(1).split(",")]
                times = [float(x.strip()) for x in t_match.group(1).split(",")]
                result = effective_yield(outflow, cfs, times)
                return {"success": True, "explanation": "Solving for effective annual yield (IRR).", "function_called": "effective_yield", "result": result}

        # ── Total interest paid ───────────────────────────────────────────────
        if any(w in q for w in ["total interest", "interest paid", "interest during"]):
            k_match = re.search(r"(\d+)\s*(payments?|months?|installments?)", q)
            year_match = re.search(r"(\d+)\s*year", q)
            large = [n for n in nums if n >= 1000]
            principal = large[0] if large else None
            k = float(k_match.group(1)) if k_match else (float(year_match.group(1)) * 12 if year_match else None)
            loan_years_match = re.search(r"over\s*(\d+)\s*year", q)
            loan_years = float(loan_years_match.group(1)) if loan_years_match else 5
            comp_freq = 12 if "monthly" in q else (2 if "semi" in q else (4 if "quarter" in q else 12))
            if principal and rate and k:
                result = total_interest_paid(principal, rate, comp_freq, loan_years, int(k))
                return {
                    "success": True,
                    "explanation": f"Total interest paid during first {int(k)} payments on a loan of {principal:,.0f} at {rate*100}%.",
                    "function_called": "total_interest_paid",
                    "result": result,
                }

        # ── Outstanding balance ───────────────────────────────────────────────
        if any(w in q for w in ["outstanding", "balance after", "remaining balance", "loan balance"]):
            k_match = re.search(r"after\s+(?:the\s+)?(\d+)(?:st|nd|rd|th)?\s+payment", q)
            if not k_match:
                k_match = re.search(r"(\d+)(?:st|nd|rd|th)?\s+payment", q)
            loan_years_match = re.search(r"over\s*(\d+)\s*year", q)
            loan_years = float(loan_years_match.group(1)) if loan_years_match else 5
            large = [n for n in nums if n >= 1000]
            principal = large[0] if large else None
            k = int(k_match.group(1)) if k_match else None
            comp_freq = 12 if "monthly" in q else (2 if "semi" in q else (4 if "quarter" in q else 12))
            if principal and rate and k:
                result = outstanding_balance(principal, rate, comp_freq, loan_years, k)
                return {
                    "success": True,
                    "explanation": f"Outstanding balance after payment {k} on a loan of {principal:,.0f} at {rate*100}%.",
                    "function_called": "outstanding_balance",
                    "result": result,
                }

        # ── Loan repayment ────────────────────────────────────────────────────
        if any(w in q for w in ["loan", "repayment", "installment", "monthly payment", "borrow"]):
            large = [n for n in nums if n >= 1000]
            principal = large[0] if large else None
            year_match = re.search(r"(\d+)\s*year", q)
            loan_years = float(year_match.group(1)) if year_match else 5
            comp_freq = 12 if "monthly" in q else (2 if "semi" in q else (4 if "quarter" in q else 1))
            if principal and rate:
                result = loan_repayment(principal, rate, comp_freq, loan_years)
                return {
                    "success": True,
                    "explanation": f"Computing monthly repayment on a loan of {principal:,.0f} at {rate*100}% over {loan_years} years.",
                    "function_called": "loan_repayment",
                    "result": result,
                }

        # ── Bond pricing ──────────────────────────────────────────────────────
        if any(w in q for w in ["bond", "coupon", "redemption", "redeemable", "purchase price"]):
            year_match = re.search(r"(\d+)[- ]year", q)
            years = float(year_match.group(1)) if year_match else None
            if not years:
                n_match = re.search(r"(\d+)\s*years", q)
                years = float(n_match.group(1)) if n_match else None
            large = [n for n in nums if n >= 1000]
            face = large[0] if large else None
            coupon_rate = rates[0] if len(rates) >= 1 else None
            yield_rate  = rates[1] if len(rates) >= 2 else None
            coupon_freq = 1
            if any(w in q for w in ["semi-annual", "semiannual", "semi annual", "every six", "twice", "payable semi"]):
                coupon_freq = 2
            elif "quarterly" in q:
                coupon_freq = 4
            elif "monthly" in q:
                coupon_freq = 12
            yield_freq = coupon_freq
            if "convertible semi" in q or "convertible half" in q:
                yield_freq = 2
            elif "convertible quarterly" in q:
                yield_freq = 4
            elif "convertible monthly" in q:
                yield_freq = 12
            if face and coupon_rate and yield_rate and years:
                result = bond_price(face=face, coupon_rate=coupon_rate, coupon_freq=coupon_freq,
                                    years=years, yield_rate=yield_rate, yield_freq=yield_freq)
                return {
                    "success": True,
                    "explanation": (f"Pricing a {years}-year bond: face {face:,.0f}, "
                                    f"coupon {coupon_rate*100}% p.a. paid {coupon_freq}× per year, "
                                    f"yield {yield_rate*100}% p.a. compounded {yield_freq}× per year."),
                    "function_called": "bond_price",
                    "result": result,
                }
            else:
                return {"success": False, "error": (
                    "Bond question detected but missing details. Include: face value, coupon rate, yield rate, term.\n"
                    "Example: 'Price a 15-year bond, face 100000, coupon 9% semi-annual, yield 10% semi-annual.'")}

        # ── Force of interest ─────────────────────────────────────────────────
        if "force of interest" in q and "from" not in q and "convert" not in q:
            if rate:
                result = force_of_interest(rate)
                return {"success": True, "explanation": f"Computing force of interest for i = {rate}", "function_called": "force_of_interest", "result": result}
            if nums:
                i = nums[0] if nums[0] < 1 else nums[0] / 100
                result = force_of_interest(i)
                return {"success": True, "explanation": f"Computing force of interest for i = {i}", "function_called": "force_of_interest", "result": result}

        # ── Rate conversion ───────────────────────────────────────────────────
        if any(w in q for w in ["convert", "equivalent", "compounded", "nominal", "effective annual"]):
            if rate is None and nums:
                rate = nums[0] if nums[0] < 1 else nums[0] / 100
            from_comp, to_comp = 1, 1
            if "monthly" in q and ("to" in q or "annual" in q or "effective" in q):
                from_comp, to_comp = 12, 1
            elif "quarterly" in q and ("to" in q or "annual" in q):
                from_comp, to_comp = 4, 1
            elif "semi" in q and ("to" in q or "annual" in q):
                from_comp, to_comp = 2, 1
            elif "annual" in q and "monthly" in q:
                from_comp, to_comp = 1, 12
            elif "continuous" in q:
                from_comp, to_comp = 0, 1
            if rate:
                result = convert_rate(rate, from_comp, to_comp)
                return {"success": True, "explanation": f"Converting {rate*100:.4f}% from compounding {from_comp} to {to_comp}", "function_called": "convert_rate", "result": result}

        # ── Solve for n ───────────────────────────────────────────────────────
        if any(w in q for w in ["how many years", "how long", "number of years", "number of periods", "solve for n"]):
            if rate and len(nums) >= 2:
                result = solve_n(nums[0], nums[1], rate)
                return {"success": True, "explanation": f"Solving for n: PV={nums[0]}, FV={nums[1]}, i={rate}", "function_called": "solve_n", "result": result}

        # ── Solve for rate ────────────────────────────────────────────────────
        if any(w in q for w in ["what rate", "what interest", "solve for i", "find the rate", "annual rate"]):
            if len(nums) >= 3:
                result = solve_rate(nums[0], nums[1], nums[2])
                return {"success": True, "explanation": f"Solving for i: PV={nums[0]}, FV={nums[1]}, n={nums[2]}", "function_called": "solve_rate", "result": result}
            elif len(nums) >= 2:
                n_match = re.search(r"(\d+)\s*(years?|periods?)", q)
                if n_match:
                    n = float(n_match.group(1))
                    result = solve_rate(nums[0], nums[1], n)
                    return {"success": True, "explanation": f"Solving for i: PV={nums[0]}, FV={nums[1]}, n={n}", "function_called": "solve_rate", "result": result}

        # ── Future Value ──────────────────────────────────────────────────────
        if any(w in q for w in ["future value", "fv", "accumulated", "grow", "worth in"]):
            n_match = re.search(r"(\d+)\s*(years?|periods?)", q)
            n = float(n_match.group(1)) if n_match else (nums[-1] if nums else 0)
            if rate and nums:
                result = solve_fv(pv=nums[0], pmt=0, i=rate, n=n)
                return {"success": True, "explanation": f"Computing FV: PV={nums[0]}, i={rate}, n={n}", "function_called": "solve_fv", "result": result}

        # ── Present Value (default) ───────────────────────────────────────────
        n_match = re.search(r"(\d+)\s*(years?|periods?)", q)
        n = float(n_match.group(1)) if n_match else None
        if rate and nums and n:
            fv = nums[0]
            result = solve_pv(fv=fv, pmt=0, i=rate, n=n)
            return {
                "success": True,
                "explanation": f"Discounting {fv:,.2f} back {n} years at {rate*100}%",
                "function_called": "solve_pv",
                "result": result,
            }

        # ── Fallback ──────────────────────────────────────────────────────────
        return {
            "success": False,
            "error": (
                "I couldn't extract enough information. Try one of these:\n"
                "- PV: 'What is the PV of $10,000 in 5 years at 8%?'\n"
                "- Bond: 'Price a 15-year bond, face 100000, coupon 9% semi-annual, yield 10% semi-annual.'\n"
                "- Loan: 'Monthly repayment on a loan of 80000 at 12% monthly over 5 years.'\n"
                "- Balance: 'Outstanding balance after the 24th payment on a loan of 80000 at 12% monthly over 5 years.'\n"
                "- Interest: 'Total interest paid during first 24 payments on loan of 80000 at 12% monthly over 5 years.'"
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Something went wrong: {str(e)}. Try rephrasing your question.",
        }
