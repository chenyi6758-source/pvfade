"""End-to-end example: sizing a residential PV-storage system in Shanghai.

Pipeline: pvlib PV simulation -> degradation-aware lifetime dispatch ->
techno-economics -> grid search over PV kW x battery kWh.

Run:  python examples/shanghai_household.py
"""

import numpy as np
import pandas as pd

from pvfade import grid_search
from pvfade.pv import simulate_pv_ac


def synthetic_household_load(year: int = 2025, tz: str = "Asia/Shanghai") -> pd.Series:
    """Double-hump residential load profile (kW), ~4500 kWh/year."""
    times = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq="h", tz=tz)[:-1]
    hod = times.hour.to_numpy(dtype=float)
    # morning + evening peaks on a 0.35 kW base
    shape = (
        0.35
        + 0.55 * np.exp(-((hod - 7.5) ** 2) / 3.0)
        + 1.15 * np.exp(-((hod - 19.5) ** 2) / 6.0)
    )
    doy = times.dayofyear.to_numpy(dtype=float)
    seasonal = 1.0 + 0.25 * np.cos(2 * np.pi * (doy - 200) / 365.25)  # summer AC
    load = shape * seasonal
    # scale to ~4500 kWh/year
    load *= 4500.0 / load.sum()
    return pd.Series(load, index=times, name="load_kw")


def main() -> None:
    latitude, longitude = 31.23, 121.47  # Shanghai
    load = synthetic_household_load()
    print(f"Annual load: {load.sum():.0f} kWh")

    pv_example = simulate_pv_ac(latitude, longitude, 6.0)
    print(f"6 kW PV annual yield: {pv_example.sum():.0f} kWh "
          f"(capacity factor {pv_example.sum() / (6.0 * 8760):.1%})")

    results = grid_search(
        pv_kw_options=[4.0, 6.0, 8.0, 10.0],
        batt_kwh_options=[5.0, 10.0, 15.0, 20.0],
        load_kw=load,
        latitude=latitude,
        longitude=longitude,
        import_rate=0.60,      # CNY/kWh residential TOU average
        export_rate=0.05,      # CNY/kWh feed-in
        capex_pv_per_kw=4000,  # CNY/kW installed
        capex_batt_per_kwh=1200,  # CNY/kWh installed
        discount_rate=0.05,
        max_years=25,
        tz="Asia/Shanghai",
        # LFP-like aging: ~6000 equivalent full cycles to 80% SOH
        battery_kwargs={"k_cycle": 0.0026, "k_cal": 0.015},
    )
    pd.set_option("display.width", 160)
    print("\nTop configurations by NPV (CNY):")
    print(results.head(8).to_string(index=False))

    best = results.iloc[0]
    payback = best["payback_years"]
    payback_str = f"{payback:.1f} years" if payback is not None else "never"
    print(f"\nBest: {best['pv_kw']:.0f} kW PV + {best['batt_kwh']:.0f} kWh battery")
    print(f"  NPV: CNY {best['npv']:.0f} | LCOS: CNY {best['lcos']:.2f}/kWh "
          f"| payback: {payback_str} "
          f"| simulated lifetime: {int(best['years_simulated'])} years "
          f"(battery EOL)")

    # The money slide: what would a naive nameplate-constant model say?
    naive = grid_search(
        pv_kw_options=[best["pv_kw"]],
        batt_kwh_options=[best["batt_kwh"]],
        load_kw=load,
        latitude=latitude,
        longitude=longitude,
        import_rate=0.60,
        export_rate=0.05,
        capex_pv_per_kw=4000,
        capex_batt_per_kwh=1200,
        discount_rate=0.05,
        max_years=25,
        tz="Asia/Shanghai",
        battery_kwargs={"k_cycle": 0.0, "k_cal": 0.0},  # no degradation
    ).iloc[0]
    print(f"\nSame config WITHOUT degradation modeling:")
    print(f"  NPV: CNY {naive['npv']:.0f} | simulated lifetime: "
          f"{int(naive['years_simulated'])} years (no fade assumed)")
    print(f"  -> ignoring degradation overstates NPV by "
          f"CNY {naive['npv'] - best['npv']:.0f}; that gap is why pvfade exists.")


if __name__ == "__main__":
    main()
