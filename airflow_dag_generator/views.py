import json
import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from .generators import get_all_generators, get_generator, safe_manual_reload
from .utils import save_dag_file
from .utils.metadata_parser import MetadataParser

logger = logging.getLogger(__name__)

dag_generator_bp = Blueprint(
    'dag_generator',
    __name__,
    template_folder='templates/dag_generator',
    static_folder='templates/static',
    url_prefix='/dag-generator'
)


@dag_generator_bp.route('/')
def index():
    """Главная страница генератора DAG'ов"""
    generators = get_all_generators()
    return render_template('index.html', generators=generators)


@dag_generator_bp.route('/api/generators')
def api_generators():
    """API для получения списка всех генераторов"""
    try:
        generators = get_all_generators()
        generators_list = []
        
        for name, generator in generators.items():
            try:
                generators_list.append({
                    'name': name,
                    'display_name': generator.get_display_name(),
                    'description': generator.get_description(),
                    'class_name': generator.__class__.__name__
                })
            except Exception as e:
                logger.error(f"Error getting info for generator {name}: {e}")
                generators_list.append({
                    'name': name,
                    'display_name': name.replace('_', ' ').title(),
                    'description': 'Description unavailable',
                    'class_name': 'Unknown'
                })
        
        return jsonify({
            'status': 'success',
            'generators': generators_list,
            'count': len(generators_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting generators: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'generators': [],
            'count': 0
        }), 500


@dag_generator_bp.route('/api/generators/<generator_name>/fields')
def api_generator_fields(generator_name):
    """API для получения полей конкретного генератора"""
    try:
        logger.info(f"Getting fields for generator: {generator_name}")
        
        generator = get_generator(generator_name)
        if not generator:
            logger.error(f"Generator '{generator_name}' not found")
            return jsonify({
                'success': False,
                'error': f'Генератор "{generator_name}" не найден'
            }), 404

        # Получаем поля формы
        try:
            form_fields = generator.get_form_fields()
            logger.info(f"Got {len(form_fields)} fields for generator {generator_name}")
        except Exception as e:
            logger.error(f"Error getting form fields: {e}")
            # Fallback: пытаемся собрать поля вручную
            form_fields = []
            
            # Обязательные поля
            try:
                required_fields = generator.get_required_fields()
                for field_name in required_fields:
                    form_fields.append({
                        'name': field_name,
                        'type': 'text',
                        'label': field_name.replace('_', ' ').title(),
                        'required': True,
                        'placeholder': f'Enter {field_name}...'
                    })
            except Exception as req_e:
                logger.error(f"Error getting required fields: {req_e}")
            
            # Опциональные поля
            try:
                optional_fields = generator.get_optional_fields()
                for field_name, default_value in optional_fields.items():
                    form_fields.append({
                        'name': field_name,
                        'type': 'text',
                        'label': field_name.replace('_', ' ').title(),
                        'required': False,
                        'default': default_value,
                        'placeholder': f'Enter {field_name}...'
                    })
            except Exception as opt_e:
                logger.error(f"Error getting optional fields: {opt_e}")

        return jsonify({
            'success': True,
            'display_name': generator.get_display_name(),
            'description': generator.get_description(),
            'fields': form_fields,
            'generator_info': {
                'name': generator.generator_name,
                'display_name': generator.get_display_name(),
                'description': generator.get_description(),
                'version': getattr(generator, 'template_version', '1.0.0')
            }
        })

    except Exception as e:
        logger.error(f"Error getting generator fields for {generator_name}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Ошибка получения полей генератора: {str(e)}'
        }), 500


