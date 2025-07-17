"""
Определение плагина для Apache Airflow
"""
from airflow.plugins_manager import AirflowPlugin

# Относительный импорт
from .views import dag_generator_bp


class DagGeneratorPlugin(AirflowPlugin):
    """Плагин для генерации DAG'ов через веб-интерфейс Airflow"""

    name = "dag_generator"
    
    flask_blueprints = [dag_generator_bp]

    appbuilder_menu_items = [
        {
            "name": "Generate DAG",
            "category": "Tools",
            "category_icon": "fa-cogs",
            "href": "/dag-generator/",
        }
    ]

    appbuilder_views = []
    
    security_manager_view_menus = [
        {
            "name": "DAG Generator",
            "permissions": [
                ("can_read", "DAG Generator"),
                ("can_create", "DAG Generator"),
            ]
        }
    ]

    @staticmethod
    def get_version() -> str:
        """Возвращает версию плагина"""
        try:
            from importlib.metadata import version
            return version("airflow-dag-generator")
        except ImportError:
            return "0.1.0"
