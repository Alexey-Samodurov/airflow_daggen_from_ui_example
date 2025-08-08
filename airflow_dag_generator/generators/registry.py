from typing import Dict, List, Optional, Any
import logging
from threading import RLock
from .base_generator import BaseGenerator

logger = logging.getLogger(__name__)


class GeneratorRegistry:
    """
    Registry for managing generator instances.

    This class provides thread-safe methods to register, unregister, retrieve, list, and manage generator instances.
    It ensures only instances of BaseGenerator are registered. Additionally, it supports overwriting existing
    generator registrations and provides utility methods for listing and accessing generator metadata.
    """

    def __init__(self):
        """
        Initializes an instance of the class.

        Attributes:
            _generators (Dict[str, BaseGenerator]): A mapping of string keys to BaseGenerator instances.
            _lock (RLock): A reentrant lock for thread-safe operations.
        """
        self._generators: Dict[str, BaseGenerator] = {}
        self._lock = RLock()

    def register(self, generator: BaseGenerator, force: bool = False) -> bool:
        """
        Registers a generator instance to the manager with an optional overwrite capability.

        Args:
            generator (BaseGenerator): The generator instance to register.
            force (bool): If True, overwrite the existing generator with the same name.

        Returns:
            bool: True if the generator was registered successfully, otherwise False.

        Raises:
            ValueError: If the provided generator is not an instance of BaseGenerator.
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
        """
        Unregisters a generator by its name.

        Checks if a generator with the provided name exists, unregisters it,
        and removes it from the internal collection of generators.

        Args:
            name: The name of the generator to be unregistered.

        Returns:
            True if the generator was successfully unregistered, otherwise False.
        """
        with self._lock:
            if name in self._generators:
                del self._generators[name]
                logger.info(f"Unregistered generator: {name}")
                return True
            return False

    def get(self, name: str) -> Optional[BaseGenerator]:
        """
        Retrieves a generator by its name.

        This method fetches a generator instance from the internal storage, if available,
        based on the given name.

        Args:
            name (str): The name of the generator to retrieve.

        Returns:
            Optional[BaseGenerator]: The generator instance if found, otherwise None.
        """
        with self._lock:
            return self._generators.get(name)

    def list_generators(self) -> List[Dict[str, Any]]:
        """
        Retrieves a list of generators with their associated information.

        The method returns details about each available generator, including its name, display name,
        description, required fields, and optional fields. If an error occurs during information
        retrieval for a generator, default information is included instead.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each containing details about a generator.
        """
        with self._lock:
            generators_list = []
            for generator in self._generators.values():
                try:
                    # Получаем информацию о генераторе
                    generator_info = {
                        'name': generator.generator_name,
                        'display_name': generator.get_display_name(),
                        'description': generator.get_description()
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
        """
        Returns a copy of the registered generators dictionary in a thread-safe manner.

        Raises:
            None

        Returns:
            Dict[str, BaseGenerator]: A copy of the registered generators.
        """
        with self._lock:
            return self._generators.copy()

    def get_generator_names(self) -> List[str]:
        """
        Fetch the names of all available generators.

        Returns:
            List[str]: A list containing the names of all available generators.
        """
        with self._lock:
            return list(self._generators.keys())

    def list_all(self) -> List[str]:
        """
        Lists all generator names available.

        Returns:
            List[str]: A list containing the names of all generators.
        """
        return self.get_generator_names()

    def clear(self):
        """
        Clears the registry of all stored generators in a thread-safe manner.

        This method acquires a lock to ensure that the registry is safely cleared even
        when accessed concurrently. Logging is performed to indicate the clearing process.
        """
        with self._lock:
            self._generators.clear()
            logger.info("Registry cleared")

    def __len__(self) -> int:
        with self._lock:
            return len(self._generators)

    def __contains__(self, name: str) -> bool:
        with self._lock:
            return name in self._generators


# Глобальный реестр
_global_registry = GeneratorRegistry()


def get_registry() -> GeneratorRegistry:
    """
    Retrieves the global generator registry instance.

    The function returns the single global instance of the generator registry
    used throughout the application for managing generators.

    Returns:
        GeneratorRegistry: The global registry instance.
    """
    return _global_registry


def register_generator(generator: BaseGenerator, force: bool = False) -> bool:
    """
    Registers a generator in the registry, allowing it to be used.

    If a generator with the same name already exists, it will only be replaced
    if the 'force' parameter is set to True. This function ensures that the
    specified generator is appropriately recognized by the system.

    Args:
        generator (BaseGenerator): The generator instance to register.
        force (bool, optional): Whether to overwrite existing generator. Defaults to False.

    Returns:
        bool: True if the generator was successfully registered, else False.
    """
    return get_registry().register(generator, force)


def get_generator(name: str) -> Optional[BaseGenerator]:
    """
    Fetches a generator instance by its name from the global registry.

    This function retrieves a generator object registered under the provided
    name within the global registry. If the specified name does not exist in
    the registry, None is returned.

    Args:
        name (str): The unique identifier of the generator to fetch.

    Returns:
        Optional[BaseGenerator]: The generator instance if found, otherwise None.
    """
    return get_registry().get(name)


def list_generators() -> List[Dict[str, Any]]:
    """
    Lists all available generators from the registry.

    This function retrieves and returns a list of registered generators from the
    registry. Each generator is represented as a dictionary containing relevant
    information.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a generator
        with its associated details.
    """
    return get_registry().list_generators()


def get_generators_dict() -> Dict[str, BaseGenerator]:
    """
    Returns a dictionary of registered generators.

    This method retrieves a dictionary containing instances of all registered
    generators using the registry system. The dictionary keys represent the
    generator names, and the values are the corresponding generator instances.

    Returns:
        Dict[str, BaseGenerator]: A dictionary mapping generator names to their
        respective generator instances.
    """
    return get_registry().get_generators_dict()
