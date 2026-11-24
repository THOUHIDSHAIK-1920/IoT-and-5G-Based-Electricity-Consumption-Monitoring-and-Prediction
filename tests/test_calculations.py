"""
VoltSense 5G - Unit Tests for Electrical and Cost Calculations
"""
import pytest
import math
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.calculations import (
    calculate_apparent_power,
    calculate_active_power,
    calculate_reactive_power,
    calculate_energy_increment_kwh,
    calculate_energy_cost,
    calculate_load_factor,
    calculate_carbon_emissions,
    calculate_power_factor_efficiency
)


def test_apparent_power():
    # S = V * I = 230V * 10A = 2300 VA
    s = calculate_apparent_power(230.0, 10.0)
    assert s == 2300.0


def test_active_power():
    # P = V * I * PF = 230V * 10A * 0.9 = 2070 W
    p = calculate_active_power(230.0, 10.0, 0.90)
    assert p == 2070.0
    # Active power cannot exceed apparent power
    s = calculate_apparent_power(230.0, 10.0)
    assert p <= s


def test_reactive_power():
    # S = 2300 VA, P = 2070 W
    # Q = sqrt(2300^2 - 2070^2) = sqrt(5290000 - 4284900) = sqrt(1005100) = 1002.55 VAR
    q = calculate_reactive_power(2300.0, 2070.0)
    assert abs(q - 1002.55) < 0.1


def test_energy_increment_kwh():
    # 1000W running for 1 hour (3600 seconds) must equal exactly 1.0 kWh
    e1 = calculate_energy_increment_kwh(1000.0, 3600.0)
    assert abs(e1 - 1.0) < 1e-5

    # 5000W running for 30 minutes (1800 seconds) = 5kW * 0.5h = 2.5 kWh
    e2 = calculate_energy_increment_kwh(5000.0, 1800.0)
    assert abs(e2 - 2.5) < 1e-5


def test_energy_cost():
    # 100 kWh at 7.50 INR/kWh = 750.00 INR
    cost = calculate_energy_cost(100.0, 7.50)
    assert cost == 750.0


def test_load_factor():
    # Avg load 5000W, Peak load 10000W -> Load factor 0.50
    lf = calculate_load_factor(5000.0, 10000.0)
    assert lf == 0.50


def test_carbon_emissions():
    # 100 kWh * 0.82 kg CO2/kWh = 82.0 kg CO2
    co2 = calculate_carbon_emissions(100.0)
    assert co2 == 82.0


def test_power_factor_efficiency():
    # High PF should be optimal
    optimal_audit = calculate_power_factor_efficiency(0.96, 1000.0, 7500.0)
    assert optimal_audit["status"] in ("OPTIMAL", "INCENTIVE_ELIGIBLE")

    # Low PF (0.75) should trigger penalty risk
    penalty_audit = calculate_power_factor_efficiency(0.75, 1000.0, 7500.0)
    assert penalty_audit["status"] == "PENALTY_RISK"
    assert penalty_audit["penalty_inr"] > 0
