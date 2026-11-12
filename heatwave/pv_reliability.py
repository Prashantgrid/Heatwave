"""PV inverter component temperature and capacitor lifetime consumption."""

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ThermalParameters:
    """Parameters of one component's effective thermal path."""

    resistance_k_per_w: float
    time_constant_h: float

    def __post_init__(self):
        values = (self.resistance_k_per_w, self.time_constant_h)
        if not all(np.isfinite(v) and v > 0 for v in values):
            raise ValueError("Thermal resistance and time constant must be finite and positive.")


@dataclass(frozen=True)
class CapacitorParameters:
    """Temperature-only lifetime law at specified ripple and voltage conditions."""

    reference_temperature_c: float
    reference_life_h: float
    halving_interval_k: float

    def __post_init__(self):
        if not np.isfinite(self.reference_temperature_c) or self.reference_temperature_c <= -273.15:
            raise ValueError("Reference temperature must be finite and above absolute zero.")
        values = (self.reference_life_h, self.halving_interval_k)
        if not all(np.isfinite(v) and v > 0 for v in values):
            raise ValueError("Reference life and temperature halving interval must be finite and positive.")


def integrate_history(history, thermal, capacitor, initial_temperature_c, initial_life_used):
    """Integrate a contiguous history with constant forcing within each interval.

    Timestamp and forcing refer to the beginning of the interval. The component
    temperature at the end is the exact first-order response. Lifetime use
    integrates the temperature-dependent rate with the midpoint rule.
    """
    fields = ["timestamp_utc", "duration_h", "ambient_c", "heat_loss_w"]
    if history.empty or not set(fields).issubset(history.columns):
        raise ValueError(f"Provide at least one row with {', '.join(fields)}.")
    if not np.isfinite(initial_temperature_c) or initial_temperature_c <= -273.15:
        raise ValueError("Initial temperature must be finite and above absolute zero.")
    if not np.isfinite(initial_life_used) or initial_life_used < 0:
        raise ValueError("Initial lifetime consumption must be finite and nonnegative.")

    result = history.loc[:, fields].copy()
    result["timestamp_utc"] = pd.to_datetime(result["timestamp_utc"], utc=True, format="mixed")
    duration, ambient, loss = result[fields[1:]].to_numpy(dtype=float).T
    if result["timestamp_utc"].isna().any() or not np.isfinite([duration, ambient, loss]).all():
        raise ValueError("Timestamps and physical inputs must be complete and finite.")
    if (duration <= 0).any() or (ambient <= -273.15).any() or (loss < 0).any():
        raise ValueError("Use positive durations, physical temperatures and nonnegative heat losses.")
    gaps = result["timestamp_utc"].diff().dt.total_seconds().to_numpy()[1:] / 3600
    if not np.allclose(gaps, duration[:-1], atol=1e-9, rtol=0):
        raise ValueError("Intervals must be contiguous and in chronological order.")

    equilibrium = ambient + thermal.resistance_k_per_w * loss
    fraction_remaining_half = np.exp(-duration / (2 * thermal.time_constant_h))
    midpoint = np.empty(len(result))
    end = np.empty(len(result))
    temperature = initial_temperature_c
    for i, (target, half) in enumerate(zip(equilibrium, fraction_remaining_half)):
        midpoint[i] = target + (temperature - target) * half
        temperature = target + (temperature - target) * half**2
        end[i] = temperature

    with np.errstate(over="ignore"):
        rate = np.exp2((midpoint - capacitor.reference_temperature_c) / capacitor.halving_interval_k)
        increment = duration * rate / capacitor.reference_life_h
        cumulative = initial_life_used + np.cumsum(increment)
    if not np.isfinite(cumulative).all():
        raise ValueError("Lifetime calculation overflowed. Check units and the lifetime law's applicable range.")

    result["component_mid_c"] = midpoint
    result["component_end_c"] = end
    result["life_used_increment"] = increment
    result["life_used_fraction"] = cumulative
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("history", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--resistance-k-per-w", type=float, required=True)
    parser.add_argument("--time-constant-h", type=float, required=True)
    parser.add_argument("--reference-temperature-c", type=float, required=True)
    parser.add_argument("--reference-life-h", type=float, required=True)
    parser.add_argument("--halving-interval-k", type=float, required=True)
    parser.add_argument("--initial-temperature-c", type=float, required=True)
    parser.add_argument("--initial-life-used", type=float, required=True)
    args = parser.parse_args()
    thermal = ThermalParameters(args.resistance_k_per_w, args.time_constant_h)
    capacitor = CapacitorParameters(
        args.reference_temperature_c, args.reference_life_h, args.halving_interval_k
    )
    output = integrate_history(
        pd.read_csv(args.history), thermal, capacitor,
        args.initial_temperature_c, args.initial_life_used
    )
    output.to_csv(args.output, index=False)


if __name__ == "__main__":
    main()
