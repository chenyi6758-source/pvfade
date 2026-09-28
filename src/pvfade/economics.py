"""Techno-economic metrics for PV-storage systems.

All multi-year metrics discount future cash flows / energy at ``discount_rate``.
Degradation enters through the annual energy and cash-flow series produced by
:func:`pvfade.dispatch.simulate_lifetime`, so economics always reflect a
fading battery rather than a nameplate-constant one.
"""

from __future__ import annotations

import numpy as np


def npv(
    capex: float,
    annual_cashflows: list[float] | np.ndarray,
    discount_rate: float,
) -> float:
    """Net present value: ``-capex + sum(cf_t / (1 + r)^t)``."""
    if discount_rate <= -1:
        raise ValueError("discount_rate must be > -1")
    cfs = np.asarray(annual_cashflows, dtype=float)
    years = np.arange(1, len(cfs) + 1)
    return float(-capex + np.sum(cfs / (1.0 + discount_rate) ** years))


def lcos(
    capex_battery: float,
    annual_discharged_kwh: list[float] | np.ndarray,
    opex_per_year: float = 0.0,
    discount_rate: float = 0.05,
) -> float:
    """Levelized cost of storage (currency per kWh discharged)."""
    discharged = np.asarray(annual_discharged_kwh, dtype=float)
    if np.any(discharged < 0):
        raise ValueError("discharged energy must be non-negative")
    years = np.arange(1, len(discharged) + 1)
    disc = (1.0 + discount_rate) ** years
    total_cost = capex_battery + float(np.sum(opex_per_year / disc))
    total_energy = float(np.sum(discharged / disc))
    if total_energy <= 0:
        raise ValueError("no discharged energy: LCOS is undefined")
    return total_cost / total_energy


def simple_payback(
    capex: float,
    annual_cashflows: list[float] | np.ndarray,
) -> float | None:
    """First year in which cumulative undiscounted cash flow covers capex.

    Returns ``None`` if payback never happens within the given horizon.
    Fractional years are interpolated linearly within the payback year.
    """
    cumulative = 0.0
    for year, cf in enumerate(annual_cashflows, start=1):
        prev = cumulative
        cumulative += float(cf)
        if cumulative >= capex:
            if cf <= 0:
                return float(year)
            frac = (capex - prev) / cf
            return (year - 1) + frac
    return None
