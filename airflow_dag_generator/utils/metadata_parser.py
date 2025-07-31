"""
Парсер метаданных из DAG файлов
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class MetadataParser:
    """Парсер для извлечения метаданных из DAG файлов"""
    
    # Улучшенный паттерн для поиска полных метаданных JSON
    METADATA_PATTERN = re.compile(
        r'META:\s*(\{[^}]*\}\s*)', 
        re.MULTILINE | re.DOTALL
    )
    
    def __init__(self, dags_folder: Optional[str] = None):
        """
        Args:
            dags_folder: Путь к папке с DAG'ами. Если None, берется из Airflow конфига
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
        Извлекает метаданные из DAG файла
        
        Args:
            file_path: Путь к файлу DAG'а
            
        Returns:
            Словарь с метаданными или None, если метаданные не найдены
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
        Извлекает JSON метаданных из содержимого файла
        
        Args:
            content: Содержимое файла
            
        Returns:
            JSON строка с метаданными или None
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
        Сканирует все сгенерированные DAG'и в папке
        
        Returns:
            Список словарей с метаданными найденных DAG'ов
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
        Ищет DAG по его ID
        
        Args:
            dag_id: Идентификатор DAG'а
            
        Returns:
            Метаданные DAG'а или None, если не найден
        """
        for dag_info in self.scan_generated_dags():
            if dag_info.get('cfg', {}).get('dag_id') == dag_id:
                return dag_info
        return None
    
    def find_outdated_dags(self, current_template_versions: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Находит DAG'и с устаревшими версиями шаблонов
        
        Args:
            current_template_versions: Словарь {generator_name: current_version}
            
        Returns:
            Список DAG'ов, требующих обновления
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
        Получает статистику по сгенерированным DAG'ам
        
        Returns:
            Словарь со статистикой
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
    Создает строку метаданных для встраивания в докстринг
    
    Args:
        generator_name: Имя генератора
        template_version: Версия шаблона
        config: Конфигурация DAG'а
        
    Returns:
        Строка с метаданными в формате META:{...}
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
    Сохраняет ВСЕ параметры формы в метаданных без исключений
    
    Args:
        config: Полная конфигурация из формы
        
    Returns:
        Полная конфигурация со всеми параметрами
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
