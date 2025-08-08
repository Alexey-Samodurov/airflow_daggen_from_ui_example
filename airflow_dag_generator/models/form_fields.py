from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class FieldType(str, Enum):
    """
    Enumeration for different types of form fields.

    FieldType class defines various types of fields that can be used in a form.
    Each field type represents a specific input method or data type.
    """
    TEXT = "text"
    EMAIL = "email"
    TEXTAREA = "textarea"
    SELECT = "select"
    CHECKBOX = "checkbox"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    URL = "url"
    MULTISELECT = "multiselect"
    HIDDEN = "hidden"
    PASSWORD = "password"


class SelectOption(BaseModel):
    """
    Represents a selectable option for a dropdown or similar UI element.

    This class encapsulates the details of an option, including its underlying value, display text, and optional label.
    """
    value: str
    text: str
    label: Optional[str] = None

class FormField(BaseModel):
    """
    Represents a form field with specific attributes and validations.

    This class is used to define structure, properties, and behavior for a form field. It includes
    attributes like name, type, label, default value, validation patterns, range limitations, etc.,
    and allows conversion to a dictionary format for compatibility with other systems.

    Attributes:
        name: The name of the form field.
        type: The type of the form field, defined by FieldType.
        label: The human-readable label for the form field.
        required: Determines if the field is mandatory. Defaults to False.
        default_value: The default value of the field, if any.
        placeholder: Placeholder text to display in the field.
        help_text: Additional explanatory text for the field.
        pattern: Regular expression for validating the field's input.
        min: Minimum value for numeric fields.
        max: Maximum value for numeric fields.
        step: Increment step for numeric fields.
        options: List of selectable options for dropdown or similar fields.
        rows: Number of rows for textarea-type fields.

    Methods:
        to_dict:
            Converts the instance to a dictionary, excluding fields with None values. Allows
            compatibility with an existing codebase by ensuring the options attribute is
            properly serialized.
    """
    name: str
    type: FieldType
    label: str
    required: bool = False
    default_value: Optional[Union[str, int, float, bool]] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    pattern: Optional[str] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None
    options: Optional[List[SelectOption]] = None
    rows: Optional[int] = None  # для textarea

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the object to a dictionary representation, preserving specified serialization rules.

        Returns:
            Dict[str, Any]: A dictionary representation of the object, with serialization adjustments such as
            renamed keys for JavaScript compatibility.
        """
        result = self.model_dump(exclude_none=True)
        if self.options:
            result['options'] = [opt.model_dump() for opt in self.options]

        if 'default_value' in result:
            result['default'] = result.pop('default_value')

        return result
