"""
Встроенный Hello World генератор
"""
from typing import Dict, Any, List
from datetime import datetime
from .base_generator import BaseGenerator


class HelloWorldGenerator(BaseGenerator):
    """Простой Hello World генератор для демонстрации"""
    
    def __init__(self):
        super().__init__(generator_name="hello_world")
    
    def get_display_name(self) -> str:
        return "Hello World DAG"
    
    def get_description(self) -> str:
        return "Простой Hello World DAG с одной задачей Python operator"
    
    def get_required_fields(self) -> List[str]:
        return ['dag_id', 'schedule_interval', 'owner']
    
    def get_optional_fields(self) -> Dict[str, Any]:
        return {
            'description': 'Generated Hello World DAG',
            'tags': 'generated, hello-world',
            'catchup': False,
            'max_active_runs': 1,
            'retries': 1,
            'retry_delay_minutes': 5,
            'greeting_message': 'Hello World from DAG Generator!'
        }
    
    def get_form_fields(self) -> List[Dict[str, Any]]:
        """Кастомизированные поля формы"""
        return [
            {
                'name': 'dag_id',
                'type': 'text',
                'label': 'DAG ID',
                'required': True,
                'placeholder': 'my_hello_world_dag',
                'pattern': '^[a-zA-Z0-9_-]+$',
                'help_text': 'Unique identifier for the DAG (letters, numbers, underscores, hyphens)'
            },
            {
                'name': 'schedule_interval',
                'type': 'select',
                'label': 'Schedule Interval',
                'required': True,
                'options': [
                    {'value': '@daily', 'text': 'Daily'},
                    {'value': '@hourly', 'text': 'Hourly'},
                    {'value': '@weekly', 'text': 'Weekly'},
                    {'value': '0 2 * * *', 'text': 'Daily at 2 AM'},
                    {'value': 'None', 'text': 'Manual trigger only'}
                ]
            },
            {
                'name': 'owner',
                'type': 'text',
                'label': 'Owner',
                'required': True,
                'default': 'airflow',
                'placeholder': 'airflow'
            },
            {
                'name': 'description',
                'type': 'textarea',
                'label': 'Description',
                'required': False,
                'default': 'Generated Hello World DAG',
                'placeholder': 'Enter DAG description...'
            },
            {
                'name': 'greeting_message',
                'type': 'text',
                'label': 'Greeting Message',
                'required': False,
                'default': 'Hello World from DAG Generator!',
                'placeholder': 'Custom greeting message'
            },
            {
                'name': 'tags',
                'type': 'text',
                'label': 'Tags',
                'required': False,
                'default': 'generated, hello-world',
                'placeholder': 'tag1, tag2, tag3',
                'help_text': 'Comma-separated tags'
            },
            {
                'name': 'catchup',
                'type': 'checkbox',
                'label': 'Enable Catchup',
                'required': False,
                'default': False,
                'help_text': 'Whether to catch up on missed runs'
            },
            {
                'name': 'retries',
                'type': 'number',
                'label': 'Retries',
                'required': False,
                'default': 1,
                'min': 0,
                'max': 10
            }
        ]
    
    def generate(self, form_data: Dict[str, Any]) -> str:
        """Генерирует код DAG'а на основе переданных параметров"""
        
        # Валидация
        validation_result = self.validate_config(form_data)
        if not validation_result['valid']:
            raise ValueError(f"Invalid configuration: {validation_result['errors']}")
        
        # Извлекаем параметры с значениями по умолчанию
        dag_id = form_data.get('dag_id')
        schedule_interval = form_data.get('schedule_interval')
        description = form_data.get('description', 'Generated Hello World DAG')
        owner = form_data.get('owner', 'airflow')
        greeting_message = form_data.get('greeting_message', 'Hello World from DAG Generator!')
        tags = form_data.get('tags', 'generated, hello-world')
        catchup = form_data.get('catchup', False)
        retries = form_data.get('retries', 1)
        retry_delay_minutes = form_data.get('retry_delay_minutes', 5)
        max_active_runs = form_data.get('max_active_runs', 1)
        
        # Обрабатываем теги
        if isinstance(tags, str):
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        else:
            tags_list = tags if isinstance(tags, list) else ['generated', 'hello-world']
        
        # Генерируем код DAG'а
        dag_code = f'''"""
{description}

Generated by: {self.get_display_name()}
Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def say_hello(**context):
    """Hello World task function"""
    greeting = "{greeting_message}"
    dag_id = "{dag_id}"
    execution_date = context.get('ds', 'Unknown')
    
    print("=" * 50)
    print(greeting)
    print(f"DAG ID: {{dag_id}}")
    print(f"Execution Date: {{execution_date}}")
    print(f"Owner: {owner}")
    print("=" * 50)
    
    # Возвращаем информацию для XCom
    return {{
        "message": greeting,
        "dag_id": dag_id,
        "execution_date": execution_date,
        "status": "success"
    }}


# Default arguments
default_args = {{
    'owner': '{owner}',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': {retries},
    'retry_delay': timedelta(minutes={retry_delay_minutes}),
}}

# Create DAG
with DAG(
    dag_id='{dag_id}',
    default_args=default_args,
    description='{description}',
    schedule_interval='{schedule_interval}',
    start_date=datetime(2024, 1, 1),
    catchup={catchup},
    max_active_runs={max_active_runs},
    tags={tags_list},
) as dag:

    # Hello World task
    hello_task = PythonOperator(
        task_id='hello_world_task',
        python_callable=say_hello,
        doc_md="""
        ### Hello World Task
        
        This task prints a greeting message and returns execution information.
        
        **Generated by:** {self.get_display_name()}  
        **Message:** {greeting_message}
        """,
    )

    # Single task, no dependencies needed
    hello_task
'''

        return dag_code
