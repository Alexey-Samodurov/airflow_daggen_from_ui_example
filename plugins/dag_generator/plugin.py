import os
import sys

# Добавляем текущую папку в путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from airflow.plugins_manager import AirflowPlugin

# Теперь можем импортировать без проблем
from views import dag_generator_bp


class DagGeneratorPlugin(AirflowPlugin):
    """Плагин для генерации DAG'ов через веб-интерфейс Airflow"""

    name = "dag_generator"

    # Используем только Flask Blueprint
    flask_blueprints = [dag_generator_bp]

    # Добавляем пункт в меню (для Airflow 2.0+)
    appbuilder_menu_items = [
        {
            "name": "Generate DAG",
            "category": "Tools",
            "category_icon": "fa-cogs",
            "href": "/dag-generator/",
        }
    ]

    # Определяем права доступа для плагина
    appbuilder_views = []
    
    # Добавляем требуемые разрешения
    security_manager_view_menus = [
        {
            "name": "DAG Generator",
            "permissions": [
                ("can_read", "DAG Generator"),
                ("can_create", "DAG Generator"),
            ]
        }
    ]
