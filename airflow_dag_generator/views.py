import logging
import os
import re
import secrets
import time

from flask import (
    render_template, request, redirect, url_for, flash, jsonify,
    session
)

from airflow_dag_generator.generators.discovery import get_discovery_manager
from airflow_dag_generator.generators.registry import get_registry, list_generators, get_generator

from flask import Blueprint

# Создаем Blueprint для веб-интерфейса
dag_generator_bp = Blueprint(
    'dag_generator',
    __name__,
    template_folder='templates',
    static_folder='templates/static',
    url_prefix='/dag-generator'
)

logger = logging.getLogger(__name__)


def get_csrf_token():
    """Получаем CSRF токен из Flask-WTF - ПРОСТАЯ ВЕРСИЯ"""
    try:
        from flask_wtf.csrf import generate_csrf
        return generate_csrf()
    except:
        try:
            from flask import g
            if hasattr(g, 'csrf_token'):
                return g.csrf_token
        except:
            pass
    return ""


def validate_dag_id(dag_id):
    """Простая валидация DAG ID"""
    if not dag_id:
        return False

    # DAG ID должен содержать только буквы, цифры и подчеркивания
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]*$'
    return bool(re.match(pattern, dag_id))


def save_dag_file(dag_id, dag_code):
    """Сохраняет DAG файл в папку dags"""
    try:
        # Получаем путь к папке dags (обычно /opt/airflow/dags в контейнере)
        dags_folder = os.environ.get('AIRFLOW__CORE__DAGS_FOLDER', '/opt/airflow/dags')

        # Создаем имя файла
        filename = f"{dag_id}.py"
        file_path = os.path.join(dags_folder, filename)

        # Создаем папку если не существует
        os.makedirs(dags_folder, exist_ok=True)

        # Сохраняем файл
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(dag_code)

        logger.info(f"DAG file saved: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"Error saving DAG file: {e}")
        raise


def get_templates_and_schedules():
    """Возвращает доступные шаблоны и расписания"""
    try:
        generators_list = list_generators()

        # Формируем словарь шаблонов
        templates = {}
        for generator in generators_list:
            templates[generator['name']] = generator['display_name']

        # Общие варианты расписаний
        schedules = [
            {'value': '@once', 'text': 'Один раз'},
            {'value': '@daily', 'text': 'Ежедневно'},
            {'value': '@hourly', 'text': 'Каждый час'},
            {'value': '@weekly', 'text': 'Еженедельно'},
            {'value': '@monthly', 'text': 'Ежемесячно'},
            {'value': '0 */6 * * *', 'text': 'Каждые 6 часов'},
            {'value': None, 'text': 'Без расписания'}
        ]

        return templates, schedules

    except Exception as e:
        logger.error(f"Error getting templates and schedules: {e}")
        return {}, []


@dag_generator_bp.route('/')
def index():
    """Главная страница генератора DAG'ов"""
    try:
        # Получаем данные для шаблона
        templates, schedules = get_templates_and_schedules()
        csrf_token = get_csrf_token()

        # Отладочная информация
        logger.info(f"Index page: {len(templates)} templates available")
        logger.info(f"Templates: {list(templates.keys())}")

        # Проверяем пути к статическим файлам
        blueprint_folder = os.path.dirname(__file__)
        static_folder = os.path.join(blueprint_folder, 'templates', 'static')
        logger.info(f"Blueprint folder: {blueprint_folder}")
        logger.info(f"Static folder path: {static_folder}")
        logger.info(f"Static folder exists: {os.path.exists(static_folder)}")

        if os.path.exists(static_folder):
            js_folder = os.path.join(static_folder, 'js')
            if os.path.exists(js_folder):
                js_files = os.listdir(js_folder)
                logger.info(f"JS files found: {js_files}")
            else:
                logger.warning(f"JS folder not found: {js_folder}")

        return render_template(
            'dag_generator/index.html',
            templates=templates,
            schedules=schedules,
            csrf_token=csrf_token
        )

    except Exception as e:
        logger.error(f"Error in index route: {e}")
        import traceback
        traceback.print_exc()
        return f"Error loading page: {str(e)}", 500


@dag_generator_bp.route('/api/generators')
def api_get_generators():
    """API эндпоинт для получения списка генераторов"""
    try:
        generators = list_generators()
        logger.info(f"API: returning {len(generators)} generators")
        return jsonify({
            'status': 'success',
            'generators': generators
        })
    except Exception as e:
        logger.error(f"Error getting generators: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@dag_generator_bp.route('/api/csrf-token')
def get_csrf_token_endpoint():
    """API эндпоинт для получения CSRF токена"""
    try:
        token = get_csrf_token()
        return jsonify({
            'success': True,
            'csrf_token': token
        })
    except Exception as e:
        logger.error(f"Error getting CSRF token: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dag_generator_bp.route('/api/generators/<generator_type>/fields')
def api_get_generator_fields(generator_type):
    """API эндпоинт для получения полей генератора"""
    try:
        generator = get_generator(generator_type)
        if not generator:
            return jsonify({
                'success': False,
                'error': f'Генератор {generator_type} не найден'
            }), 404

        # Получаем поля от генератора
        fields = generator.get_form_fields()

        return jsonify({
            'success': True,
            'display_name': generator.get_display_name(),
            'description': generator.get_description(),
            'fields': fields,
            'validation_rules': getattr(generator, 'validation_rules', {})
        })

    except Exception as e:
        logger.error(f"Error getting generator fields: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



@dag_generator_bp.route('/api/hot-reload/status')
def api_hot_reload_status():
    """API эндпоинт для получения статуса hot-reload"""
    try:
        discovery_manager = get_discovery_manager()
        if discovery_manager:
            is_active = discovery_manager.is_hot_reload_active()
            return jsonify({
                'success': True,
                'hot_reload_active': is_active,
                'status': 'active' if is_active else 'inactive'
            })
        else:
            return jsonify({
                'success': True,
                'hot_reload_active': False,
                'status': 'unavailable'
            })
    except Exception as e:
        logger.error(f"Error getting hot reload status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dag_generator_bp.route('/api/hot-reload/start', methods=['POST'])
def api_hot_reload_start():
    """API эндпоинт для запуска hot-reload"""
    try:
        discovery_manager = get_discovery_manager()
        if discovery_manager:
            success = discovery_manager.start_hot_reload()
            return jsonify({
                'success': success,
                'message': 'Hot-reload запущен' if success else 'Hot-reload уже запущен или недоступен'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Discovery manager недоступен'
            }), 500
    except Exception as e:
        logger.error(f"Error starting hot reload: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dag_generator_bp.route('/api/hot-reload/stop', methods=['POST'])
def api_hot_reload_stop():
    """API эндпоинт для остановки hot-reload"""
    try:
        discovery_manager = get_discovery_manager()
        if discovery_manager:
            success = discovery_manager.stop_hot_reload()
            return jsonify({
                'success': success,
                'message': 'Hot-reload остановлен' if success else 'Hot-reload уже остановлен'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Discovery manager недоступен'
            }), 500
    except Exception as e:
        logger.error(f"Error stopping hot reload: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dag_generator_bp.route('/api/health')
def api_health_check():
    """API эндпоинт для проверки здоровья системы"""
    try:
        registry = get_registry()
        discovery_manager = get_discovery_manager()

        return jsonify({
            'success': True,
            'status': 'healthy',
            'generators_count': len(registry),
            'hot_reload_active': discovery_manager.is_hot_reload_active() if discovery_manager else False,
            'timestamp': int(time.time()) if 'time' in globals() else None
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@dag_generator_bp.route('/form')
def form():
    """Страница с формой для настройки генератора"""
    try:
        templates, schedules = get_templates_and_schedules()
        csrf_token = get_csrf_token()

        return render_template(
            'dag_generator/form.html',
            templates=templates,
            schedules=schedules,
            csrf_token=csrf_token
        )

    except Exception as e:
        logger.error(f"Error in form route: {e}")
        return f"Error loading form: {str(e)}", 500

@dag_generator_bp.route('/preview', methods=['POST'])
def preview_dag():
    """Предпросмотр DAG - показывает страницу с кодом"""
    try:
        logger.info(f"=== PREVIEW REQUEST ===")
        
        # Получаем данные из запроса
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            generator_type = data.get('generator_type')
            form_data = data.get('form_data', {})
            is_api_request = True
        else:
            generator_type = request.form.get('generator_type')
            form_data = dict(request.form)
            form_data.pop('generator_type', None)
            form_data.pop('csrf_token', None)
            is_api_request = False

        if not generator_type:
            error_msg = 'Не указан тип генератора'
            if is_api_request:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                return error_msg, 400

        # Получаем генератор
        generator = get_generator(generator_type)
        if not generator:
            error_msg = 'Генератор не найден'
            if is_api_request:
                return jsonify({'success': False, 'error': error_msg}), 404
            else:
                return error_msg, 404

        # Генерируем код для предпросмотра
        dag_code = generator.generate(form_data)

        if is_api_request:
            # API запрос - возвращаем JSON
            return jsonify({
                'success': True,
                'dag_code': dag_code,
                'generator_info': {
                    'name': generator_type,
                    'display_name': generator.get_display_name(),
                    'description': generator.get_description()
                }
            })
        else:
            # ============ ВОТ ЗДЕСЬ БЫЛА ПРОБЛЕМА! ============
            # Веб запрос - показываем страницу предпросмотра
            # ОБЯЗАТЕЛЬНО передаем csrf_token в шаблон!
            csrf_token = get_csrf_token()
            
            return render_template(
                'dag_generator/preview.html',
                dag_code=dag_code,
                form_data=form_data,
                generator_type=generator_type,
                generator_name=generator.get_display_name(),
                csrf_token=csrf_token  # ← ЭТО БЫЛО ПРОПУЩЕНО!
            )

    except Exception as e:
        logger.error(f"Error in preview: {e}")
        error_msg = f'Ошибка предпросмотра: {str(e)}'
        if is_api_request:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            return error_msg, 500


@dag_generator_bp.route('/generate', methods=['POST'])
def generate_dag():
    """Генерация DAG - всегда возвращает JSON"""
    try:
        # Получаем данные из запроса
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            generator_type = data.get('generator_type')
            form_data = data.get('form_data', {})
            
            # Проверяем CSRF токен для JSON запросов
            csrf_token = request.headers.get('X-CSRFToken')
            #if not validate_csrf_token(csrf_token):
            #    return jsonify({
            #        'success': False, 
            #        'error': 'Invalid CSRF token'
            #    }), 400
        else:
            generator_type = request.form.get('generator_type')
            form_data = dict(request.form)
            csrf_token = form_data.pop('csrf_token', None)
            form_data.pop('generator_type', None)
            
            # Проверяем CSRF токен для form запросов
            #if not validate_csrf_token(csrf_token):
            #    return jsonify({
            #        'success': False, 
            #        'error': 'Invalid CSRF token'
            #    }), 400

        logger.info(f"Generate request - Generator: {generator_type}")

        if not generator_type:
            return jsonify({
                'success': False,
                'error': 'Не указан тип генератора'
            }), 400

        generator = get_generator(generator_type)
        if not generator:
            return jsonify({
                'success': False,
                'error': 'Генератор не найден'
            }), 404

        # Генерируем DAG
        dag_code = generator.generate(form_data)

        # Сохраняем DAG файл
        dag_id = form_data.get('dag_id', 'generated_dag')
        dag_file_path = save_dag_file(dag_id, dag_code)

        # Всегда возвращаем JSON для обработки в JavaScript
        return jsonify({
            'success': True,
            'dag_code': dag_code,
            'dag_file_path': dag_file_path,
            'message': 'DAG успешно создан',
            'generator_info': {
                'name': generator_type,
                'display_name': generator.get_display_name(),
                'description': generator.get_description()
            }
        })

    except Exception as e:
        logger.error(f"Error in generate: {e}")
        return jsonify({
            'success': False,
            'error': f'Ошибка генерации: {str(e)}'
        }), 500


@dag_generator_bp.route('/reload')
def reload_generators():
    """Перезагрузка всех генераторов"""
    try:
        # Получаем менеджер обнаружения
        discovery_manager = get_discovery_manager()

        if discovery_manager:
            # Принудительно перезагружаем все генераторы
            count = discovery_manager.force_reload_all()
            flash(f'Перезагружено {count} генераторов', 'success')
        else:
            flash('Менеджер обнаружения недоступен', 'warning')

        return redirect(url_for('dag_generator.index'))

    except Exception as e:
        logger.error(f"Error reloading generators: {e}")
        flash(f'Ошибка перезагрузки: {str(e)}', 'error')
        return redirect(url_for('dag_generator.index'))
