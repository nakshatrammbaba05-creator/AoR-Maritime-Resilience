# Optimizing Maritime Cargo Routes for Resilience under Strategic Chokepoint Disruptions

**Authors:** Arpita Gupta (MBA/11/034); Kriti Kabra (MBA/11/116); Nakshatra Mehta (MBA/BA05/056); Swapnil Chourasiya (MBA/11/240)<br>
**Course:** Analysis of Risk (AoR)<br>
**Research paper:** Rokaya Lassoued, “Chokepoint-aware maritime logistics reconfiguration under security disruptions: a scenario-based mixed-integer optimization framework,” *Journal of Transportation Security*, 19, 35 (2026). [https://doi.org/10.1007/s12198-026-00357-8](https://doi.org/10.1007/s12198-026-00357-8)<br>
**Prototype:** [Render app](https://aor-maritime-resilience.onrender.com/)

## AI usage note

AI was used to help interpret the approved research paper, draft documentation, implement the educational prototype, and prepare model tests. The team must review and understand the final model, inputs, assumptions, and outputs, and must be able to explain them. All demonstration values are synthetic and are not represented as verified shipping data or security intelligence.

## 1. Business Requirements Document (BRD)

### Business problem

Maritime cargo plans often depend on a small number of strategic corridors. If a chokepoint becomes risky or capacity-constrained, continuing with the nominal plan can create shortages and excessive security exposure. Decision-makers need a structured way to compare rerouting, substitute-port options, emergency inventory, and unmet demand while considering cost, delay, emissions, and a security-risk limit.

### Objective and users

The project demonstrates a tactical decision-support tool for logistics planners and business stakeholders. Given an assessed disruption scenario, it recommends an illustrative allocation of cargo across abstract route options and reports the associated trade-offs. It does **not** forecast conflict, track individual vessels, or provide operational routing advice.

### Scope

The demonstration uses the Strait of Hormuz as the motivating case and includes four illustrative cargo classes, three abstract route options, and three scenarios: normal operations, severe disruption, and partial recovery. A “passive nominal” comparator keeps cargo on the direct corridor, using only emergency inventory and shortage when direct capacity is insufficient.

Included: scenario selection, demand/capacity/risk/inventory what-if controls, MILP optimization, passive-policy comparison, cost and resilience indicators, and visualizations.

Excluded: verified commodity flows, live AIS or security feeds, vessel-level navigation, port queues, dynamic time periods, and production deployment. Interactive simulation is required; external live feeds are not.

### Success criteria

1. Every cargo unit is accounted for as routed, supplied by emergency inventory, or unmet.
2. The optimized plan respects route, port, availability, and risk-budget constraints.
3. Under the severe illustrative case, reconfiguration reduces shortage relative to the passive nominal comparator.
4. Changing a control reruns the optimization and updates results and charts.
5. Assumptions, units, and limitations are visible to users.

## 2. Software Requirements Specification (SRS)

| ID | Requirement |
|---|---|
| FR-1 | Let users choose normal, severe-disruption, or partial-recovery conditions. |
| FR-2 | Let users adjust aggregate demand, direct-corridor capacity, risk tolerance, and emergency-inventory availability. |
| FR-3 | Solve the MILP for all scenarios when inputs change and show solver status. |
| FR-4 | Display cargo-by-route allocations, inventory use, unmet demand, total cost, delay, emissions, risk exposure, and risk-budget use. |
| FR-5 | Compare the optimized plan with a passive direct-corridor-only policy. The comparator does not enforce the risk budget so that violations can be shown. |
| FR-6 | Display scenario-weighted expected cost using the documented illustrative scenario weights. |
| FR-7 | Label all synthetic inputs and explain that route options are abstract and require real-world validation. |
| NFR-1 | For the small teaching instance, complete each scenario solve within 30 seconds on a typical laptop. |
| NFR-2 | Reject invalid scenario IDs and negative what-if multipliers explicitly. |
| NFR-3 | Present costs, volumes, risk exposure, and emissions as illustrative units or indices—not as measured real-world values. |

### Data and units

| Input | Meaning | Demonstration treatment |
|---|---|---|
| Cargo demand | Required volume by cargo class | Synthetic cargo units |
| Route and port capacity | Maximum flow in a scenario | Synthetic cargo units |
| Route cost, delay, emissions | Per-unit route attributes | Illustrative cost/delay/emissions indices |
| Route risk | Scenario-specific exposure per unit | Illustrative risk index |
| Emergency inventory | Maximum buffered volume by cargo class | Synthetic cargo units |
| Scenario weights | Weights for expected-cost comparison | Assumptions: 0.35, 0.35, 0.30; not empirical probabilities |

The model uses four cargo classes (crude oil, liquefied natural gas, refined products, fertilizer-related cargo) with base demands of 100, 70, 60, and 40 units. These figures are made for the prototype and are not drawn from the paper’s Hormuz estimates.

## 3. Technical Design Document (TDD)

### Model outline

This is a route-based MILP inspired by the CAMLRP in R1. For each observed scenario, the model chooses cargo flows, route activation, emergency inventory, and shortage. Scenario decisions are independent; the prototype solves each scenario separately and computes expected cost as the scenario-weighted sum. It is therefore a scenario-conditioned recourse evaluation—not a full two-stage stochastic program.

### Sets and parameters

| Symbol | Definition |
|---|---|
| \(K\) | Cargo classes; \(R\) route options; \(\Omega\) scenarios; \(P\) ports |
| \(q_k\) | Demand for cargo \(k\) |
| \(\bar{x}_{kr}\) | Nominal allocation (all base demand assigned to the direct route) |
| \(c_r, \ell_r, e_r\) | Per-unit transport cost, delay index, and emissions index on route \(r\) |
| \(\rho_{r\omega}\) | Risk exposure per unit on route \(r\) in scenario \(\omega\) |
| \(U_{r\omega}, B_{p\omega}\) | Route and port capacities |
| \(a_{r\omega}\) | 1 if route \(r\) is available in scenario \(\omega\), otherwise 0 |
| \(I_k, \mu_k\) | Emergency inventory limit and shortage penalty |
| \(R^{max}_\omega\) | Scenario risk-exposure budget |
| \(\pi_\omega\) | Scenario weight, with \(\sum_\omega \pi_\omega=1\) |

### Decision variables

| Variable | Domain | Meaning |
|---|---|---|
| \(x_{kr\omega}\) | Nonnegative continuous | Cargo \(k\) sent on route \(r\) |
| \(u_{kr\omega}\) | Binary | Cargo \(k\) uses route \(r\) |
| \(y_{r\omega}\) | Binary | Route \(r\) is activated |
| \(z_{k\omega}\) | Nonnegative continuous | Cargo served from emergency inventory |
| \(s_{k\omega}\) | Nonnegative continuous | Unmet cargo demand |
| \(w_{kr\omega}\) | Nonnegative continuous | Absolute deviation from nominal flow |

### Objective

Minimize the scenario-weighted sum of transportation, route activation, nominal-plan deviation, delay, emergency-inventory, shortage, security-risk, and emissions costs:

\[
\min \sum_{\omega\in\Omega}\pi_\omega\left[
\sum_{k,r}c_r x_{kr\omega}
+\sum_r f_r y_{r\omega}
+\sum_{k,r}\eta w_{kr\omega}
+\sum_{k,r}\lambda \ell_r x_{kr\omega}
+\sum_k g z_{k\omega}
+\sum_k\mu_k s_{k\omega}
+\gamma\sum_{k,r}\rho_{r\omega}x_{kr\omega}
+\phi\sum_{k,r}e_r x_{kr\omega}
\right].
\]

The prototype’s cost coefficients \(\eta,\lambda,g,\gamma,\phi\) and route attributes are illustrative. Lower cost is not the only goal: the model also has a hard risk-budget constraint.

### Constraints

Demand balance:
\[
\sum_{r}x_{kr\omega}+z_{k\omega}+s_{k\omega}=q_k
\quad\forall k,\omega.
\]

Inventory availability:
\[
z_{k\omega}\le I_k\quad\forall k,\omega.
\]

Route capacity and availability:
\[
\sum_k x_{kr\omega}\le U_{r\omega}y_{r\omega},\qquad
y_{r\omega}\le a_{r\omega}\quad\forall r,\omega.
\]

Route-use linking and limited shipment splitting:
\[
x_{kr\omega}\le q_k u_{kr\omega},\qquad
u_{kr\omega}\le y_{r\omega},\qquad
\sum_r u_{kr\omega}\le L_k\quad\forall k,\omega.
\]

Port capacity:
\[
\sum_{k,r}\beta_{rp}x_{kr\omega}\le B_{p\omega}
\quad\forall p,\omega,
\]
where \(\beta_{rp}=1\) when route \(r\) uses port \(p\).

Nominal-plan deviation:
\[
w_{kr\omega}\ge x_{kr\omega}-\bar{x}_{kr},\qquad
w_{kr\omega}\ge \bar{x}_{kr}-x_{kr\omega}
\quad\forall k,r,\omega.
\]

Security-risk budget:
\[
\sum_{k,r}\rho_{r\omega}x_{kr\omega}\le R^{max}_\omega
\quad\forall\omega.
\]

Domains: \(x,z,s,w\ge0\), \(u,y\in\{0,1\}\). The prototype uses a tight flow bound \(q_k\) in the route-use linking constraint. The passive comparator restricts choices to the direct route and does not enforce the risk-budget constraint; it is a benchmark, not a feasible optimized policy.

### Prototype architecture

`src/camlrp/data.py` stores transparent synthetic inputs. `src/camlrp/model.py` builds and solves the MILP with SciPy’s HiGHS-backed `milp` solver and calculates KPIs. `app.py` provides Streamlit controls, optimization runs, charts, and policy comparisons. No external data connection is required.

### Illustrative implementation results

The following are reproducible outputs for the prototype's default synthetic inputs—not results reported by R1 and not measured maritime data.

| Scenario | Optimized transported | Inventory | Shortage | Risk exposure / budget | Passive-policy shortage |
|---|---:|---:|---:|---:|---:|
| Normal operations | 270 | 0 | 0 | 21.60 / 100 | 0 |
| Severe disruption | 220 | 43 | 7 | 65.00 / 65 | 147 |
| Partial recovery | 227 | 43 | 0 | 58.66 / 90 | 77 |

In the severe case, the optimized plan reduces shortage by 140 illustrative units compared with the passive plan, while remaining within the risk budget. The passive plan has risk exposure of 80 against a limit of 65. The normal case keeps all 270 units on the nominal corridor. These outputs demonstrate the intended trade-off; their magnitudes have no real-world interpretation.

## 4. Testing plan and sample test cases

### Test approach

Use automated model tests for demand accounting, risk-budget feasibility, input validation, and scenario behavior. Then run the app manually: change each control, verify the selected scenario and comparison update, inspect the demand-level table, and confirm the synthetic-data warning remains visible. Recheck all scenarios before presenting.

| ID | Sample input | Expected result |
|---|---|---|
| TC-01 Normal feasibility | Demand 100/70/60/40; direct capacity 270; risk budget 100 | Solver returns an optimal plan; all demand is accounted for; shortage is zero; risk stays within budget. |
| TC-02 Severe reconfiguration | Same demand; direct/alternative/substitute route capacities 80/120/70; port capacities 150/70; risk budget 65 | Optimized plan respects the risk limit and has less shortage than the direct-only passive comparator. |
| TC-03 Inventory disabled | Severe scenario; inventory multiplier 0 | All cargo classes show zero inventory use; remaining demand is routed or reported as shortage. |
| TC-04 Demand increase | Any scenario; demand multiplier 1.2 | Total demand rises to 324 units; each unit is routed, covered by inventory, or shown as shortage. |
| TC-05 Tight risk tolerance | Severe scenario; risk-budget multiplier 0.5 | Risk exposure is at most 32.5 index units; outputs remain feasible with any necessary shortage reported. |
| TC-06 Increased direct capacity | Severe scenario; direct-capacity multiplier 1.2 | Direct-route capacity increases by 20%; the optimization still respects all route and port capacities and the risk budget. |
| TC-07 Passive-policy comparison | Severe scenario; direct-only policy; no risk-budget enforcement | Comparator shows direct-only flows, inventory/shortage balance, and its risk-budget-use percentage; any violation is explicitly called out. |
| TC-08 Zero risk budget | Any scenario; risk-budget multiplier 0 | No positive-risk route flow is allowed; demand is assigned to inventory or shortage. |
| TC-09 Invalid input | Unknown scenario or negative multiplier | The model rejects the input with a clear validation error. |
| TC-10 Scenario aggregation | Default scenario weights 0.35/0.35/0.30 | Displayed expected cost equals the weighted sum of the three separately optimized scenario costs. |

## 5. Assumptions, limitations, and responsible use

All numerical inputs are synthetic teaching data. The route labels describe abstract options and do not establish that a specific route or port can serve each cargo class. Risk values are not threat intelligence; emissions and delay values are indices, not measured quantities. The app does not fetch current shipping data. Real use would require validated routes, commodity compatibility, capacity and cost data, security expertise, and current authorized sources.

The model is aggregate and single-period. It omits individual vessels, transit-time scheduling, contractual commitments, port queues, and time-dependent inventory. It treats scenarios as externally assessed and does not optimize pre-disruption preparedness. Results should be interpreted as a demonstration of trade-offs, not as advice for real maritime operations.

## References

Lassoued, R. (2026). Chokepoint-aware maritime logistics reconfiguration under security disruptions: a scenario-based mixed-integer optimization framework. *Journal of Transportation Security, 19*, 35. https://doi.org/10.1007/s12198-026-00357-8
