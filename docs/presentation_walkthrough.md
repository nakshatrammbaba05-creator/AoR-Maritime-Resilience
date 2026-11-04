# Presentation walkthrough

**Project:** Optimizing Maritime Cargo Routes for Resilience under Strategic Chokepoint Disruptions<br>
**Recommended duration:** 8 minutes for the presentation and prototype, 5 minutes for Q&A, and 2 minutes of buffer in the 15-minute slot.

## 1. Business problem — 2 minutes

“Our project studies how a maritime logistics planner can reconfigure an existing cargo plan when a strategic chokepoint becomes risky or capacity-constrained. Keeping cargo on the nominal route can lead to shortage or excess risk. We model choices among the nominal corridor, abstract alternative routes, substitute-port/multimodal options, emergency inventory, and shortage.”

Emphasize that the project is a tactical decision-support demonstration, not conflict prediction or vessel navigation.

## 2. Model — 2 minutes

“We use a small scenario-conditioned MILP. It allocates each cargo class to routes, inventory, or shortage. The objective combines transport and activation costs, deviation from the nominal plan, delay, inventory, shortage, risk exposure, and emissions. Constraints enforce demand balance, route and port capacities, availability, route splitting, and a scenario-specific risk budget.”

Explain the trade-off: avoiding a risky route can require longer or more expensive alternatives; the model shows this alongside any shortage and emissions impact. The three scenario solves are independent, and scenario weights are used to calculate expected cost.

## 3. Testing plan — 2 minutes

Show the small normal case and severe case. Explain that tests check demand accounting, capacity and risk limits, input handling, and whether reconfiguration reduces shortage versus the passive direct-only policy. Mention that all sample inputs are illustrative, not measured shipping data.

## 4. Prototype demonstration — 2 minutes

1. Open the Streamlit app and point out the synthetic-data notice.
2. Select **Severe disruption** and show allocations, shortage, risk-budget use, and the passive-policy comparison.
3. Tighten security risk tolerance and let the app rerun the model.
4. Increase emergency inventory or direct capacity and explain how the allocation/KPIs change.
5. Show the all-scenario comparison and cost breakdown.

## 5. Closing

“The main insight is that resilience is not just keeping the original route open. It is having feasible alternatives and explicitly balancing service, cost, security exposure, and emissions. Our prototype makes those scenario trade-offs visible, while the synthetic-data caveat keeps the conclusions within the evidence.”

## Likely questions

- **Are these actual Hormuz cargo volumes?** No. They are synthetic demonstration units.
- **Does the app use live vessel/security data?** No; live data is not required for this prototype. The scenario and inputs are user-controlled.
- **Does it predict disruptions?** No. It optimizes a response after a scenario is selected.
- **Is it a full two-stage stochastic program?** No. It solves each assessed scenario independently and aggregates the costs using scenario weights.
- **Why allow shortages?** To keep severe cases feasible and make the service-versus-cost trade-off explicit; shortage receives a large penalty.
