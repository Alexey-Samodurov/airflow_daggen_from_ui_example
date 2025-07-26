"""
Генератор DAG'ов для работы с API
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from airflow_dag_generator.generators.base_generator import BaseGenerator


class ApiDagGenerator(BaseGenerator):
    """Генератор DAG'ов для работы с API"""

    def __init__(self):
        super().__init__(generator_name="api_dag")  # ✅ Правильная инициализация

    def get_display_name(self) -> str:
        return "API интеграция"

    def get_description(self) -> str:
        return "DAG для получения данных из REST API"

    def get_required_fields(self) -> List[str]:  # ✅ Правильная сигнатура
        return ['dag_id', 'schedule_interval', 'owner']

    def get_optional_fields(self) -> Dict[str, Any]:  # ✅ Правильная сигнатура
        return {
            'description': 'DAG для работы с API',
            'api_url': 'https://jsonplaceholder.typicode.com/posts/1',
            'timeout': 30,
            'retries': 2,
            'retry_delay_minutes': 2,
            'tags': 'generated, api',
            'catchup': False,
            'max_active_runs': 1
        }

    def get_form_fields(self) -> List[Dict[str, Any]]:
        """Кастомизированные поля формы для API генератора"""
        return [
            {
                'name': 'dag_id',
                'type': 'text',
                'label': 'DAG ID',
                'required': True,
                'placeholder': 'my_api_dag',
                'pattern': '^[a-zA-Z0-9_-]+$',
                'help_text': 'Уникальный идентификатор DAG (буквы, цифры, подчёркивания, дефисы)'
            },
            {
                'name': 'schedule_interval',
                'type': 'select',
                'label': 'Расписание',
                'required': True,
                'options': [
                    {'value': '@daily', 'text': 'Ежедневно'},
                    {'value': '@hourly', 'text': 'Каждый час'},
                    {'value': '@weekly', 'text': 'Еженедельно'},
                    {'value': '0 2 * * *', 'text': 'Ежедневно в 2:00'},
                    {'value': 'None', 'text': 'Только вручную'}
                ],
                'default': '@daily'
            },
            {
                'name': 'owner',
                'type': 'text',
                'label': 'Владелец',
                'required': True,
                'default': 'airflow',
                'placeholder': 'airflow'
            },
            {
                'name': 'description',
                'type': 'textarea',
                'label': 'Описание',
                'required': False,
                'default': 'DAG для работы с API',
                'placeholder': 'Введите описание DAG...'
            },
            {
                'name': 'api_url',
                'type': 'text',
                'label': 'URL API',
                'required': False,
                'default': 'https://jsonplaceholder.typicode.com/posts/1',
                'placeholder': 'https://api.example.com/data',
                'help_text': 'URL для получения данных'
            },
            {
                'name': 'timeout',
                'type': 'number',
                'label': 'Таймаут (сек)',
                'required': False,
                'default': 30,
                'min': 1,
                'max': 300,
                'help_text': 'Таймаут запроса в секундах'
            },
            {
                'name': 'retries',
                'type': 'number',
                'label': 'Количество попыток',
                'required': False,
                'default': 2,
                'min': 0,
                'max': 10
            },
            {
                'name': 'tags',
                'type': 'text',
                'label': 'Теги',
                'required': False,
                'default': 'generated, api',
                'placeholder': 'тег1, тег2, тег3',
                'help_text': 'Теги через запятую'
            },
            {
                'name': 'catchup',
                'type': 'checkbox',
                'label': 'Включить Catchup',
                'required': False,
                'default': False,
                'help_text': 'Выполнять ли пропущенные запуски'
            }
        ]

    def generate(self, form_data: Dict[str, Any]) -> str:  # ✅ Правильная сигнатура
        """Генерирует код DAG'а для работы с API"""

        # Валидация
        validation_result = self.validate_config(form_data)
        if not validation_result['valid']:
            raise ValueError(f"Неверная конфигурация: {validation_result['errors']}")

        # Извлекаем параметры с значениями по умолчанию
        dag_id = form_data.get('dag_id')
        description = form_data.get('description', 'DAG для работы с API')
        schedule_interval = form_data.get('schedule_interval', '@daily')
        owner = form_data.get('owner', 'airflow')
        api_url = form_data.get('api_url', 'https://jsonplaceholder.typicode.com/posts/1')
        timeout = form_data.get('timeout', 30)
        retries = form_data.get('retries', 2)
        retry_delay_minutes = form_data.get('retry_delay_minutes', 2)
        tags = form_data.get('tags', 'generated, api')
        catchup = form_data.get('catchup', False)
        max_active_runs = form_data.get('max_active_runs', 1)

        # Обрабатываем теги
        if isinstance(tags, str):
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        else:
            tags_list = tags if isinstance(tags, list) else ['generated', 'api']

        dag_code = f'''"""
{description}

Generated by: {self.get_display_name()}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import json
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator


def fetch_api_data(**context):
    """Получает данные из API"""
    import requests

    api_url = "{api_url}"

    try:
        print(f"🌐 Запрос к API: {{api_url}}")

        response = requests.get(api_url, timeout={timeout})
        response.raise_for_status()

        data = response.json()

        print(f"✅ Данные получены: {{data}}")

        # Сохраняем данные в XCom
        return {{
            'status_code': response.status_code,
            'data': data,
            'url': api_url
        }}

    except Exception as e:
        print(f"❌ Ошибка API запроса: {{e}}")
        raise


def process_api_response(**context):
    """Обрабатывает ответ от API"""
    ti = context['ti']

    # Получаем данные из предыдущей задачи
    api_result = ti.xcom_pull(task_ids='fetch_data')

    if not api_result:
        raise ValueError("Нет данных от API")

    data = api_result['data']

    print(f"🔄 Обработка данных: {{data}}")

    # Простая обработка - извлекаем заголовок
    if isinstance(data, dict) and 'title' in data:
        processed = {{
            'original_title': data['title'],
            'title_length': len(data['title']),
            'processed_at': str(datetime.now())
        }}
    else:
        processed = {{'raw_data': str(data)}}

    print(f"✅ Данные обработаны: {{processed}}")

    return processed


def save_results(**context):
    """Сохраняет результаты в файл"""
    ti = context['ti']

    processed_data = ti.xcom_pull(task_ids='process_data')

    output_file = '/tmp/api_results.json'

    with open(output_file, 'w') as f:
        json.dump(processed_data, f, indent=2)

    print(f"💾 Результаты сохранены в: {{output_file}}")

    return output_file


# Настройки DAG'а
default_args = {{
    'owner': '{owner}',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': {retries},
    'retry_delay': timedelta(minutes={retry_delay_minutes}),
}}

# Создание DAG'
with DAG(
    dag_id='{dag_id}',
    default_args=default_args,
    description='{description}',
    schedule_interval='{schedule_interval}',
    start_date=datetime(2024, 1, 1),
    catchup={str(catchup).lower()},
    tags={tags_list},
    max_active_runs={max_active_runs},
) as dag:

    # Получение данных из API
    fetch_data = PythonOperator(
        task_id='fetch_data',
        python_callable=fetch_api_data,
    )

    # Обработка данных
    process_data = PythonOperator(
        task_id='process_data',
        python_callable=process_api_response,
    )

    # Сохранение результатов
    save_data = PythonOperator(
        task_id='save_results',
        python_callable=save_results,
    )

    # Проверка созданного файла
    verify_file = BashOperator(
        task_id='verify_output',
        bash_command='ls -la /tmp/api_results.json && cat /tmp/api_results.json',
    )

    # Последовательность выполнения
    fetch_data >> process_data >> save_data >> verify_file
'''

        return dag_code
