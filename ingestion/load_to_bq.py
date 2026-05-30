import os
import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

# ── Config ──────────────────────────────────────────────────────────────────
PROJECT_ID = "gold-north-america"
DATASET_ID = "gold_north_america"
DATA_DIR   = "data/raw"

# ── Files to load ────────────────────────────────────────────────────────────
files = {
    "results":        "results.csv",
    "goalscorers":    "goalscorers.csv",
    "shootouts":      "shootouts.csv",
    "former_names":   "former_names.csv",
    "fifa_rankings":  "fifa_rankings.csv",
    "squad_quality":  "fifa_player_ratings/fifa_wc2026_dataset.csv",
}

# ── BigQuery client ──────────────────────────────────────────────────────────
key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
client = bigquery.Client.from_service_account_json(key_path, project=PROJECT_ID)

# ── Create dataset if it doesn't exist ───────────────────────────────────────
dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
dataset_ref.location = "US"
try:
    client.create_dataset(dataset_ref, exists_ok=True)
    print(f"Dataset '{DATASET_ID}' ready")
except Exception as e:
    print(f"Dataset error: {e}")

# ── Load each file ────────────────────────────────────────────────────────────
for table_name, filename in files.items():
    filepath = os.path.join(DATA_DIR, filename)
    print(f"\nLoading {filename} → {DATASET_ID}.{table_name}...")

    df = pd.read_csv(filepath)
    print(f"  Rows: {len(df)} | Columns: {list(df.columns)}")

    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )

    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # Wait for job to complete

    table = client.get_table(table_id)
    print(f"  ✓ Loaded {table.num_rows} rows into {table_id}")

print("\n✓ All tables loaded successfully")