"""
Генераторы DAG'ов
"""

import os
import sys

# Добавляем текущую папку в путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from hello_world_generator import HelloWorldGenerator

__all__ = ['HelloWorldGenerator']
