"""Daily batch pipeline: per-meter daily consumption aggregates.

Reads raw minute-level readings from the Data Collection database and
upserts one row per (meter, day) into analytics_daily — average and peak
power plus sub-metering energy totals. The Data Analysis Service serves
the results via GET /analysis/daily/{meter_id}.

Design notes:
- Full refresh each run: the readings table is small (hundreds of
  thousands of rows), so recomputing everything nightly is simpler and
  self-healing. Switch to incremental-by-day partitions when data grows.
- Idempotent: the composite (meter_id, day) primary key plus
  ON CONFLICT DO UPDATE makes reruns and backfills safe.
- Schema is owned by the collection service's Alembic migrations
  (0003_analytics_daily); this DAG only writes data.

Connection: `collection_db`, injected via the AIRFLOW_CONN_COLLECTION_DB
environment variable in docker-compose.yml.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator

UPSERT_SQL = """
INSERT INTO analytics_daily (
    meter_id, day, avg_power, peak_power,
    kitchen_wh, laundry_wh, water_heater_ac_wh, samples, computed_at
)
SELECT
    meter_id,
    timestamp::date                AS day,
    AVG(global_active_power)      AS avg_power,
    MAX(global_active_power)      AS peak_power,
    SUM(sub_metering_1)           AS kitchen_wh,
    SUM(sub_metering_2)           AS laundry_wh,
    SUM(sub_metering_3)           AS water_heater_ac_wh,
    COUNT(*)                      AS samples,
    NOW()                         AS computed_at
FROM readings
GROUP BY meter_id, timestamp::date
ON CONFLICT (meter_id, day) DO UPDATE SET
    avg_power          = EXCLUDED.avg_power,
    peak_power         = EXCLUDED.peak_power,
    kitchen_wh         = EXCLUDED.kitchen_wh,
    laundry_wh         = EXCLUDED.laundry_wh,
    water_heater_ac_wh = EXCLUDED.water_heater_ac_wh,
    samples            = EXCLUDED.samples,
    computed_at        = EXCLUDED.computed_at;
"""

VERIFY_SQL = """
SELECT COUNT(*) AS aggregate_rows, COUNT(DISTINCT meter_id) AS meters
FROM analytics_daily;
"""

with DAG(
    dag_id="daily_consumption_aggregates",
    description="Upsert per-meter daily aggregates from raw readings into analytics_daily",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "owner": "smartgrid",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["smartgrid", "batch", "analytics"],
) as dag:
    upsert_daily_aggregates = SQLExecuteQueryOperator(
        task_id="upsert_daily_aggregates",
        conn_id="collection_db",
        sql=UPSERT_SQL,
    )

    verify_aggregates = SQLExecuteQueryOperator(
        task_id="verify_aggregates",
        conn_id="collection_db",
        sql=VERIFY_SQL,
        show_return_value_in_logs=True,
    )

    upsert_daily_aggregates >> verify_aggregates
