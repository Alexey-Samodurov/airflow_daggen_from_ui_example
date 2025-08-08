import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel, ValidationError, Field, create_model

from airflow_dag_generator.models.form_fields import FormField, FieldType

logger = logging.getLogger(__name__)


class BaseGenerator(ABC):
    """
    Abstract base class for DAG code generators.

    This class defines the structure for custom DAG generators which can
    generate DAG code, provide form fields, validate configurations, and
    return metadata about the generator. It includes helper methods for
    display name and description customization.
    """

    def __init__(self, generator_name: str, display_name: Optional[str] = None, description: Optional[str] = None):
        self.generator_name = generator_name
        self._display_name = display_name
        self._description = description
        self.template_version = "1.0.0"

    @abstractmethod
    def generate(self, form_data: Dict[str, Any]) -> str:
        """
        Abstract method for generating a string output based on provided form data.

        This method should be implemented by subclasses to process input data and
        generate a corresponding string representation.

        Args:
            form_data (Dict[str, Any]): Input data required for string generation.

        Returns:
            str: The generated string output.

        Raises:
            NotImplementedError: If the method is called directly without an implementation.
        """
        pass


    def get_display_name(self) -> str:
        """
        Returns the display name based on the available attributes.

        If a display name is explicitly set, it returns that value. Otherwise, it formats and returns the
        generator name with underscores replaced by spaces and capitalized accordingly.

        Returns:
            str: The formatted display name or the explicitly set display name.
        """
        if self._display_name:
            return self._display_name
        return self.generator_name.replace('_', ' ').title()

    def get_description(self) -> str:
        """
        Returns the description of the DAG generator.

        The description is fetched from the internal state if available, otherwise it
        returns a default description including the display name of the generator.

        Returns:
            str: The description of the DAG generator.
        """
        if self._description:
            return self._description
        return f"DAG generator: {self.get_display_name()}"

    def get_form_fields(self) -> List[FormField]:
        """
        Returns a list of all form fields.

        This method retrieves all the form fields associated
        with the form. The form fields define individual
        components of a form such as text boxes, checkboxes,
        or buttons.

        Returns:
            List[FormField]: A list of form field objects representing
            components of the form.
        """
        return []

    def get_config_model(self) -> Type[BaseModel]:
        """
        Generates a dynamic Pydantic BaseModel based on form fields.

        This method inspects the form fields associated with the current generator
        to dynamically construct a Pydantic model. It maps form field types to
        corresponding Python types, applies validation constraints such as minimum,
        maximum values, patterns, and determines whether fields are required or
        optional.

        Returns:
            Type[BaseModel]: A Pydantic model dynamically constructed based on
            the configuration of form fields.

        Raises:
            ValueError: If an unsupported field type is encountered or required parameters
            are missing while building the model.
        """
        form_fields = self.get_form_fields()
        if not form_fields:
            return create_model(
                f'{self.generator_name.title()}Config',
                dag_id=(str, Field(..., description="DAG identifier"))
            )

        # Создаем поля для Pydantic модели на основе FormField
        model_fields = {}

        for field in form_fields:
            # Определяем тип на основе типа поля
            if field.type == FieldType.CHECKBOX:
                field_type = bool
            elif field.type == FieldType.NUMBER:
                field_type = int  # или float, если нужно
            else:
                field_type = str  # Большинство полей - строки

            # Создаем Field с параметрами
            field_kwargs = {'description': field.help_text or field.label}

            # Добавляем ограничения
            if field.pattern and field_type == str:
                field_kwargs['pattern'] = field.pattern

            if field.min is not None and field_type in (int, float):
                field_kwargs['ge'] = field.min

            if field.max is not None and field_type in (int, float):
                field_kwargs['le'] = field.max

            # Определяем обязательность и значения по умолчанию
            if field.required:
                if field.default_value is not None:
                    model_fields[field.name] = (field_type, Field(default=field.default_value, **field_kwargs))
                else:
                    model_fields[field.name] = (field_type, Field(..., **field_kwargs))
            else:
                default_val = field.default_value
                model_fields[field.name] = (Optional[field_type], Field(default=default_val, **field_kwargs))

        # Создаем динамическую Pydantic модель
        model_name = f'{self.generator_name.title()}Config'
        return create_model(model_name, **model_fields)

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates a configuration dictionary against a predefined data model.

        This method attempts to validate the provided configuration dictionary using
        the structured data model defined by `get_config_model`. It returns the
        validated configuration if successful or details of validation errors if
        validation fails.

        Args:
            config (Dict[str, Any]): The configuration data to be validated.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - valid (bool): Whether the configuration is valid.
                - errors (List[str]): Validation error messages, if any.
                - warnings (List[str]): Validation warnings, if any.
                - validated_data (Any): Validated data after applying the model (if valid).
        """
        try:
            config_model = self.get_config_model()
            validated_config = config_model(**config)
            return {
                'valid': True,
                'errors': [],
                'warnings': [],
                'validated_data': validated_config.model_dump()
            }
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field_name = ' -> '.join(str(loc) for loc in error['loc'])
                errors.append(f"{field_name}: {error['msg']}")

            return {
                'valid': False,
                'errors': errors,
                'warnings': []
            }

    def get_validated_config(self, form_data: Dict[str, Any]) -> BaseModel:
        """
        Validates and converts form data into a configuration model instance.

        Args:
            form_data (Dict[str, Any]): Input data to validate and convert.

        Returns:
            BaseModel: An instance of the configuration model with validated data.

        Raises:
            ValueError: If the form data fails validation.
        """
        validation_result = self.validate_config(form_data)
        if not validation_result['valid']:
            raise ValueError(f"Invalid configuration: {validation_result['errors']}")

        config_model = self.get_config_model()
        return config_model(**form_data)

    def get_generator_info(self) -> Dict[str, Any]:
        """
        Retrieves detailed information about the generator.

        Returns:
            Dict[str, Any]: A dictionary containing the generator's name, display
            name, description, form fields as dictionaries, and validation rules.
        """
        form_fields = self.get_form_fields()
        return {
            'name': self.generator_name,
            'display_name': self.get_display_name(),
            'description': self.get_description(),
            'fields': [field.to_dict() for field in form_fields],
            'validation_rules': self._get_validation_rules_from_fields()
        }

    def _get_validation_rules_from_fields(self) -> Dict[str, Any]:
        """
        Extracts validation rules from form fields and organizes them in a dictionary.

        Returns:
            Dict[str, Any]: A dictionary where keys are field names and values are their validation rules.
        """
        rules = {}
        for field in self.get_form_fields():
            field_rules = {}

            if field.required:
                field_rules['required'] = True
            if field.pattern:
                field_rules['pattern'] = field.pattern
            if field.min is not None:
                field_rules['min'] = field.min
            if field.max is not None:
                field_rules['max'] = field.max

            if field_rules:
                rules[field.name] = field_rules

        return rules

    def generate_with_metadata(self, form_data: Dict[str, Any]) -> str:
        """
        Generates DAG code with embedded metadata.

        Creates a DAG code string based on provided form data, embeds metadata into the
        code using the generator's name, template version, and configuration.

        Args:
            form_data (Dict[str, Any]): Input configuration data for the DAG generation.

        Returns:
            str: The generated DAG code with embedded metadata.
        """
        dag_code = self.generate(form_data)

        from airflow_dag_generator.utils.metadata_parser import create_metadata_string
        metadata_string = create_metadata_string(
            generator_name=self.generator_name,
            template_version=getattr(self, 'template_version', '1.0.0'),
            config=form_data
        )

        return self._embed_metadata_in_docstring(dag_code, metadata_string)

    def _embed_metadata_in_docstring(self, dag_code: str, metadata_string: str) -> str:
        """
        Embeds metadata within a Python multi-line docstring in the provided code block.

        This method inserts metadata into the first encountered docstring in the
        provided DAG code. If no docstring exists, a new one is created at the top of
        the code. Metadata is always placed within triple double quotes.

        Args:
            dag_code (str): The source code to embed metadata into.
            metadata_string (str): The metadata content to embed inside the docstring.

        Returns:
            str: The modified source code with embedded metadata.
        """
        if '"""' not in dag_code:
            return f'"""\n{metadata_string}\n"""\n\n{dag_code}'

        first_start = dag_code.find('"""')
        if first_start == -1:
            return dag_code

        first_end = dag_code.find('"""', first_start + 3)
        if first_end == -1:
            return dag_code

        return (dag_code[:first_end] +
                f"\n\n{metadata_string}\n" +
                dag_code[first_end:])

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.generator_name}')"

    def __repr__(self) -> str:
        return self.__str__()
