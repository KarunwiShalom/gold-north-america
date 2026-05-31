import os
import json
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = "gold-north-america"
DATASET = "gold_north_america"
TABLE = "predictions_group_stage"

def get_client():
    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    return bigquery.Client.from_service_account_json(key_path, project=PROJECT_ID)

def load_predictions():
    df = pd.read_csv("data/predictions_group_stage.csv")
    print(f"Loaded {len(df)} predictions from CSV")

    client = get_client()
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    print(f"Written {len(df)} predictions to BigQuery")

if __name__ == "__main__":
    load_predictions()
