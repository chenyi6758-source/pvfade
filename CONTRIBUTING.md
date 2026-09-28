# Contributing to pvfade

Thanks for considering a contribution. pvfade is a small, research-driven
project: every change should trace back to a real modeling or engineering
need.

## Ground rules

- **One PR, one idea.** Keep changes minimal and focused.
- **No fabricated results.** Anything quantitative (a parameter default, a
  benchmark number, a claim in the README) must be reproducible from the
  code, the tests, or a cited source. If you add a default parameter, say
  where it came from in the docstring or a code comment.
- **Tests for behavior changes.** New features and bug fixes come with a
  regression test under `tests/`. Run `pytest` before pushing.
- **Docs follow code.** Update docstrings and the README when behavior or
  assumptions change.

## Workflow

1. Fork the repo and create a feature branch from `main`.
2. Install in editable mode with test extras: `pip install -e ".[test]"`.
3. Make your change, add/adjust tests, run `pytest -q`.
4. Open a pull request describing *what* changed and *why* (link an issue
   if one exists).

## Style

- Python 3.11+, type hints on public functions, NumPy-style docstrings.
- Keep the public API surface small; prefer module-level functions over new
  classes unless state is genuinely needed.
- Line length: keep it readable, ~100 columns max.

## Roadmap context

- **v0.2**: PyPSA-based dispatch optimization (LP/MILP) next to the
  rule-based strategy; time-of-use tariff arbitrage.
- **v0.3 (Phase 2)**: multi-energy coupling — heat pumps via TESPy,
  distribution-grid interaction via pandapower.

Proposals aligned with the roadmap are especially welcome.
