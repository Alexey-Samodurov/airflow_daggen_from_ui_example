import os
import sys
import logging

# Добавляем текущую папку в путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from airflow.configuration import conf
from flask import Blueprint, request, jsonify, render_template, redirect, session
from flask import current_app

# Теперь можем импортировать без проблем
from generators.hello_world_generator import HelloWorldGenerator
from utils.validators import validate_dag_syntax

# Настраиваем логирование
logger = logging.getLogger(__name__)

# Создаем Blueprint
dag_generator_bp = Blueprint(
    "dag_generator_plugin", 
    __name__,
    template_folder="templates",
    static_folder="static", 
    url_prefix="/dag-generator"
)


def get_csrf_token():
    """Получаем CSRF токен из Flask-WTF"""
    try:
        from flask_wtf.csrf import generate_csrf
        return generate_csrf()
    except:
        try:
            # Альтернативный способ для старых версий
            from flask import g
            if hasattr(g, 'csrf_token'):
                return g.csrf_token
        except:
            pass
    return ""


def get_templates_and_schedules():
    """Получаем доступные шаблоны и расписания"""
    templates = {
        'hello_world': 'Hello World DAG'
    }

    schedules = [
        ('@daily', 'Daily'),
        ('@hourly', 'Hourly'), 
        ('@weekly', 'Weekly'),
        ('0 2 * * *', 'Daily at 2 AM'),
        ('0 */6 * * *', 'Every 6 hours'),
        ('0 0 * * 0', 'Weekly on Sunday'),
        ('0 0 1 * *', 'Monthly'),
    ]
    
    return templates, schedules


@dag_generator_bp.route("/")
def index():
    """Главная страница генератора DAG'ов"""
    logger.info("Открыта главная страница DAG Generator")
    
    # Получаем данные для отображения
    templates, schedules = get_templates_and_schedules()
    
    # Пытаемся получить CSRF токен
    csrf_token = get_csrf_token()
    logger.info(f"CSRF токен получен: {csrf_token[:20] if csrf_token else 'пустой'}...")
    
    return render_template(
        "dag_generator/index.html",
        templates=templates,
        schedules=schedules,
        csrf_token=csrf_token
    )


