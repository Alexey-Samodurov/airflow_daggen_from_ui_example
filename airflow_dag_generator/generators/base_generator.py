"""
Базовый класс для генераторов DAG
"""
import json
import logging
from datetime import datetime
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

    def get_template_version(self) -> str:
        """Возвращает версию шаблона генератора"""
        return getattr(self, 'template_version', '1.0.0')

    def get_default_values(self) -> Dict[str, Any]:
        """
        Возвращает значения по умолчанию для формы

        Returns:
            Словарь с значениями по умолчанию
        """
        # Объединяем с существующими optional_fields
        defaults = self.get_optional_fields().copy()

        # Добавляем базовые значения
        defaults.update({
            'owner': 'airflow',
            'retries': 1,
            'schedule_interval': '@daily'
        })

        return defaults

    # === ГЛАВНЫЙ МЕТОД ДЛЯ ГЕНЕРАЦИИ С МЕТАДАННЫМИ ===
    def generate_with_metadata(self, form_data: Dict[str, Any]) -> str:
        """
        Генерирует DAG с метаданными

        Args:
            form_data: Данные формы

        Returns:
            Код DAG'а с встроенными метаданными
        """
        # Валидируем конфигурацию
        validation_result = self.validate_config(form_data)
        if not validation_result['valid']:
            raise ValueError(f"Invalid configuration: {validation_result['errors']}")

        # Импортируем функцию создания метаданных из utils
        from ..utils.metadata_parser import create_metadata_string

        # Создаем строку метаданных со ВСЕМИ параметрами
        metadata_string = create_metadata_string(
            generator_name=self.generator_name,
            template_version=self.get_template_version(),
            config=form_data  # Передаем ПОЛНУЮ конфигурацию
        )

        # Генерируем базовый код
        dag_code = self.generate(form_data)

        # Встраиваем метаданные в докстринг
        return self._embed_metadata_in_docstring(dag_code, metadata_string)

    def _embed_metadata_in_docstring(self, dag_code: str, metadata_string: str) -> str:
        """
        Встраивает метаданные в докстринг DAG'а

        Args:
            dag_code: Исходный код DAG'а
            metadata_string: Строка с метаданными

        Returns:
            Код DAG'а с встроенными метаданными
        """
        import re

        # Ищем первый многострочный докстринг (обычно в начале файла)
        docstring_pattern = r'("""[\s\S]*?""")'
        match = re.search(docstring_pattern, dag_code)

        if match:
            original_docstring = match.group(1)

            # Создаем новый докстринг с метаданными
            new_docstring = original_docstring[:-3] + f"\n{metadata_string}\n" + '"""'

            # Заменяем оригинальный докстринг
            updated_code = dag_code.replace(original_docstring, new_docstring, 1)
            return updated_code
        else:
            # Если докстринг не найден, добавляем его в начало
            metadata_docstring = f'"""\nGenerated DAG\n\n{metadata_string}\n"""\n\n'
            return metadata_docstring + dag_code

    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===
    def update_existing_dag(self, file_path: str, new_form_data: Dict[str, Any]) -> str:
        """
        Обновляет существующий DAG новыми данными

        Args:
            file_path: Путь к существующему файлу DAG'а
            new_form_data: Новые данные формы

        Returns:
            Обновленный код DAG'а
        """
        # Просто перегенерируем DAG с новыми данными и метаданными
        return self.generate_with_metadata(new_form_data)

    def validate_form_data(self, form_data: Dict[str, Any]) -> List[str]:
        """
        Валидирует данные формы (расширенная версия validate_config)

        Args:
            form_data: Данные для валидации

        Returns:
            Список ошибок валидации (пустой список если ошибок нет)
        """
        # Используем существующий метод валидации
        validation_result = self.validate_config(form_data)
        errors = validation_result.get('errors', [])

        # Дополнительная валидация DAG ID
        dag_id = form_data.get('dag_id')
        if dag_id:
            if not dag_id.replace('_', '').replace('-', '').isalnum():
                errors.append('DAG ID должен содержать только буквы, цифры, подчеркивания и дефисы')

        return errors

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.generator_name}')"

    def __repr__(self) -> str:
        return self.__str__()
