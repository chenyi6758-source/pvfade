import numpy as np
import pandas as pd

from pvfade.sizing import grid_search


def _load():
    times = pd.date_range("2025-01-01", "2026-01-01", freq="h",
                          tz="Asia/Shanghai")[:-1]
    hod = times.hour.to_numpy(dtype=float)
    load = pd.Series(0.5 + 0.8 * np.exp(-((hod - 19.0) ** 2) / 8.0),
                     index=times, name="load_kw")
    return load


def _search(**kwargs):
    defaults = dict(
        pv_kw_options=[4.0, 6.0],
        batt_kwh_options=[5.0, 10.0],
        load_kw=_load(),
        latitude=31.23,
        longitude=121.47,
        import_rate=0.60,
        export_rate=0.05,
        capex_pv_per_kw=4000,
        capex_batt_per_kwh=1200,
        discount_rate=0.05,
        max_years=2,
        tz="Asia/Shanghai",
    )
    defaults.update(kwargs)
    return grid_search(**defaults)


def test_grid_search_returns_ranked_configurations():
    res = _search()
    assert len(res) == 4  # 2 PV options x 2 battery options
    expected_cols = {"pv_kw", "batt_kwh", "npv", "lcos", "payback_years",
                     "years_simulated", "lifetime_self_consumed_kwh",
                     "final_retention"}
    assert expected_cols.issubset(res.columns)
    # sorted by NPV descending
    assert (res["npv"].diff().dropna() <= 0).all()
    assert (res["final_retention"] <= 1.0).all()
    assert (res["years_simulated"] >= 1).all()


def test_grid_search_degradation_changes_npv():
    # The project's core claim: ignoring degradation overstates value.
    aged = _search()
    naive = _search(battery_kwargs={"k_cycle": 0.0, "k_cal": 0.0})
    assert not aged.empty and not naive.empty
    # every configuration is worth less once fade is modeled
    merged = aged.merge(naive, on=["pv_kw", "batt_kwh"],
                        suffixes=("_aged", "_naive"))
    assert (merged["npv_aged"] < merged["npv_naive"]).all()


def test_grid_search_forwards_battery_kwargs():
    res = _search(battery_kwargs={"k_cycle": 0.0026, "k_cal": 0.015})
    assert not res.empty
    assert (res["final_retention"] <= 1.0).all()