@dag_generator_bp.route("/csrf-token")
def get_csrf_token_endpoint():
    """Эндпоинт для получения CSRF токена через AJAX"""
    try:
        csrf_token = get_csrf_token()
        return jsonify({
            "csrf_token": csrf_token,
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Ошибка получения CSRF токена: {e}")
        return jsonify({
            "csrf_token": "",
            "status": "error",
            "message": str(e)
        })


@dag_generator_bp.route("/form")
def form():
    """Форма создания DAG'а"""
    logger.info("Открыта форма создания DAG'а")
    
    templates, schedules = get_templates_and_schedules()
    csrf_token = get_csrf_token()

    return render_template(
        "dag_generator/form.html", 
        templates=templates,
        schedules=schedules,
        csrf_token=csrf_token
    )


@dag_generator_bp.route("/test", methods=["GET", "POST"])
def test():
    """Тестовый эндпоинт для проверки CSRF"""
    csrf_token = get_csrf_token()
    method = request.method
    
    logger.info(f"Тестовый эндпоинт вызван методом {method}")
    
    if method == "POST":
        # Логируем данные запроса
        logger.info(f"POST данные: {request.form.to_dict()}")
        logger.info(f"JSON данные: {request.get_json() if request.is_json else 'нет'}")
        logger.info(f"Headers: {dict(request.headers)}")
    
    return jsonify({
        "status": "success",
        "message": f"Тестовый эндпоинт работает! Метод: {method}",
        "csrf_token": csrf_token,
        "session_id": session.get('_id', 'no_session'),
        "app_name": current_app.name
    })


@dag_generator_bp.route("/generate", methods=["POST"])
def generate_dag():
    """API для генерации DAG'а"""
    try:
        logger.info("Начинаем генерацию DAG'а")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Content-Type: {request.headers.get('Content-Type')}")
        
        # Получаем данные из запроса
        if request.is_json:
            form_data = request.get_json()
            logger.info("Данные получены как JSON")
        else:
            form_data = request.form.to_dict()
            logger.info("Данные получены как form data")
            
        logger.info(f"Полученные данные: {form_data}")

        # Валидация входных данных
        required_fields = ['dag_id', 'template_type', 'schedule_interval']
        for field in required_fields:
            if not form_data.get(field):
                logger.error(f"Отсутствует обязательное поле: {field}")
                return jsonify({
                    "status": "error",
                    "message": f"Field '{field}' is required"
                }), 400

        # Дополнительная валидация dag_id
        dag_id = form_data['dag_id'] 
        logger.info(f"Проверяем DAG ID: {dag_id}")
        
        if not dag_id.replace('_', '').replace('-', '').isalnum():
            logger.error(f"Некорректный DAG ID: {dag_id}")
            return jsonify({
                "status": "error", 
                "message": "DAG ID should contain only letters, numbers, hyphens and underscores"
            }), 400

        # Выбираем генератор
        generator = get_generator(form_data['template_type'])
        if not generator:
            logger.error(f"Неизвестный тип шаблона: {form_data['template_type']}")
            return jsonify({
                "status": "error",
                "message": f"Unknown template: {form_data['template_type']}"
            }), 400

        logger.info("Начинаем генерацию кода DAG'а")
        
        # Добавляем информацию о создателе в данные
        form_data['creator'] = 'dag_generator'
        form_data['owner'] = form_data.get('owner', 'airflow')
        
        # Генерируем DAG
        dag_content = generator.generate(form_data)
        logger.info("Код DAG'а сгенерирован успешно")

        # Валидируем синтаксис
        logger.info("Валидируем синтаксис")
        validation_result = validate_dag_syntax(dag_content)
        if not validation_result['valid']:
            logger.error(f"Ошибка валидации: {validation_result['error']}")
            return jsonify({
                "status": "error",
                "message": f"Generated DAG has syntax errors: {validation_result['error']}"
            }), 400

        # Определяем путь для сохранения (берем из конфига Airflow)
        dags_folder = conf.get('core', 'dags_folder')
        dag_file_path = os.path.join(dags_folder, f"{form_data['dag_id']}.py")
        logger.info(f"Путь для сохранения: {dag_file_path}")

        # Проверяем, что DAG с таким именем не существует
        if os.path.exists(dag_file_path):
            logger.error(f"DAG уже существует: {dag_file_path}")
            return jsonify({
                "status": "error",
                "message": f"DAG with id '{form_data['dag_id']}' already exists"
            }), 400

        # Сохраняем DAG
        logger.info("Сохраняем файл DAG'а")
        with open(dag_file_path, 'w', encoding='utf-8') as f:
            f.write(dag_content)
        logger.info("DAG успешно сохранен")

        return jsonify({
            "status": "success",
            "message": f"DAG '{form_data['dag_id']}' created successfully", 
            "dag_file": dag_file_path,
            "preview_url": f"/dag-generator/preview/{form_data['dag_id']}"
        })

    except Exception as e:
        logger.exception("Ошибка при генерации DAG'а")
        return jsonify({
            "status": "error",
            "message": f"Error generating DAG: {str(e)}"
        }), 500


@dag_generator_bp.route("/preview/<dag_id>")
def preview_dag(dag_id):
    """Предпросмотр сгенерированного DAG'а"""
    logger.info(f"Открыт предпросмотр DAG'а: {dag_id}")
    
    dags_folder = conf.get('core', 'dags_folder')
    dag_file_path = os.path.join(dags_folder, f"{dag_id}.py")

    if not os.path.exists(dag_file_path):
        logger.error(f"Файл DAG'а не найден: {dag_file_path}")
        return redirect("/dag-generator/")

    with open(dag_file_path, 'r', encoding='utf-8') as f:
        dag_content = f.read()

    return render_template(
        "dag_generator/preview.html",
        dag_id=dag_id,
        dag_content=dag_content,
        username='dag_generator'
    )


def get_generator(template_type):
    """Получаем генератор по типу шаблона"""
    generators = {
        'hello_world': HelloWorldGenerator(),
    }
    return generators.get(template_type)
