import pytest

from pvfade.economics import lcos, npv, simple_payback


def test_npv_no_discount():
    assert npv(100.0, [60.0, 60.0], 0.0) == pytest.approx(20.0)


def test_npv_discounts_future_cashflows():
    # r = 100%: year-1 cash flow of 200 has present value 100
    assert npv(100.0, [200.0], 1.0) == pytest.approx(0.0)


def test_npv_empty_cashflows():
    assert npv(100.0, [], 0.05) == pytest.approx(-100.0)


def test_lcos_simple_case():
    # 1000 currency capex, 1000 kWh discharged in year 1, no discount
    assert lcos(1000.0, [1000.0], discount_rate=0.0) == pytest.approx(1.0)


def test_lcos_rejects_no_energy():
    with pytest.raises(ValueError):
        lcos(1000.0, [0.0, 0.0], discount_rate=0.05)


def test_simple_payback_fractional_year():
    assert simple_payback(100.0, [60.0, 60.0]) == pytest.approx(1 + 40.0 / 60.0)


def test_simple_payback_exact_year():
    assert simple_payback(120.0, [60.0, 60.0]) == pytest.approx(2.0)


def test_simple_payback_never():
    assert simple_payback(1000.0, [10.0, 10.0]) is None
