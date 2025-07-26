"""
Реестр генераторов DAG
"""
from typing import Dict, List, Optional, Any
import logging
from threading import RLock
from .base_generator import BaseGenerator

logger = logging.getLogger(__name__)


class GeneratorRegistry:
    """Потокобезопасный реестр генераторов"""

    def __init__(self):
        self._generators: Dict[str, BaseGenerator] = {}
        self._lock = RLock()

    def register(self, generator: BaseGenerator, force: bool = False) -> bool:
        """
        Регистрирует генератор в реестре

        Args:
            generator: Экземпляр генератора
            force: Перезаписать если уже существует

        Returns:
            True если успешно зарегистрирован
        """
        if not isinstance(generator, BaseGenerator):
            raise ValueError(f"Generator must be an instance of BaseGenerator, got {type(generator)}")

        with self._lock:
            name = generator.generator_name

            if name in self._generators and not force:
                logger.warning(f"Generator '{name}' already exists. Use force=True to overwrite.")
                return False

            self._generators[name] = generator
            logger.info(f"Registered generator: {name} ({generator.__class__.__name__})")
            return True

    def unregister(self, name: str) -> bool:
        """Удаляет генератор из реестра"""
        with self._lock:
            if name in self._generators:
                del self._generators[name]
                logger.info(f"Unregistered generator: {name}")
                return True
            return False

    def get(self, name: str) -> Optional[BaseGenerator]:
        """Получает генератор по имени"""
        with self._lock:
            return self._generators.get(name)

    def list_generators(self) -> List[Dict[str, Any]]:
        """Возвращает список всех зарегистрированных генераторов"""
        with self._lock:
            generators_list = []
            for generator in self._generators.values():
                try:
                    # Получаем информацию о генераторе
                    generator_info = {
                        'name': generator.generator_name,
                        'display_name': generator.get_display_name(),
                        'description': generator.get_description(),
                        'required_fields': generator.get_required_fields(),
                        'optional_fields': generator.get_optional_fields()
                    }
                    generators_list.append(generator_info)
                except Exception as e:
                    logger.error(f"Error getting info for generator {generator.generator_name}: {e}")
                    # Добавляем базовую информацию
                    generators_list.append({
                        'name': generator.generator_name,
                        'display_name': generator.generator_name.replace('_', ' ').title(),
                        'description': 'Generator description unavailable',
                        'required_fields': [],
                        'optional_fields': {}
                    })
            return generators_list

    def get_generators_dict(self) -> Dict[str, BaseGenerator]:
        """Возвращает словарь всех генераторов"""
        with self._lock:
            return self._generators.copy()

    def get_generator_names(self) -> List[str]:
        """Возвращает список имен всех генераторов"""
        with self._lock:
            return list(self._generators.keys())

    def clear(self):
        """Очищает весь реестр"""
        with self._lock:
            self._generators.clear()
            logger.info("Registry cleared")

    def reload_from_file(self, file_path: str) -> int:
        """
        Перезагружает генераторы из файла

        Returns:
            Количество перезагруженных генераторов
        """
        try:
            from pathlib import Path
            from .discovery import GeneratorDiscovery

            discovery = GeneratorDiscovery()
            generators = discovery._load_generators_from_file(Path(file_path))

            reloaded_count = 0
            for name, generator in generators.items():
                if self.register(generator, force=True):
                    reloaded_count += 1

            return reloaded_count

        except Exception as e:
            logger.error(f"Error reloading generators from {file_path}: {e}")
            return 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._generators)

    def __contains__(self, name: str) -> bool:
        with self._lock:
            return name in self._generators


# Глобальный реестр
_global_registry = GeneratorRegistry()


def get_registry() -> GeneratorRegistry:
    """Получает глобальный реестр генераторов"""
    return _global_registry


def register_generator(generator: BaseGenerator, force: bool = False) -> bool:
    """Регистрирует генератор в глобальном реестре"""
    return get_registry().register(generator, force)


def get_generator(name: str) -> Optional[BaseGenerator]:
    """Получает генератор из глобального реестра"""
    return get_registry().get(name)


def list_generators() -> List[Dict[str, Any]]:
    """Получает список всех генераторов из глобального реестра"""
    return get_registry().list_generators()


def get_generators_dict() -> Dict[str, BaseGenerator]:
    """Получает словарь всех генераторов из глобального реестра"""
    return get_registry().get_generators_dict()
