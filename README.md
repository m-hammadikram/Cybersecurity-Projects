# 🛡️ SOC Alert Fatigue Reduction Engine

A SOC analyst portfolio project that tackles a real, day-to-day pain point in
Security Operations Centers: **alert fatigue**. Analysts routinely face
hundreds to thousands of alerts per day, most of them false positives or
duplicates — which causes real incidents to get buried in noise.

This project simulates a realistic SIEM alert stream, then applies:

1. **A transparent risk-scoring model** — ranks alerts 0–100 based on
   severity, asset criticality, source reputation (chronic false-positive
   sources get down-weighted), and time-of-day anomaly.
2. **A correlation engine** — groups related raw alerts (same source IP +
   user, within a rolling time window) into a single incident, the way a
   real SOAR platform or Splunk correlation search would.
3. **An interactive Streamlit dashboard** — shows the before/after impact:
   raw alert volume vs. correlated, prioritized incidents an analyst
   actually needs to review.

## Why this project

Most SOC portfolio projects stop at "I stood up a SIEM." This one goes a
step further and demonstrates the actual analytical thinking a SOC
analyst (and detection engineer) is paid for: reducing noise, prioritizing
signal, and explaining *why* an alert matters.

## Live demo

Deploy this yourself on [Streamlit Community Cloud](https://share.streamlit.io)
by pointing it at `app.py` in this repo — free hosting, takes about 2 minutes.

## Project structure

```
alert-fatigue-reduction/
├── app.py                # Streamlit dashboard (entry point)
├── generate_data.py      # Synthetic SIEM alert generator
├── scoring_engine.py      # Risk scoring logic
├── correlation.py         # Alert -> incident correlation logic
├── requirements.txt
├── data/                  # Generated CSVs land here (gitignored by default)
└── README.md
```

## Run it locally

```bash
git clone https://github.com/<your-username>/alert-fatigue-reduction.git
cd alert-fatigue-reduction
pip install -r requirements.txt
streamlit run app.py
```

Or run the pipeline standalone from the command line:

```bash
python generate_data.py --days 7 --alerts-per-day 400
python scoring_engine.py
python correlation.py
```

## How the scoring works

Each alert gets a `risk_score` (0-100) from a weighted, fully explainable
formula (see `scoring_engine.py`):

| Factor | Weight | Notes |
|---|---|---|
| Alert severity (low/med/high/critical) | 45% | Base signal strength |
| Asset criticality (1-5) | 25% | A failed login on a dev laptop ≠ failed login on the domain controller |
| Time-of-day anomaly | 10% | Off-hours / weekend activity scores higher |
| Chronic noise source penalty | multiplicative | Sources with a known high false-positive history get dampened |

Weights are intentionally simple and interpretable rather than a black-box
ML model — in real SOC environments, analysts and auditors need to be able
to explain why an alert was prioritized (or suppressed).

## How correlation works

Alerts sharing the same `src_ip` and `user`, occurring within a configurable
time window (default 20 minutes), are grouped into a single **incident**.
This collapses multi-stage attack chains (e.g. port scan → brute force →
privilege escalation → beaconing) from 5+ separate alerts into one incident
an analyst reviews holistically — instead of 5 disconnected tickets.

## Example impact (synthetic data, 7 days / ~400 alerts/day)

```
Raw alerts:            ~2,500
Correlated incidents:  ~1,080
Volume reduction:      ~57%
```

Note that raw *volume* reduction is only half the story — the bigger win is
that the queue is now **ranked by risk score**. Filtering the triage queue
to Medium/High priority only typically leaves an analyst with a much smaller,
high-signal list to work through first.

*(Exact numbers vary by simulation seed — the dashboard shows live figures
for whatever data you generate or upload.)*

## Extending this project

Ideas for taking it further (good talking points for interviews):

- Swap the synthetic generator for a real dataset (CICIDS2017, NSL-KDD) or
  live Suricata/Zeek logs
- Feed `incidents.csv` into a MISP instance to enrich with real threat intel
- Replace the weighted scoring model with a trained classifier and compare
  precision/recall against the rule-based baseline
- Add a feedback loop where analysts mark incidents as true/false positive,
  and use that to auto-tune the chronic-noise-source list

## Disclaimer

This is a portfolio/learning project using entirely synthetic data. It is
not a production detection system, and scoring weights should be tuned
against real environment telemetry before any operational use.
