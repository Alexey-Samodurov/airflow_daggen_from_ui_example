from airflow.plugins_manager import AirflowPlugin
from .views import dag_generator_bp


class DagGeneratorPlugin(AirflowPlugin):
    """
    Represents a custom Airflow plugin for generating DAGs.

    The DagGeneratorPlugin enables integration of a custom DAG generator into the Airflow web
    UI under a specific category and menu. It provides additional objects for use in the Airflow
    application such as blueprints and menu items, while also managing security and permissions.
    The plugin includes version retrieval for its package.

    Attributes:
        name (str): The name of the plugin.
        flask_blueprints (list): A list of Flask blueprints to register.
        appbuilder_menu_items (list): Definitions of custom menu items for the Airflow navigation bar.
        appbuilder_views (list): A list of views to add to the AppBuilder.
        security_manager_view_menus (list): View menus with permissions for security management.
    """

    name = "dag_generator"
    
    flask_blueprints = [dag_generator_bp]

    appbuilder_menu_items = [
        {
            "name": "Generate DAG",
            "category": "Custom tools",
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
            return "no version info available"
