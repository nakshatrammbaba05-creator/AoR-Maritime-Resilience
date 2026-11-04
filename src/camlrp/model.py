"""MILP formulation and result calculations for the demonstration app."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from camlrp.data import ScenarioData


@dataclass(frozen=True)
class SolveResult:
    scenario_id: str
    scenario_label: str
    status: str
    total_cost: float
    route_flows: dict[tuple[str, str], float]
    route_active: dict[str, bool]
    inventory: dict[str, float]
    shortage: dict[str, float]
    components: dict[str, float]
    risk_exposure: float
    risk_budget: float
    emissions: float
    delay_exposure: float

    @property
    def total_demand(self) -> float:
        return sum(
            sum(self.route_flows.get((demand_id, route_id), 0.0) for route_id in self.route_active)
            + self.inventory[demand_id]
            + self.shortage[demand_id]
            for demand_id in self.inventory
        )

    @property
    def total_inventory(self) -> float:
        return sum(self.inventory.values())

    @property
    def total_shortage(self) -> float:
        return sum(self.shortage.values())

    @property
    def risk_budget_use_percent(self) -> float:
        if isclose(self.risk_budget, 0.0):
            return 0.0 if isclose(self.risk_exposure, 0.0) else float("inf")
        return 100.0 * self.risk_exposure / self.risk_budget


def solve_scenario(
    data: ScenarioData,
    *,
    allow_reconfiguration: bool = True,
    enforce_risk_budget: bool = True,
) -> SolveResult:
    """Solve the CAMLRP for one observed scenario using SciPy/HiGHS."""
    demands = data.demands
    routes = data.routes if allow_reconfiguration else data.routes[:1]
    scenario = data.scenario
    demand_ids = [demand.id for demand in demands]
    route_ids = [route.id for route in routes]

    x_index: dict[tuple[str, str], int] = {}
    u_index: dict[tuple[str, str], int] = {}
    y_index: dict[str, int] = {}
    z_index: dict[str, int] = {}
    s_index: dict[str, int] = {}
    w_index: dict[tuple[str, str], int] = {}
    variable_count = 0

    def allocate(mapping: dict, key: object) -> None:
        nonlocal variable_count
        mapping[key] = variable_count
        variable_count += 1

    for demand_id in demand_ids:
        for route_id in route_ids:
            allocate(x_index, (demand_id, route_id))
    for demand_id in demand_ids:
        for route_id in route_ids:
            allocate(u_index, (demand_id, route_id))
    for route_id in route_ids:
        allocate(y_index, route_id)
    for demand_id in demand_ids:
        allocate(z_index, demand_id)
    for demand_id in demand_ids:
        allocate(s_index, demand_id)
    for demand_id in demand_ids:
        for route_id in route_ids:
            allocate(w_index, (demand_id, route_id))

    objective = np.zeros(variable_count)
    integrality = np.zeros(variable_count, dtype=int)
    lower_bounds = np.zeros(variable_count)
    upper_bounds = np.full(variable_count, np.inf)
    constraints: list[tuple[dict[int, float], float, float]] = []

    demand_by_id = {demand.id: demand for demand in demands}
    route_by_id = {route.id: route for route in routes}

    for demand_id in demand_ids:
        demand = demand_by_id[demand_id]
        for route_id in route_ids:
            route = route_by_id[route_id]
            x = x_index[(demand_id, route_id)]
            u = u_index[(demand_id, route_id)]
            w = w_index[(demand_id, route_id)]
            risk_intensity = scenario.route_risk[route_id]

            objective[x] = (
                route.unit_cost
                + data.delay_cost * route.delay_units
                + data.emissions_cost * route.emissions_per_unit
                + data.risk_cost * risk_intensity
            )
            objective[u] = 0.0
            objective[w] = data.deviation_cost
            integrality[u] = 1
            upper_bounds[x] = demand.quantity
            upper_bounds[u] = 1.0
            upper_bounds[w] = demand.quantity

            nominal_flow = demand.quantity if route_id == "direct" else 0.0
            constraints.append(({w: 1.0, x: -1.0}, -nominal_flow, np.inf))
            constraints.append(({w: 1.0, x: 1.0}, nominal_flow, np.inf))
            constraints.append(
                ({x: 1.0, u: -demand.quantity}, -np.inf, 0.0)
            )
            constraints.append(({u: 1.0, y_index[route_id]: -1.0}, -np.inf, 0.0))

        z = z_index[demand_id]
        s = s_index[demand_id]
        objective[z] = data.inventory_cost
        objective[s] = demand.shortage_penalty
        upper_bounds[z] = demand.inventory_limit
        upper_bounds[s] = demand.quantity

        balance = {x_index[(demand_id, route_id)]: 1.0 for route_id in route_ids}
        balance[z] = 1.0
        balance[s] = 1.0
        constraints.append((balance, demand.quantity, demand.quantity))

        route_limit = {u_index[(demand_id, route_id)]: 1.0 for route_id in route_ids}
        constraints.append((route_limit, -np.inf, data.max_routes_per_demand))

    for route_id in route_ids:
        route = route_by_id[route_id]
        y = y_index[route_id]
        objective[y] = route.activation_cost
        integrality[y] = 1
        upper_bounds[y] = 1.0
        route_is_available = scenario.route_available[route_id]
        constraints.append(
            ({y: 1.0}, 0.0, 1.0 if route_is_available else 0.0)
        )

        capacity_row = {y: -scenario.route_capacity[route_id]}
        for demand_id in demand_ids:
            capacity_row[x_index[(demand_id, route_id)]] = 1.0
        constraints.append((capacity_row, -np.inf, 0.0))

    for port_id, capacity in scenario.port_capacity.items():
        port_routes = [route for route in routes if route.port == port_id]
        if port_routes:
            port_row = {
                x_index[(demand_id, route.id)]: 1.0
                for route in port_routes
                for demand_id in demand_ids
            }
            constraints.append((port_row, -np.inf, capacity))

    if enforce_risk_budget:
        risk_row = {
            x_index[(demand_id, route_id)]: scenario.route_risk[route_id]
            for demand_id in demand_ids
            for route_id in route_ids
        }
        constraints.append((risk_row, -np.inf, scenario.risk_budget))

    matrix = lil_matrix((len(constraints), variable_count), dtype=float)
    constraint_lower = np.empty(len(constraints))
    constraint_upper = np.empty(len(constraints))
    for row_index, (coefficients, lower, upper) in enumerate(constraints):
        for column_index, coefficient in coefficients.items():
            if column_index >= 0:
                matrix[row_index, column_index] = coefficient
        constraint_lower[row_index] = lower
        constraint_upper[row_index] = upper

    result = milp(
        c=objective,
        integrality=integrality,
        bounds=Bounds(lower_bounds, upper_bounds),
        constraints=LinearConstraint(
            matrix.tocsr(), constraint_lower, constraint_upper
        ),
        options={"time_limit": 30.0, "mip_rel_gap": 1e-8},
    )
    if result.x is None:
        raise RuntimeError(
            f"Optimization failed for {scenario.label}: "
            f"{result.message or 'no feasible solution returned'}"
        )

    solution = result.x
    flows = {
        (demand_id, route_id): max(0.0, float(solution[x_index[(demand_id, route_id)]]))
        for demand_id in demand_ids
        for route_id in route_ids
    }
    inventory = {demand_id: max(0.0, float(solution[z_index[demand_id]])) for demand_id in demand_ids}
    shortage = {demand_id: max(0.0, float(solution[s_index[demand_id]])) for demand_id in demand_ids}
    active = {
        route_id: any(
            flows[(demand_id, route_id)] > 1e-6 for demand_id in demand_ids
        )
        for route_id in route_ids
    }

    components = {
        "Transportation": sum(
            flows[(demand_id, route_id)] * route_by_id[route_id].unit_cost
            for demand_id in demand_ids
            for route_id in route_ids
        ),
        "Route activation": sum(
            route_by_id[route_id].activation_cost
            for route_id in route_ids
            if active[route_id]
        ),
        "Plan deviation": sum(
            abs(
                flows[(demand_id, route_id)]
                - (
                    demand_by_id[demand_id].quantity
                    if route_id == "direct"
                    else 0.0
                )
            )
            * data.deviation_cost
            for demand_id in demand_ids
            for route_id in route_ids
        ),
        "Delay": sum(
            flows[(demand_id, route_id)]
            * route_by_id[route_id].delay_units
            * data.delay_cost
            for demand_id in demand_ids
            for route_id in route_ids
        ),
        "Emergency inventory": sum(inventory.values()) * data.inventory_cost,
        "Shortage": sum(
            shortage[demand_id] * demand_by_id[demand_id].shortage_penalty
            for demand_id in demand_ids
        ),
        "Security risk": data.risk_cost
        * sum(
            flows[(demand_id, route_id)] * scenario.route_risk[route_id]
            for demand_id in demand_ids
            for route_id in route_ids
        ),
        "Emissions": data.emissions_cost
        * sum(
            flows[(demand_id, route_id)]
            * route_by_id[route_id].emissions_per_unit
            for demand_id in demand_ids
            for route_id in route_ids
        ),
    }
    total_cost = sum(components.values())
    risk_exposure = sum(
        flows[(demand_id, route_id)] * scenario.route_risk[route_id]
        for demand_id in demand_ids
        for route_id in route_ids
    )
    emissions = sum(
        flows[(demand_id, route_id)] * route_by_id[route_id].emissions_per_unit
        for demand_id in demand_ids
        for route_id in route_ids
    )
    delay_exposure = sum(
        flows[(demand_id, route_id)] * route_by_id[route_id].delay_units
        for demand_id in demand_ids
        for route_id in route_ids
    )

    return SolveResult(
        scenario_id=scenario.id,
        scenario_label=scenario.label,
        status="Optimal" if result.status == 0 else str(result.message),
        total_cost=total_cost,
        route_flows=flows,
        route_active=active,
        inventory=inventory,
        shortage=shortage,
        components=components,
        risk_exposure=risk_exposure,
        risk_budget=scenario.risk_budget,
        emissions=emissions,
        delay_exposure=delay_exposure,
    )
