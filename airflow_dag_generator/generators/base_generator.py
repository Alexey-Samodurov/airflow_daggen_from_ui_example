import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class BaseGenerator(ABC):
    """Упрощенный базовый абстрактный класс для всех генераторов DAG"""

    def __init__(self, generator_name: str):
        """
        Инициализация базового генератора

        Args:
            generator_name: Уникальное имя генератора (например, 'hello_world')
        """
        self.generator_name = generator_name

    @abstractmethod
    def get_display_name(self) -> str:
        """Возвращает человекочитаемое название генератора"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Возвращает описание генератора"""
        pass

    @abstractmethod
    def get_form_fields(self) -> List[Dict[str, Any]]:
        """
        Возвращает конфигурацию полей для веб-формы

        Returns:
            Список словарей с конфигурацией полей:
            [
                {
                    'name': 'field_name',
                    'type': 'text|select|textarea|checkbox|number|email',
                    'label': 'Human readable label',
                    'required': True|False,
                    'default_value': 'default value',
                    'placeholder': 'placeholder text',
                    'options': [{'value': 'val', 'label': 'Label'}]  # для select
                }
            ]
        """
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

    # === МЕТОДЫ С БАЗОВОЙ РЕАЛИЗАЦИЕЙ ===

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Базовая валидация конфигурации

        Returns:
            Dict с ключами: valid (bool), errors (List[str]), warnings (List[str])
        """
        errors = []
        warnings = []

        # Получаем обязательные поля из конфигурации формы
        required_fields = [field['name'] for field in self.get_form_fields() if field.get('required')]

        # Проверяем обязательные поля
        for field_name in required_fields:
            value = config.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"Поле '{field_name}' обязательно для заполнения")

        # Базовые проверки DAG ID (если есть)
        dag_id = config.get('dag_id', '').strip()
        if dag_id:
            if not dag_id.replace('_', '').replace('-', '').isalnum():
                errors.append("DAG ID должен содержать только буквы, цифры, подчеркивания и дефисы")
            if len(dag_id) > 200:
                errors.append("DAG ID слишком длинный (максимум 200 символов)")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def get_generator_info(self) -> Dict[str, Any]:
        """Возвращает информацию о генераторе для API"""
        return {
            'name': self.generator_name,
            'display_name': self.get_display_name(),
            'description': self.get_description(),
            'fields': self.get_form_fields(),
            'validation_rules': self._get_validation_rules()
        }

    def _get_validation_rules(self) -> Dict[str, Any]:
        """Извлекает правила валидации из конфигурации полей"""
        rules = {}
        for field in self.get_form_fields():
            field_rules = {}

            if field.get('required'):
                field_rules['required'] = True

            if field.get('pattern'):
                field_rules['pattern'] = field['pattern']

            if field.get('min'):
                field_rules['min'] = field['min']

            if field.get('max'):
                field_rules['max'] = field['max']

            if field_rules:
                rules[field['name']] = field_rules

        return rules

    def generate_with_metadata(self, form_data: Dict[str, Any]) -> str:
        """
        Generates code with metadata embedded in the first docstring.

        This method generates the main code using provided form data, creates a metadata
        string using generator details and form data, and embeds the metadata string into
        the first docstring of the generated code.

        Args:
            form_data (Dict[str, Any]): Configuration data for code generation.

        Returns:
            str: Generated code with metadata embedded in the first docstring.
        """
        # Генерируем основной код
        dag_code = self.generate(form_data)
        
        # Создаем метаданные
        from airflow_dag_generator.utils.metadata_parser import create_metadata_string
        metadata_string = create_metadata_string(
            generator_name=self.generator_name,
            template_version=getattr(self, 'template_version', '1.0.0'),
            config=form_data
        )
        
        # Встраиваем метаданные в первый docstring
        return self._embed_metadata_in_docstring(dag_code, metadata_string)

    def _embed_metadata_in_docstring(self, dag_code: str, metadata_string: str) -> str:
        """
        Appends metadata string into the first docstring found in the provided DAG code.

        Attempts to inject a metadata string into an existing docstring within the DAG code. If no
        docstring is found, it prepends a new one containing the metadata string.

        Args:
            dag_code (str): The source code of the DAG as a string.
            metadata_string (str): Metadata to embed into the docstring.

        Returns:
            str: The updated DAG code containing the metadata within the docstring or prepending a
            new one.
        """
        if '"""' not in dag_code:
            # Если нет docstring, добавляем в начало файла
            return f'"""\n{metadata_string}\n"""\n\n{dag_code}'
        
        # Ищем конец первого docstring
        first_start = dag_code.find('"""')
        if first_start == -1:
            return dag_code
            
        first_end = dag_code.find('"""', first_start + 3)
        if first_end == -1:
            return dag_code
        
        # Вставляем метаданные перед закрывающими кавычками
        return (dag_code[:first_end] + 
                f"\n\n{metadata_string}\n" + 
                dag_code[first_end:])

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.generator_name}')"

    def __repr__(self) -> str:
        return self.__str__()
