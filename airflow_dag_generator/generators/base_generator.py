"""
Базовый класс для генераторов DAG
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class BaseGenerator(ABC):
    """Базовый абстрактный класс для всех генераторов DAG"""

    def __init__(self, generator_name: str):
        """
        Инициализация базового генератора

        Args:
            generator_name: Уникальное имя генератора (например, 'hello_world')
        """
        self.generator_name = generator_name

    # Основные абстрактные методы

    @abstractmethod
    def get_display_name(self) -> str:
        """Возвращает человекочитаемое название генератора"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Возвращает описание генератора"""
        pass

    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """Возвращает список обязательных полей для генерации"""
        pass

    @abstractmethod
    def get_optional_fields(self) -> Dict[str, Any]:
        """Возвращает словарь необязательных полей с значениями по умолчанию"""
        pass

    @abstractmethod
    def generate(self, form_data: Dict[str, Any]) -> str:
        """
        Основной метод генерации DAG из конфигурации

        Args:
            form_data: Словарь с данными из формы

        Returns:
            Строка с сгенерированным Python кодом DAG
        """
        pass

    # Методы с реализацией по умолчанию (могут быть переопределены)

    def get_form_fields(self) -> List[Dict[str, Any]]:
        """
        Возвращает конфигурацию полей для веб-формы
        Может быть переопределен для кастомизации UI
        """
        fields = []

        # Обязательные поля
        for field_name in self.get_required_fields():
            field_config = self._get_default_field_config(field_name, required=True)
            fields.append(field_config)

        # Необязательные поля
        for field_name, default_value in self.get_optional_fields().items():
            field_config = self._get_default_field_config(field_name, required=False)
            field_config['default'] = default_value
            fields.append(field_config)

        return fields

    def _get_default_field_config(self, field_name: str, required: bool = True) -> Dict[str, Any]:
        """Генерирует конфигурацию поля по умолчанию"""
        field_name_lower = field_name.lower()

        # Определяем тип поля на основе имени
        if 'email' in field_name_lower:
            field_type = 'email'
            placeholder = 'user@example.com'
        elif 'password' in field_name_lower:
            field_type = 'password'
            placeholder = ''
        elif 'schedule' in field_name_lower:
            field_type = 'select'
            placeholder = ''
        elif 'description' in field_name_lower:
            field_type = 'textarea'
            placeholder = 'Enter description...'
        elif 'tags' in field_name_lower:
            field_type = 'text'
            placeholder = 'tag1, tag2, tag3'
        elif field_name_lower in ['retries', 'max_active_runs', 'chunk_size']:
            field_type = 'number'
            placeholder = ''
        elif field_name_lower in ['catchup', 'depends_on_past']:
            field_type = 'checkbox'
            placeholder = ''
        else:
            field_type = 'text'
            placeholder = f'Enter {field_name.replace("_", " ").lower()}...'

        return {
            'name': field_name,
            'type': field_type,
            'label': field_name.replace('_', ' ').title(),
            'required': required,
            'placeholder': placeholder
        }

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Валидирует конфигурацию для генерации DAG

        Returns:
            Dict с ключами: valid (bool), errors (List[str]), warnings (List[str])
        """
        errors = []
        warnings = []

        # Проверяем обязательные поля
        for field in self.get_required_fields():
            value = config.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"Field '{field}' is required")

        # Базовые проверки
        dag_id = config.get('dag_id', '').strip()
        if dag_id:
            if not dag_id.replace('_', '').replace('-', '').isalnum():
                errors.append("DAG ID must contain only letters, numbers, underscores and hyphens")
            if len(dag_id) > 200:
                errors.append("DAG ID is too long (max 200 characters)")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def get_preview_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию для предварительного просмотра"""
        config = {}

        # Заполняем обязательные поля примерами
        required_examples = {
            'dag_id': f'example_{self.generator_name}_dag',
            'owner': 'airflow',
            'schedule_interval': '@daily',
            'description': f'Example {self.get_display_name()}',
        }

        for field in self.get_required_fields():
            config[field] = required_examples.get(field, f'example_{field}')

        # Добавляем значения по умолчанию
        config.update(self.get_optional_fields())

        return config

    def get_generator_info(self) -> Dict[str, Any]:
        """Возвращает полную информацию о генераторе"""
        return {
            'name': self.generator_name,
            'display_name': self.get_display_name(),
            'description': self.get_description(),
            'required_fields': self.get_required_fields(),
            'optional_fields': self.get_optional_fields(),
            'form_fields': self.get_form_fields(),
            'class_name': self.__class__.__name__,
            'module_name': self.__class__.__module__
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.generator_name}')"

    def __repr__(self) -> str:
        return self.__str__()
