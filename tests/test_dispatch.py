import numpy as np
import pandas as pd
import pytest

from pvfade.battery import BatterySpec
from pvfade.dispatch import self_consumption_dispatch, simulate_lifetime


def _spec(**kwargs):
    defaults = dict(nominal_kwh=10.0, charge_kw=5.0, discharge_kw=5.0)
    defaults.update(kwargs)
    return BatterySpec(**defaults)


def test_dispatch_energy_conservation():
    rng = np.random.default_rng(42)
    pv = pd.Series(np.clip(rng.normal(2.0, 2.5, 8760), 0, None))
    load = pd.Series(np.clip(rng.normal(1.5, 1.0, 8760), 0, None))
    spec = _spec()
    res = self_consumption_dispatch(pv, load, spec)

    charge_loss = (res["charge_kwh"] * (1 - spec.charge_eff)).sum()
    discharge_loss = (res["discharge_kwh"] * (1 / spec.discharge_eff - 1)).sum()
    soc_initial = 0.5 * spec.nominal_kwh  # default initial_soc_frac / usable
    soc_delta = res["soc_kwh"].iloc[-1] - soc_initial
    balance = (
        res["pv_kwh"].sum() + res["import_kwh"].sum()
        - res["load_kwh"].sum() - res["export_kwh"].sum()
        - charge_loss - discharge_loss - soc_delta
    )
    assert balance == pytest.approx(0.0, abs=1e-6)


def test_dispatch_soc_stays_within_bounds():
    rng = np.random.default_rng(0)
    pv = pd.Series(np.clip(rng.normal(3.0, 3.0, 8760), 0, None))
    load = pd.Series(np.clip(rng.normal(1.0, 0.8, 8760), 0, None))
    spec = _spec(soc_min=0.1, soc_max=0.9)
    res = self_consumption_dispatch(pv, load, spec)
    assert (res["soc_kwh"] >= spec.soc_min * spec.nominal_kwh - 1e-9).all()
    assert (res["soc_kwh"] <= spec.soc_max * spec.nominal_kwh + 1e-9).all()
    assert (res["import_kwh"] >= 0).all()
    assert (res["export_kwh"] >= 0).all()


def test_dispatch_no_battery_matches_direct_balance():
    pv = pd.Series([0.0, 4.0, 0.0])
    load = pd.Series([1.0, 1.0, 1.0])
    spec = _spec()
    # zero usable capacity -> pure pass-through
    res = self_consumption_dispatch(pv, load, spec, usable_kwh=1e-9,
                                    initial_soc_frac=0.5)
    assert res["import_kwh"].iloc[0] == pytest.approx(1.0)
    assert res["export_kwh"].iloc[1] == pytest.approx(3.0)
    assert res["import_kwh"].iloc[2] == pytest.approx(1.0)


def test_dispatch_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        self_consumption_dispatch(pd.Series([1.0, 2.0]), pd.Series([1.0]),
                                  _spec())


def test_simulate_lifetime_fades_over_time():
    pv = pd.Series(np.full(8760, 2.0))
    load = pd.Series(np.full(8760, 1.5))
    spec = _spec()
    life = simulate_lifetime(pv, load, spec, max_years=25)
    assert not life.empty
    assert life["retention"].is_monotonic_decreasing
    assert (life["retention"] >= spec.eol_retention).all()


def test_simulate_lifetime_stops_at_eol():
    pv = pd.Series(np.full(8760, 5.0))
    load = pd.Series(np.full(8760, 4.0))
    # aggressive aging -> EOL well before max_years
    spec = _spec(k_cycle=0.05, k_cal=0.05)
    life = simulate_lifetime(pv, load, spec, max_years=25)
    assert len(life) < 25
