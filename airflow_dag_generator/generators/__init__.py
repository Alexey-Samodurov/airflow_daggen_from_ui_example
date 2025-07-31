"""
Система генераторов DAG
"""

# Импортируем базовые компоненты
import threading
import logging

from airflow_dag_generator.generators.base_generator import BaseGenerator
from airflow_dag_generator.generators.registry import (
    GeneratorRegistry,
    get_registry,
    register_generator,
    get_generator,
    list_generators
)
from airflow_dag_generator.generators.discovery import (
    get_discovery_manager,
    discover_and_register_generators,
    manual_reload_all
)

logger = logging.getLogger(__name__)

# Флаг инициализации
_initialized = False
_initialization_lock = threading.RLock()

def initialize_generator_system(force_reload=False):
    """Инициализирует всю систему генераторов с защитой от повторной инициализации"""
    global _initialized
    
    with _initialization_lock:
        if _initialized and not force_reload:
            logger.debug("Generator system already initialized, skipping")
            registry = get_registry()
            return {
                'total_count': len(registry),
                'discovered_count': 0,
                'already_initialized': True
            }
        
        logger.info("Initializing DAG Generator system...")
        registry = get_registry()
        
        # Если принудительная перезагрузка - очищаем реестр
        if force_reload:
            registry.clear()
            logger.info("Registry cleared for force reload")
        
        # Обнаруживаем и регистрируем внешние генераторы
        discovered_count = 0
        try:
            discovered_count = discover_and_register_generators()
            logger.info(f"Discovered {discovered_count} external generators")
        except Exception as e:
            logger.warning(f"Failed to discover external generators: {e}")
        
        total_generators = len(registry)
        logger.info(f"🚀 DAG Generator system initialized successfully!")
        logger.info(f"📊 Total generators: {total_generators}")
        
        # Выводим список всех зарегистрированных генераторов
        if total_generators > 0:
            generators_list = list_generators()
            generator_names = [g['name'] for g in generators_list]
            logger.info(f"📋 Available generators: {generator_names}")
        else:
            logger.error("❌ No generators found! Something is wrong with initialization.")
        
        _initialized = True
        
        return {
            'discovered_count': discovered_count,
            'total_count': total_generators,
            'already_initialized': False
        }


def safe_manual_reload():
    """Безопасная ручная перезагрузка всех генераторов"""
    logger.info("=== MANUAL RELOAD REQUESTED ===")
    
    try:
        # Принудительная инициализация
        result = initialize_generator_system(force_reload=True)
        
        # Дополнительно пытаемся через discovery manager
        try:
            discovery_manager = get_discovery_manager()
            if discovery_manager:
                additional_count = discovery_manager.manual_reload_all()
                logger.info(f"Discovery manager loaded additional {additional_count} generators")
        except Exception as e:
            logger.warning(f"Discovery manager reload failed: {e}")
        
        # Финальная проверка
        registry = get_registry()
        final_count = len(registry)
        
        logger.info(f"=== MANUAL RELOAD COMPLETED: {final_count} total generators ===")
        return final_count
        
    except Exception as e:
        logger.error(f"Manual reload failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def get_all_generators():
    """Возвращает словарь всех доступных генераторов"""
    registry = get_registry()
    generators_dict = {}
    
    for name in registry.list_all():
        try:
            generator = registry.get(name)
            if generator:
                generators_dict[name] = generator
        except Exception as e:
            logger.error(f"Error getting generator {name}: {e}")
    
    return generators_dict


# Инициализируем при импорте модуля (но только один раз)
try:
    import threading
    _init_result = initialize_generator_system()
    logger.info(f"Initial initialization result: {_init_result}")
except Exception as e:
    logger.error(f"Failed to initialize generator system: {e}")
    import traceback
    traceback.print_exc()
    _init_result = None

# Public API
__all__ = [
    # Базовые классы
    'BaseGenerator',
    'GeneratorRegistry',

    # Функции реестра
    'get_registry',
    'register_generator',
    'get_generator',
    'get_all_generators',  # ДОБАВЛЕНО!
    'list_generators',

    # Функции обнаружения и hot-reload
    'get_discovery_manager',
    'discover_and_register_generators',
    'manual_reload_all',

    # Инициализация
    'initialize_generator_system',
    'safe_manual_reload',
]
