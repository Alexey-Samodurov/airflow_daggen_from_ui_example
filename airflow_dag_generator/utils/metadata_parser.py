import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class MetadataParser:
    """Parses and manages metadata of DAG files.

    This class provides functionality to extract, scan, and manage metadata
    from Directed Acyclic Graph (DAG) files in a given folder. Includes methods
    to analyze generated DAGs, identify outdated templates, and fetch statistics.

    Attributes:
        METADATA_PATTERN (Pattern): Regular expression pattern to extract JSON metadata.
    """
    
    METADATA_PATTERN = re.compile(
        r'META:\s*(\{[^}]*\}\s*)', 
        re.MULTILINE | re.DOTALL
    )
    
    def __init__(self, dags_folder: Optional[str] = None):
        """
        Initializes the object with the given or default dags folder path.

        Attributes:
            dags_folder (str | None): Path to the directory containing DAGs. Defaults to the 'dags_folder'
            defined in Airflow configuration. If the configuration is unavailable or invalid, it creates
            a 'dags' folder in the current working directory or assigns '/tmp/dags' as fallback.

        Args:
            dags_folder (Optional[str]): Custom path to the DAGs folder. If not provided, the module tries
            to read the configuration from Airflow or set default paths automatically.
        """
        if dags_folder is None:
            try:
                from airflow.configuration import conf
                self.dags_folder = conf.get('core', 'dags_folder')
            except ImportError:
                # Fallback для разработки
                self.dags_folder = os.path.join(os.getcwd(), 'dags')
                # Если нет папки dags, создаем ее
                if not os.path.exists(self.dags_folder):
                    try:
                        os.makedirs(self.dags_folder)
                    except:
                        self.dags_folder = '/tmp/dags'
        else:
            self.dags_folder = dags_folder
    
    def parse_dag_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parses a DAG file and extracts metadata in JSON format.

        This method reads the content of the specified file, extracts a JSON-formatted metadata section,
        and parses it into a dictionary. Additional information about the file is appended to the metadata,
        such as file path, name, size, and modification time. If the metadata cannot be extracted or an
        error occurs, None is returned.

        Args:
            file_path (str): Path to the DAG file to be parsed.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing metadata if extraction and parsing succeed,
            otherwise None.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Читаем весь файл, но ограничиваем поиск первой частью
                content = f.read()
            
            # Ищем метаданные специальным методом
            metadata_json = self._extract_metadata_json(content)
            
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                    
                    # Добавляем информацию о файле
                    metadata['file_path'] = file_path
                    metadata['file_name'] = os.path.basename(file_path)
                    metadata['file_size'] = os.path.getsize(file_path)
                    metadata['file_mtime'] = os.path.getmtime(file_path)
                    
                    return metadata
                    
                except json.JSONDecodeError as e:
                    print(f"JSON decode error in {file_path}: {e}")
                    print(f"Problematic JSON: {metadata_json}")
            
        except Exception as e:
            print(f"Error parsing metadata from {file_path}: {e}")
        
        return None
    
    def _extract_metadata_json(self, content: str) -> Optional[str]:
        """
        Extracts JSON metadata from content if it starts with 'META:' and is a valid JSON object.

        Searches for a JSON object starting with 'META:' within the provided content. Ensures that the JSON is well-formed
        and enclosed by matching braces.

        Args:
            content (str): The content string to search for metadata.

        Returns:
            Optional[str]: Extracted JSON string if found, otherwise None.
        """
        # Ищем строку META: в первой части файла
        meta_pos = content.find('META:')
        if meta_pos == -1:
            return None
        
        # Начинаем поиск с позиции после META:
        start_pos = meta_pos + 5  # len('META:')
        
        # Пропускаем пробелы
        while start_pos < len(content) and content[start_pos].isspace():
            start_pos += 1
        
        # Должна начинаться с {
        if start_pos >= len(content) or content[start_pos] != '{':
            return None
        
        # Ищем соответствующую закрывающую скобку
        brace_count = 0
        current_pos = start_pos
        
        while current_pos < len(content):
            char = content[current_pos]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Нашли полный JSON
                    return content[start_pos:current_pos + 1]
            current_pos += 1
        
        return None
    
    def scan_generated_dags(self) -> List[Dict[str, Any]]:
        """
        Scans the specified DAGs folder for Python files and extracts metadata using the provided parser.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing the metadata for each valid DAG discovered.
        """
        generated_dags = []
        
        try:
            if not os.path.exists(self.dags_folder):
                print(f"DAGs folder does not exist: {self.dags_folder}")
                return []
                
            for dag_file in Path(self.dags_folder).rglob("*.py"):
                # Пропускаем системные файлы
                if dag_file.name.startswith('__'):
                    continue
                    
                metadata = self.parse_dag_file(str(dag_file))
                if metadata:
                    generated_dags.append(metadata)
        
        except Exception as e:
            print(f"Error scanning DAGs folder {self.dags_folder}: {e}")
        
        return generated_dags
    
    def find_dag_by_id(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """
        Find the DAG by its unique ID.

        This method searches for a directed acyclic graph (DAG) within the generated DAGs
        by matching the specified DAG ID.

        Args:
            dag_id: Unique identifier of the DAG.

        Returns:
            The DAG information as a dictionary if found. Returns None if not found.
        """
        for dag_info in self.scan_generated_dags():
            if dag_info.get('cfg', {}).get('dag_id') == dag_id:
                return dag_info
        return None
    
    def find_outdated_dags(self, current_template_versions: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Identifies outdated DAGs based on current template versions.

        Scans generated DAGs and compares their template versions with provided current template
        versions. If discrepancies are found, marks the DAGs as outdated and provides the current
        template version.

        Args:
            current_template_versions (Dict[str, str]): A dictionary mapping generator names to their
                current template versions.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing information about outdated DAGs,
                including their current template versions and whether they need an update.
        """
        outdated = []
        
        for dag_info in self.scan_generated_dags():
            generator_name = dag_info.get('gen')
            template_version = dag_info.get('ver')
            current_version = current_template_versions.get(generator_name)
            
            if current_version and template_version != current_version:
                dag_info['needs_update'] = True
                dag_info['current_template_version'] = current_version
                outdated.append(dag_info)
        
        return outdated
    
    def get_dag_statistics(self) -> Dict[str, Any]:
        """
        Collects and compiles statistical data about dynamically generated DAGs.

        Returns:
            Dict[str, Any]: A dictionary containing the statistics of generated DAGs, including:
                - Total number of generated DAGs.
                - Information grouped by generators with counts and versions.
                - Recent activity list containing the top 10 recently modified DAGs.

        Raises:
            KeyError: If any expected key is missing from the DAGs during processing.
        """
        dags = self.scan_generated_dags()
        
        stats = {
            'total_generated_dags': len(dags),
            'generators': {},
            'recent_activity': []
        }
        
        # Группируем по генераторам
        for dag in dags:
            gen_name = dag.get('gen', 'unknown')
            if gen_name not in stats['generators']:
                stats['generators'][gen_name] = {
                    'count': 0,
                    'versions': set()
                }
            
            stats['generators'][gen_name]['count'] += 1
            stats['generators'][gen_name]['versions'].add(dag.get('ver', 'unknown'))
        
        # Конвертируем sets в lists для JSON сериализации
        for gen_info in stats['generators'].values():
            gen_info['versions'] = list(gen_info['versions'])
        
        # Последние изменения (топ 10)
        sorted_dags = sorted(dags, key=lambda x: x.get('file_mtime', 0), reverse=True)[:10]
        stats['recent_activity'] = [
            {
                'dag_id': dag.get('cfg', {}).get('dag_id', 'unknown'),
                'generator': dag.get('gen', 'unknown'),
                'modified': datetime.fromtimestamp(dag.get('file_mtime', 0)).isoformat()
            }
            for dag in sorted_dags
        ]
        
        return stats


def create_metadata_string(generator_name: str, template_version: str, config: Dict[str, Any]) -> str:
    """
    Generates a metadata string in a specific format.

    This function generates a metadata string which includes the generator name,
    template version, and configuration details. The current timestamp is also included
    in the metadata. The metadata is returned as a structured JSON string prefixed
    with "META:".

    Args:
        generator_name (str): The name of the generator.
        template_version (str): The version of the template being used.
        config (Dict[str, Any]): Configuration values as a dictionary.

    Returns:
        str: A JSON-formatted string prefixed with "META:", containing the metadata.
    """
    # Создаем полные метаданные с ВСЕМИ параметрами формы
    metadata = {
        "gen": generator_name,
        "ver": template_version,
        "cfg": _preserve_all_config(config),  # ИСПРАВИЛИ: используем правильную функцию
        "ts": int(datetime.now().timestamp())
    }
    
    # Генерируем JSON
    return f"META:{json.dumps(metadata, separators=(',', ':'), ensure_ascii=False)}"


def _preserve_all_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preserves configuration by excluding web-form related fields.

    This function filters out certain predefined fields from a configuration
    dictionary typically related to web forms. The remaining fields, including
    empty strings, False, or 0, are preserved as is.

    Args:
        config (Dict[str, Any]): Configuration dictionary to process.

    Returns:
        Dict[str, Any]: Filtered configuration dictionary with web-form fields
        excluded.
    """
    # Исключаем только служебные поля, связанные с веб-формой
    exclude_fields = {
        'csrf_token', 
        'submit', 
        '_method',
        '_token'
    }
    
    preserved_config = {}
    
    for field, value in config.items():
        if field not in exclude_fields:
            # Сохраняем все значения как есть, включая пустые строки, False, 0, etc.
            preserved_config[field] = value
    
    return preserved_config
