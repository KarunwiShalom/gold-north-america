# Gold in North America
**2026 FIFA World Cup Prediction Model**

A tournament simulation model built on historical match data, FIFA rankings, 
and squad quality scores. Uses a Poisson distribution to estimate scoreline 
probabilities and Monte Carlo simulation (10,000 runs) to produce win 
probabilities for all 48 teams.

Built with Python · dbt · BigQuery · Streamlit

---

## Method

### Team Strength Ratings
Each team's attack and defence ratings are derived from weighted historical 
results since 2016. Weights favour recent matches and higher-stakes competitions 
(World Cup matches weighted 4×, friendlies 1×). Ratings are normalised so that 
1.0 represents a league-average team.

For teams with limited international history, ratings are blended with a 
FIFA-points-derived rating using a `history_trust` score (capped at 1.0 after 
300 matches). This prevents inflated ratings from teams with strong records 
against weak regional opposition.

### Match Simulation
Expected goals (λ) for each fixture are calculated as:

1. λ_home = home_attack × away_defence × avg_attack × home_squad_multiplier

2. λ_away = away_attack × home_defence × avg_attack × away_squad_multiplier

Scoreline probabilities are drawn from a Poisson distribution. Win/draw/loss 
probabilities are derived from the full scoreline matrix.

### Tournament Simulation
The full 48-team tournament is simulated 10,000 times. Group stage standings 
follow FIFA tiebreaker rules. The Round of 32 bracket uses the official FIFA 
2026 group-to-slot mapping. Knockout draws are settled by Poisson sampling; 
penalty shootouts are modelled as 50/50.

---

## Data Sources

| File | Source | Version / Date |
|------|--------|---------------|
| `results.csv` | [Kaggle: martj42/international-football-results](https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017) | Downloaded May 2026 |
| `goalscorers.csv` | Same dataset | Downloaded May 2026 |
| `shootouts.csv` | Same dataset | Downloaded May 2026 |
| `former_names.csv` | Same dataset | Downloaded May 2026 |
| `fifa_rankings.csv` | Scraped from Sofascore via Selenium (`scripts/scrape_fifa_rankings.py`) | April 1 2026 snapshot |
| `fifa_wc2026_dataset.csv` | [Kaggle: sabujmodak/fifa-wc-2026-real-data-model](https://www.kaggle.com/datasets/sabujmodak/fifa-wc-2026-real-data-model-jan-19-2026) | January 2026 |

Raw data files are not stored in this repository. To reproduce:
1. Download the Kaggle datasets linked above
2. Run `scripts/scrape_fifa_rankings.py` to regenerate FIFA rankings
3. Place all files in `data/raw/`

---

## Setup

### Prerequisites
- Python 3.11
- GCP project with BigQuery enabled
- dbt-bigquery
- A service account key with BigQuery Admin role

### Installation

```bash
git clone https://github.com/KarunwiShalom/gold-north-america.git
cd gold-north-america
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Credentials
Create a `.secrets/` folder and add your GCP service account key as `gcp_key.json`. Then:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=".secrets/gcp_key.json"
```

### Run the pipeline

```bash
# Load raw data to BigQuery
python ingestion/load_to_bq.py

# Run dbt models
cd dbt_project && dbt run && cd ..

# Generate predictions
python model/poisson_model.py
python model/monte_carlo.py

# Launch app
streamlit run app/streamlit_app.py
```

---

## Known Limitations

- No home advantage adjustment (tournament hosted across USA, Canada, Mexico)
- Penalty shootouts modelled as 50/50 — no historical shootout data incorporated
- Squad quality scores sourced from January 2026; pre-tournament roster changes not reflected
- FIFA rankings snapshot from April 1 2026

---

## Author
Shalom Karunwi · May 2026
