"""pvfade: degradation-aware design and dispatch optimization for PV-storage systems."""

from pvfade.battery import BatterySpec, capacity_retention
from pvfade.dispatch import self_consumption_dispatch, simulate_lifetime
from pvfade.economics import lcos, npv, simple_payback
from pvfade.pv import simulate_pv_ac
from pvfade.sizing import grid_search

__version__ = "0.1.0"

__all__ = [
    "BatterySpec",
    "capacity_retention",
    "self_consumption_dispatch",
    "simulate_lifetime",
    "lcos",
    "npv",
    "simple_payback",
    "simulate_pv_ac",
    "grid_search",
]
