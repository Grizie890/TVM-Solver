"""
tvm_tools.py
------------
Pure deterministic TVM calculations — no AI, no side effects.
Sign convention: cash inflows are POSITIVE, outflows are NEGATIVE.
Covers: PV, FV, rate, n, rate conversions, force of interest,
        equation of value, bond pricing, loan amortization, yield of return.
"""

import math


# ── 1. PRESENT VALUE ──────────────────────────────────────────────────────────

def solve_pv(fv: float = 0, pmt: float = 0, i: float = 0, n: float = 0) -> dict:
    if i == 0:
        pv = fv + pmt * n
    else:
        pv_lump = fv / (1 + i) ** n
        pv_annuity = pmt * (1 - (1 + i) ** -n) / i if pmt != 0 else 0
        pv = pv_lump + pv_annuity
    return {
        "result": round(pv, 6),
        "label": "PV",
        "formula": "PV = FV/(1+i)^n + PMT×[1-(1+i)^-n]/i",
        "inputs": {"FV": fv, "PMT": pmt, "i": i, "n": n},
    }


# ── 2. FUTURE VALUE ───────────────────────────────────────────────────────────

def solve_fv(pv: float = 0, pmt: float = 0, i: float = 0, n: float = 0) -> dict:
    if i == 0:
        fv = pv + pmt * n
    else:
        fv_lump = pv * (1 + i) ** n
        fv_annuity = pmt * ((1 + i) ** n - 1) / i if pmt != 0 else 0
        fv = fv_lump + fv_annuity
    return {
        "result": round(fv, 6),
        "label": "FV",
        "formula": "FV = PV×(1+i)^n + PMT×[(1+i)^n - 1]/i",
        "inputs": {"PV": pv, "PMT": pmt, "i": i, "n": n},
    }


# ── 3. INTEREST RATE ──────────────────────────────────────────────────────────

def solve_rate(pv: float, fv: float, n: float) -> dict:
    if pv == 0:
        raise ValueError("PV cannot be zero when solving for rate.")
    if n <= 0:
        raise ValueError("n must be positive.")
    ratio = fv / pv
    if ratio <= 0:
        raise ValueError("FV/PV must be positive to solve for a real rate.")
    i = ratio ** (1 / n) - 1
    return {
        "result": round(i, 8),
        "label": "i (periodic rate)",
        "formula": "i = (FV/PV)^(1/n) - 1",
        "inputs": {"PV": pv, "FV": fv, "n": n},
    }


# ── 4. NUMBER OF PERIODS ──────────────────────────────────────────────────────

def solve_n(pv: float, fv: float, i: float) -> dict:
    if i <= 0:
        raise ValueError("i must be positive to solve for n.")
    if pv == 0 or fv == 0:
        raise ValueError("Neither PV nor FV can be zero.")
    ratio = fv / pv
    if ratio <= 0:
        raise ValueError("FV/PV must be positive to solve for n.")
    n = math.log(ratio) / math.log(1 + i)
    return {
        "result": round(n, 6),
        "label": "n (periods)",
        "formula": "n = ln(FV/PV) / ln(1+i)",
        "inputs": {"PV": pv, "FV": fv, "i": i},
    }


# ── 5. RATE CONVERSIONS ───────────────────────────────────────────────────────

def convert_rate(nominal_rate: float, from_compounding: int, to_compounding: int) -> dict:
    if from_compounding == 0:
        ear = math.exp(nominal_rate) - 1
    else:
        ear = (1 + nominal_rate / from_compounding) ** from_compounding - 1
    if to_compounding == 0:
        result = math.log(1 + ear)
        label = "Force of interest (δ)"
    else:
        result = to_compounding * ((1 + ear) ** (1 / to_compounding) - 1)
        label = f"Nominal rate compounded {to_compounding}×/year"
    return {
        "result": round(result, 8),
        "label": label,
        "ear": round(ear, 8),
        "formula": "EAR = (1 + r/m)^m - 1  →  r_new = m_new×[(1+EAR)^(1/m_new)-1]",
        "inputs": {
            "nominal_rate": nominal_rate,
            "from_compounding": from_compounding,
            "to_compounding": to_compounding,
        },
    }


# ── 6. FORCE OF INTEREST ─────────────────────────────────────────────────────

def force_of_interest(i_effective_annual: float) -> dict:
    if i_effective_annual <= -1:
        raise ValueError("Effective annual rate must be greater than -1.")
    delta = math.log(1 + i_effective_annual)
    return {
        "result": round(delta, 8),
        "label": "Force of interest (δ)",
        "formula": "δ = ln(1 + i)",
        "inputs": {"i_effective_annual": i_effective_annual},
    }


