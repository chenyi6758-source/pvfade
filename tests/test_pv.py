import numpy as np
import pandas as pd
import pytest

from pvfade.pv import simulate_pv_ac, synthetic_ambient_temperature


def test_simulate_pv_ac_shape_and_nonnegativity():
    pv = simulate_pv_ac(31.23, 121.47, 5.0, year=2025)
    assert len(pv) == 8760
    assert (pv >= 0).all()
    assert pv.sum() > 0  # Shanghai gets sun


def test_simulate_pv_ac_zero_at_night():
    pv = simulate_pv_ac(31.23, 121.47, 5.0, year=2025)
    midnight = pv.loc["2025-01-15 00:00:00+08:00"]
    assert midnight == 0.0


def test_simulate_pv_ac_peak_below_nameplate():
    pv = simulate_pv_ac(31.23, 121.47, 5.0, year=2025)
    assert pv.max() <= 5.0  # inverter + temperature losses


def test_simulate_pv_ac_scales_with_capacity():
    small = simulate_pv_ac(31.23, 121.47, 2.0, year=2025).sum()
    big = simulate_pv_ac(31.23, 121.47, 4.0, year=2025).sum()
    assert big == pytest.approx(2 * small, rel=1e-6)


def test_simulate_pv_ac_rejects_bad_inputs():
    with pytest.raises(ValueError):
        simulate_pv_ac(31.23, 121.47, 0.0)
    with pytest.raises(ValueError):
        simulate_pv_ac(31.23, 121.47, 5.0, clearness=1.5)


def test_synthetic_ambient_temperature_seasonality():
    times = pd.date_range("2025-01-01", "2026-01-01", freq="h", tz="Asia/Shanghai")[:-1]
    temp = synthetic_ambient_temperature(times, t_mean=17.0)
    jan = temp.loc["2025-01"].mean()
    jul = temp.loc["2025-07"].mean()
    assert jul > jan  # northern hemisphere
    assert abs(temp.mean() - 17.0) < 0.5
