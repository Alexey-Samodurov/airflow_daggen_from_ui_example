"""
Генераторы DAG'ов
"""

from .hello_world_generator import HelloWorldGenerator

__all__ = ['HelloWorldGenerator', 'get_generator']

# Реестр генераторов
GENERATORS = {
    'hello_world': HelloWorldGenerator,
}

def get_generator(generator_type: str):
    """Получить генератор по типу"""
    generator_class = GENERATORS.get(generator_type)
    if generator_class:
        return generator_class()
    return None
