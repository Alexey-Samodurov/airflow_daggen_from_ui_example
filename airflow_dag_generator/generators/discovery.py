"""
Система автообнаружения генераторов с hot-reload
"""
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from threading import RLock, Timer
from typing import List, Dict, Set

from airflow.configuration import conf

from .base_generator import BaseGenerator
from .registry import get_registry

# Опциональный импорт watchdog
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    Observer = None
    FileSystemEventHandler = None

logger = logging.getLogger(__name__)


class GeneratorFileHandler(FileSystemEventHandler):
    """Обработчик изменений файлов генераторов"""

    def __init__(self, discovery_manager):
        super().__init__()
        self.discovery_manager = discovery_manager
        self.reload_delay = 1.0
        self.pending_reloads = {}
        self.lock = RLock()

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return

        # Игнорируем служебные файлы
        if self._should_ignore_file(event.src_path):
            return

        self._schedule_reload(event.src_path)

    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return

        if self._should_ignore_file(event.src_path):
            return

        logger.info(f"New generator file detected: {event.src_path}")
        self._schedule_reload(event.src_path)

    def _should_ignore_file(self, file_path: str) -> bool:
        """Проверяет, нужно ли игнорировать файл"""
        path = Path(file_path)
        return (
                path.name.startswith('_') or
                path.name == '__init__.py' or
                '.pyc' in path.name or
                '__pycache__' in str(path)
        )

    def _schedule_reload(self, file_path: str):
        """Планирует перезагрузку с задержкой для избежания множественных вызовов"""
        with self.lock:
            # Отменяем предыдущую перезагрузку
            if file_path in self.pending_reloads:
                self.pending_reloads[file_path].cancel()

            # Планируем новую
            timer = Timer(self.reload_delay, self._reload_file, [file_path])
            self.pending_reloads[file_path] = timer
            timer.start()

    def _reload_file(self, file_path: str):
        """Выполняет перезагрузку файла"""
        try:
            reloaded_count = self.discovery_manager.reload_single_file(file_path)
            if reloaded_count > 0:
                logger.info(f"✅ Hot reloaded {reloaded_count} generator(s) from {file_path}")
            else:
                logger.debug(f"No generators found in {file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to hot reload {file_path}: {e}")
        finally:
            with self.lock:
                self.pending_reloads.pop(file_path, None)


