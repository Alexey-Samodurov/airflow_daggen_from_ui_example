import logging

logger = logging.getLogger(__name__)

def _try_flask_wtf_csrf():
    """Попытка получить CSRF токен через Flask-WTF"""
    try:
        from flask_wtf.csrf import generate_csrf
        return generate_csrf()
    except ImportError:
        # Flask-WTF недоступен
        return None


def _try_flask_g_csrf():
    """Попытка получить CSRF токен из Flask.g"""
    try:
        from flask import g
        return getattr(g, 'csrf_token', None)
    except (ImportError, RuntimeError):
        # Flask недоступен или вне контекста приложения
        return None


def get_csrf_token():
    """Получаем CSRF токен из доступных источников"""
    # Пробуем Flask-WTF
    token = _try_flask_wtf_csrf()
    if token:
        return token

    # Пробуем Flask.g
    token = _try_flask_g_csrf()
    if token:
        return token

    # Возвращаем пустую строку если токен не найден
    return ""

def _create_schedule_options():
    """Создает список доступных вариантов расписания"""
    return [
        {'value': '@once', 'text': 'Один раз'},
        {'value': '@daily', 'text': 'Ежедневно'},
        {'value': '@hourly', 'text': 'Каждый час'},
        {'value': '@weekly', 'text': 'Еженедельно'},
        {'value': '@monthly', 'text': 'Ежемесячно'},
        {'value': '0 */6 * * *', 'text': 'Каждые 6 часов'},
        {'value': None, 'text': 'Без расписания'}
    ]

def get_templates_and_schedules():
    """Возвращает доступные шаблоны и расписания"""
    try:
        from airflow_dag_generator.generators import list_generators
        generators_list = list_generators()
        templates = {
            generator['name']: generator['display_name']
            for generator in generators_list
        }
        schedules = _create_schedule_options()
        return templates, schedules
    except Exception as e:
        logger.error(f"Error getting templates and schedules: {e}")
        return {}, []



def save_dag_file(dag_id, dag_code):
    """Сохраняет DAG файл в папку dags"""
    import os
    try:
        dags_folder = os.environ.get('AIRFLOW__CORE__DAGS_FOLDER', '/opt/airflow/dags')
        filename = f"{dag_id}.py"
        file_path = os.path.join(dags_folder, filename)
        os.makedirs(dags_folder, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(dag_code)

        logger.info(f"DAG file saved: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error saving DAG file: {e}")
        raise