def rate_from_force(delta: float) -> dict:
    i = math.exp(delta) - 1
    return {
        "result": round(i, 8),
        "label": "Effective annual rate (i)",
        "formula": "i = e^δ - 1",
        "inputs": {"delta": delta},
    }


# ── 7. EQUATION OF VALUE ─────────────────────────────────────────────────────

def equation_of_value(cashflows: list, i: float, valuation_time: float = 0) -> dict:
    net = 0.0
    detail = []
    for cf in cashflows:
        amt = cf["amount"]
        t = cf["time"]
        dt = valuation_time - t
        factor = (1 + i) ** dt
        value_at_t0 = amt * factor
        net += value_at_t0
        detail.append({
            "amount": amt,
            "time": t,
            "factor": round(factor, 6),
            "value_at_valuation": round(value_at_t0, 6),
        })
    return {
        "result": round(net, 6),
        "label": f"Net value at t={valuation_time}",
        "formula": "Σ CF_t × (1+i)^(T-t)",
        "balanced": abs(net) < 1e-4,
        "detail": detail,
        "inputs": {"i": i, "valuation_time": valuation_time},
    }


# ── 8. BOND PRICING ───────────────────────────────────────────────────────────

def bond_price(
    face: float,
    coupon_rate: float,
    coupon_freq: int,
    years: float,
    yield_rate: float,
    yield_freq: int,
    redemption: float = None,
) -> dict:
    """
    P = C·v^n + Fr·a_{n|i}
    C = redemption, F = face, r = coupon rate per period,
    i = yield per period, n = total coupon periods
    """
    if redemption is None:
        redemption = face

    i = yield_rate / yield_freq
    n = int(years * coupon_freq)
    r = coupon_rate / coupon_freq
    coupon = face * r

    v = 1 / (1 + i)
    v_n = v ** n
    a_n = (1 - v_n) / i

    price = redemption * v_n + coupon * a_n

    return {
        "result": round(price, 4),
        "label": "Bond Price (P)",
        "formula": "P = C·v^n + Fr·a_{n|i}",
        "interpretation": (
            f"The bond should be purchased for {round(price, 2):,.2f}. "
            f"Since price {'<' if price < face else '>'} face value, "
            f"the bond trades at a {'discount' if price < face else 'premium'} "
            f"because the coupon rate is {'below' if price < face else 'above'} the yield."
        ),
        "inputs": {
            "Face value (F)": face,
            "Redemption value (C)": redemption,
            "Coupon rate (nominal annual)": f"{coupon_rate*100}%",
            "Coupon frequency": f"{coupon_freq}× per year",
            "Yield rate (nominal annual)": f"{yield_rate*100}%",
            "Yield frequency": f"{yield_freq}× per year",
            "Term (years)": years,
            "Periods (n)": n,
            "Yield per period (i)": round(i, 6),
            "Coupon per period (Fr)": round(coupon, 4),
            "v^n": round(v_n, 6),
            "Annuity factor a_{n|i}": round(a_n, 6),
        },
    }


# ── 9. LOAN MONTHLY REPAYMENT ─────────────────────────────────────────────────

def loan_repayment(
    principal: float,
    annual_rate: float,
    compounding_freq: int,
    years: float,
    payment_freq: int = 12,
) -> dict:
    """
    Monthly repayment on a loan using the annuity formula.
    PMT = PV × i / [1 - (1+i)^-n]
    Converts the nominal annual rate to the payment period rate first.
    """
    # Convert nominal rate to effective per payment period
    ear = (1 + annual_rate / compounding_freq) ** compounding_freq - 1
    i_per_period = (1 + ear) ** (1 / payment_freq) - 1
    n = int(years * payment_freq)

    pmt = principal * i_per_period / (1 - (1 + i_per_period) ** -n)

    return {
        "result": round(pmt, 4),
        "label": "Monthly Repayment (PMT)",
        "formula": "PMT = PV × i / [1 - (1+i)^-n]",
        "interpretation": (
            f"The borrower pays {round(pmt, 2):,.2f} every month for {n} months. "
            f"Total repaid = {round(pmt*n, 2):,.2f}. "
            f"Total interest = {round(pmt*n - principal, 2):,.2f}."
        ),
        "inputs": {
            "Principal (PV)": principal,
            "Nominal annual rate": f"{annual_rate*100}%",
            "Compounding frequency": f"{compounding_freq}× per year",
            "EAR": round(ear, 6),
            "Rate per payment period (i)": round(i_per_period, 8),
            "Number of payments (n)": n,
        },
    }


