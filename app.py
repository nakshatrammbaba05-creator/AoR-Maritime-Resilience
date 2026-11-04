from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from camlrp.data import SCENARIOS, build_scenario_data
from camlrp.model import SolveResult, solve_scenario


PROJECT_TITLE = (
    "Optimizing Maritime Cargo Routes for Resilience under "
    "Strategic Chokepoint Disruptions"
)

st.set_page_config(
    page_title="Maritime Resilience Simulator",
    page_icon="🚢",
    layout="wide",
)

st.title("Maritime Resilience Simulator")
st.caption(PROJECT_TITLE)
st.warning(
    "Educational prototype using synthetic, illustrative values. "
    "It does not use live vessel or security feeds and is not an operational "
    "routing recommendation."
)

with st.sidebar:
    st.header("What-if controls")
    st.caption("Each change reruns the MILP for all three scenarios.")
    demand_multiplier = st.slider(
        "Cargo demand", min_value=0.7, max_value=1.4, value=1.0, step=0.1,
        format="%.1fx",
    )
    direct_capacity_multiplier = st.slider(
        "Nominal corridor capacity", min_value=0.5, max_value=1.5, value=1.0,
        step=0.1, format="%.1fx",
    )
    risk_budget_multiplier = st.slider(
        "Security risk tolerance", min_value=0.5, max_value=1.5, value=1.0,
        step=0.1, format="%.1fx",
    )
    inventory_multiplier = st.slider(
        "Emergency inventory", min_value=0.0, max_value=2.0, value=1.0,
        step=0.1, format="%.1fx",
    )
    selected_scenario_id = st.selectbox(
        "Scenario to inspect",
        options=[scenario.id for scenario in SCENARIOS],
        format_func=lambda scenario_id: next(
            scenario.label for scenario in SCENARIOS if scenario.id == scenario_id
        ),
    )


@st.cache_data(show_spinner=False)
def run_scenario(
    scenario_id: str,
    demand_factor: float,
    capacity_factor: float,
    risk_factor: float,
    inventory_factor: float,
) -> tuple[SolveResult, SolveResult]:
    scenario_data = build_scenario_data(
        scenario_id,
        demand_multiplier=demand_factor,
        direct_capacity_multiplier=capacity_factor,
        risk_budget_multiplier=risk_factor,
        inventory_multiplier=inventory_factor,
    )
    optimized = solve_scenario(scenario_data)
    nominal = solve_scenario(
        scenario_data,
        allow_reconfiguration=False,
        enforce_risk_budget=False,
    )
    return optimized, nominal


scenario_results: dict[str, tuple[SolveResult, SolveResult]] = {}
with st.spinner("Re-optimizing scenario plans..."):
    for scenario in SCENARIOS:
        scenario_results[scenario.id] = run_scenario(
            scenario.id,
            demand_multiplier,
            direct_capacity_multiplier,
            risk_budget_multiplier,
            inventory_multiplier,
        )

selected_result, selected_nominal = scenario_results[selected_scenario_id]
selected_data = build_scenario_data(
    selected_scenario_id,
    demand_multiplier=demand_multiplier,
    direct_capacity_multiplier=direct_capacity_multiplier,
    risk_budget_multiplier=risk_budget_multiplier,
    inventory_multiplier=inventory_multiplier,
)
demand_by_id = {demand.id: demand for demand in selected_data.demands}
route_by_id = {route.id: route for route in selected_data.routes}

st.subheader(selected_result.scenario_label)
st.write(selected_data.scenario.description)

