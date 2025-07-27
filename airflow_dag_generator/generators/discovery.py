"""
Система обнаружения генераторов с ручной перезагрузкой
"""
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from threading import RLock
from typing import List, Dict

from airflow.configuration import conf

from .base_generator import BaseGenerator
from .registry import get_registry

logger = logging.getLogger(__name__)


class GeneratorDiscovery:
    """Менеджер обнаружения генераторов с ручной перезагрузкой"""

    def __init__(self):
        self.discovery_paths = self._get_discovery_paths()
        self.loaded_modules = {}  # file_path -> (module_name, mod_time)
        self.lock = RLock()

    def _get_discovery_paths(self) -> List[Path]:
        """Получает список путей для поиска генераторов"""
        paths = []

        # 1. Plugins folder
        try:
            plugins_folder = conf.get('core', 'plugins_folder')
            if plugins_folder:
                plugins_path = Path(plugins_folder)
                if plugins_path.exists():
                    # Поддиректория generators
                    generators_path = plugins_path / 'generators'
                    if generators_path.exists():
                        paths.append(generators_path)

                    # Также сканируем сам plugins folder
                    paths.append(plugins_path)
        except Exception as e:
            logger.warning(f"Could not get plugins folder: {e}")

        # 2. DAGs folder (поддиректория generators)
        try:
            dags_folder = conf.get('core', 'dags_folder')
            if dags_folder:
                dags_generators_path = Path(dags_folder) / 'generators'
                if dags_generators_path.exists():
                    paths.append(dags_generators_path)
        except Exception as e:
            logger.warning(f"Could not get dags folder: {e}")

        # 3. Переменная окружения
        env_paths = os.getenv('AIRFLOW_DAG_GENERATOR_PATHS', '')
        if env_paths:
            for path_str in env_paths.split(':'):
                path = Path(path_str.strip())
                if path.exists() and path.is_dir():
                    paths.append(path)

        # 4. Текущая директория (для разработки)
        current_generators = Path.cwd() / 'generators'
        if current_generators.exists():
            paths.append(current_generators)

        logger.info(f"Generator discovery paths: {[str(p) for p in paths]}")
        return paths

    def discover_generators(self, force_reload=False) -> Dict[str, BaseGenerator]:
        """Обнаруживает все генераторы в путях поиска"""
        discovered = {}

        for path in self.discovery_paths:
            try:
                path_generators = self._discover_in_path(path, force_reload=force_reload)
                discovered.update(path_generators)
            except Exception as e:
                logger.error(f"Error discovering in {path}: {e}")

        return discovered

    def _discover_in_path(self, path: Path, force_reload=False) -> Dict[str, BaseGenerator]:
        """Обнаруживает генераторы в конкретном пути"""
        generators = {}

        logger.debug(f"Scanning for generators in: {path}")

        for py_file in path.rglob('*.py'):
            if self._should_skip_file(py_file):
                continue

            try:
                file_generators = self._load_generators_from_file(py_file, force_reload=force_reload)
                generators.update(file_generators)
            except Exception as e:
                logger.warning(f"Could not load generators from {py_file}: {e}")

        return generators

    def _should_skip_file(self, file_path: Path) -> bool:
        """Проверяет, нужно ли пропустить файл"""
        return (
                file_path.name.startswith('_') or
                file_path.name == '__init__.py' or
                '__pycache__' in str(file_path)
        )

    def _load_generators_from_file(self, file_path: Path, force_reload=False) -> Dict[str, BaseGenerator]:
        """Загружает генераторы из Python файла"""
        generators = {}

        try:
            # Создаем уникальное имя модуля
            relative_path = self._get_relative_path(file_path)
            module_name = f"discovered_generator_{relative_path.replace('/', '_').replace('.py', '')}"

            # Проверяем время модификации
            mod_time = file_path.stat().st_mtime

            with self.lock:
                # Если принудительная перезагрузка - удаляем из кэша
                if force_reload and file_path in self.loaded_modules:
                    cached_module_name, _ = self.loaded_modules[file_path]
                    if cached_module_name in sys.modules:
                        del sys.modules[cached_module_name]
                    del self.loaded_modules[file_path]
                
                # Проверяем кэш только если не принудительная перезагрузка
                elif not force_reload and file_path in self.loaded_modules:
                    cached_module_name, cached_mod_time = self.loaded_modules[file_path]
                    if cached_mod_time >= mod_time:
                        # Файл не изменился, возвращаем пустой результат
                        logger.debug(f"Skipping {file_path} - not modified")
                        return generators

                    # Удаляем старый модуль
                    if cached_module_name in sys.modules:
                        del sys.modules[cached_module_name]

            # Загружаем модуль
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return generators

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Ищем классы генераторов
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseGenerator) and
                        obj != BaseGenerator and
                        not inspect.isabstract(obj)):

                    try:
                        generator = obj()
                        generators[generator.generator_name] = generator
                        logger.info(f"Loaded generator '{generator.generator_name}' from {file_path}")
                    except Exception as e:
                        logger.error(f"Could not instantiate {name} from {file_path}: {e}")

            # Обновляем кэш
            with self.lock:
                self.loaded_modules[file_path] = (module_name, mod_time)

        except Exception as e:
            logger.error(f"Error loading module from {file_path}: {e}")

        return generators

    def _get_relative_path(self, file_path: Path) -> str:
        """Получает относительный путь файла"""
        for discovery_path in self.discovery_paths:
            try:
                if file_path.is_relative_to(discovery_path):
                    return str(file_path.relative_to(discovery_path))
            except (ValueError, AttributeError):
                continue
        return file_path.name

    def manual_reload_all(self) -> int:
        """Ручная перезагрузка всех генераторов"""
        logger.info("Manual reload of all generators requested...")

        # 1. СНАЧАЛА ОЧИЩАЕМ РЕЕСТР - ЭТО ВАЖНО!
        registry = get_registry()
        registry.clear()
        logger.info("Registry cleared")

        # 2. Очищаем кэш модулей
        with self.lock:
            modules_to_remove = []
            for module_name in sys.modules.keys():
                if module_name.startswith('discovered_generator_'):
                    modules_to_remove.append(module_name)

            for module_name in modules_to_remove:
                del sys.modules[module_name]

            self.loaded_modules.clear()
            logger.info(f"Cleared {len(modules_to_remove)} cached modules")

        # 3. Принудительно перезагружаем все генераторы
        count = self.register_discovered_generators(force_reload=True)
        logger.info(f"Manual reload completed: {count} generators loaded")
        return count

    def register_discovered_generators(self, force_reload=False) -> int:
        """Регистрирует все обнаруженные генераторы"""
        registry = get_registry()
        discovered = self.discover_generators(force_reload=force_reload)

        registered_count = 0
        for name, generator in discovered.items():
            try:
                if registry.register(generator, force=True):
                    registered_count += 1
            except Exception as e:
                logger.error(f"Could not register generator {name}: {e}")

        logger.info(f"Registered {registered_count} discovered generators")
        return registered_count

    def get_discovery_stats(self) -> Dict:
        """Получает статистику обнаружения генераторов"""
        stats = {
            'discovery_paths': [str(p) for p in self.discovery_paths],
            'loaded_modules_count': len(self.loaded_modules),
            'loaded_files': []
        }

        with self.lock:
            for file_path, (module_name, mod_time) in self.loaded_modules.items():
                stats['loaded_files'].append({
                    'file_path': str(file_path),
                    'module_name': module_name,
                    'mod_time': mod_time,
                    'exists': file_path.exists()
                })

        return stats


# Глобальный экземпляр
_discovery_manager = GeneratorDiscovery()


def get_discovery_manager() -> GeneratorDiscovery:
    """Получает глобальный менеджер обнаружения"""
    return _discovery_manager


def discover_and_register_generators() -> int:
    """Обнаруживает и регистрирует генераторы"""
    return _discovery_manager.register_discovered_generators()


def manual_reload_all() -> int:
    """Ручная перезагрузка всех генераторов"""
    return _discovery_manager.manual_reload_all()


def get_discovery_stats() -> Dict:
    """Получает статистику обнаружения"""
    return _discovery_manager.get_discovery_stats()
