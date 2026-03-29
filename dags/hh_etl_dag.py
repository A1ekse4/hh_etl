from __future__ import annotations

import os
import uuid
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator

NOTEBOOK_PATH = Path(__file__).parent.parent / "hh_etl.ipynb"
OUTPUT_DIR = Path("/tmp/hh_etl_outputs")

default_args = {
    "owner": "etl",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}


def run_etl_notebook(**context) -> None:
    """Выполняет ноутбук через papermill, передавая etl_id и дату запуска."""
    import papermill as pm

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    run_id = str(uuid.uuid4())
    logical_date = context["logical_date"].isoformat()
    output_path = OUTPUT_DIR / f"hh_etl_{logical_date[:10]}_{run_id[:8]}.ipynb"

    pm.execute_notebook(
        str(NOTEBOOK_PATH),
        str(output_path),
        parameters={},
        kernel_name="python3",
        log_output=True,
    )


with DAG(
    dag_id="hh_etl",
    description="Инкрементальная загрузка вакансий с hh.ru в PostgreSQL",
    schedule="0 6 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    default_args=default_args,
    tags=["etl", "hh", "vacancies"],
    doc_md=__doc__,
) as dag:

    run_notebook = PythonOperator(
        task_id="run_hh_etl_notebook",
        python_callable=run_etl_notebook,
    )