total_demand = sum(demand.quantity for demand in selected_data.demands)
transported = total_demand - selected_result.total_inventory - selected_result.total_shortage
rerouted = sum(
    flow
    for (demand_id, route_id), flow in selected_result.route_flows.items()
    if route_id != "direct"
)
rerouted_percent = 100.0 * rerouted / total_demand if total_demand else 0.0
metrics = st.columns(3)
metrics[0].metric(
    "Total cost",
    f"{selected_result.total_cost:,.0f}",
    help="Illustrative cost units",
)
metrics[1].metric(
    f"Transported (of {total_demand:,.0f})",
    f"{transported:,.1f}",
    help="Illustrative cargo units",
)
metrics[2].metric(
    "Shortage",
    f"{selected_result.total_shortage:,.1f}",
    help="Illustrative cargo units",
)
risk_metrics = st.columns(3)
risk_metrics[0].metric(
    "Risk budget used",
    f"{selected_result.risk_budget_use_percent:,.1f}%",
    help=f"Risk-budget limit: {selected_result.risk_budget:,.1f} index units",
)
risk_metrics[1].metric(
    "Rerouted",
    f"{rerouted_percent:,.1f}%",
    help=f"{rerouted:,.1f} illustrative cargo units",
)
risk_metrics[2].metric("Emissions index", f"{selected_result.emissions:,.1f}")

flow_rows = [
    {
        "Cargo": demand_by_id[demand_id].label,
        "Route option": route_by_id[route_id].label,
        "Quantity": flow,
    }
    for (demand_id, route_id), flow in selected_result.route_flows.items()
    if flow > 1e-6
]
flow_frame = pd.DataFrame(flow_rows)

left, right = st.columns(2)
with left:
    st.markdown("#### Optimized cargo allocation")
    if flow_frame.empty:
        st.info("No cargo is assigned to a route in this scenario.")
    else:
        allocation_chart = px.bar(
            flow_frame,
            x="Cargo",
            y="Quantity",
            color="Route option",
            barmode="stack",
            title="Cargo units assigned by route option",
            color_discrete_sequence=["#00A6A6", "#F2A65A", "#52796F"],
        )
        allocation_chart.update_layout(
            xaxis_title=None,
            yaxis_title="Illustrative cargo units",
            legend_title=None,
        )
        st.plotly_chart(allocation_chart, width="stretch")
with right:
    st.markdown("#### Objective cost breakdown")
    cost_frame = pd.DataFrame(
        [
            {"Cost component": component, "Cost": amount}
            for component, amount in selected_result.components.items()
            if amount > 1e-6
        ]
    )
    cost_chart = px.bar(
        cost_frame,
        x="Cost",
        y="Cost component",
        orientation="h",
        title="Illustrative cost units",
        color_discrete_sequence=["#355070"],
    )
    cost_chart.update_layout(yaxis_title=None, xaxis_title="Cost")
    st.plotly_chart(cost_chart, width="stretch")

st.markdown("#### Optimized plan vs. passive nominal plan")
comparison_frame = pd.DataFrame(
    [
        {
            "Policy": "Optimized reconfiguration",
            "Shortage": selected_result.total_shortage,
            "Risk budget used (%)": selected_result.risk_budget_use_percent,
            "Total cost": selected_result.total_cost,
        },
        {
            "Policy": "Passive nominal route only",
            "Shortage": selected_nominal.total_shortage,
            "Risk budget used (%)": (
                100.0 * selected_nominal.risk_exposure / selected_nominal.risk_budget
                if selected_nominal.risk_budget > 0
                else 0.0
            ),
            "Total cost": selected_nominal.total_cost,
        },
    ]
)
st.dataframe(comparison_frame, hide_index=True, width="stretch")
if selected_nominal.risk_exposure > selected_nominal.risk_budget + 1e-6:
    st.info(
        "The passive plan exceeds the selected scenario's risk budget. "
        "Its risk limit is intentionally not enforced so the comparison can "
        "show the consequence of keeping the nominal route."
    )

st.markdown("#### Scenario comparison")
scenario_rows = []
expected_cost = 0.0
for scenario in SCENARIOS:
    optimized, _ = scenario_results[scenario.id]
    demand_for_scenario = sum(
        demand.quantity
        for demand in build_scenario_data(
            scenario.id, demand_multiplier=demand_multiplier
        ).demands
    )
    scenario_rows.append(
        {
            "Scenario": scenario.label,
            "Weight": scenario.probability,
            "Total cost": optimized.total_cost,
            "Shortage": optimized.total_shortage,
            "Inventory used": optimized.total_inventory,
            "Delay exposure": optimized.delay_exposure,
            "Risk budget used (%)": optimized.risk_budget_use_percent,
            "Emissions index": optimized.emissions,
            "Rerouted (%)": (
                100.0
                * sum(
                    flow
                    for (demand_id, route_id), flow in optimized.route_flows.items()
                    if route_id != "direct"
                )
                / demand_for_scenario
                if demand_for_scenario
                else 0.0
            ),
        }
    )
    expected_cost += scenario.probability * optimized.total_cost

