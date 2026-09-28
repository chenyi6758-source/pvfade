# Changelog

All notable changes to pvfade are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-09-28

### Added
- PV yield chain on pvlib: solar position → Ineichen clear-sky (scaled by a
  clearness factor) → transposition → cell temperature → PVWatts DC/AC.
- Rule-based self-consumption dispatch with hourly energy bookkeeping and a
  year-by-year lifetime loop.
- Degradation feedback: square-root cycle + calendar aging laws mirroring
  SEI-growth physics close the loop between dispatch and usable capacity;
  simulation stops at battery end of life.
- Optional `calibrate_cycle_aging_with_pybamm()` helper fitting the
  cycle-aging coefficient from a short PyBaMM SPM run (`pip install
  pvfade[pybamm]`).
- Techno-economics on the faded energy series: NPV, LCOS, simple payback.
- `grid_search()` sizing over PV kW × battery kWh ranked by NPV.
- Test suite (30 tests), GitHub Actions CI (Python 3.11/3.12), and a
  runnable Shanghai household end-to-end example.
