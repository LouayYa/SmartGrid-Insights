"""Manually-triggered pipeline: (re)load the UCI dataset into ingestion.

Replaces "call POST /api/v1/load by hand" as the documented way to seed
the platform: the load endpoint is idempotent (wipe + reload), Airflow
supplies retries with backoff, and a verification task confirms rows
actually landed before the run is marked successful.
"""
import os
from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

INGESTION_URL = os.getenv("INGESTION_API_URL", "http://ingestion:8001")


def load_dataset():
    resp = requests.post(f"{INGESTION_URL}/api/v1/load", timeout=600)
    resp.raise_for_status()
    body = resp.json()
    if body.get("records_loaded", 0) <= 0:
        raise ValueError(f"Load reported no records: {body}")
    print(f"Loaded {body['records_loaded']} records")
    return body["records_loaded"]


def verify_dataset():
    resp = requests.get(
        f"{INGESTION_URL}/api/v1/consumption",
        params={"limit": 1},
        timeout=60,
    )
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        raise ValueError("Verification failed: /consumption returned no rows after load")
    print(f"Verified: first record ID {rows[0]['ID']} on {rows[0]['Date']}")


with DAG(
    dag_id="ingest_dataset",
    description="Idempotent (re)load of the UCI household power CSV into the ingestion DB",
    schedule=None,  # manual trigger only
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "owner": "smartgrid",
        "retries": 3,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["smartgrid", "ingestion"],
) as dag:
    load = PythonOperator(task_id="load_dataset", python_callable=load_dataset)
    verify = PythonOperator(task_id="verify_dataset", python_callable=verify_dataset)

    load >> verify
