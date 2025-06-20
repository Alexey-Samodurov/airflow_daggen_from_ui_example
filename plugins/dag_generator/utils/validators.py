import ast
import sys
from typing import Dict, Any


def validate_dag_syntax(dag_content: str) -> Dict[str, Any]:
    """
    Валидирует синтаксис сгенерированного DAG'а
    
    Args:
        dag_content (str): Код DAG'а для валидации
        
    Returns:
        dict: Результат валидации с полями 'valid' и 'error'
    """
    try:
        # Пытаемся парсить код как AST
        ast.parse(dag_content)
        
        # Дополнительная проверка - компиляция
        compile(dag_content, '<string>', 'exec')
        
        return {
            'valid': True,
            'error': None
        }
        
    except SyntaxError as e:
        return {
            'valid': False,
            'error': f"Syntax Error at line {e.lineno}: {e.msg}"
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error': f"Compilation Error: {str(e)}"
        }


def validate_dag_id(dag_id: str) -> Dict[str, Any]:
    """
    Валидирует корректность DAG ID
    
    Args:
        dag_id (str): ID DAG'а для валидации
        
    Returns:
        dict: Результат валидации
    """
    if not dag_id:
        return {
            'valid': False,
            'error': 'DAG ID cannot be empty'
        }
    
    # Проверяем, что содержит только допустимые символы
    if not dag_id.replace('_', '', 1).replace('-', '', 1).isalnum():
        return {
            'valid': False,
            'error': 'DAG ID can only contain letters, numbers, underscores and hyphens'
        }
    
    # Проверяем длину
    if len(dag_id) > 250:
        return {
            'valid': False,
            'error': 'DAG ID is too long (max 250 characters)'
        }
    
    return {
        'valid': True,
        'error': None
    }
