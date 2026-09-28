"""Photovoltaic generation modeling built on pvlib.

This module wraps pvlib's modeling chain

    solar position -> clear-sky irradiance -> transposition ->
    cell temperature -> DC -> AC

into a single function returning an hourly AC power time series for a full
year. Where on-site measurements are unavailable, a clear-sky model scaled by
a clearness factor is used as a transparent, reproducible stand-in for
measured weather data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib


def synthetic_ambient_temperature(
    times: pd.DatetimeIndex,
    t_mean: float = 17.0,
    t_annual_amp: float = 12.0,
    t_daily_amp: float = 4.0,
) -> pd.Series:
    """Simple annual + diurnal ambient temperature model (°C).

    Parameters
    ----------
    times : pd.DatetimeIndex
        Time steps to evaluate.
    t_mean : float
        Annual mean ambient temperature in °C.
    t_annual_amp : float
        Amplitude of the annual cycle in °C (coldest ~mid-January).
    t_daily_amp : float
        Amplitude of the diurnal cycle in °C (warmest ~14:00).

    Returns
    -------
    pd.Series
        Ambient temperature in °C.
    """
    doy = times.dayofyear.to_numpy(dtype=float)
    hod = times.hour.to_numpy(dtype=float) + times.minute.to_numpy(dtype=float) / 60.0
    temp = (
        t_mean
        - t_annual_amp * np.cos(2.0 * np.pi * (doy - 15.0) / 365.25)
        + t_daily_amp * np.cos(2.0 * np.pi * (hod - 14.0) / 24.0)
    )
    return pd.Series(temp, index=times, name="temp_air_c")


def simulate_pv_ac(
    latitude: float,
    longitude: float,
    capacity_kw: float,
    tilt: float | None = None,
    azimuth: float = 180.0,
    year: int = 2025,
    tz: str = "Asia/Shanghai",
    clearness: float = 0.75,
    t_mean: float = 17.0,
) -> pd.Series:
    """Simulate hourly AC power (kW) of a fixed-tilt PV array for one year.

    Uses pvlib's Ineichen clear-sky model scaled by ``clearness`` to emulate
    average cloud cover, the isotropic transposition model via
    :func:`pvlib.irradiance.get_total_irradiance`, the PVWatts DC model, and
    the PVWatts inverter model.

    Parameters
    ----------
    latitude, longitude : float
        Site coordinates in degrees.
    capacity_kw : float
        Nameplate DC capacity in kW.
    tilt : float, optional
        Surface tilt in degrees; defaults to ``abs(latitude)``.
    azimuth : float
        Surface azimuth in degrees (180 = south in the northern hemisphere).
    year : int
        Calendar year to simulate (leap years handled by pandas).
    tz : str
        Timezone of the output index.
    clearness : float
        Multiplicative derate applied to clear-sky irradiance (0-1].
    t_mean : float
        Annual mean ambient temperature in °C.

    Returns
    -------
    pd.Series
        Hourly AC power in kW, indexed by local time.
    """
    if capacity_kw <= 0:
        raise ValueError("capacity_kw must be positive")
    if not 0 < clearness <= 1:
        raise ValueError("clearness must be in (0, 1]")
    if tilt is None:
        tilt = abs(latitude)

    times = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq="h", tz=tz)[:-1]

    location = pvlib.location.Location(latitude, longitude, tz=tz)
    solpos = location.get_solarposition(times)
    cs = location.get_clearsky(times, model="ineichen")
    ghi = (cs["ghi"] * clearness).clip(lower=0.0)
    dni = (cs["dni"] * clearness).clip(lower=0.0)
    dhi = (cs["dhi"] * clearness).clip(lower=0.0)

    total = pvlib.irradiance.get_total_irradiance(
        tilt,
        azimuth,
        solpos["apparent_zenith"],
        solpos["azimuth"],
        dni,
        ghi,
        dhi,
    )
    poa = total["poa_global"].fillna(0.0).clip(lower=0.0)

    temp_air = synthetic_ambient_temperature(times, t_mean=t_mean)
    temp_cell = pvlib.temperature.pvsyst_cell(poa, temp_air, wind_speed=1.0)

    dc_w = pvlib.pvsystem.pvwatts_dc(
        poa, temp_cell, pdc0=capacity_kw * 1000.0, gamma_pdc=-0.004
    )
    ac_w = pvlib.inverter.pvwatts(dc_w, pdc0=capacity_kw * 1000.0)

    ac_kw = (ac_w / 1000.0).clip(lower=0.0)
    ac_kw.index = times
    ac_kw.name = "pv_ac_kw"
    return ac_kw
