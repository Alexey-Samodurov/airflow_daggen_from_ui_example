"""
Airflow DAG Generator

Библиотека для генерации DAG'ов через веб-интерфейс Apache Airflow.
"""

__version__ = "0.1.0"
__author__ = "Aleksei Samodurov"
__email__ = "damestos988@gmail.com"
__description__ = "Airflow plugin for generating DAGs through web interface"

# Правильные относительные импорты
try:
    from .plugin import DagGeneratorPlugin
    from .views import dag_generator_bp
except ImportError as e:
    print(f"Warning: Could not import components: {e}")
    DagGeneratorPlugin = None
    dag_generator_bp = None

__all__ = [
    'DagGeneratorPlugin',
    'dag_generator_bp',
    '__version__',
    '__author__',
    '__email__',
    '__description__'
]

def get_version():
    """Получить версию пакета"""
    return __version__

def get_plugin():
    """Получить экземпляр плагина"""
    if DagGeneratorPlugin is None:
        raise ImportError("DagGeneratorPlugin not available")
    return DagGeneratorPlugin()
