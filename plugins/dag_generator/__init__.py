
"""
DAG Generator Plugin для Apache Airflow
"""

import os
import sys

# Добавляем текущую папку в путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

__version__ = "1.0.0"

# Импортируем основные компоненты (с обработкой ошибок)
try:
    from plugin import DagGeneratorPlugin
except ImportError as e:
    print(f"Warning: Could not import DagGeneratorPlugin: {e}")
    DagGeneratorPlugin = None

# Это нужно для того, чтобы Airflow автоматически нашел плагин
__all__ = ['DagGeneratorPlugin']
