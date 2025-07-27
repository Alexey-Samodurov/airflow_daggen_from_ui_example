import logging

from flask import (
    render_template, request, jsonify,
    Blueprint
)

from airflow_dag_generator.generators import (
    get_registry, list_generators, get_generator, safe_manual_reload
)
from airflow_dag_generator.utils.utils import get_csrf_token, get_templates_and_schedules, save_dag_file

# Создаем Blueprint для веб-интерфейса
dag_generator_bp = Blueprint(
    'dag_generator',
    __name__,
    template_folder='templates',
    static_folder='templates/static',
    url_prefix='/dag-generator'
)

logger = logging.getLogger(__name__)


@dag_generator_bp.route('/')
def index():
    """Главная страница генератора DAG'ов"""
    try:
        templates, schedules = get_templates_and_schedules()
        csrf_token = get_csrf_token()

        logger.info(f"Index page: {len(templates)} templates available")
        logger.info(f"Templates: {list(templates.keys())}")

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


@dag_generator_bp.route('/api/debug/registry')
def api_debug_registry():
    """ОТЛАДОЧНЫЙ эндпоинт для проверки состояния реестра"""
    try:
        registry = get_registry()
        generators_dict = registry.get_generators_dict()
        
        debug_info = {
            'registry_size': len(registry),
            'generator_names': list(generators_dict.keys()),
            'generators_details': []
        }
        
        for name, gen in generators_dict.items():
            debug_info['generators_details'].append({
                'name': name,
                'class': gen.__class__.__name__,
                'display_name': gen.get_display_name(),
                'module': gen.__class__.__module__,
                'file': getattr(gen.__class__, '__module__', 'unknown')
            })
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
    except Exception as e:
        logger.error(f"Error in debug registry: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dag_generator_bp.route('/api/reload/manual', methods=['POST'])
def api_manual_reload():
    """API эндпоинт для безопасной ручной перезагрузки генераторов"""
    try:
        logger.info("=== MANUAL RELOAD API CALLED ===")
        
        # Используем безопасную функцию перезагрузки
        count = safe_manual_reload()
        
        logger.info(f"Manual reload API completed: {count} generators loaded")
        return jsonify({
            'success': True,
            'reloaded_count': count,
            'message': f'Перезагружено {count} генераторов'
        })
    except Exception as e:
        logger.error(f"Error during manual reload API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dag_generator_bp.route('/api/generators/<generator_type>/fields')
def api_get_generator_fields(generator_type):
    """API эндпоинт для получения полей генератора"""
    try:
        logger.info(f"=== GETTING FIELDS FOR GENERATOR: {generator_type} ===")
        
        # Проверяем реестр перед использованием
        registry = get_registry()
        all_generators = registry.get_generator_names()
        logger.info(f"Available generators in registry: {all_generators}")
        
        generator = get_generator(generator_type)
        if not generator:
            # Пытаемся перезагрузить и еще раз найти
            logger.warning(f"Generator '{generator_type}' not found, trying reload...")
            try:
                safe_manual_reload()
                generator = get_generator(generator_type)
            except:
                pass
            
            if not generator:
                logger.error(f"Generator '{generator_type}' not found even after reload")
                return jsonify({
                    'success': False,
                    'error': f'Генератор {generator_type} не найден'
                }), 404

        logger.info(f"Found generator: {generator.__class__.__name__}")

        # Получаем поля от генератора
        fields = generator.get_form_fields()
        logger.info(f"Generator fields: {len(fields)} fields")

        return jsonify({
            'success': True,
            'display_name': generator.get_display_name(),
            'description': generator.get_description(),
            'fields': fields,
            'validation_rules': getattr(generator, 'validation_rules', {})
        })

    except Exception as e:
        logger.error(f"Error getting generator fields: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dag_generator_bp.route('/preview', methods=['POST'])
def preview_dag():
    """Предпросмотр DAG с проверкой генератора"""
    try:
        logger.info(f"=== PREVIEW REQUEST ===")
        
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

        # Получаем генератор с попыткой перезагрузки
        generator = get_generator(generator_type)
        if not generator:
            logger.warning(f"Generator '{generator_type}' not found for preview, trying reload...")
            try:
                safe_manual_reload()
                generator = get_generator(generator_type)
            except:
                pass
        
        if not generator:
            error_msg = 'Генератор не найден'
            if is_api_request:
                return jsonify({'success': False, 'error': error_msg}), 404
            else:
                return error_msg, 404

        # Генерируем код для предпросмотра
        dag_code = generator.generate(form_data)

        if is_api_request:
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
            csrf_token = get_csrf_token()
            return render_template(
                'dag_generator/preview.html',
                dag_code=dag_code,
                form_data=form_data,
                generator_type=generator_type,
                generator_name=generator.get_display_name(),
                csrf_token=csrf_token
            )

    except Exception as e:
        logger.error(f"Error in preview: {e}")
        import traceback
        traceback.print_exc()
        error_msg = f'Ошибка предпросмотра: {str(e)}'
        if is_api_request:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            return error_msg, 500


@dag_generator_bp.route('/generate', methods=['POST'])
def generate_dag():
    """Генерация DAG с проверкой генератора"""
    try:
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            generator_type = data.get('generator_type')
            form_data = data.get('form_data', {})
        else:
            generator_type = request.form.get('generator_type')
            form_data = dict(request.form)
            form_data.pop('generator_type', None)
            form_data.pop('csrf_token', None)

        logger.info(f"Generate request - Generator: {generator_type}")

        if not generator_type:
            return jsonify({
                'success': False,
                'error': 'Не указан тип генератора'
            }), 400

        # Получаем генератор с попыткой перезагрузки
        generator = get_generator(generator_type)
        if not generator:
            logger.warning(f"Generator '{generator_type}' not found for generation, trying reload...")
            try:
                safe_manual_reload()
                generator = get_generator(generator_type)
            except:
                pass
        
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
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Ошибка генерации: {str(e)}'
        }), 500
