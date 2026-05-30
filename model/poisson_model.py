import os
import numpy as np
import pandas as pd
from scipy.stats import poisson
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

# ── Connect to BigQuery ───────────────────────────────────────────────────────
key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
client = bigquery.Client.from_service_account_json(key_path, project="gold-north-america")

# ── Load enriched fixtures from mart ─────────────────────────────────────────
def load_fixtures():
    query = """
        SELECT *
        FROM `gold-north-america.gold_north_america.mart_group_fixtures_enriched`
        ORDER BY date, group_name
    """
    df = client.query(query).to_dataframe()
    print(f"Loaded {len(df)} fixtures")
    return df


# ── Poisson match prediction ──────────────────────────────────────────────────
def predict_match(lambda_home, lambda_away, max_goals=10):
    """
    Given lambda values for both teams, return:
    - prob_home_win
    - prob_draw
    - prob_away_win
    - most likely scoreline
    - full scoreline probability matrix
    """
    # Build scoreline probability matrix
    # Each cell = P(home scores i) * P(away scores j)
    home_probs = [poisson.pmf(i, lambda_home) for i in range(max_goals + 1)]
    away_probs = [poisson.pmf(i, lambda_away) for i in range(max_goals + 1)]
    matrix = np.outer(home_probs, away_probs)

    # Win/draw/loss probabilities
    prob_home_win = float(np.sum(np.tril(matrix, -1)))  # home > away
    prob_away_win = float(np.sum(np.triu(matrix, 1)))   # away > home
    prob_draw     = float(np.sum(np.diag(matrix)))      # home == away

    # Most likely scoreline
    idx = np.unravel_index(matrix.argmax(), matrix.shape)
    most_likely_score = f"{idx[0]}-{idx[1]}"

    return {
        "prob_home_win":     round(prob_home_win, 4),
        "prob_draw":         round(prob_draw, 4),
        "prob_away_win":     round(prob_away_win, 4),
        "most_likely_score": most_likely_score,
        "matrix":            matrix
    }


# ── Predict all group stage fixtures ─────────────────────────────────────────
def predict_all_fixtures(df):
    results = []
    for _, row in df.iterrows():
        pred = predict_match(row["lambda_home"], row["lambda_away"])
        results.append({
            "date":             row["date"],
            "group":            row["group_name"],
            "home_team":        row["home_team"],
            "away_team":        row["away_team"],
            "lambda_home":      row["lambda_home"],
            "lambda_away":      row["lambda_away"],
            "prob_home_win":    pred["prob_home_win"],
            "prob_draw":        pred["prob_draw"],
            "prob_away_win":    pred["prob_away_win"],
            "most_likely_score":pred["most_likely_score"],
        })
    return pd.DataFrame(results)


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fixtures = load_fixtures()
    predictions = predict_all_fixtures(fixtures)

    print("\nSample predictions:")
    print(predictions[["home_team", "away_team", "lambda_home",
                        "lambda_away", "prob_home_win", "prob_draw",
                        "prob_away_win", "most_likely_score"]].head(10).to_string())

    # Save to CSV for inspection
    predictions.to_csv("data/predictions_group_stage.csv", index=False)
    print(f"\nSaved {len(predictions)} predictions to data/predictions_group_stage.csv")