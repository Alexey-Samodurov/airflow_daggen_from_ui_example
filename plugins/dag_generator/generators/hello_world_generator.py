from datetime import datetime


class HelloWorldGenerator:
    """Генератор простого Hello World DAG'а"""

    def generate(self, form_data):
        """
        Генерирует код DAG'а на основе переданных параметров

        Args:
            form_data (dict): Данные из формы с параметрами DAG'а

        Returns:
            str: Сгенерированный код DAG'а
        """
        dag_id = form_data.get('dag_id')
        schedule_interval = form_data.get('schedule_interval')
        description = form_data.get('description', 'Hello World DAG generated automatically')
        owner = form_data.get('owner', 'airflow')

        # Генерируем код DAG'а
        dag_code = f'''"""
{description}

Generated automatically by DAG Generator Plugin
Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


# Определяем функцию для выполнения
def say_hello(date: str):
    """Простая функция Hello World"""
    print("Hello World from DAG Generator!")
    print(f"DAG ID: {dag_id}")
    print("Execution Date: {date}")
    return "Hello World task completed successfully!"


# Настройки DAG'а по умолчанию
default_args = {{
    'owner': '{owner}',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}}

# Создание DAG'а
with DAG(
    dag_id='{dag_id}',
    default_args=default_args,
    description='{description}',
    schedule_interval='{schedule_interval}',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['generated', 'hello-world'],
) as dag:

    # Определяем задачу
    PythonOperator(
        task_id='hello_world_task',
        python_callable=say_hello,
        op_args='{{{{ ds }}}}',
    )

    # Задача выполняется одна, поэтому зависимости не нужны
'''

        return dag_code
