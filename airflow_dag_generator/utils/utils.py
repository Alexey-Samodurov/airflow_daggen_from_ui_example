import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

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
        from airflow_dag_generator.generators import get_all_generators
        generators = get_all_generators()
        templates = {
            name: generator.get_display_name()
            for name, generator in generators.items()
        }
        schedules = _create_schedule_options()
        return templates, schedules
    except Exception as e:
        logger.error(f"Error getting templates and schedules: {e}")
        return {}, []

def get_dags_folder() -> str:
    """Получает путь к папке DAG'ов из конфигурации Airflow"""
    try:
        from airflow.configuration import conf
        return conf.get('core', 'dags_folder')
    except Exception as e:
        logger.warning(f"Could not get dags_folder from Airflow config: {e}")
        # Fallback к переменной окружения или значению по умолчанию
        return os.environ.get('AIRFLOW__CORE__DAGS_FOLDER', '/opt/airflow/dags')

def ensure_dags_folder_exists() -> str:
    """Проверяет существование папки DAG'ов и создает её при необходимости"""
    dags_folder = get_dags_folder()
    
    if not os.path.exists(dags_folder):
        try:
            os.makedirs(dags_folder, exist_ok=True)
            logger.info(f"Created dags folder: {dags_folder}")
        except Exception as e:
            logger.error(f"Failed to create dags folder {dags_folder}: {e}")
            raise
    
    return dags_folder

def generate_dag_filename(dag_id: str) -> str:
    """Генерирует безопасное имя файла для DAG'а"""
    # Очищаем dag_id от недопустимых символов
    safe_dag_id = "".join(c for c in dag_id if c.isalnum() or c in "_-")
    return f"{safe_dag_id}.py"

def save_dag_file(dag_id: str, dag_code: str) -> str:
    """Сохраняет DAG файл в папку dags"""
    try:
        # Используем улучшенные функции
        dags_folder = ensure_dags_folder_exists()
        filename = generate_dag_filename(dag_id)
        file_path = os.path.join(dags_folder, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(dag_code)

        logger.info(f"DAG file saved: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error saving DAG file: {e}")
        raise

def delete_dag_file(file_path: str) -> bool:
    """Удаляет файл DAG'а"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"DAG file deleted: {file_path}")
            return True
        else:
            logger.warning(f"DAG file not found for deletion: {file_path}")
            return False
    except Exception as e:
        logger.error(f"Failed to delete DAG file {file_path}: {e}")
        return False

def read_dag_file(file_path: str) -> Optional[str]:
    """Читает содержимое файла DAG'а"""
    try:
        if not os.path.exists(file_path):
            logger.warning(f"DAG file not found: {file_path}")
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    except Exception as e:
        logger.error(f"Failed to read DAG file {file_path}: {e}")
        return None

def get_file_stats(file_path: str) -> Dict[str, Any]:
    """Получает статистику файла"""
    try:
        if not os.path.exists(file_path):
            return {}
            
        stat = os.stat(file_path)
        from datetime import datetime
        return {
            'size': stat.st_size,
            'mtime': stat.st_mtime,
            'created': stat.st_ctime,
            'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created_date': datetime.fromtimestamp(stat.st_ctime).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get file stats for {file_path}: {e}")
        return {}

def validate_dag_id(dag_id: str) -> tuple[bool, str]:
    """Валидирует DAG ID"""
    if not dag_id:
        return False, "DAG ID не может быть пустым"
    
    if len(dag_id) < 3:
        return False, "DAG ID должен содержать минимум 3 символа"
    
    if len(dag_id) > 250:
        return False, "DAG ID не должен превышать 250 символов"
    
    # Проверяем допустимые символы
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if not set(dag_id).issubset(allowed_chars):
        return False, "DAG ID может содержать только буквы, цифры, подчеркивания и дефисы"
    
    # Не должен начинаться с цифры
    if dag_id[0].isdigit():
        return False, "DAG ID не должен начинаться с цифры"
    
    return True, ""
