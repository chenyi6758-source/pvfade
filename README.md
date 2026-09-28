# pvfade

[![CI](https://github.com/chenyi6758-source/pvfade/actions/workflows/ci.yml/badge.svg)](https://github.com/chenyi6758-source/pvfade/actions/workflows/ci.yml)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

**Degradation-aware design and dispatch optimization for PV-storage systems.**

Most PV-storage sizing tools assume the battery is nameplate-constant: fixed
round-trip efficiency, fixed usable capacity, forever. In reality, every
charge-discharge cycle grows the solid-electrolyte interphase (SEI) and
steals lithium inventory, so usable capacity fades year after year — and the
dispatch strategy itself decides how fast. pvfade closes that loop.

## The idea

```
pvlib (PV yield) ──► dispatch optimizer ──► degradation model ──┐
                        │                                      │
                        ▼                                      ▼
                   economics ◄── capacity fade feeds back ──────┘
                   (NPV / LCOS / payback)
```

1. **PV** — hourly AC generation from [pvlib](https://pvlib-python.readthedocs.io/)
   (solar position → clear-sky → transposition → cell temperature → inverter).
2. **Dispatch** — rule-based self-consumption maximization, simulated
   year-by-year.
3. **Degradation** — square-root cycle + calendar aging laws mirroring
   SEI-growth physics as implemented in
   [PyBaMM](https://www.pybamm.org/)'s aging submodels. An optional helper
   fits the aging rate directly from a short PyBaMM single-particle-model run
   (`pip install pvfade[pybamm]`).
4. **Economics** — NPV, LCOS and payback computed on the *faded* energy
   series, not nameplate fantasy.
5. **Sizing** — grid search over PV kW × battery kWh ranked by NPV.

## Quickstart

```python
from pvfade import BatterySpec, grid_search, simulate_lifetime, simulate_pv_ac

# 1. PV generation (Shanghai, 6 kW, south-facing)
pv = simulate_pv_ac(31.23, 121.47, capacity_kw=6.0)

# 2. Battery with degradation
spec = BatterySpec(nominal_kwh=10.0, charge_kw=5.0, discharge_kw=5.0)

# 3. Lifetime simulation with degradation feedback (needs your load profile)
life = simulate_lifetime(pv, load_kw, spec, max_years=25)
print(life[["year", "retention", "self_consumed_kwh"]].head())

# 4. Find the best configuration
results = grid_search(
    pv_kw_options=[4, 6, 8, 10],
    batt_kwh_options=[5, 10, 15, 20],
    load_kw=load_kw,
    latitude=31.23, longitude=121.47,
    import_rate=0.60, export_rate=0.05,          # CNY/kWh
    capex_pv_per_kw=4000, capex_batt_per_kwh=1200,  # CNY
    discount_rate=0.05,
)
print(results.head())
```

See [`examples/shanghai_household.py`](examples/shanghai_household.py) for a
complete runnable example.

## Why this doesn't exist yet

PV-yield tools (pvlib) model generation beautifully but stop at the meter.
Battery tools (PyBaMM) model electrochemistry beautifully but stop at the
cell terminals. Techno-economic studies usually bolt a *constant* battery
onto a PV profile and call it a sizing study — while the literature (e.g.
recent solar-plus-storage sizing work) explicitly flags that neglecting
long-term cycling and degradation biases lifecycle cost. pvfade is the
missing coupling layer: physics-informed fade inside the economic loop.

## Model assumptions & limitations

Honest boundaries of v0.1 — these are roadmap items, not hidden caveats:

- **Weather**: clear-sky irradiance scaled by a `clearness` factor, not
  measured TMY data. Swap in your own weather series via `pv_kw` inputs
  wherever it matters.
- **Battery**: no replacement is modeled — the lifetime simulation stops at
  end of life (`eol_retention`, default 80% SOH). Calendar aging uses a
  single coefficient at ~25 °C; temperature- and SOC-dependent aging is
  future work.
- **PV modules**: module degradation over the 25-year horizon is not
  modeled yet.
- **Dispatch**: rule-based self-consumption maximization only. PyPSA-based
  LP/MILP dispatch optimization and time-of-use arbitrage arrive in v0.2.

## Roadmap

- **v0.1** — PV + storage sizing with degradation-aware dispatch (this release)
- **v0.2** — PyPSA-based dispatch optimization (LP/MILP) alongside the
  rule-based strategy; time-of-use tariff arbitrage
- **v0.3 (Phase 2)** — multi-energy coupling: heat pumps via
  [TESPy](https://github.com/oemof/tespy), distribution-grid interaction via
  [pandapower](https://github.com/e2nIEE/pandapower)

## Install

```bash
pip install pvfade            # core
pip install "pvfade[pybamm]"  # + PyBaMM-based aging calibration
```

From source:

```bash
git clone https://github.com/chenyi6758-source/pvfade
cd pvfade
pip install -e ".[test]"
pytest
```

## License

BSD-3-Clause. Built on the shoulders of
[pvlib](https://github.com/pvlib/pvlib-python),
[PyBaMM](https://github.com/pybamm-team/PyBaMM),
[pandas](https://pandas.pydata.org/) and [SciPy](https://scipy.org/).
