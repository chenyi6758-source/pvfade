import pytest

from pvfade.battery import BatterySpec, capacity_retention


def test_capacity_retention_fresh_cell():
    assert capacity_retention(0.0, 0.0) == pytest.approx(1.0)


def test_capacity_retention_decreases_with_cycling():
    r1 = capacity_retention(100.0, 0.0)
    r2 = capacity_retention(1000.0, 0.0)
    assert 1.0 > r1 > r2 > 0.0


def test_capacity_retention_decreases_with_time():
    assert capacity_retention(0.0, 5.0) < capacity_retention(0.0, 1.0)


def test_capacity_retention_sqrt_law():
    # doubling the sqrt(EFC) doubles the cycle fade contribution
    fade_100 = 1.0 - capacity_retention(100.0, 0.0)
    fade_400 = 1.0 - capacity_retention(400.0, 0.0)
    assert fade_400 == pytest.approx(2 * fade_100, rel=1e-9)


def test_capacity_retention_floored_at_zero():
    assert capacity_retention(1e9, 1e9) == 0.0


def test_capacity_retention_rejects_negative():
    with pytest.raises(ValueError):
        capacity_retention(-1.0, 0.0)
    with pytest.raises(ValueError):
        capacity_retention(0.0, -1.0)


def test_battery_spec_validation():
    with pytest.raises(ValueError):
        BatterySpec(nominal_kwh=0.0, charge_kw=1.0, discharge_kw=1.0)
    with pytest.raises(ValueError):
        BatterySpec(nominal_kwh=10.0, charge_kw=1.0, discharge_kw=1.0,
                     soc_min=0.9, soc_max=0.1)
    with pytest.raises(ValueError):
        BatterySpec(nominal_kwh=10.0, charge_kw=1.0, discharge_kw=1.0,
                     charge_eff=1.5)
    # valid spec constructs fine
    spec = BatterySpec(nominal_kwh=10.0, charge_kw=5.0, discharge_kw=5.0)
    assert spec.soc_max == 0.9
