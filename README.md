# Optimizing Maritime Cargo Routes for Resilience under Strategic Chokepoint Disruptions

An educational, interactive demonstration of the Chokepoint-Aware Maritime
Logistics Reconfiguration Problem (CAMLRP) described in R1. The app solves a
small mixed-integer linear program (MILP) for normal, severe-disruption, and
partial-recovery scenarios.

> **Important:** This prototype uses synthetic, illustrative values. It is not
> connected to live vessel, port, insurance, or security data and is not an
> operational routing recommendation.

## Run locally

Requires Python 3.10 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Changing the scenario or any what-if control immediately reruns the optimization.
No live external data feed is required. If a data integration is added later, it
must be sourced, timestamped, and clearly distinguished from illustrative values.
Run the model checks with `python -m pytest`.

## Host on Streamlit Community Cloud

The app is prepared for Streamlit Community Cloud. Push the project source,
`pyproject.toml`, and `requirements.txt` to a GitHub repository, create a new
app at [share.streamlit.io](https://share.streamlit.io/), and select `app.py`
as the entry point. The deployment installs the local `camlrp` package from
`pyproject.toml` through the `-e .` entry in `requirements.txt`. Add the
resulting app URL to the report's prototype field. Do not upload secrets or
unnecessary source PDFs with the app.

## Project files

- `app.py` — Streamlit prototype and visualizations.
- `src/camlrp/data.py` — scenario, route, and cargo inputs.
- `src/camlrp/model.py` — MILP and passive nominal-policy comparator.
- `tests/test_model.py` — model behavior and constraint tests.
- `docs/final_report.md` — Notion-ready project report.
- `docs/presentation_walkthrough.md` — presentation guide and demo sequence.

## Model outline

For each observed disruption scenario, the MILP chooses cargo flow by route,
route activation, emergency inventory, and unmet demand. It minimizes
transportation, activation, nominal-plan deviation, delay, inventory, shortage,
security-risk, and emissions costs. Constraints enforce demand balance, route
availability and capacity, port capacity, a route-splitting limit, and the
scenario's security-risk budget. The scenarios are solved independently; this
is a scenario-conditioned recourse evaluation, not a full two-stage stochastic
program.

For a complete explanation of assumptions, notation, requirements, and tests,
see `docs/final_report.md`.