@dag_generator_bp.route('/api/reload/manual', methods=['POST'])
def api_manual_reload():
    """API для ручной перезагрузки генераторов"""
    try:
        logger.info("Manual reload requested via API")
        count = safe_manual_reload()
        
        return jsonify({
            'success': True,
            'message': f'Перезагружено {count} генераторов',
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Manual reload failed: {e}")
        return jsonify({
            'success': False,
            'error': f'Ошибка перезагрузки: {str(e)}'
        }), 500


@dag_generator_bp.route('/api/reload/status')
def api_reload_status():
    """API для получения статуса системы перезагрузки"""
    try:
        from .generators.discovery import get_discovery_stats
        stats = get_discovery_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting reload status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dag_generator_bp.route('/create', methods=['POST'])
def create_dag():
    """Создание нового DAG'а"""
    try:
        # Определяем тип запроса
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            generator_type = data.get('generator_type')
            form_data = data.get('form_data', {})
        else:
            generator_type = request.form.get('generator_type')
            form_data = dict(request.form)
            form_data.pop('generator_type', None)
            form_data.pop('csrf_token', None)

        # Получаем генератор
        generator = get_generator(generator_type)
        if not generator:
            return jsonify({
                'success': False,
                'error': f'Генератор "{generator_type}" не найден'
            }), 404

        # Валидируем данные
        try:
            validation_result = generator.validate_config(form_data)
            if not validation_result.get('valid', True):
                return jsonify({
                    'success': False,
                    'errors': validation_result.get('errors', [])
                }), 400
        except Exception as val_e:
            logger.warning(f"Validation failed: {val_e}")

        # Генерируем DAG с полными метаданными
        if hasattr(generator, 'generate_with_metadata'):
            dag_code = generator.generate_with_metadata(form_data)
        else:
            dag_code = generator.generate(form_data)
        
        # Сохраняем файл
        dag_id = form_data['dag_id']
        file_path = save_dag_file(dag_id, dag_code)

        return jsonify({
            'success': True,
            'message': f'DAG "{dag_id}" успешно создан',
            'dag_code': dag_code,
            'dag_id': dag_id,
            'dag_file_path': file_path
        })

    except Exception as e:
        logger.error(f"Error in create_dag: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Ошибка создания DAG: {str(e)}'
        }), 500


@dag_generator_bp.route('/api/preview', methods=['POST'])
def api_preview_dag():
    """API для предпросмотра кода DAG'а"""
    try:
        data = request.get_json()
        generator_type = data.get('generator_type')
        config = data.get('config', {})
        
        generator = get_generator(generator_type)
        if not generator:
            return jsonify({
                'success': False,
                'error': f'Генератор "{generator_type}" не найден'
            }), 404

        # Валидируем данные
        try:
            validation_result = generator.validate_config(config)
            if not validation_result.get('valid', True):
                return jsonify({
                    'success': False,
                    'errors': validation_result.get('errors', [])
                }), 400
        except Exception as val_e:
            logger.warning(f"Validation failed: {val_e}")

        # Генерируем код с метаданными
        if hasattr(generator, 'generate_with_metadata'):
            preview_code = generator.generate_with_metadata(config)
        else:
            preview_code = generator.generate(config)

        return jsonify({
            'success': True,
            'preview_code': preview_code,
            'config_used': config
        })

    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dag_generator_bp.route('/api/generate', methods=['POST'])
def api_generate_dag():
    """API для генерации DAG'а"""
    try:
        data = request.get_json()
        generator_type = data.get('generator_type')
        config = data.get('config', {})
        
        generator = get_generator(generator_type)
        if not generator:
            return jsonify({
                'success': False,
                'error': f'Генератор "{generator_type}" не найден'
            }), 404

        # Валидируем данные
        try:
            validation_result = generator.validate_config(config)
            if not validation_result.get('valid', True):
                return jsonify({
                    'success': False,
                    'errors': validation_result.get('errors', [])
                }), 400
        except Exception as val_e:
            logger.warning(f"Validation failed: {val_e}")

        # Генерируем DAG с полными метаданными
        if hasattr(generator, 'generate_with_metadata'):
            dag_code = generator.generate_with_metadata(config)
        else:
            dag_code = generator.generate(config)
        
        # Сохраняем файл
        dag_id = config['dag_id']
        file_path = save_dag_file(dag_id, dag_code)

        return jsonify({
            'success': True,
            'message': f'DAG "{dag_id}" успешно создан',
            'dag_code': dag_code,
            'dag_id': dag_id,
            'dag_file_path': file_path
        })

    except Exception as e:
        logger.error(f"Error in api_generate_dag: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Ошибка создания DAG: {str(e)}'
        }), 500


