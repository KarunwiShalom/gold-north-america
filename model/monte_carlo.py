import os
import json
import numpy as np
import pandas as pd
from scipy.stats import poisson
from google.cloud import bigquery
from google.oauth2 import service_account
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# ── Connect to BigQuery ───────────────────────────────────────────────────────
def get_client():
    try:
        import streamlit as st
        if "GCP_CREDENTIALS" in st.secrets:
            credentials_info = json.loads(st.secrets["GCP_CREDENTIALS"])
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info
            )
            return bigquery.Client(
                credentials=credentials,
                project="gold-north-america"
            )
    except Exception:
        pass
    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    return bigquery.Client.from_service_account_json(
        key_path, project="gold-north-america"
    )

# ── Load fixtures ─────────────────────────────────────────────────────────────
def load_fixtures():
    client = get_client()
    query = """
        SELECT *
        FROM `gold-north-america.gold_north_america.mart_group_fixtures_enriched`
        ORDER BY date, group_name
    """
    return client.query(query).to_dataframe()


# ── Simulate a single match ───────────────────────────────────────────────────
def simulate_match(lambda_home, lambda_away):
    """Sample a scoreline from Poisson distributions."""
    home_goals = np.random.poisson(lambda_home)
    away_goals = np.random.poisson(lambda_away)
    return home_goals, away_goals

# ── Simulate a single match with penalty shootout ────────────────────────────
def simulate_match_knockout(lambda_home, lambda_away):
    home_goals, away_goals = simulate_match(lambda_home, lambda_away)
    if home_goals > away_goals:
        return "home"
    elif away_goals > home_goals:
        return "away"
    else:
        return "home" if np.random.random() < 0.5 else "away"

# ── Simulate group stage ──────────────────────────────────────────────────────
def simulate_group_stage(fixtures_df):
    standings = defaultdict(lambda: {
        'points': 0, 'gd': 0, 'gf': 0, 'group': ''
    })
    for _, row in fixtures_df.iterrows():
        home = row['home_team']
        away = row['away_team']
        group = row['group_name']
        standings[home]['group'] = group
        standings[away]['group'] = group
        hg, ag = simulate_match(row['lambda_home'], row['lambda_away'])
        standings[home]['gf'] += hg
        standings[away]['gf'] += ag
        standings[home]['gd'] += hg - ag
        standings[away]['gd'] += ag - hg
        if hg > ag:
            standings[home]['points'] += 3
        elif ag > hg:
            standings[away]['points'] += 3
        else:
            standings[home]['points'] += 1
            standings[away]['points'] += 1
    return standings

# ── Get group standings ───────────────────────────────────────────────────────
def get_group_standings(standings):
    groups = defaultdict(list)
    for team, stats in standings.items():
        groups[stats['group']].append((team, stats))
    sorted_groups = {}
    for group, teams in groups.items():
        sorted_teams = sorted(
            teams,
            key=lambda x: (x[1]['points'], x[1]['gd'], x[1]['gf']),
            reverse=True
        )
        sorted_groups[group] = [t[0] for t in sorted_teams]
    return sorted_groups

# ── Get best third place teams ────────────────────────────────────────────────
def get_best_third_place(standings, group_standings):
    third_place_teams = []
    for group, teams in group_standings.items():
        if len(teams) >= 3:
            third_team = teams[2]
            stats = standings[third_team]
            third_place_teams.append((third_team, stats, group))
    third_place_teams.sort(
        key=lambda x: (x[1]['points'], x[1]['gd'], x[1]['gf']),
        reverse=True
    )
    return [t[0] for t in third_place_teams[:8]]

# ── Build Round of 32 bracket ─────────────────────────────────────────────────
def build_r32_bracket(group_standings, best_third):
    g = group_standings
    def get(group, pos):
        teams = g.get(group, [])
        return teams[pos] if len(teams) > pos else "TBD"
    bracket = [
        (get('E', 0), best_third[0]),
        (get('I', 0), best_third[1]),
        (get('A', 0), get('B', 1)),
        (get('F', 0), get('C', 1)),
        (get('K', 1), get('L', 1)),
        (get('H', 0), best_third[2]),
        (get('D', 0), best_third[3]),
        (get('G', 0), get('J', 1)),
        (get('C', 0), get('G', 1)),
        (get('B', 0), get('A', 1)),
        (get('J', 0), best_third[4]),
        (get('K', 0), best_third[5]),
        (get('L', 0), best_third[6]),
        (get('C', 0), get('D', 1)),
        (get('E', 1), get('I', 1)),
        (get('F', 1), get('H', 1)),
    ]
    return bracket

