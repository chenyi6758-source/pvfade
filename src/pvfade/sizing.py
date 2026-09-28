"""System sizing: grid search over PV and battery capacities.

For every (PV kW, battery kWh) combination the full chain is executed:

    pvlib PV simulation -> degradation-aware lifetime dispatch -> economics

so the ranking reflects faded, real-world performance rather than
nameplate assumptions.
"""

from __future__ import annotations

import pandas as pd

from pvfade.battery import BatterySpec
from pvfade.dispatch import simulate_lifetime
from pvfade.economics import lcos, npv, simple_payback
from pvfade.pv import simulate_pv_ac


def grid_search(
    pv_kw_options: list[float],
    batt_kwh_options: list[float],
    load_kw: pd.Series,
    latitude: float,
    longitude: float,
    import_rate: float,
    export_rate: float,
    capex_pv_per_kw: float,
    capex_batt_per_kwh: float,
    discount_rate: float = 0.05,
    max_years: int = 25,
    c_rate: float = 0.5,
    battery_kwargs: dict | None = None,
    **pv_kwargs,
) -> pd.DataFrame:
    """Rank PV-storage configurations by net present value.

    Parameters
    ----------
    pv_kw_options, batt_kwh_options : list of float
        Candidate PV capacities (kW) and battery capacities (kWh).
    load_kw : pd.Series
        Hourly load in kW for one representative year (reused each year).
    latitude, longitude : float
        Site coordinates.
    import_rate, export_rate : float
        Grid import price and PV export feed-in price (currency/kWh).
    capex_pv_per_kw, capex_batt_per_kwh : float
        Capital costs.
    discount_rate : float
        Discount rate for NPV/LCOS.
    max_years : int
        Lifetime horizon; may end earlier at battery end of life.
    c_rate : float
        Battery power rating as a fraction of energy capacity.
    battery_kwargs : dict, optional
        Extra keyword arguments forwarded to :class:`BatterySpec`, e.g.
        ``{"k_cycle": 0.0026}`` for LFP-like cycle aging.
    **pv_kwargs
        Forwarded to :func:`pvfade.pv.simulate_pv_ac`.

    Returns
    -------
    pd.DataFrame
        One row per configuration, sorted by ``npv`` descending.
    """
    battery_kwargs = battery_kwargs or {}
    rows: list[dict] = []
    pv_cache: dict[float, pd.Series] = {}
    for pv_kw in pv_kw_options:
        if pv_kw not in pv_cache:
            pv_cache[pv_kw] = simulate_pv_ac(
                latitude, longitude, pv_kw, **pv_kwargs
            )
        pv = pv_cache[pv_kw]
        for batt_kwh in batt_kwh_options:
            spec = BatterySpec(
                nominal_kwh=batt_kwh,
                charge_kw=batt_kwh * c_rate,
                discharge_kw=batt_kwh * c_rate,
                **battery_kwargs,
            )
            life = simulate_lifetime(pv, load_kw, spec, max_years=max_years)
            if life.empty:
                continue
            years_simulated = int(life["year"].iloc[-1])
            annual_savings = (
                life["self_consumed_kwh"] * import_rate
                + life["export_kwh"] * export_rate
            ).to_numpy()
            capex = pv_kw * capex_pv_per_kw + batt_kwh * capex_batt_per_kwh
            capex_batt = batt_kwh * capex_batt_per_kwh
            value_npv = npv(capex, annual_savings, discount_rate)
            value_lcos = lcos(
                capex_batt,
                life["discharge_kwh"].to_numpy(),
                discount_rate=discount_rate,
            )
            rows.append(
                {
                    "pv_kw": pv_kw,
                    "batt_kwh": batt_kwh,
                    "npv": value_npv,
                    "lcos": value_lcos,
                    "payback_years": simple_payback(capex, annual_savings),
                    "years_simulated": years_simulated,
                    "lifetime_self_consumed_kwh": float(life["self_consumed_kwh"].sum()),
                    "final_retention": float(life["retention"].iloc[-1]),
                }
            )
    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("npv", ascending=False).reset_index(drop=True)
    return result
