import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
from google.cloud import bigquery

PROJECT_ID = "gold-north-america"
DATASET    = "gold_north_america"
TABLE      = "predictions_knockout"

# API names → fixture names (for strength lookup)
API_TO_FIXTURE = {
    'Czechia':             'Czech Republic',
    'Bosnia-Herzegovina':  'Bosnia and Herzegovina',
    'Cape Verde Islands':  'Cape Verde',
    'Congo DR':            'DR Congo',
}

def get_client():
    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    return bigquery.Client.from_service_account_json(key_path, project=PROJECT_ID)

def get_team_strength(fixtures_df, api_name):
    name = API_TO_FIXTURE.get(api_name, api_name)
    home_row = fixtures_df[fixtures_df['home_team'] == name]
    away_row = fixtures_df[fixtures_df['away_team'] == name]
    if not home_row.empty:
        return (float(home_row.iloc[0]['home_attack']),
                float(home_row.iloc[0]['home_defence']),
                float(home_row.iloc[0]['home_squad_multiplier']))
    elif not away_row.empty:
        return (float(away_row.iloc[0]['away_attack']),
                float(away_row.iloc[0]['away_defence']),
                float(away_row.iloc[0]['away_squad_multiplier']))
    else:
        print(f"  WARNING: no strength data for '{api_name}' (mapped: '{name}') — using global avg")
        avg = float(fixtures_df['lambda_home'].mean())
        return (avg, 1.0, 1.0)

def predict_match(lambda_home, lambda_away, max_goals=10):
    home_probs = [poisson.pmf(i, lambda_home) for i in range(max_goals + 1)]
    away_probs = [poisson.pmf(i, lambda_away) for i in range(max_goals + 1)]
    matrix = np.outer(home_probs, away_probs)
    prob_home_win = float(np.sum(np.tril(matrix, -1)))
    prob_away_win = float(np.sum(np.triu(matrix, 1)))
    prob_draw     = float(np.sum(np.diag(matrix)))
    idx = np.unravel_index(matrix.argmax(), matrix.shape)
    return {
        'prob_home_win':     round(prob_home_win, 4),
        'prob_draw':         round(prob_draw, 4),
        'prob_away_win':     round(prob_away_win, 4),
        'most_likely_score': f"{idx[0]}-{idx[1]}"
    }

def main():
    client = get_client()

    fixtures_df = client.query("""
        SELECT * FROM `gold-north-america.gold_north_america.mart_group_fixtures_enriched`
    """).to_dataframe()
    global_avg = float(fixtures_df['lambda_home'].mean())

    knockout_df = client.query("""
        SELECT date, home_team, away_team, stage, group_name
        FROM `gold-north-america.gold_north_america.actual_results`
        WHERE stage != 'GROUP_STAGE'
        ORDER BY date
    """).to_dataframe()

    if knockout_df.empty:
        print("No knockout matches found.")
        return

    print(f"Found {len(knockout_df)} knockout matches. Generating predictions...")
    rows = []
    knockout_df = knockout_df[knockout_df['home_team'].notna() & knockout_df['away_team'].notna()]
    print(f"After filtering nulls: {len(knockout_df)} matches to predict")
    for _, match in knockout_df.iterrows():
        home, away = match['home_team'], match['away_team']
        ha, hd, hm = get_team_strength(fixtures_df, home)
        aa, ad, am = get_team_strength(fixtures_df, away)
        lambda_home = round(ha * ad * global_avg * hm, 4)
        lambda_away = round(aa * hd * global_avg * am, 4)
        pred = predict_match(lambda_home, lambda_away)
        stage_label = match['stage'].replace('_', ' ').title()
        rows.append({
            'date':            str(match['date']),
            'group':           stage_label,
            'home_team':       home,
            'away_team':       away,
            'lambda_home':     lambda_home,
            'lambda_away':     lambda_away,
            'prob_home_win':   pred['prob_home_win'],
            'prob_draw':       pred['prob_draw'],
            'prob_away_win':   pred['prob_away_win'],
            'most_likely_score': pred['most_likely_score']
        })
        print(f"  {home} vs {away} | λH={lambda_home} λA={lambda_away} | "
              f"H:{pred['prob_home_win']:.1%} D:{pred['prob_draw']:.1%} A:{pred['prob_away_win']:.1%}")

    df = pd.DataFrame(rows)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    client.load_table_from_dataframe(df, f"{PROJECT_ID}.{DATASET}.{TABLE}", job_config=job_config).result()
    print(f"\nDone. {len(df)} knockout predictions written to BigQuery.")

if __name__ == "__main__":
    main()
