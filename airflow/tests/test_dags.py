"""DAG validity tests.

Run where Airflow is installed — e.g. inside the scheduler container:

    docker compose exec airflow-scheduler \
        python -m pytest /opt/airflow/tests -v
"""
import os

from airflow.models import DagBag

DAGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dags")


def _dagbag():
    return DagBag(dag_folder=DAGS_DIR, include_examples=False)


def test_dags_import_without_errors():
    bag = _dagbag()
    assert bag.import_errors == {}, f"DAG import errors: {bag.import_errors}"


def test_expected_dags_present():
    bag = _dagbag()
    assert set(bag.dag_ids) == {"daily_consumption_aggregates", "ingest_dataset"}


def test_aggregates_dag_shape():
    dag = _dagbag().get_dag("daily_consumption_aggregates")
    assert dag.schedule_interval == "@daily"
    assert not dag.catchup
    upsert = dag.get_task("upsert_daily_aggregates")
    verify = dag.get_task("verify_aggregates")
    assert verify.task_id in [t.task_id for t in upsert.downstream_list]


def test_ingest_dag_is_manual_only():
    dag = _dagbag().get_dag("ingest_dataset")
    assert dag.schedule_interval is None
    assert dag.get_task("load_dataset").retries == 3
