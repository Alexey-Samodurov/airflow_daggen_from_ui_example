"""


Generated automatically by DAG Generator Plugin
Created: 2025-06-20 08:58:15
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


# Определяем функцию для выполнения
def say_hello():
    """Простая функция Hello World"""
    print("Hello World from DAG Generator!")
    print(f"DAG ID: new_dag")
    print("Execution Date: {{ ds }}")
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
dag = DAG(
    dag_id='new_dag',
    default_args=default_args,
    description='',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['generated', 'hello-world'],
)

# Определяем задачу
hello_world_task = PythonOperator(
    task_id='hello_world_task',
    python_callable=say_hello,
    dag=dag,
)

# Задача выполняется одна, поэтому зависимости не нужны
