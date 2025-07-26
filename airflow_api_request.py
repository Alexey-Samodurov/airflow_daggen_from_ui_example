import requests
from requests.auth import HTTPBasicAuth
import time
import statistics
from typing import Dict, Any, List, Tuple

class AirflowBenchmarkClient:
    def __init__(self, base_url: str, username: str, password: str):
        """
        Инициализация клиента для бенчмарка Airflow API
        
        Args:
            base_url: Базовый URL Airflow
            username: Имя пользователя для аутентификации
            password: Пароль для аутентификации
        """
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        
    def get_dag_info(self, dag_id: str) -> Dict[str, Any]:
        """
        Получение информации о конкретном DAG
        
        Args:
            dag_id: ID DAG для получения информации
            
        Returns:
            Словарь с информацией о DAG
        """
        url = f"{self.base_url}/api/v1/dags/{dag_id}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении информации о DAG {dag_id}: {e}")
            return {}
    
    def pause_dag(self, dag_id: str) -> Tuple[bool, float]:
        """
        Приостановка (выключение) DAG
        
        Args:
            dag_id: ID DAG для приостановки
            
        Returns:
            Tuple (успешность операции, время выполнения в секундах)
        """
        url = f"{self.base_url}/api/v1/dags/{dag_id}"
        data = {"is_paused": True}
        
        start_time = time.time()
        try:
            response = self.session.patch(url, json=data)
            end_time = time.time()
            response.raise_for_status()
            return True, end_time - start_time
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            print(f"Ошибка при приостановке DAG {dag_id}: {e}")
            return False, end_time - start_time
    
    def unpause_dag(self, dag_id: str) -> Tuple[bool, float]:
        """
        Возобновление (включение) DAG
        
        Args:
            dag_id: ID DAG для возобновления
            
        Returns:
            Tuple (успешность операции, время выполнения в секундах)
        """
        url = f"{self.base_url}/api/v1/dags/{dag_id}"
        data = {"is_paused": False}
        
        start_time = time.time()
        try:
            response = self.session.patch(url, json=data)
            end_time = time.time()
            response.raise_for_status()
            return True, end_time - start_time
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            print(f"Ошибка при возобновлении DAG {dag_id}: {e}")
            return False, end_time - start_time
    
    def benchmark_dag_operations(self, dag_id: str, iterations: int = 1000) -> Dict[str, Any]:
        """
        Бенчмарк операций включения/выключения DAG
        
        Args:
            dag_id: ID DAG для тестирования
            iterations: Количество итераций для каждой операции
            
        Returns:
            Словарь со статистикой времени выполнения
        """
        print(f"Запуск бенчмарка для DAG: {dag_id}")
        print(f"Количество итераций: {iterations}")
        print("-" * 50)
        
        # Получаем текущее состояние DAG
        dag_info = self.get_dag_info(dag_id)
        if not dag_info:
            return {"error": "Не удалось получить информацию о DAG"}
        
        initial_state = dag_info.get('is_paused', True)
        print(f"Начальное состояние DAG (приостановлен): {initial_state}")
        
        pause_times = []
        unpause_times = []
        failed_operations = 0
        
        for i in range(iterations):
            # Прогресс
            if (i + 1) % 100 == 0:
                print(f"Выполнено итераций: {i + 1}/{iterations}")
            
            # Включение DAG (unpause)
            success, duration = self.unpause_dag(dag_id)
            if success:
                unpause_times.append(duration)
            else:
                failed_operations += 1
            
            # Небольшая задержка между операциями
            time.sleep(0.01)
            
            # Выключение DAG (pause)
            success, duration = self.pause_dag(dag_id)
            if success:
                pause_times.append(duration)
            else:
                failed_operations += 1
            
            # Небольшая задержка между операциями
            time.sleep(0.01)
        
        # Возвращаем DAG в исходное состояние
        if initial_state:
            self.pause_dag(dag_id)
        else:
            self.unpause_dag(dag_id)
        
        # Вычисляем статистики
        return self._calculate_statistics(pause_times, unpause_times, failed_operations, iterations)
    
    def _calculate_statistics(self, pause_times: List[float], unpause_times: List[float], 
                            failed_operations: int, iterations: int) -> Dict[str, Any]:
        """
        Вычисление статистик времени выполнения
        """
        def get_stats(times: List[float]) -> Dict[str, float]:
            if not times:
                return {"min": 0, "max": 0, "mean": 0, "median": 0, "std": 0}
            
            return {
                "min": min(times),
                "max": max(times),
                "mean": statistics.mean(times),
                "median": statistics.median(times),
                "std": statistics.stdev(times) if len(times) > 1 else 0
            }
        
        pause_stats = get_stats(pause_times)
        unpause_stats = get_stats(unpause_times)
        
        return {
            "iterations": iterations,
            "failed_operations": failed_operations,
            "success_rate": ((len(pause_times) + len(unpause_times)) / (iterations * 2)) * 100,
            "pause_operations": {
                "count": len(pause_times),
                "times_ms": {k: v * 1000 for k, v in pause_stats.items()},
                "times_sec": pause_stats
            },
            "unpause_operations": {
                "count": len(unpause_times),
                "times_ms": {k: v * 1000 for k, v in unpause_stats.items()},
                "times_sec": unpause_stats
            },
            "total_time": sum(pause_times) + sum(unpause_times)
        }
    
    def print_benchmark_results(self, results: Dict[str, Any]) -> None:
        """
        Вывод результатов бенчмарка в читаемом формате
        """
        if "error" in results:
            print(f"Ошибка: {results['error']}")
            return
        
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТЫ БЕНЧМАРКА")
        print("=" * 60)
        
        print(f"Общее количество итераций: {results['iterations']}")
        print(f"Неудачных операций: {results['failed_operations']}")
        print(f"Процент успешных операций: {results['success_rate']:.2f}%")
        print(f"Общее время выполнения: {results['total_time']:.2f} сек")
        
        print("\n" + "-" * 30)
        print("ОПЕРАЦИИ ПРИОСТАНОВКИ (PAUSE)")
        print("-" * 30)
        pause_stats = results['pause_operations']
        print(f"Количество операций: {pause_stats['count']}")
        print(f"Минимальное время: {pause_stats['times_ms']['min']:.2f} мс")
        print(f"Максимальное время: {pause_stats['times_ms']['max']:.2f} мс")
        print(f"Среднее время: {pause_stats['times_ms']['mean']:.2f} мс")
        print(f"Медианное время: {pause_stats['times_ms']['median']:.2f} мс")
        print(f"Стандартное отклонение: {pause_stats['times_ms']['std']:.2f} мс")
        
        print("\n" + "-" * 30)
        print("ОПЕРАЦИИ ВОЗОБНОВЛЕНИЯ (UNPAUSE)")
        print("-" * 30)
        unpause_stats = results['unpause_operations']
        print(f"Количество операций: {unpause_stats['count']}")
        print(f"Минимальное время: {unpause_stats['times_ms']['min']:.2f} мс")
        print(f"Максимальное время: {unpause_stats['times_ms']['max']:.2f} мс")
        print(f"Среднее время: {unpause_stats['times_ms']['mean']:.2f} мс")
        print(f"Медианное время: {unpause_stats['times_ms']['median']:.2f} мс")
        print(f"Стандартное отклонение: {unpause_stats['times_ms']['std']:.2f} мс")