# ── 10. OUTSTANDING LOAN BALANCE ──────────────────────────────────────────────

def outstanding_balance(
    principal: float,
    annual_rate: float,
    compounding_freq: int,
    years: float,
    after_payment: int,
    payment_freq: int = 12,
) -> dict:
    """
    Outstanding balance immediately after the k-th payment (prospective method).
    Balance = PMT × a_{(n-k)|i}  where a is the annuity-immediate factor.
    """
    ear = (1 + annual_rate / compounding_freq) ** compounding_freq - 1
    i = (1 + ear) ** (1 / payment_freq) - 1
    n = int(years * payment_freq)

    pmt = principal * i / (1 - (1 + i) ** -n)
    remaining = n - after_payment
    balance = pmt * (1 - (1 + i) ** -remaining) / i

    return {
        "result": round(balance, 4),
        "label": f"Outstanding Balance after payment {after_payment}",
        "formula": "Balance = PMT × [1-(1+i)^-(n-k)] / i",
        "interpretation": (
            f"After {after_payment} payments, {remaining} payments remain. "
            f"The outstanding balance is {round(balance, 2):,.2f}."
        ),
        "inputs": {
            "Principal": principal,
            "Monthly rate (i)": round(i, 8),
            "Total payments (n)": n,
            "Payments made (k)": after_payment,
            "Remaining payments": remaining,
            "Monthly payment (PMT)": round(pmt, 4),
        },
    }


# ── 11. TOTAL INTEREST PAID OVER k PAYMENTS ──────────────────────────────────

def total_interest_paid(
    principal: float,
    annual_rate: float,
    compounding_freq: int,
    years: float,
    num_payments: int,
    payment_freq: int = 12,
) -> dict:
    """
    Total interest paid during the first k payments.
    Interest = k × PMT - (Principal - Outstanding Balance after k payments)
    """
    ear = (1 + annual_rate / compounding_freq) ** compounding_freq - 1
    i = (1 + ear) ** (1 / payment_freq) - 1
    n = int(years * payment_freq)

    pmt = principal * i / (1 - (1 + i) ** -n)
    remaining = n - num_payments
    balance_after_k = pmt * (1 - (1 + i) ** -remaining) / i

    principal_repaid = principal - balance_after_k
    total_paid = pmt * num_payments
    interest_paid = total_paid - principal_repaid

    return {
        "result": round(interest_paid, 4),
        "label": f"Total Interest Paid (first {num_payments} payments)",
        "formula": "Interest = k×PMT − (Principal − Balance_k)",
        "interpretation": (
            f"Over the first {num_payments} payments: "
            f"total paid = {round(total_paid, 2):,.2f}, "
            f"principal repaid = {round(principal_repaid, 2):,.2f}, "
            f"interest paid = {round(interest_paid, 2):,.2f}."
        ),
        "inputs": {
            "Principal": principal,
            "Monthly rate (i)": round(i, 8),
            "Monthly payment (PMT)": round(pmt, 4),
            "Payments made (k)": num_payments,
            "Balance after k payments": round(balance_after_k, 4),
            "Principal repaid": round(principal_repaid, 4),
        },
    }


# ── 12. EFFECTIVE ANNUAL YIELD (IRR-based) ────────────────────────────────────

def effective_yield(
    initial_outflow: float,
    cashflows: list,
    times_years: list,
    guess: float = 0.05,
) -> dict:
    """
    Solve for the effective annual rate of return (IRR) using Newton-Raphson.
    cashflows and times_years must be the same length.
    initial_outflow: amount invested at time 0 (positive number).
    NPV = -outflow + Σ CF_t / (1+i)^t = 0  → solve for i.
    """
    i = guess
    for _ in range(1000):
        npv = -initial_outflow
        dnpv = 0.0
        for cf, t in zip(cashflows, times_years):
            npv  += cf / (1 + i) ** t
            dnpv -= t * cf / (1 + i) ** (t + 1)
        if abs(npv) < 1e-8:
            break
        if dnpv == 0:
            break
        i -= npv / dnpv

    return {
        "result": round(i, 8),
        "label": "Effective Annual Yield (IRR)",
        "formula": "Solve: −P + Σ CF_t·v^t = 0  for v = 1/(1+i)",
        "interpretation": (
            f"The investor's effective annual rate of return is {round(i*100, 4)}%. "
            "This is the rate that equates the present value of all inflows to the initial investment."
        ),
        "inputs": {
            "Initial outflow": initial_outflow,
            "Number of cashflows": len(cashflows),
            "Cashflows": cashflows,
            "Times (years)": times_years,
        },
    }
