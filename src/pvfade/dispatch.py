"""Dispatch strategies and multi-year lifetime simulation.

The core dispatch is an hourly rule-based strategy maximizing
self-consumption: surplus PV charges the battery, deficits discharge it, and
only the remainder is exchanged with the grid. :func:`simulate_lifetime`
closes the loop that most sizing tools leave open: every simulated year the
usable battery capacity is reduced according to the degradation model, so
dispatch, energy throughput, and economics all feel capacity fade.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pvfade.battery import BatterySpec, capacity_retention


def self_consumption_dispatch(
    pv_kw: pd.Series | np.ndarray,
    load_kw: pd.Series | np.ndarray,
    spec: BatterySpec,
    usable_kwh: float | None = None,
    initial_soc_frac: float = 0.5,
    dt_h: float = 1.0,
) -> pd.DataFrame:
    """Hourly self-consumption-maximizing dispatch for one simulation period.

    Parameters
    ----------
    pv_kw, load_kw : array-like
        PV AC power and load power in kW at each step.
    spec : BatterySpec
        Battery nameplate and efficiency parameters.
    usable_kwh : float, optional
        Usable energy capacity; defaults to ``spec.nominal_kwh``. Pass a
        faded value to dispatch a degraded battery.
    initial_soc_frac : float
        Initial state of charge as a fraction of ``usable_kwh``.
    dt_h : float
        Step length in hours.

    Returns
    -------
    pd.DataFrame
        Per-step ``pv_kwh``, ``load_kwh``, ``charge_kwh``, ``discharge_kwh``,
        ``soc_kwh``, ``import_kwh`` and ``export_kwh``.
    """
    pv = np.asarray(pv_kw, dtype=float)
    load = np.asarray(load_kw, dtype=float)
    if pv.shape != load.shape:
        raise ValueError("pv_kw and load_kw must have the same length")
    if np.any(pv < 0) or np.any(load < 0):
        raise ValueError("pv_kw and load_kw must be non-negative")

    usable = spec.nominal_kwh if usable_kwh is None else usable_kwh
    if usable <= 0:
        raise ValueError("usable_kwh must be positive")
    soc_lo = spec.soc_min * usable
    soc_hi = spec.soc_max * usable
    soc = float(np.clip(initial_soc_frac, spec.soc_min, spec.soc_max)) * usable

    n = len(pv)
    charge = np.zeros(n)
    discharge = np.zeros(n)
    imp = np.zeros(n)
    exp = np.zeros(n)
    soc_trace = np.zeros(n)

    for t in range(n):
        net = (pv[t] - load[t]) * dt_h  # kWh surplus (+) or deficit (-)
        if net >= 0:
            # Charge from surplus, limited by power and headroom (AC-side).
            headroom = (soc_hi - soc) / spec.charge_eff
            ch = min(net, spec.charge_kw * dt_h, max(0.0, headroom))
            soc += ch * spec.charge_eff
            charge[t] = ch
            exp[t] = net - ch
        else:
            need = -net
            # Discharge to meet deficit, limited by power and stored energy.
            available = (soc - soc_lo) * spec.discharge_eff
            dch = min(need, spec.discharge_kw * dt_h, max(0.0, available))
            soc -= dch / spec.discharge_eff
            discharge[t] = dch
            imp[t] = need - dch
        soc_trace[t] = soc

    index = pv_kw.index if isinstance(pv_kw, pd.Series) else None
    return pd.DataFrame(
        {
            "pv_kwh": pv * dt_h,
            "load_kwh": load * dt_h,
            "charge_kwh": charge,
            "discharge_kwh": discharge,
            "soc_kwh": soc_trace,
            "import_kwh": imp,
            "export_kwh": exp,
        },
        index=index,
    )


def simulate_lifetime(
    pv_kw: pd.Series | np.ndarray,
    load_kw: pd.Series | np.ndarray,
    spec: BatterySpec,
    max_years: int = 25,
    initial_soc_frac: float = 0.5,
    dt_h: float = 1.0,
) -> pd.DataFrame:
    """Simulate year-by-year operation with degradation feedback.

    Each year the battery is dispatched with its faded usable capacity
    (``nominal_kwh * retention``). Throughput accumulates into equivalent
    full cycles, which together with calendar time drive the next year's
    retention via :func:`pvfade.battery.capacity_retention`. The simulation
    stops at ``max_years`` or when retention falls below ``spec.eol_retention``.

    Returns
    -------
    pd.DataFrame
        One row per simulated year with energy flows, ``retention``,
        ``equivalent_full_cycles`` and ``eol`` flag.
    """
    if max_years < 1:
        raise ValueError("max_years must be >= 1")

    efc = 0.0
    rows: list[dict] = []
    for year in range(1, max_years + 1):
        retention = capacity_retention(efc, year - 1, spec.k_cycle, spec.k_cal)
        eol = retention < spec.eol_retention
        if eol:
            break
        usable = spec.nominal_kwh * retention
        res = self_consumption_dispatch(
            pv_kw, load_kw, spec,
            usable_kwh=usable,
            initial_soc_frac=initial_soc_frac,
            dt_h=dt_h,
        )
        throughput = float(res["charge_kwh"].sum() + res["discharge_kwh"].sum())
        efc += throughput / spec.nominal_kwh
        rows.append(
            {
                "year": year,
                "retention": retention,
                "usable_kwh": usable,
                "equivalent_full_cycles": efc,
                "throughput_kwh": throughput,
                "pv_kwh": float(res["pv_kwh"].sum()),
                "load_kwh": float(res["load_kwh"].sum()),
                "self_consumed_kwh": float(res["load_kwh"].sum() - res["import_kwh"].sum()),
                "import_kwh": float(res["import_kwh"].sum()),
                "export_kwh": float(res["export_kwh"].sum()),
                "discharge_kwh": float(res["discharge_kwh"].sum()),
                "eol": False,
            }
        )
    return pd.DataFrame(rows)
