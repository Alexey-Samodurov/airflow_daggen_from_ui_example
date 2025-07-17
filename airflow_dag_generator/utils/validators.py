"""
Валидаторы для проверки DAG'ов
"""
import ast
import logging

logger = logging.getLogger(__name__)


def validate_dag_syntax(dag_content: str) -> dict:
    """
    Валидация синтаксиса DAG'а
    
    Args:
        dag_content: Содержимое файла DAG'а
        
    Returns:
        dict: {'valid': bool, 'error': str}
    """
    try:
        # Пытаемся распарсить код как AST
        ast.parse(dag_content)
        logger.info("Синтаксис DAG'а валиден")
        return {'valid': True, 'error': None}
    except SyntaxError as e:
        error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
        logger.error(f"Ошибка синтаксиса: {error_msg}")
        return {'valid': False, 'error': error_msg}
    except Exception as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(f"Ошибка валидации: {error_msg}")
        return {'valid': False, 'error': error_msg}


def validate_dag_id(dag_id: str) -> dict:
    """
    Валидация ID DAG'а
    
    Args:
        dag_id: Идентификатор DAG'а
        
    Returns:
        dict: {'valid': bool, 'error': str}
    """
    if not dag_id:
        return {'valid': False, 'error': 'DAG ID cannot be empty'}
    
    if not dag_id.replace('_', '').replace('-', '').isalnum():
        return {'valid': False, 'error': 'DAG ID should contain only letters, numbers, hyphens and underscores'}
    
    if len(dag_id) > 200:
        return {'valid': False, 'error': 'DAG ID is too long (max 200 characters)'}
    
    return {'valid': True, 'error': None}
