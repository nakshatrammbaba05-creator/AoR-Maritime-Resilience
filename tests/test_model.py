from math import isclose

import pytest

from camlrp.data import build_scenario_data
from camlrp.model import solve_scenario


@pytest.mark.parametrize("scenario_id", ["normal", "severe", "recovery"])
def test_optimized_scenario_respects_balance_and_risk_budget(scenario_id: str) -> None:
    data = build_scenario_data(scenario_id)
    result = solve_scenario(data)

    assert result.status == "Optimal"
    assert isclose(result.total_demand, sum(d.quantity for d in data.demands), abs_tol=1e-5)
    assert result.risk_exposure <= result.risk_budget + 1e-5
    assert all(value >= -1e-8 for value in result.inventory.values())
    assert all(value >= -1e-8 for value in result.shortage.values())
    assert all(
        result.inventory[demand.id] <= demand.inventory_limit + 1e-5
        for demand in data.demands
    )
    for route in data.routes:
        route_flow = sum(
            result.route_flows[(demand.id, route.id)] for demand in data.demands
        )
        assert route_flow <= data.scenario.route_capacity[route.id] + 1e-5
        assert route_flow <= sum(d.quantity for d in data.demands) * (
            1 if data.scenario.route_available[route.id] else 0
        ) + 1e-5
    for port_id, capacity in data.scenario.port_capacity.items():
        port_flow = sum(
            result.route_flows[(demand.id, route.id)]
            for demand in data.demands
            for route in data.routes
            if route.port == port_id
        )
        assert port_flow <= capacity + 1e-5
    for demand in data.demands:
        used_routes = sum(
            result.route_flows[(demand.id, route.id)] > 1e-6
            for route in data.routes
        )
        assert used_routes <= data.max_routes_per_demand


def test_normal_case_uses_nominal_corridor_without_shortage() -> None:
    result = solve_scenario(build_scenario_data("normal"))

    assert result.total_shortage <= 1e-6
    assert result.route_flows[("crude", "direct")] > 0
    assert all(
        result.route_flows[(demand_id, route_id)] <= 1e-6
        for demand_id in ["crude", "lng", "products", "fertilizer"]
        for route_id in ["alternative", "substitute"]
    )
    assert result.risk_budget_use_percent < 100.0


def test_reconfiguration_reduces_severe_scenario_shortage() -> None:
    data = build_scenario_data("severe")
    optimized = solve_scenario(data)
    passive = solve_scenario(
        data,
        allow_reconfiguration=False,
        enforce_risk_budget=False,
    )

    assert optimized.total_shortage < passive.total_shortage
    assert optimized.risk_exposure <= data.scenario.risk_budget + 1e-5
    assert passive.risk_exposure > data.scenario.risk_budget


def test_input_multipliers_are_applied_and_validated() -> None:
    base = build_scenario_data("severe")
    changed = build_scenario_data(
        "severe",
        demand_multiplier=1.2,
        direct_capacity_multiplier=0.8,
        risk_budget_multiplier=0.7,
        inventory_multiplier=0.0,
    )

    assert isclose(changed.demands[0].quantity, base.demands[0].quantity * 1.2)
    assert isclose(
        changed.scenario.route_capacity["direct"],
        base.scenario.route_capacity["direct"] * 0.8,
    )
    assert isclose(changed.scenario.risk_budget, base.scenario.risk_budget * 0.7)
    assert changed.demands[0].inventory_limit == 0.0
    with pytest.raises(ValueError, match="finite, non-negative"):
        build_scenario_data("severe", demand_multiplier=-1.0)
    with pytest.raises(ValueError, match="finite, non-negative"):
        build_scenario_data("severe", risk_budget_multiplier=float("nan"))


def test_zero_risk_budget_prohibits_positive_risk_route_flows() -> None:
    data = build_scenario_data("severe", risk_budget_multiplier=0.0)
    result = solve_scenario(data)

    assert result.risk_exposure == pytest.approx(0.0)
    assert sum(result.route_flows.values()) == pytest.approx(0.0)
    assert result.total_inventory + result.total_shortage == pytest.approx(
        sum(demand.quantity for demand in data.demands)
    )