# ── Simulate knockout round ───────────────────────────────────────────────────
def simulate_knockout_round(bracket, team_lambdas):
    winners = []
    for home, away in bracket:
        if home == "TBD" or away == "TBD":
            winners.append(home if away == "TBD" else away)
            continue
        lh = team_lambdas.get(home, {}).get('attack', 1.0)
        la = team_lambdas.get(away, {}).get('attack', 1.0)
        hd = team_lambdas.get(home, {}).get('defence', 1.0)
        ad = team_lambdas.get(away, {}).get('defence', 1.0)
        baseline = 1.1
        lh_adj = lh * ad * baseline
        la_adj = la * hd * baseline
        result = simulate_match_knockout(lh_adj, la_adj)
        winners.append(home if result == "home" else away)
    return winners

# ── Build team lambda lookup ──────────────────────────────────────────────────
def build_team_lambdas(fixtures_df):
    team_lambdas = {}
    for _, row in fixtures_df.iterrows():
        team_lambdas[row['home_team']] = {
            'attack':  row['home_attack'],
            'defence': row['home_defence']
        }
        team_lambdas[row['away_team']] = {
            'attack':  row['away_attack'],
            'defence': row['away_defence']
        }
    return team_lambdas

# ── Full tournament simulation ────────────────────────────────────────────────
def simulate_tournament(fixtures_df, team_lambdas):
    standings = simulate_group_stage(fixtures_df)
    group_standings = get_group_standings(standings)
    best_third = get_best_third_place(standings, group_standings)
    r32_bracket = build_r32_bracket(group_standings, best_third)
    r16_teams = simulate_knockout_round(r32_bracket, team_lambdas)
    r16_bracket = list(zip(r16_teams[0::2], r16_teams[1::2]))
    qf_teams = simulate_knockout_round(r16_bracket, team_lambdas)
    qf_bracket = list(zip(qf_teams[0::2], qf_teams[1::2]))
    sf_teams = simulate_knockout_round(qf_bracket, team_lambdas)
    sf_bracket = list(zip(sf_teams[0::2], sf_teams[1::2]))
    finalists = simulate_knockout_round(sf_bracket, team_lambdas)
    final_bracket = [tuple(finalists)]
    champion = simulate_knockout_round(final_bracket, team_lambdas)
    return {
        'winner':    champion[0],
        'finalists': set(finalists),
        'semi':      set(sf_teams),
        'quarters':  set(qf_teams),
        'r16':       set(r16_teams),
    }

# ── Monte Carlo ───────────────────────────────────────────────────────────────
def run_monte_carlo(fixtures_df, n=10000):
    team_lambdas = build_team_lambdas(fixtures_df)
    win_count      = defaultdict(int)
    final_count    = defaultdict(int)
    semi_count     = defaultdict(int)
    quarter_count  = defaultdict(int)
    r16_count      = defaultdict(int)
    print(f"Running {n:,} simulations...")
    for i in range(n):
        if (i + 1) % 1000 == 0:
            print(f"  {i+1:,} / {n:,} complete")
        result = simulate_tournament(fixtures_df, team_lambdas)
        win_count[result['winner']] += 1
        for t in result['finalists']:  final_count[t]   += 1
        for t in result['semi']:       semi_count[t]    += 1
        for t in result['quarters']:   quarter_count[t] += 1
        for t in result['r16']:        r16_count[t]     += 1
    all_teams = list(team_lambdas.keys())
    rows = []
    for team in sorted(all_teams):
        rows.append({
            'team':        team,
            'win_pct':     round(win_count[team] / n * 100, 2),
            'final_pct':   round(final_count[team] / n * 100, 2),
            'semi_pct':    round(semi_count[team] / n * 100, 2),
            'quarter_pct': round(quarter_count[team] / n * 100, 2),
            'r16_pct':     round(r16_count[team] / n * 100, 2),
        })
    df = pd.DataFrame(rows).sort_values('win_pct', ascending=False).reset_index(drop=True)
    df.index += 1
    return df

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Loading fixtures...")
    fixtures = load_fixtures()
    print(f"Loaded {len(fixtures)} fixtures")
    results = run_monte_carlo(fixtures, n=10000)
    print("\n🏆 Tournament Win Probabilities (10,000 simulations)")
    print("=" * 70)
    print(results[['team', 'win_pct', 'final_pct', 'semi_pct',
                   'quarter_pct', 'r16_pct']].to_string())
    results.to_csv("data/monte_carlo_results.csv", index=False)
    print(f"\nSaved to data/monte_carlo_results.csv")