@dag_generator_bp.route('/update', methods=['POST'])
def update_dag():
    """Обновление существующего DAG'а"""
    try:
        # Определяем тип запроса
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            generator_type = data.get('generator_type')
            form_data = data.get('form_data', {})
            original_dag_id = data.get('original_dag_id')
        else:
            generator_type = request.form.get('generator_type')
            form_data = dict(request.form)
            original_dag_id = form_data.pop('original_dag_id', None)
            form_data.pop('generator_type', None)
            form_data.pop('csrf_token', None)

        if not original_dag_id:
            return jsonify({
                'success': False,
                'error': 'Не указан оригинальный DAG ID'
            }), 400

        # Получаем генератор
        generator = get_generator(generator_type)
        if not generator:
            return jsonify({
                'success': False,
                'error': f'Генератор "{generator_type}" не найден'
            }), 404

        # Валидируем данные
        try:
            validation_result = generator.validate_config(form_data)
            if not validation_result.get('valid', True):
                return jsonify({
                    'success': False,
                    'errors': validation_result.get('errors', [])
                }), 400
        except Exception as val_e:
            logger.warning(f"Validation failed: {val_e}")

        # Ищем оригинальный файл
        parser = MetadataParser()
        original_dag_info = parser.find_dag_by_id(original_dag_id)
        if not original_dag_info:
            return jsonify({
                'success': False,
                'error': f'Оригинальный DAG "{original_dag_id}" не найден'
            }), 404

        original_file_path = original_dag_info['file_path']

        # Генерируем обновленный DAG с полными метаданными
        if hasattr(generator, 'generate_with_metadata'):
            updated_dag_code = generator.generate_with_metadata(form_data)
        else:
            updated_dag_code = generator.generate(form_data)

        # Проверяем, изменился ли ID
        new_dag_id = form_data['dag_id']
        if new_dag_id != original_dag_id:
            # Создаем новый файл с новым именем
            new_file_path = save_dag_file(new_dag_id, updated_dag_code)
            
            # Удаляем старый файл
            try:
                os.remove(original_file_path)
                logger.info(f"Removed old DAG file: {original_file_path}")
            except OSError as e:
                logger.warning(f"Could not remove old file {original_file_path}: {e}")

            file_path = new_file_path
            message = f'DAG переименован с "{original_dag_id}" на "{new_dag_id}" и обновлен'
        else:
            # Перезаписываем существующий файл
            with open(original_file_path, 'w', encoding='utf-8') as f:
                f.write(updated_dag_code)
            file_path = original_file_path
            message = f'DAG "{new_dag_id}" успешно обновлен'

        return jsonify({
            'success': True,
            'message': message,
            'dag_code': updated_dag_code,
            'dag_id': new_dag_id,
            'dag_file_path': file_path,
            'was_renamed': new_dag_id != original_dag_id
        })

    except Exception as e:
        logger.error(f"Error in update_dag: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Ошибка обновления DAG: {str(e)}'
        }), 500


@dag_generator_bp.route('/api/search-dags')
def api_search_dags():
    """API для поиска DAG'ов по dag_id с подсказками"""
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify({
                'success': True,
                'suggestions': []
            })

        parser = MetadataParser()
        generated_dags = parser.scan_generated_dags()
        
        # Фильтруем DAG'и по поисковому запросу
        suggestions = []
        for dag in generated_dags:
            dag_id = dag.get('cfg', {}).get('dag_id', '')
            if query.lower() in dag_id.lower():
                suggestions.append({
                    'dag_id': dag_id,
                    'generator_type': dag.get('gen', 'unknown'),
                    'description': dag.get('cfg', {}).get('description', '')[:100],
                    'last_modified': datetime.fromtimestamp(dag.get('file_mtime', 0)).strftime('%Y-%m-%d %H:%M'),
                    'version': dag.get('ver', 'unknown')
                })
        
        # Сортируем по релевантности (точные совпадения сначала, потом по алфавиту)
        suggestions.sort(key=lambda x: (
            0 if x['dag_id'].lower().startswith(query.lower()) else 1,
            x['dag_id']
        ))
        
        return jsonify({
            'success': True,
            'suggestions': suggestions[:10],
            'total_found': len(suggestions)
        })

    except Exception as e:
        logger.error(f"Error searching DAGs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dag_generator_bp.route('/api/dag/<dag_id>')
def api_get_dag(dag_id):
    """API для получения информации о конкретном DAG'е"""
    try:
        parser = MetadataParser()
        dag_info = parser.find_dag_by_id(dag_id)
        
        if not dag_info:
            return jsonify({
                'success': False,
                'error': f'DAG "{dag_id}" не найден или не содержит метаданных'
            }), 404

        # Добавляем дополнительную информацию
        dag_info['file_info'] = {
            'size': dag_info.get('file_size', 0),
            'last_modified': datetime.fromtimestamp(dag_info.get('file_mtime', 0)).isoformat(),
            'path': dag_info.get('file_path', '')
        }

        return jsonify({
            'success': True,
            'dag_info': dag_info
        })

    except Exception as e:
        logger.error(f"Error getting DAG {dag_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dag_generator_bp.route('/delete/<dag_id>', methods=['POST'])
def delete_dag(dag_id):
    """Удаление DAG'а"""
    try:
        parser = MetadataParser()
        dag_info = parser.find_dag_by_id(dag_id)
        
        if not dag_info:
            return jsonify({
                'success': False,
                'error': f'DAG "{dag_id}" не найден'
            }), 404

        file_path = dag_info['file_path']
        
        # Удаляем файл
        os.remove(file_path)
        
        logger.info(f"Deleted DAG file: {file_path}")
        
        return jsonify({
            'success': True,
            'message': f'DAG "{dag_id}" успешно удален'
        })

    except Exception as e:
        logger.error(f"Error deleting DAG {dag_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Ошибка удаления DAG: {str(e)}'
        }), 500
