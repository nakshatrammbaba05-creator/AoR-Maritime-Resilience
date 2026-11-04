"""Illustrative, explicitly synthetic data for the CAMLRP demonstration."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Demand:
    id: str
    label: str
    quantity: float
    inventory_limit: float
    shortage_penalty: float


@dataclass(frozen=True)
class Route:
    id: str
    label: str
    port: str
    unit_cost: float
    delay_units: float
    emissions_per_unit: float
    activation_cost: float


@dataclass(frozen=True)
class Scenario:
    id: str
    label: str
    description: str
    probability: float
    route_capacity: dict[str, float]
    port_capacity: dict[str, float]
    route_risk: dict[str, float]
    route_available: dict[str, bool]
    risk_budget: float


@dataclass(frozen=True)
class ScenarioData:
    scenario: Scenario
    demands: tuple[Demand, ...]
    routes: tuple[Route, ...]
    deviation_cost: float = 1.0
    delay_cost: float = 1.5
    inventory_cost: float = 18.0
    risk_cost: float = 8.0
    emissions_cost: float = 0.4
    max_routes_per_demand: int = 2


DEMANDS = (
    Demand("crude", "Crude oil", 100.0, 15.0, 120.0),
    Demand("lng", "Liquefied natural gas", 70.0, 10.0, 140.0),
    Demand("products", "Refined products", 60.0, 10.0, 110.0),
    Demand("fertilizer", "Fertilizer-related cargo", 40.0, 8.0, 90.0),
)

ROUTES = (
    Route(
        "direct",
        "Nominal corridor (via Hormuz)",
        "destination",
        unit_cost=10.0,
        delay_units=0.0,
        emissions_per_unit=4.0,
        activation_cost=0.0,
    ),
    Route(
        "alternative",
        "Alternative maritime corridor",
        "destination",
        unit_cost=17.0,
        delay_units=3.0,
        emissions_per_unit=9.0,
        activation_cost=120.0,
    ),
    Route(
        "substitute",
        "Substitute-port / multimodal option",
        "substitute_port",
        unit_cost=16.0,
        delay_units=2.0,
        emissions_per_unit=6.0,
        activation_cost=80.0,
    ),
)

SCENARIOS = (
    Scenario(
        id="normal",
        label="Normal operations",
        description="The nominal corridor is available with ample capacity and low risk.",
        probability=0.35,
        route_capacity={"direct": 270.0, "alternative": 70.0, "substitute": 35.0},
        port_capacity={"destination": 285.0, "substitute_port": 35.0},
        route_risk={"direct": 0.08, "alternative": 0.12, "substitute": 0.10},
        route_available={"direct": True, "alternative": True, "substitute": True},
        risk_budget=100.0,
    ),
    Scenario(
        id="severe",
        label="Severe disruption",
        description="Direct capacity is sharply constrained; alternatives have limited capacity.",
        probability=0.35,
        route_capacity={"direct": 80.0, "alternative": 120.0, "substitute": 70.0},
        port_capacity={"destination": 150.0, "substitute_port": 70.0},
        route_risk={"direct": 1.0, "alternative": 0.20, "substitute": 0.10},
        route_available={"direct": True, "alternative": True, "substitute": True},
        risk_budget=65.0,
    ),
    Scenario(
        id="recovery",
        label="Partial recovery",
        description="Some direct capacity returns, while alternative routes remain in use.",
        probability=0.30,
        route_capacity={"direct": 150.0, "alternative": 120.0, "substitute": 90.0},
        port_capacity={"destination": 220.0, "substitute_port": 90.0},
        route_risk={"direct": 0.35, "alternative": 0.10, "substitute": 0.08},
        route_available={"direct": True, "alternative": True, "substitute": True},
        risk_budget=90.0,
    ),
)

SCENARIO_BY_ID = {scenario.id: scenario for scenario in SCENARIOS}


def build_scenario_data(
    scenario_id: str,
    *,
    demand_multiplier: float = 1.0,
    direct_capacity_multiplier: float = 1.0,
    risk_budget_multiplier: float = 1.0,
    inventory_multiplier: float = 1.0,
) -> ScenarioData:
    """Return a scenario copy with validated what-if multipliers applied."""
    if scenario_id not in SCENARIO_BY_ID:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    for name, value in (
        ("demand multiplier", demand_multiplier),
        ("direct capacity multiplier", direct_capacity_multiplier),
        ("risk budget multiplier", risk_budget_multiplier),
        ("inventory multiplier", inventory_multiplier),
    ):
        if not isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a finite, non-negative number")

    original = SCENARIO_BY_ID[scenario_id]
    scenario = Scenario(
        id=original.id,
        label=original.label,
        description=original.description,
        probability=original.probability,
        route_capacity={
            route_id: capacity
            * (direct_capacity_multiplier if route_id == "direct" else 1.0)
            for route_id, capacity in original.route_capacity.items()
        },
        port_capacity=original.port_capacity.copy(),
        route_risk=original.route_risk.copy(),
        route_available=original.route_available.copy(),
        risk_budget=original.risk_budget * risk_budget_multiplier,
    )
    demands = tuple(
        Demand(
            id=demand.id,
            label=demand.label,
            quantity=demand.quantity * demand_multiplier,
            inventory_limit=demand.inventory_limit * inventory_multiplier,
            shortage_penalty=demand.shortage_penalty,
        )
        for demand in DEMANDS
    )
    return ScenarioData(scenario=scenario, demands=demands, routes=ROUTES)
