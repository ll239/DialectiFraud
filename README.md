# DialectiFraud

A credit card fraud triage tool that applies Hegelian dialectical reasoning — thesis, antithesis, synthesis — to flagged transactions before rendering a final risk decision.

Instead of a single model call producing one verdict, each transaction goes through three roles:

1. **Thesis** — a fraud analyst argues why the transaction is suspicious (3-4 specific reasons)
2. **Antithesis** — a customer advocate argues why it's a false positive (3-4 specific reasons)
3. **Synthesis** — a senior risk officer weighs both arguments and issues a final call: risk tier (HIGH/MEDIUM/LOW), confidence %, false-positive likelihood %, and a one-line recommended action

## Two modes

**Single Transaction** — paste a free-text description of one flagged transaction and see the three-panel breakdown live.

**Batch Analysis (CSV)** — upload a transaction CSV. A simple rule-based baseline flagger (mimicking a legacy fraud system) flags transactions that trip 2+ weak signals (large amount, odd hour, long gap since last activity, distance from home). A sample of the flagged transactions is then re-analyzed through the dialectical engine. If you map a ground-truth fraud label column, you get a measured false-positive-reduction number: how many of the baseline's false alarms the dialectical re-score correctly cleared, and how much real fraud it still caught.

## Architecture

Thesis and antithesis both read the identical transaction description independently — neither sees the other's argument until synthesis weighs both. In batch mode, the same pipeline runs on a sample of transactions a rule-based baseline flagger caught, and results are scored against a ground-truth label to produce a measured false-positive-reduction figure.

```mermaid
flowchart TD
    A1["Single Transaction<br/>free-text description"] --> TD["Transaction Description"]
    A2["Batch CSV Upload<br/>column mapping → baseline flagger<br/>(2+ weak signals)"] --> TD

    TD --> TH["THESIS<br/>Fraud Analyst agent<br/>Claude Sonnet 5"]
    TD --> AN["ANTITHESIS<br/>Customer Advocate agent<br/>Claude Sonnet 5"]

    TH --> SY["SYNTHESIS<br/>Senior Risk Officer agent<br/>Claude Sonnet 5"]
    AN --> SY

    SY --> RT["Risk Tier"]
    SY --> CF["Confidence %"]
    SY --> FP["FP Likelihood %"]
    SY --> AC["Recommended Action"]

    RT -.batch mode, vs. ground truth.-> GT["Aggregate Metrics<br/>FP cleared / fraud caught / fraud missed"]

    classDef thesis fill:#3a1414,stroke:#dc2626,color:#f5c2c2
    classDef antithesis fill:#12301c,stroke:#16a34a,color:#bdeecb
    classDef synthesis fill:#0f1f3d,stroke:#2563eb,color:#bcd2fb

    class TH thesis
    class AN antithesis
    class SY synthesis
```

A more detailed interactive version is [here](https://claude.ai/code/artifact/f1d16992-1887-443e-8a4d-8c355863e658).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/streamlit run app.py
```

Enter your Anthropic API key in the sidebar (or set the `ANTHROPIC_API_KEY` environment variable before launching). The key is never stored — it's only held in the Streamlit session.

## Model

Uses `claude-sonnet-5` via the Anthropic API.

## Batch mode CSV format

No fixed schema is required — after upload you map your own columns to: amount (required), merchant, category, timestamp, cardholder ID, latitude/longitude pairs (customer + merchant, optional, used for distance-based risk signals), and a ground-truth fraud label (optional, unlocks the measured accuracy metrics). Column names are auto-guessed from common naming conventions and can be corrected in the UI.

---

*Dialectical reasoning approach informed by Microsoft Research's Hegelian Dialectic framework (ICML 2025), applied here to fraud triage rather than the paper's original math/science reasoning domain.*