st.dataframe(
    pd.DataFrame(scenario_rows).style.format(
        {
            "Weight": "{:.0%}",
            "Total cost": "{:,.1f}",
            "Shortage": "{:,.1f}",
            "Inventory used": "{:,.1f}",
            "Delay exposure": "{:,.1f}",
            "Risk budget used (%)": "{:,.1f}%",
            "Emissions index": "{:,.1f}",
            "Rerouted (%)": "{:,.1f}%",
        }
    ),
    hide_index=True,
    width="stretch",
)
st.metric("Scenario-weighted expected cost", f"{expected_cost:,.1f} illustrative units")

with st.expander("Inspect model inputs, decisions, and assumptions"):
    st.markdown("#### Cargo inputs")
    cargo_input_rows = [
        {
            "Cargo": demand.label,
            "Demand": demand.quantity,
            "Inventory limit": demand.inventory_limit,
            "Shortage penalty": demand.shortage_penalty,
        }
        for demand in selected_data.demands
    ]
    st.dataframe(
        pd.DataFrame(cargo_input_rows).style.format(
            {
                "Demand": "{:,.1f}",
                "Inventory limit": "{:,.1f}",
                "Shortage penalty": "{:,.1f}",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    st.markdown("#### Route inputs")
    route_input_rows = [
        {
            "Route option": route.label,
            "Available": selected_data.scenario.route_available[route.id],
            "Capacity": selected_data.scenario.route_capacity[route.id],
            "Port": route.port,
            "Risk index": selected_data.scenario.route_risk[route.id],
            "Cost / unit": route.unit_cost,
            "Delay index": route.delay_units,
            "Emissions index / unit": route.emissions_per_unit,
        }
        for route in selected_data.routes
    ]
    st.dataframe(
        pd.DataFrame(route_input_rows).style.format(
            {
                "Capacity": "{:,.1f}",
                "Risk index": "{:,.2f}",
                "Cost / unit": "{:,.1f}",
                "Delay index": "{:,.1f}",
                "Emissions index / unit": "{:,.1f}",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Port capacities: "
        + "; ".join(
            f"{port}: {capacity:,.1f}"
            for port, capacity in selected_data.scenario.port_capacity.items()
        )
        + f". Risk budget: {selected_data.scenario.risk_budget:,.1f} index units."
    )

    st.markdown("#### Optimized demand-level decisions")
    decision_rows = []
    for demand in selected_data.demands:
        decision = {
            "Cargo": demand.label,
            "Demand": demand.quantity,
            "Emergency inventory": selected_result.inventory[demand.id],
            "Unmet demand": selected_result.shortage[demand.id],
        }
        for route in selected_data.routes:
            decision[route.label] = selected_result.route_flows.get(
                (demand.id, route.id), 0.0
            )
        decision_rows.append(decision)
    st.dataframe(
        pd.DataFrame(decision_rows).style.format(
            {column: "{:,.1f}" for column in pd.DataFrame(decision_rows).columns[1:]}
        ),
        hide_index=True,
        width="stretch",
    )
    st.write(
        "Volumes, costs, risk intensities, capacities, delays, and emissions "
        "are illustrative indices created for this class prototype. Route "
        "options are abstract and do not assert that a specific corridor or "
        "port can carry every cargo class. Scenario weights are modeling "
        "assumptions, not empirical probabilities."
    )

st.caption(
    "Model status: "
    + ", ".join(
        f"{scenario.label} — {scenario_results[scenario.id][0].status}"
        for scenario in SCENARIOS
    )
)
