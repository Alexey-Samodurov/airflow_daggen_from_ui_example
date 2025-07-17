"""
fuck shit

Generated automatically by DAG Generator Plugin
Created: 2025-07-17 10:55:48
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


# Определяем функцию для выполнения
def say_hello(date: str):
    """Простая функция Hello World"""
    print("Hello World from DAG Generator!")
    print(f"DAG ID: my_super_dag")
    print("Execution Date: {date}")
    return "Hello World task completed successfully!"


# Настройки DAG'а по умолчанию
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Создание DAG'а
with DAG(
    dag_id='my_super_dag',
    default_args=default_args,
    description='fuck shit',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['generated', 'hello-world'],
) as dag:

    # Определяем задачу
    PythonOperator(
        task_id='hello_world_task',
        python_callable=say_hello,
        op_args=['{{ ds }}'],
    )

    # Задача выполняется одна, поэтому зависимости не нужны