class GeneratorDiscovery:
    """Менеджер обнаружения и hot-reload генераторов"""

    def __init__(self):
        self.discovery_paths = self._get_discovery_paths()
        self.loaded_modules = {}  # file_path -> (module_name, mod_time)
        self.observer = None
        self.watched_paths: Set[Path] = set()
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

    def discover_generators(self) -> Dict[str, BaseGenerator]:
        """Обнаруживает все генераторы в путях поиска"""
        discovered = {}

        for path in self.discovery_paths:
            try:
                path_generators = self._discover_in_path(path)
                discovered.update(path_generators)
            except Exception as e:
                logger.error(f"Error discovering in {path}: {e}")

        return discovered

    def _discover_in_path(self, path: Path) -> Dict[str, BaseGenerator]:
        """Обнаруживает генераторы в конкретном пути"""
        generators = {}

        logger.debug(f"Scanning for generators in: {path}")

        for py_file in path.rglob('*.py'):
            if self._should_skip_file(py_file):
                continue

            try:
                file_generators = self._load_generators_from_file(py_file)
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

    def _load_generators_from_file(self, file_path: Path) -> Dict[str, BaseGenerator]:
        """Загружает генераторы из Python файла"""
        generators = {}

        try:
            # Создаем уникальное имя модуля
            relative_path = self._get_relative_path(file_path)
            module_name = f"discovered_generator_{relative_path.replace('/', '_').replace('.py', '')}"

            # Проверяем время модификации
            mod_time = file_path.stat().st_mtime

            with self.lock:
                if file_path in self.loaded_modules:
                    cached_module_name, cached_mod_time = self.loaded_modules[file_path]
                    if cached_mod_time >= mod_time:
                        # Файл не изменился, возвращаем пустой результат
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

    def reload_single_file(self, file_path: str) -> int:
        """Перезагружает генераторы из одного файла"""
        path_obj = Path(file_path)

        try:
            generators = self._load_generators_from_file(path_obj)

            registry = get_registry()
            reloaded_count = 0

            for name, generator in generators.items():
                if registry.register(generator, force=True):
                    reloaded_count += 1

            return reloaded_count

        except Exception as e:
            logger.error(f"Error reloading file {file_path}: {e}")
            return 0

    def register_discovered_generators(self) -> int:
        """Регистрирует все обнаруженные генераторы"""
        registry = get_registry()
        discovered = self.discover_generators()

        registered_count = 0
        for name, generator in discovered.items():
            try:
                if registry.register(generator, force=True):
                    registered_count += 1
            except Exception as e:
                logger.error(f"Could not register generator {name}: {e}")

        logger.info(f"Registered {registered_count} discovered generators")
        return registered_count

    def start_hot_reload(self) -> bool:
        """Запускает систему hot-reload"""
        if not HAS_WATCHDOG:
            logger.error("Watchdog not available. Install with: pip install watchdog")
            return False

        if self.observer and self.observer.is_alive():
            logger.warning("Hot reload already running")
            return True

        try:
            self.observer = Observer()
            handler = GeneratorFileHandler(self)

            # Добавляем все пути для наблюдения
            for path in self.discovery_paths:
                if path.exists():
                    self.observer.schedule(handler, str(path), recursive=True)
                    self.watched_paths.add(path)
                    logger.info(f"Watching: {path}")

            if self.watched_paths:
                self.observer.start()
                logger.info("✅ Hot reload started")
                return True
            else:
                logger.warning("No valid paths to watch")
                return False

        except Exception as e:
            logger.error(f"Failed to start hot reload: {e}")
            return False

    def stop_hot_reload(self) -> bool:
        """Останавливает систему hot-reload"""
        if self.observer and self.observer.is_alive():
            try:
                self.observer.stop()
                self.observer.join(timeout=5)
                logger.info("🛑 Hot reload stopped")
                return True
            except Exception as e:
                logger.error(f"Error stopping hot reload: {e}")
                return False
        return True

    def is_hot_reload_active(self) -> bool:
        """Проверяет, активен ли hot-reload"""
        return self.observer and self.observer.is_alive()

    def force_reload_all(self) -> int:
        """Принудительно перезагружает все генераторы"""
        logger.info("Force reloading all generators...")

        # Очищаем кэш модулей
        with self.lock:
            modules_to_remove = []
            for module_name in sys.modules.keys():
                if module_name.startswith('discovered_generator_'):
                    modules_to_remove.append(module_name)

            for module_name in modules_to_remove:
                del sys.modules[module_name]

            self.loaded_modules.clear()

        # Перезагружаем
        return self.register_discovered_generators()


# Глобальный экземпляр
_discovery_manager = GeneratorDiscovery()


def get_discovery_manager() -> GeneratorDiscovery:
    """Получает глобальный менеджер обнаружения"""
    return _discovery_manager


def discover_and_register_generators() -> int:
    """Обнаруживает и регистрирует генераторы"""
    return _discovery_manager.register_discovered_generators()


def start_hot_reload() -> bool:
    """Запускает hot-reload"""
    return _discovery_manager.start_hot_reload()


def stop_hot_reload() -> bool:
    """Останавливает hot-reload"""
    return _discovery_manager.stop_hot_reload()


def is_hot_reload_active() -> bool:
    """Проверяет статус hot-reload"""
    return _discovery_manager.is_hot_reload_active()


def force_reload_all() -> int:
    """Принудительная перезагрузка всех генераторов"""
    return _discovery_manager.force_reload_all()