def main():
    """
    Основная функция для запуска бенчмарка
    """
    # Настройки подключения к Airflow
    AIRFLOW_URL = "https://airflow-kube02008.samokat.io"
    USERNAME = "alsamodurov"  # Замените на ваше имя пользователя
    PASSWORD = ""  # Замените на ваш пароль
    
    DAG_ID = "cmn_push_provider"
    ITERATIONS = 1000
    
    # Создание клиента
    client = AirflowBenchmarkClient(AIRFLOW_URL, USERNAME, PASSWORD)
    
    # Проверяем существование DAG
    dag_info = client.get_dag_info(DAG_ID)
    if not dag_info:
        print(f"DAG '{DAG_ID}' не найден или недоступен")
        return
    
    print(f"DAG '{DAG_ID}' найден:")
    print(f"- Описание: {dag_info.get('description', 'Нет описания')}")
    print(f"- Активный: {dag_info.get('is_active', False)}")
    print(f"- Приостановлен: {dag_info.get('is_paused', True)}")
    
    # Запуск бенчмарка
    start_time = time.time()
    results = client.benchmark_dag_operations(DAG_ID, ITERATIONS)
    end_time = time.time()
    
    print(f"\nОбщее время выполнения бенчмарка: {end_time - start_time:.2f} сек")
    
    # Вывод результатов
    client.print_benchmark_results(results)
    
    # Сохранение результатов в файл
    import json
    with open(f'airflow_benchmark_{DAG_ID}_{ITERATIONS}.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nРезультаты сохранены в файл: airflow_benchmark_{DAG_ID}_{ITERATIONS}.json")

if __name__ == "__main__":
    main()
