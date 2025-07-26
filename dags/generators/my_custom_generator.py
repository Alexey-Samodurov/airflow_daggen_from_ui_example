from airflow_dag_generator.generators.base_generator import BaseGenerator
from typing import Dict, Any, List
from datetime import datetime


class MyCustomGenerator(BaseGenerator):
    def __init__(self):
        super().__init__(generator_name="my_custom")

    def get_display_name(self) -> str:
        return "My Custom DAG"

    def get_description(self) -> str:
        return "Custom DAG generator for my specific needs"

    def get_required_fields(self) -> List[str]:
        return ['dag_id', 'schedule_interval', 'owner']

    def get_optional_fields(self) -> Dict[str, Any]:
        return {
            'description': 'Custom generated DAG',
            'custom_param': 'default_value'
        }

    def generate(self, form_data: Dict[str, Any]) -> str:
        # Ваш код генерации DAG
        return f'''
# Custom DAG generated at {datetime.now()}
from airflow import DAG
# ... ваш код DAG ...
'''
