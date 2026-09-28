"""Degradation-aware lithium-ion battery models.

Two layers:

1. :class:`BatterySpec` + :func:`capacity_retention`: a reduced-order model
   whose square-root laws mirror SEI-growth-dominated capacity fade as
   implemented in PyBaMM's aging submodels (e.g. single-particle models with
   reaction-limited SEI growth, where lithium-inventory loss grows with the
   square root of charge throughput and of time).
2. :func:`calibrate_cycle_aging_with_pybamm` (optional): runs a short PyBaMM
   simulation to fit the cycle-aging coefficient ``k_cycle`` for a specific
   cell parameter set instead of using the literature default.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass
class BatterySpec:
    """Nameplate and aging parameters of a battery energy storage unit."""

    nominal_kwh: float
    charge_kw: float
    discharge_kw: float
    charge_eff: float = 0.95
    discharge_eff: float = 0.95
    soc_min: float = 0.10
    soc_max: float = 0.90
    k_cycle: float = 0.006
    """Retention loss per sqrt(equivalent full cycle); ~0.006 fits NMC/graphite
    cells reaching 80% SOH after roughly 1000 equivalent full cycles."""
    k_cal: float = 0.025
    """Retention loss per sqrt(year) of calendar aging at ~25 °C."""
    eol_retention: float = 0.80
    """End of life: simulation stops once retention falls below this."""

    def __post_init__(self) -> None:
        if self.nominal_kwh <= 0:
            raise ValueError("nominal_kwh must be positive")
        if self.charge_kw <= 0 or self.discharge_kw <= 0:
            raise ValueError("charge/discharge power must be positive")
        for name in ("charge_eff", "discharge_eff"):
            eff = getattr(self, name)
            if not 0 < eff <= 1:
                raise ValueError(f"{name} must be in (0, 1]")
        if not 0 <= self.soc_min < self.soc_max <= 1:
            raise ValueError("require 0 <= soc_min < soc_max <= 1")
        if not 0 < self.eol_retention < 1:
            raise ValueError("eol_retention must be in (0, 1)")


def capacity_retention(
    equivalent_full_cycles: float,
    years: float,
    k_cycle: float = 0.006,
    k_cal: float = 0.025,
) -> float:
    """Fraction of nominal capacity remaining after cycling + calendar aging.

    Cycle aging follows ``1 - k_cycle * sqrt(EFC)`` and calendar aging
    ``1 - k_cal * sqrt(years)``, the square-root form characteristic of
    diffusion-limited SEI growth (see e.g. PyBaMM's SEI submodels).
    """
    if equivalent_full_cycles < 0:
        raise ValueError("equivalent_full_cycles must be non-negative")
    if years < 0:
        raise ValueError("years must be non-negative")
    retention = (
        1.0
        - k_cycle * math.sqrt(equivalent_full_cycles)
        - k_cal * math.sqrt(years)
    )
    return max(0.0, retention)


def calibrate_cycle_aging_with_pybamm(
    parameter_set: str = "Chen2020",
    n_cycles: int = 10,
    c_rate: float = 0.5,
) -> float:
    """Fit ``k_cycle`` from a short PyBaMM single-particle-model simulation.

    Runs ``n_cycles`` of constant-current cycling with a reaction-limited SEI
    aging submodel and fits the square-root cycle-aging law to the simulated
    discharge-capacity fade.

    Parameters
    ----------
    parameter_set : str
        PyBaMM parameter set name, e.g. ``"Chen2020"``.
    n_cycles : int
        Number of simulated cycles to fit against.
    c_rate : float
        C-rate used for the synthetic cycling.

    Returns
    -------
    float
        Fitted ``k_cycle`` compatible with :func:`capacity_retention`.

    Notes
    -----
    Requires the ``pybamm`` extra: ``pip install pvfade[pybamm]``.
    This is an experimental calibration helper; the default ``k_cycle`` is
    used everywhere unless you explicitly call this function.
    """
    try:
        import pybamm
    except ImportError as exc:
        raise ImportError(
            "calibrate_cycle_aging_with_pybamm requires PyBaMM: "
            "pip install pvfade[pybamm]"
        ) from exc

    pybamm.set_logging_level("ERROR")
    model = pybamm.lithium_ion.SPM(
        {
            "SEI": "reaction limited",
            "SEI film resistance": "none",
            "SEI porosity change": "false",
            "lithium plating": "none",
            "loss of active material": "none",
            "particle": "Fickian diffusion",
            "thermal": "x-lumped",
        }
    )
    param = pybamm.ParameterValues(parameter_set)
    half_period_h = 1.0 / c_rate
    experiment = pybamm.Experiment(
        [
            (
                f"Discharge at {c_rate}C for {half_period_h} hours or until 3.0 V",
                "Rest for 5 minutes",
                f"Charge at {c_rate}C until 4.2 V",
                "Rest for 5 minutes",
            )
        ]
        * n_cycles
    )
    sim = pybamm.Simulation(model, parameter_values=param, experiment=experiment)
    sol = sim.solve()
    caps = sol["Discharge capacity [A.h]"].entries
    if len(caps) < 2 or caps[0] <= 0:
        raise RuntimeError("PyBaMM simulation did not return usable cycle capacities")
    fade = 1.0 - float(caps[-1]) / float(caps[0])
    return max(0.0, fade / math.sqrt(n_cycles))
