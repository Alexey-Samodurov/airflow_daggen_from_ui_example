import logging
import os
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify

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
    """
    Handles the routing for the index path and renders the main page with available generators.

    Raises:
        Any raised exceptions are handled within the route handler or the called functions.

    Returns:
        Rendered template for the index page including all available generators.
    """
    generators = get_all_generators()
    return render_template('index.html', generators=generators)


@dag_generator_bp.route('/api/generators')
def api_generators():
    """
    Handles HTTP GET requests to fetch all available DAG generators.

    This endpoint retrieves a list of DAG generators, including their metadata like name, display name,
    description, and class name for easier identification and usage. If any errors occur during the
    retrieval or processing of individual generators, fallback values are used to ensure a response
    is constructed.

    Args:
        None

    Returns:
        Response: A JSON response containing the status, a list of generators, and a count of the
        generators.

    Raises:
        None directly, but returns a 500 HTTP status in case of errors during processing.
    """
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
    """
    Handles API request to retrieve form fields for a specific generator.

    This endpoint fetches the required and optional form fields for a specified
    generator by its name. Additional generator metadata such as display name,
    description, and version is also included in the response.

    Args:
        generator_name (str): The name of the generator.

    Returns:
        Response: JSON object containing the success status, generator details,
        and form fields. If the generator is not found, a 404 status code with
        an appropriate error message is returned. For failed field retrieval or
        other errors, a 500 status code with an error message is returned.
    """
    try:
        logger.info(f"Getting fields for generator: {generator_name}")
        
        generator = get_generator(generator_name)
        if not generator:
            logger.error(f"Generator '{generator_name}' not found")
            return jsonify({
                'success': False,
                'error': f'Генератор "{generator_name}" не найден'
            }), 404

        try:
            form_fields = generator.get_form_fields()
            logger.info(f"Got {len(form_fields)} fields for generator {generator_name}")
        except Exception as e:
            logger.error(f"Error getting form fields: {e}")
            # Fallback: пытаемся собрать поля вручную
            form_fields = []
            
            # # Обязательные поля
            # try:
            #     required_fields = generator.get_required_fields()
            #     for field_name in required_fields:
            #         form_fields.append({
            #             'name': field_name,
            #             'type': 'text',
            #             'label': field_name.replace('_', ' ').title(),
            #             'required': True,
            #             'placeholder': f'Enter {field_name}...'
            #         })
            # except Exception as req_e:
            #     logger.error(f"Error getting required fields: {req_e}")
            #
            # # Опциональные поля
            # try:
            #     optional_fields = generator.get_optional_fields()
            #     for field_name, default_value in optional_fields.items():
            #         form_fields.append({
            #             'name': field_name,
            #             'type': 'text',
            #             'label': field_name.replace('_', ' ').title(),
            #             'required': False,
            #             'default': default_value,
            #             'placeholder': f'Enter {field_name}...'
            #         })
            # except Exception as opt_e:
            #     logger.error(f"Error getting optional fields: {opt_e}")

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
    """
    Handles manual reload of generators via API.

    This endpoint allows manual reload of generators through a POST request.
    A success or error response is returned based on the operation outcome.

    Returns:
        dict: A JSON response containing the status of the reload operation.
        HTTP Status Code: 200 on success, 500 on failure.
    """
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
    """
    Handles the API endpoint for checking reload status of DAGs.

    This function processes a request to check the status of DAG reloads by fetching the discovery statistics
    from the related module. If an error occurs during the process, it logs the error and returns an error response.

    Returns:
        flask.Response: A JSON response containing success status and reload statistics or error details.

    Raises:
        Exception: If any error occurs during obtaining the discovery statistics.
    """
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
    """
    Handles the creation of a Directed Acyclic Graph (DAG) based on received data.

    This function processes a POST request to generate and save a DAG definition based on provided generator type and form
    data. Validates the input, generates DAG code using the appropriate generator, and saves the resulting DAG to a file.

    Raises:
        Exception: If an unexpected error occurs during DAG creation.

    Returns:
        JSON response:
            - On success: Returns a JSON object with success flag, DAG code, DAG ID, and file path.
            - On failure: Returns a JSON object with error details and corresponding status code.
    """
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

        # Получаем генератор
        generator = get_generator(generator_type)
        if not generator:
            return jsonify({
                'success': False,
                'error': f'Генератор "{generator_type}" не найден'
            }), 404

        try:
            validation_result = generator.validate_config(form_data)
            if not validation_result.get('valid', True):
                return jsonify({
                    'success': False,
                    'errors': validation_result.get('errors', [])
                }), 400
        except Exception as val_e:
            logger.warning(f"Validation failed: {val_e}")

        if hasattr(generator, 'generate_with_metadata'):
            dag_code = generator.generate_with_metadata(form_data)
        else:
            dag_code = generator.generate(form_data)
        
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
    """
    Handles the `/api/preview` endpoint for generating a DAG preview with metadata and configuration validation.

    Raises:
        404: If the requested generator type is not found.
        400: If the provided configuration fails validation.
        500: For any unexpected server errors during processing.

    Returns:
        Response: Contains the success status, preview code or errors. In case of success, includes the configuration used.
    """
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
    """
    Handles the DAG generation API endpoint.

    This function processes POST requests to generate Directed Acyclic Graph (DAG) files based on the provided
    generator type and configuration. It validates the configurations, invokes the appropriate generator, and saves
    the generated DAG file.

    Args:
        None

    Returns:
        JSON response indicating the success or failure of the DAG generation process. Includes details like
        DAG code, DAG ID, and file path on success. Provides error messages on failure.
    """
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

        try:
            validation_result = generator.validate_config(config)
            if not validation_result.get('valid', True):
                return jsonify({
                    'success': False,
                    'errors': validation_result.get('errors', [])
                }), 400
        except Exception as val_e:
            logger.warning(f"Validation failed: {val_e}")

        dag_code = generator.generate_with_metadata(config)
        
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
    """
    Handles updates for existing Directed Acyclic Graphs (DAGs).

    This function determines the request's content type and processes the input data accordingly. It retrieves and validates
    the generator type and configuration data against predefined rules. The function updates or renames an existing DAG file
    based on the provided new configuration, removes outdated files if necessary, and returns a JSON response detailing
    the operation's result.

    Args:
        None

    Returns:
        Response: A response object containing the update result in JSON format. Includes update status, errors, and the
        updated DAG code if successful.

    Raises:
        None directly, but logs and responds with errors encountered during processing.
    """
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

        generator = get_generator(generator_type)
        if not generator:
            return jsonify({
                'success': False,
                'error': f'Генератор "{generator_type}" не найден'
            }), 404

        try:
            validation_result = generator.validate_config(form_data)
            if not validation_result.get('valid', True):
                return jsonify({
                    'success': False,
                    'errors': validation_result.get('errors', [])
                }), 400
        except Exception as val_e:
            logger.warning(f"Validation failed: {val_e}")

        parser = MetadataParser()
        original_dag_info = parser.find_dag_by_id(original_dag_id)
        if not original_dag_info:
            return jsonify({
                'success': False,
                'error': f'Оригинальный DAG "{original_dag_id}" не найден'
            }), 404

        original_file_path = original_dag_info['file_path']

        if hasattr(generator, 'generate_with_metadata'):
            updated_dag_code = generator.generate_with_metadata(form_data)
        else:
            updated_dag_code = generator.generate(form_data)

        new_dag_id = form_data['dag_id']
        if new_dag_id != original_dag_id:
            new_file_path = save_dag_file(new_dag_id, updated_dag_code)
            
            try:
                os.remove(original_file_path)
                logger.info(f"Removed old DAG file: {original_file_path}")
            except OSError as e:
                logger.warning(f"Could not remove old file {original_file_path}: {e}")

            file_path = new_file_path
            message = f'DAG переименован с "{original_dag_id}" на "{new_dag_id}" и обновлен'
        else:
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
    """
    Handles API requests to search through generated DAGs.

    This endpoint allows a client to search for DAGs by providing a query string. The search will evaluate DAG IDs and
    return matching results with metadata related to the DAGs.

    Args:
        None. The request is expected to have a `q` parameter in the query string with a minimum length of 2 characters.

    Returns:
        Response: A JSON object containing the success status, an array of matching DAG suggestions, and the total
        number of matches found. In case of an error, a JSON object with an error message and HTTP 500 status is returned.
    """
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify({
                'success': True,
                'suggestions': []
            })

        parser = MetadataParser()
        generated_dags = parser.scan_generated_dags()
        
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
    """
    Handles API requests to retrieve DAG metadata by its ID.

    Args:
        dag_id: The ID of the DAG to be retrieved.

    Returns:
        JSON response containing success status and DAG metadata if found. Returns
        404 if the DAG is not found or lacks metadata. In case of server error,
        returns a 500 status with the error message.
    """
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
    """
    Handles the deletion of a specified DAG by its ID.

    Parses the DAG metadata to locate the file associated with the specified DAG
    and proceeds to delete it. Returns a success or error response based on the
    outcome of the operation.

    Args:
        dag_id (str): The unique identifier of the DAG to be deleted.

    Returns:
        Response object: A JSON response containing the success status, message,
        or error details.
    """
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
