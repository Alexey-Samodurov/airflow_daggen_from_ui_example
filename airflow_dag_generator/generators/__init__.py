"""
Система генераторов DAG
"""

# Импортируем базовые компоненты
from airflow_dag_generator.generators.base_generator import BaseGenerator
from airflow_dag_generator.generators.registry import (
    GeneratorRegistry,
    get_registry,
    register_generator,
    get_generator,
    list_generators
)
from airflow_dag_generator.generators.hello_world_generator import HelloWorldGenerator
from airflow_dag_generator.generators.discovery import (
    get_discovery_manager,
    discover_and_register_generators,
    start_hot_reload,
    stop_hot_reload,
    is_hot_reload_active,
    force_reload_all
)

import logging
import os

# from flask import Blueprint

# Создаем Blueprint для веб-интерфейса
# dag_generator_bp = Blueprint(
#     'dag_generator',
#     __name__,
#     template_folder='templates',
#     static_folder='templates/static',  # ✅ Исправлено
#     url_prefix='/dag-generator'
# )

logger = logging.getLogger(__name__)


def initialize_generator_system():
    """Инициализирует всю систему генераторов"""
    logger.info("Initializing DAG Generator system...")

    # 1. Регистрируем только встроенный hello_world генератор
    # (остальные будут обнаружены автоматически)
    builtin_generators = [
        HelloWorldGenerator(),
    ]

    registry = get_registry()
    builtin_count = 0

    for generator in builtin_generators:
        try:
            if registry.register(generator, force=True):
                builtin_count += 1
                logger.info(f"✅ Registered builtin generator: {generator.generator_name}")
        except Exception as e:
            logger.error(f"Failed to register builtin generator {generator.generator_name}: {e}")

    logger.info(f"Registered {builtin_count} builtin generators")

    # 2. Обнаруживаем и регистрируем ВСЕ внешние генераторы автоматически
    try:
        discovered_count = discover_and_register_generators()
        logger.info(f"Discovered {discovered_count} external generators")
    except Exception as e:
        logger.warning(f"Failed to discover external generators: {e}")
        discovered_count = 0

    # 3. Пытаемся запустить hot-reload (если доступен)
    hot_reload_started = False
    try:
        hot_reload_started = start_hot_reload()
        if hot_reload_started:
            logger.info("✅ Hot-reload system started")
        else:
            logger.info("ℹ️  Hot-reload not available (install watchdog for this feature)")
    except Exception as e:
        logger.warning(f"Could not start hot-reload: {e}")

    total_generators = len(registry)
    logger.info(f"🚀 DAG Generator system initialized successfully!")
    logger.info(f"📊 Total generators: {total_generators}")
    logger.info(f"🔥 Hot-reload: {'Active' if hot_reload_started else 'Inactive'}")

    # Проверяем, что у нас есть хотя бы hello_world генератор
    if total_generators == 0:
        logger.error("❌ No generators found! Something is wrong with initialization.")
    else:
        # Выводим список всех зарегистрированных генераторов
        generators_list = list_generators()
        logger.info(f"📋 Available generators: {[g['name'] for g in generators_list]}")

    return {
        'builtin_count': builtin_count,
        'discovered_count': discovered_count,
        'total_count': total_generators,
        'hot_reload_active': hot_reload_started
    }


# Инициализируем при импорте модуля
try:
    _init_result = initialize_generator_system()
    logger.info(f"Initialization result: {_init_result}")
except Exception as e:
    logger.error(f"Failed to initialize generator system: {e}")
    import traceback
    traceback.print_exc()
    _init_result = None

# Импортируем views после создания Blueprint для регистрации маршрутов
try:
    from airflow_dag_generator import views
    logger.info("✅ Views imported successfully")
except Exception as e:
    logger.error(f"❌ Failed to import views: {e}")
    import traceback
    traceback.print_exc()

# Public API
__all__ = [
    # Blueprint
    'dag_generator_bp',

    # Базовые классы
    'BaseGenerator',
    'GeneratorRegistry',

    # Функции реестра
    'get_registry',
    'register_generator',
    'get_generator',
    'list_generators',

    # Встроенные генераторы (только hello_world как пример)
    'HelloWorldGenerator',

    # Функции обнаружения и hot-reload
    'get_discovery_manager',
    'discover_and_register_generators',
    'start_hot_reload',
    'stop_hot_reload',
    'is_hot_reload_active',
    'force_reload_all',

    # Инициализация
    'initialize_generator_system'
]
