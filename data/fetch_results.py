import os
import json
import requests
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime

API_KEY = "189d4fe402ae4b25be9b5770c8d9f3a4"
API_URL = "https://api.football-data.org/v4/competitions/WC/matches?season=2026"
PROJECT_ID = "gold-north-america"
DATASET = "gold_north_america"
TABLE = "actual_results"

# ── Connect to BigQuery ───────────────────────────────────────────────────────
def get_client():
    try:
        import streamlit as st
        if "GCP_CREDENTIALS" in st.secrets:
            credentials_info = json.loads(st.secrets["GCP_CREDENTIALS"])
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info
            )
            return bigquery.Client(credentials=credentials, project=PROJECT_ID)
    except Exception:
        pass
    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    return bigquery.Client.from_service_account_json(key_path, project=PROJECT_ID)

# ── Fetch results from API ────────────────────────────────────────────────────
def fetch_matches():
    headers = {"X-Auth-Token": API_KEY}
    response = requests.get(API_URL, headers=headers)
    response.raise_for_status()
    data = response.json()

    rows = []
    for m in data["matches"]:
        score = m["score"]["fullTime"]
        group_raw = m.get("group") or ""
        rows.append({
            "match_id":   m["id"],
            "date":       m["utcDate"][:10],
            "matchday":   m["matchday"],
            "stage":      m["stage"],
            "group_name": group_raw.replace("GROUP_", ""),
            "home_team":  m["homeTeam"]["name"],
            "away_team":  m["awayTeam"]["name"],
            "home_goals": score["home"],
            "away_goals": score["away"],
            "status":     m["status"],
            "fetched_at": datetime.utcnow().isoformat(),
        })

    df = pd.DataFrame(rows)

    # Cast types
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["home_goals"] = pd.to_numeric(df["home_goals"], errors="coerce")
    df["away_goals"] = pd.to_numeric(df["away_goals"], errors="coerce")

    def get_result(row):
        if row["status"] != "FINISHED":
            return None
        if row["home_goals"] > row["away_goals"]:
            return "home_win"
        elif row["away_goals"] > row["home_goals"]:
            return "away_win"
        else:
            return "draw"

    df["result"] = df.apply(get_result, axis=1)
    return df

# ── Write to BigQuery ─────────────────────────────────────────────────────────
def write_to_bigquery(df):
    client = get_client()
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("match_id",   "INTEGER"),
            bigquery.SchemaField("date",        "STRING"),
            bigquery.SchemaField("matchday",    "INTEGER"),
            bigquery.SchemaField("stage",       "STRING"),
            bigquery.SchemaField("group_name",  "STRING"),
            bigquery.SchemaField("home_team",   "STRING"),
            bigquery.SchemaField("away_team",   "STRING"),
            bigquery.SchemaField("home_goals",  "FLOAT"),
            bigquery.SchemaField("away_goals",  "FLOAT"),
            bigquery.SchemaField("status",      "STRING"),
            bigquery.SchemaField("fetched_at",  "STRING"),
            bigquery.SchemaField("result",      "STRING"),
        ]
    )

    # Convert date back to string for BigQuery STRING field
    df["date"] = df["date"].astype(str)

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    finished = df[df["status"] == "FINISHED"]
    print(f"Written {len(df)} matches to BigQuery ({len(finished)} finished)")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Fetching matches from football-data.org...")
    df = fetch_matches()
    print(f"Fetched {len(df)} matches, {len(df[df['status'] == 'FINISHED'])} finished")
    write_to_bigquery(df)
    print("Done.")
